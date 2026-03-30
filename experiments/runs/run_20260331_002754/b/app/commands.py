"""CLI commands for AgentHub management."""

import click
from flask import Blueprint
from flask.cli import with_appcontext
import json
from datetime import datetime, timedelta
from decimal import Decimal

from app import db
from app.models.user import User
from app.models.agent import Agent, AgentVersion, AgentCategory, AgentStatus, Tag
from app.models.subscription import Plan, PlanType, Subscription, BillingAccount
from app.models.agent_run import AgentRun, AgentRunStatus
from app.integrations.agno import AgentExecutor


@click.group()
def cli():
    """AgentHub CLI commands."""
    pass


@cli.command('seed-db')
@with_appcontext
def seed_db():
    """Seed database with demo data."""
    click.echo('Seeding database with demo data...')
    
    # Create default plans
    plans = create_default_plans()
    click.echo(f'Created {len(plans)} plans')
    
    # Create demo user
    demo_user = create_demo_user()
    click.echo(f'Created demo user: {demo_user.email}')
    
    # Create 6 marketplace agents
    agents = create_marketplace_agents(demo_user)
    click.echo(f'Created {len(agents)} marketplace agents')
    
    # Create some tags
    tags = create_tags()
    click.echo(f'Created {len(tags)} tags')
    
    # Associate tags with agents
    associate_tags_with_agents(agents, tags)
    click.echo('Associated tags with agents')
    
    # Create some agent runs
    runs = create_demo_agent_runs(demo_user, agents[:3])
    click.echo(f'Created {len(runs)} demo agent runs')
    
    db.session.commit()
    click.echo('Database seeding completed!')


@cli.command('create-admin')
@click.option('--email', prompt='Admin email', help='Admin email address')
@click.option('--username', prompt='Admin username', help='Admin username')
@click.option('--password', prompt='Admin password', hide_input=True, 
              confirmation_prompt=True, help='Admin password')
