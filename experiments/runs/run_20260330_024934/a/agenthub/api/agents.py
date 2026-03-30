"""agents.py — Agent management and execution API.

exports: router
used_by: main.py
rules:   must validate agent ownership; must handle credit deduction atomically
agent:   BackendEngineer | 2024-01-15 | implemented complete agent CRUD and execution
         message: "implement agent execution with proper error handling and rollback"
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
import uuid

from agenthub.db.session import get_db
from agenthub.db.models import Agent, AgentRun, User, CreditAccount
from agenthub.auth.dependencies import get_current_user
from agenthub.schemas.agents import AgentCreate, AgentUpdate, AgentResponse, AgentRunCreate, AgentRunResponse
from agenthub.config import settings

router = APIRouter()


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: Optional[str] = None,
    public_only: bool = True,
    limit: int = 50,
    offset: int = 0,
):
    """List available agents.
    
    Rules:   must filter by ownership and visibility; must support pagination
    """
    # Build query based on visibility and ownership
    query = db.query(Agent)
    
    if public_only:
        # Show public agents and user's own agents
        query = query.filter(
            or_(
                Agent.is_public == True,
                Agent.owner_id == current_user.id
            )
        )
    else:
        # Only show user's own agents
        query = query.filter(Agent.owner_id == current_user.id)
    
    # Apply category filter if provided
    if category:
        query = query.filter(Agent.category == category)
    
    # Apply pagination
    agents = query.filter(Agent.is_active == True)\
                  .order_by(Agent.created_at.desc())\
                  .offset(offset)\
                  .limit(limit)\
                  .all()
    
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get agent details.
    
    Rules:   must check agent visibility (public or owned by user)
    """
    # Try to find by public_id first
    agent = db.query(Agent).filter(
        or_(
            Agent.public_id == agent_id,
            Agent.slug == agent_id
        )
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check visibility
    if not agent.is_public and agent.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this agent"
        )
    
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Agent is no longer active"
        )
    
    return agent


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new agent.
    
    Rules:   must validate system_prompt; must set owner to current user
    """
    # Check if slug is already taken
    existing_agent = db.query(Agent).filter(Agent.slug == agent_data.slug).first()
    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent with this slug already exists"
        )
    
    # Create new agent
    agent = Agent(
        **agent_data.dict(),
        owner_id=current_user.id
    )
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing agent.
    
    Rules:   must verify ownership; must validate updates
    """
    # Find agent
    agent = db.query(Agent).filter(Agent.public_id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check ownership
    if agent.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this agent"
        )
    
    # Update agent fields
    update_data = agent_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    db.commit()
    db.refresh(agent)
    
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an agent.
    
    Rules:   must verify ownership; must handle cascading deletes
    """
    # Find agent
    agent = db.query(Agent).filter(Agent.public_id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check ownership
    if agent.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this agent"
        )
    
    # Soft delete (set inactive)
    agent.is_active = False
    db.commit()


@router.post("/{agent_id}/run", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
async def run_agent(
    agent_id: str,
    run_data: AgentRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute an agent run.
    
    Rules:   must deduct credits before execution; must handle async execution
    """
    # Find agent
    agent = db.query(Agent).filter(
        or_(
            Agent.public_id == agent_id,
            Agent.slug == agent_id
        ),
        Agent.is_active == True
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check visibility and ownership
    if not agent.is_public and agent.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to run this agent"
        )
    
    # Get user's credit account
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == current_user.id
    ).first()
    
    if not credit_account:
        # Create credit account if it doesn't exist
        credit_account = CreditAccount(user_id=current_user.id, balance=0.0)
        db.add(credit_account)
        db.commit()
        db.refresh(credit_account)
    
    # Check if user has enough credits
    if credit_account.balance < agent.price_per_run:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {agent.price_per_run}, Available: {credit_account.balance}"
        )
    
    # Create agent run record
    agent_run = AgentRun(
        user_id=current_user.id,
        agent_id=agent.id,
        input_data=run_data.input_data,
        metadata=run_data.metadata,
        status="pending",
        credits_used=agent.price_per_run
    )
    
    db.add(agent_run)
    
    # Deduct credits atomically
    credit_account.balance -= agent.price_per_run
    
    try:
        db.commit()
        db.refresh(agent_run)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent run: {str(e)}"
        )
    
    # Start agent execution in background
    background_tasks.add_task(execute_agent_run, agent_run.id, db)
    
    return agent_run


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_run_status(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get agent run status and results.
    
    Rules:   must verify user owns the run or has permission
    """
    # Find agent run
    agent_run = db.query(AgentRun).filter(AgentRun.public_id == run_id).first()
    
    if not agent_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found"
        )
    
    # Check ownership
    if agent_run.user_id != current_user.id:
        # Check if user can view through organization
        # (This would require additional permission checks)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this run"
        )
    
    return agent_run


@router.get("/{agent_id}/runs", response_model=List[AgentRunResponse])
async def list_agent_runs(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    """List runs for a specific agent.
    
    Rules:   must verify ownership/visibility; must support pagination
    """
    # Find agent
    agent = db.query(Agent).filter(
        or_(
            Agent.public_id == agent_id,
            Agent.slug == agent_id
        )
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check visibility
    if not agent.is_public and agent.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view runs for this agent"
        )
    
    # Get runs (only user's own runs unless they own the agent)
    query = db.query(AgentRun).filter(AgentRun.agent_id == agent.id)
    
    if agent.owner_id != current_user.id:
        query = query.filter(AgentRun.user_id == current_user.id)
    
    runs = query.order_by(AgentRun.created_at.desc())\
                .offset(offset)\
                .limit(limit)\
                .all()
    
    return runs


# Background task function for agent execution
async def execute_agent_run(run_id: int, db: Session):
    """Execute agent run in background."""
    from sqlalchemy.orm import Session as DBSession
    from agenthub.services.agent_executor import execute_agent
    
    # Create new session for background task
    session = DBSession(bind=db.bind)
    
    try:
        # Get agent run
        agent_run = session.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not agent_run:
            return
        
        # Update status to running
        agent_run.status = "running"
        agent_run.started_at = datetime.utcnow()
        session.commit()
        
        # Execute agent
        result = await execute_agent(agent_run)
        
        # Update with results
        agent_run.output_data = result.get("output", {})
        agent_run.status = "completed"
        agent_run.completed_at = datetime.utcnow()
        
    except Exception as e:
        # Handle execution failure
        agent_run.status = "failed"
        agent_run.error_message = str(e)
        agent_run.completed_at = datetime.utcnow()
        
    finally:
        session.commit()
        session.close()