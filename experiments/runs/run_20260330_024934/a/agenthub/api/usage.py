"""usage.py — Real-time usage statistics and SSE streaming API.

exports: router
used_by: main.py, dashboard frontend
rules:   must provide real-time updates; must handle concurrent connections efficiently
agent:   DataEngineer | 2024-01-15 | created SSE streaming for real-time dashboard updates
         message: "implement Redis pub/sub for scalable real-time updates"
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import asyncio
import json
import time

from agenthub.db.session import get_db
from agenthub.db.models import User, AgentRun, CreditAccount
from agenthub.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/stream")
async def stream_usage_updates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream real-time usage updates via Server-Sent Events.
    
    Rules:   must handle disconnections gracefully; must filter by user
    """
    async def event_generator():
        """Generate SSE events for usage updates."""
        try:
            # Initial state
            last_run_count = 0
            last_balance = 0.0
            
            while True:
                # Get current stats
                run_count = db.query(AgentRun).filter(
                    AgentRun.user_id == current_user.id
                ).count()
                
                credit_account = db.query(CreditAccount).filter(
                    CreditAccount.user_id == current_user.id
                ).first()
                balance = credit_account.balance if credit_account else 0.0
                
                # Check for changes
                if run_count != last_run_count or balance != last_balance:
                    yield f"data: {json.dumps({
                        'run_count': run_count,
                        'credit_balance': balance,
                        'currency': credit_account.currency if credit_account else 'USD',
                        'timestamp': time.time()
                    })}\n\n"
                    
                    last_run_count = run_count
                    last_balance = balance
                
                # Wait before next check
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            # Client disconnected
            pass
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


@router.get("/stats")
async def get_usage_stats(
    period: Optional[str] = "day",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get usage statistics for the current user.
    
    Rules:   must support different time periods; must be efficient
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, extract
    
    # Calculate time range
    now = datetime.utcnow()
    if period == "hour":
        start_time = now - timedelta(hours=1)
    elif period == "day":
        start_time = now - timedelta(days=1)
    elif period == "week":
        start_time = now - timedelta(weeks=1)
    elif period == "month":
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(days=1)  # Default to day
    
    # Get run statistics
    runs = db.query(AgentRun).filter(
        AgentRun.user_id == current_user.id,
        AgentRun.created_at >= start_time
    ).all()
    
    # Calculate metrics
    total_runs = len(runs)
    successful_runs = sum(1 for r in runs if r.status == "completed")
    failed_runs = sum(1 for r in runs if r.status == "failed")
    total_credits = sum(r.credits_used or 0 for r in runs)
    
    # Get credit balance
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == current_user.id
    ).first()
    
    # Get agent usage distribution
    from collections import Counter
    agent_usage = Counter()
    for run in runs:
        agent_usage[run.agent_id] += 1
    
    # Get top agents
    top_agents = []
    for agent_id, count in agent_usage.most_common(5):
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if agent:
            top_agents.append({
                "agent_id": str(agent.public_id),
                "agent_name": agent.name,
                "run_count": count
            })
    
    return {
        "period": period,
        "time_range": {
            "start": start_time.isoformat(),
            "end": now.isoformat()
        },
        "run_statistics": {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else 0
        },
        "credit_usage": {
            "total_credits_used": total_credits,
            "average_credits_per_run": total_credits / total_runs if total_runs > 0 else 0,
            "current_balance": credit_account.balance if credit_account else 0,
            "currency": credit_account.currency if credit_account else "USD"
        },
        "top_agents": top_agents,
        "timestamp": now.isoformat()
    }


@router.get("/export")
async def export_usage_data(
    format: str = "json",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export usage data in various formats.
    
    Rules:   must support CSV and JSON; must handle large datasets efficiently
    """
    from datetime import datetime
    
    # Parse dates
    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    else:
        start_dt = datetime.utcnow() - timedelta(days=30)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    else:
        end_dt = datetime.utcnow()
    
    # Get runs in date range
    runs = db.query(AgentRun).filter(
        AgentRun.user_id == current_user.id,
        AgentRun.created_at >= start_dt,
        AgentRun.created_at <= end_dt
    ).order_by(AgentRun.created_at.desc()).all()
    
    # Prepare data
    data = []
    for run in runs:
        agent = db.query(Agent).filter(Agent.id == run.agent_id).first()
        data.append({
            "timestamp": run.created_at.isoformat(),
            "agent_id": str(agent.public_id) if agent else None,
            "agent_name": agent.name if agent else None,
            "status": run.status,
            "credits_used": run.credits_used or 0,
            "input_summary": str(run.input_data)[:100] if run.input_data else None,
            "error_message": run.error_message
        })
    
    if format.lower() == "csv":
        import csv
        import io
        
        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys() if data else [])
        writer.writeheader()
        writer.writerows(data)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=usage_export_{datetime.utcnow().date()}.csv"
            }
        )
    
    else:  # JSON format
        return {
            "export_format": "json",
            "date_range": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat()
            },
            "total_records": len(data),
            "data": data
        }


@router.get("/limits")
async def get_usage_limits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current usage limits and remaining quotas.
    
    Rules:   must reflect plan-based limits
    """
    from agenthub.billing.plans import get_user_plan, PLANS
    
    plan = get_user_plan(db, current_user.id)
    plan_config = PLANS.get(plan, {})
    
    # Get current usage
    agent_count = db.query(Agent).filter(Agent.owner_id == current_user.id).count()
    
    scheduled_tasks = db.query(ScheduledTask).filter(
        ScheduledTask.user_id == current_user.id
    ).count()
    
    # Get concurrent runs
    running_runs = db.query(AgentRun).filter(
        AgentRun.user_id == current_user.id,
        AgentRun.status == "running"
    ).count()
    
    return {
        "plan": plan,
        "plan_name": plan_config.get("name", "Free"),
        "limits": {
            "max_agents": plan_config.get("max_agents"),
            "current_agents": agent_count,
            "remaining_agents": plan_config.get("max_agents") - agent_count if plan_config.get("max_agents") else None,
            
            "max_scheduled_tasks": plan_config.get("max_scheduled_tasks"),
            "current_scheduled_tasks": scheduled_tasks,
            "remaining_scheduled_tasks": plan_config.get("max_scheduled_tasks") - scheduled_tasks if plan_config.get("max_scheduled_tasks") else None,
            
            "concurrent_runs": plan_config.get("concurrent_runs", 1),
            "current_concurrent_runs": running_runs,
            "remaining_concurrent_runs": plan_config.get("concurrent_runs", 1) - running_runs,
            
            "credit_cap": plan_config.get("credit_cap"),
            "api_access": plan_config.get("api_access", False),
            "custom_domains": plan_config.get("custom_domains", False),
            "support_level": plan_config.get("support_level", "community")
        },
        "features": plan_config.get("features", [])
    }