@with_appcontext
def create_admin(email, username, password):
    """Create an admin user."""
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        click.echo(f'User with email {email} already exists')
        return
    
    if User.query.filter_by(username=username).first():
        click.echo(f'User with username {username} already exists')
        return
    
    # Create admin user
    admin = User(
        email=email,
        username=username,
        password=password,
        first_name='Admin',
        last_name='User',
        is_admin=True
    )
    
    # Create billing account
    billing_account = BillingAccount(user=admin)
    
    # Assign pro plan
    pro_plan = Plan.query.filter_by(type=PlanType.PRO).first()
    if pro_plan:
        subscription = Subscription(
            user=admin,
            plan=pro_plan,
            status='active',
            billing_cycle='monthly',
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
    
    db.session.add(admin)
    db.session.commit()
    
    click.echo(f'Admin user {username} created successfully')


@cli.command('run-worker')
@with_appcontext
def run_worker():
    """Run Celery worker."""
    from app.tasks import celery_app
    
    click.echo('Starting Celery worker...')
    
    # Start worker with appropriate configuration
    worker = celery_app.Worker(
        include=['app.tasks.agent_tasks'],
        loglevel='INFO',
        hostname='agenthub-worker@%h'
    )
    
    worker.start()


def create_default_plans():
    """Create default subscription plans."""
    plans_data = [
        {
            'name': 'Free',
            'type': PlanType.FREE,
            'description': 'Free plan for getting started',
            'price_monthly_usd': Decimal('0.00'),
            'price_yearly_usd': Decimal('0.00'),
            'max_agents': 3,
            'max_runs_per_day': 10,
            'max_team_members': 1,
            'features': json.dumps([
                '3 agents maximum',
                '10 runs per day',
                'Basic analytics',
                'Community support'
            ])
        },
        {
            'name': 'Basic',
            'type': PlanType.BASIC,
            'description': 'Basic plan for individual users',
            'price_monthly_usd': Decimal('19.99'),
            'price_yearly_usd': Decimal('199.99'),  # ~$16.67/month
            'max_agents': 10,
            'max_runs_per_day': 100,
            'max_team_members': 1,
            'features': json.dumps([
                '10 agents maximum',
                '100 runs per day',
                'Advanced analytics',
                'Email support',
                'API access'
            ]),
            'stripe_price_id_monthly': 'price_basic_monthly',
            'stripe_price_id_yearly': 'price_basic_yearly'
        },
        {
            'name': 'Pro',
            'type': PlanType.PRO,
            'description': 'Professional plan for power users',
            'price_monthly_usd': Decimal('49.99'),
            'price_yearly_usd': Decimal('499.99'),  # ~$41.67/month
            'max_agents': 50,
            'max_runs_per_day': 1000,
            'max_team_members': 5,
            'features': json.dumps([
                '50 agents maximum',
                '1000 runs per day',
                'Advanced analytics',
                'Priority support',
                'Custom domains',
                'Team collaboration',
                'Advanced API access'
            ]),
            'stripe_price_id_monthly': 'price_pro_monthly',
            'stripe_price_id_yearly': 'price_pro_yearly'
        },
        {
            'name': 'Team',
            'type': PlanType.TEAM,
            'description': 'Team plan for collaboration',
            'price_monthly_usd': Decimal('99.99'),
            'price_yearly_usd': Decimal('999.99'),  # ~$83.33/month
            'max_agents': 200,
            'max_runs_per_day': 5000,
            'max_team_members': 20,
            'features': json.dumps([
                '200 agents maximum',
                '5000 runs per day',
                'Advanced analytics',
                '24/7 phone support',
                'Custom domains',
                'Team management',
                'SSO integration',
                'Audit logs'
            ]),
            'stripe_price_id_monthly': 'price_team_monthly',
            'stripe_price_id_yearly': 'price_team_yearly'
        }
    ]
    
    plans = []
    for plan_data in plans_data:
        # Check if plan already exists
        existing = Plan.query.filter_by(type=plan_data['type']).first()
        if existing:
            plans.append(existing)
            continue
        
        plan = Plan(**plan_data)
        db.session.add(plan)
        plans.append(plan)
    
    return plans


def create_demo_user():
    """Create demo user for testing."""
    # Check if demo user already exists
    demo_user = User.query.filter_by(email='demo@agenthub.com').first()
    if demo_user:
        return demo_user
    
    demo_user = User(
        email='demo@agenthub.com',
        username='demo_user',
        password='demopassword123',
        first_name='Demo',
        last_name='User',
        bio='Demo user for testing AgentHub features',
        avatar_url='https://api.dicebear.com/7.x/avataaars/svg?seed=demo'
    )
    
    # Create billing account
    billing_account = BillingAccount(user=demo_user)
    
    # Assign basic plan
    basic_plan = Plan.query.filter_by(type=PlanType.BASIC).first()
    if basic_plan:
        subscription = Subscription(
            user=demo_user,
            plan=basic_plan,
            status='active',
            billing_cycle='monthly',
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
    
    db.session.add(demo_user)
    return demo_user


def create_marketplace_agents(owner):
    """Create 6 marketplace agents as required."""
    agents_data = [
        {
            'name': 'Content Summarizer',
            'slug': 'content-summarizer',
            'description': 'AI agent that summarizes long articles, documents, and research papers into concise overviews. Perfect for researchers, students, and professionals who need to digest large amounts of information quickly.',
            'short_description': 'Summarize long content into concise overviews',
            'category': AgentCategory.PRODUCTIVITY,
            'price_per_run': Decimal('0.10'),
            'is_featured': True,
            'icon_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=summarizer',
            'cover_image_url': 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=800&auto=format&fit=crop'
        },
        {
            'name': 'Code Review Assistant',
            'slug': 'code-review-assistant',
            'description': 'AI-powered code review agent that analyzes code for bugs, security vulnerabilities, and best practices. Supports multiple programming languages and provides actionable suggestions for improvement.',
            'short_description': 'Automated code review with security analysis',
            'category': AgentCategory.DEVELOPMENT,
            'price_per_run': Decimal('0.25'),
            'is_featured': True,
            'icon_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=code',
            'cover_image_url': 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w-800&auto=format&fit=crop'
        },
        {
            'name': 'Social Media Content Creator',
            'slug': 'social-media-creator',
            'description': 'Creates engaging social media posts, captions, and content calendars. Optimizes content for different platforms (Twitter, LinkedIn, Instagram) and analyzes trending topics for maximum engagement.',
            'short_description': 'Generate engaging social media content',
            'category': AgentCategory.MARKETING,
            'price_per_run': Decimal('0.15'),
            'is_featured': False,
            'icon_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=social',
            'cover_image_url': 'https://images.unsplash.com/photo-1611605698323-b1e99cfd37ea?w=800&auto=format&fit=crop'
        },
        {
            'name': 'Financial Analyst',
            'slug': 'financial-analyst',
            'description': 'Analyzes financial data, generates reports, and provides investment insights. Can process spreadsheets, market data, and economic indicators to help with financial decision making.',
            'short_description': 'Financial data analysis and reporting',
            'category': AgentCategory.FINANCE,
            'price_per_run': Decimal('0.50'),
            'is_featured': True,
            'icon_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=finance',
            'cover_image_url': 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&auto=format&fit=crop'
        },
        {
            'name': 'Customer Support Bot',
            'slug': 'customer-support-bot',
            'description': 'AI customer support agent that handles common inquiries, provides product information, and escalates complex issues to human agents. Integrates with popular helpdesk software.',
            'short_description': 'Automated customer support and FAQ',
            'category': AgentCategory.CUSTOMER_SERVICE,
            'price_per_run': Decimal('0.05'),
            'is_featured': False,
            'icon_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=support',
            'cover_image_url': 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=800&auto=format&fit=crop'
        },
        {
            'name': 'Creative Writing Assistant',
            'slug': 'creative-writing-assistant',
            'description': 'Helps with creative writing projects including stories, poetry, scripts, and marketing copy. Provides style suggestions, plot ideas, and helps overcome writer\'s block.',
            'short_description': 'Creative writing support and inspiration',
            'category': AgentCategory.CREATIVE,
            'price_per_run': Decimal('0.20'),
            'is_featured': False,
            'icon_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=writing',
            'cover_image_url': 'https://images.unsplash.com/photo-1455390582262-044cdead277a?w=800&auto=format&fit=crop'
        }
    ]
    
    agents = []
    for agent_data in agents_data:
        # Check if agent already exists
        existing = Agent.query.filter_by(slug=agent_data['slug']).first()
        if existing:
            agents.append(existing)
            continue
        
        agent = Agent(
            owner=owner,
            **agent_data
        )
        
        # Publish the agent
        agent.publish()
        
        # Create agent version with mock Agno ID
        version = AgentVersion(
            agent=agent,
            version='1.0.0',
            config=json.dumps({
                'model': 'gpt-4',
                'temperature': 0.7,
                'max_tokens': 2000,
                'system_prompt': f"You are a {agent.name}. {agent.description}"
            }),
            agno_agent_id=f'agno_{agent.slug}_{agent.id}',
            changelog='Initial version',
            is_active=True
        )
        
        # Add some reviews
        if agent.slug == 'content-summarizer':
            from app.models.agent import AgentReview
            review = AgentReview(
                agent=agent,
                user=owner,
                rating=5,
                title='Excellent summarizer!',
                content='Saved me hours of reading time. The summaries are accurate and concise.'
            )
        
        db.session.add(agent)
        agents.append(agent)
    
    return agents


def create_tags():
    """Create common tags for agents."""
    tags_data = [
        {'name': 'AI', 'slug': 'ai', 'description': 'Artificial Intelligence'},
        {'name': 'Productivity', 'slug': 'productivity', 'description': 'Productivity tools'},
        {'name': 'Automation', 'slug': 'automation', 'description': 'Automation tools'},
        {'name': 'Business', 'slug': 'business', 'description': 'Business applications'},
        {'name': 'Development', 'slug': 'development', 'description': 'Development tools'},
        {'name': 'Marketing', 'slug': 'marketing', 'description': 'Marketing tools'},
        {'name': 'Finance', 'slug': 'finance', 'description': 'Financial applications'},
        {'name': 'Creative', 'slug': 'creative', 'description': 'Creative tools'},
        {'name': 'Writing', 'slug': 'writing', 'description': 'Writing assistance'},
        {'name': 'Analysis', 'slug': 'analysis', 'description': 'Data analysis tools'},
    ]
    
    tags = []
    for tag_data in tags_data:
        existing = Tag.query.filter_by(slug=tag_data['slug']).first()
        if existing:
            tags.append(existing)
            continue
        
        tag = Tag(**tag_data)
        db.session.add(tag)
        tags.append(tag)
    
    return tags


def associate_tags_with_agents(agents, tags):
    """Associate tags with appropriate agents."""
    tag_mapping = {
        'content-summarizer': ['AI', 'Productivity', 'Analysis', 'Writing'],
        'code-review-assistant': ['AI', 'Development', 'Automation'],
        'social-media-creator': ['AI', 'Marketing', 'Creative', 'Automation'],
        'financial-analyst': ['AI', 'Finance', 'Business', 'Analysis'],
        'customer-support-bot': ['AI', 'Business', 'Automation'],
        'creative-writing-assistant': ['AI', 'Creative', 'Writing'],
    }
    
    for agent in agents:
        if agent.slug in tag_mapping:
            tag_names = tag_mapping[agent.slug]
            for tag_name in tag_names:
                tag = next((t for t in tags if t.name == tag_name), None)
                if tag and tag not in agent.tags:
                    agent.tags.append(tag)


def create_demo_agent_runs(user, agents):
    """Create demo agent runs for testing."""
    runs = []
    
    for agent in agents[:3]:  # Create runs for first 3 agents
        for i in range(3):  # 3 runs per agent
            run = AgentRun(
                agent=agent,
                user=user,
                status=AgentRunStatus.COMPLETED,
                input_data=json.dumps({
                    'text': f'Sample input for {agent.name} run #{i+1}',
                    'options': {'length': 'short', 'format': 'bullet_points'}
                }),
                output_data=json.dumps({
                    'summary': f'This is a sample summary generated by {agent.name}',
                    'key_points': ['Point 1', 'Point 2', 'Point 3'],
                    'length': 'short'
                }),
                execution_time_ms=1500 + (i * 500),
                cost_usd=Decimal(str(float(agent.price_per_run))),
                started_at=datetime.utcnow() - timedelta(hours=i*2),
                completed_at=datetime.utcnow() - timedelta(hours=i*2 - 0.1)
            )
            
            # Add some logs
            from app.models.agent_run import AgentRunLog
            log1 = AgentRunLog(
                run=run,
                level='info',
                message='Starting agent execution',
                timestamp=run.started_at
            )
            
            log2 = AgentRunLog(
                run=run,
                level='info',
                message='Agent execution completed successfully',
                timestamp=run.completed_at,
                metadata=json.dumps({'execution_time_ms': run.execution_time_ms})
            )
            
            db.session.add(run)
            runs.append(run)
    
    return runs


if __name__ == '__main__':
    cli()