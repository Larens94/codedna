"""tasks.py — Scheduled task management API.

exports: router
used_by: main.py
rules:   must validate cron expressions; must handle timezone conversions
agent:   BackendEngineer | 2024-01-15 | implemented scheduled task management
         message: "implement cron expression validation and next run calculation"
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
from croniter import croniter

from agenthub.db.session import get_db
from agenthub.db.models import User, ScheduledTask, Agent, AgentRun, CreditAccount
from agenthub.auth.dependencies import get_current_user
from agenthub.schemas.scheduler import ScheduledTaskCreate, ScheduledTaskUpdate, ScheduledTaskResponse, TaskRunResponse
from agenthub.config import settings

router = APIRouter()


def calculate_next_run(cron_expression: Optional[str], interval_seconds: Optional[int]) -> datetime:
    """Calculate next run time based on schedule."""
    now = datetime.utcnow()
    
    if cron_expression:
        # Calculate next run from cron expression
        cron = croniter(cron_expression, now)
        next_run = cron.get_next(datetime)
    elif interval_seconds:
        # Calculate next run from interval
        next_run = now + timedelta(seconds=interval_seconds)
    else:
        raise ValueError("Either cron_expression or interval_seconds must be provided")
    
    return next_run


@router.get("/", response_model=List[ScheduledTaskResponse])
async def list_scheduled_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
):
    """List user's scheduled tasks.
    
    Rules:   must filter by user; must support pagination
    """
    query = db.query(ScheduledTask).filter(ScheduledTask.user_id == current_user.id)
    
    if active_only:
        query = query.filter(ScheduledTask.is_active == True)
    
    tasks = query.order_by(desc(ScheduledTask.created_at))\
                .offset(offset)\
                .limit(limit)\
                .all()
    
    return tasks


@router.post("/", response_model=ScheduledTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new scheduled task.
    
    Rules:   must validate cron expression; must calculate next_run_at
    """
    # Verify agent exists and user has permission to use it
    agent = db.query(Agent).filter(
        Agent.id == task_data.agent_id,
        Agent.is_active == True
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or inactive"
        )
    
    # Check if user can use this agent
    if not agent.is_public and agent.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to use this agent"
        )
    
    # Calculate next run time
    next_run_at = calculate_next_run(
        task_data.cron_expression,
        task_data.interval_seconds
    )
    
    # Create scheduled task
    task = ScheduledTask(
        **task_data.dict(exclude={"cron_expression", "interval_seconds"}),
        cron_expression=task_data.cron_expression,
        interval_seconds=task_data.interval_seconds,
        user_id=current_user.id,
        next_run_at=next_run_at,
        public_id=str(uuid.uuid4())
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return task


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scheduled task details.
    
    Rules:   must verify user owns the task; must include run history
    """
    # Find task by public_id
    task = db.query(ScheduledTask).filter(ScheduledTask.public_id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found"
        )
    
    # Check ownership
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this task"
        )
    
    return task


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: str,
    task_data: ScheduledTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update scheduled task.
    
    Rules:   must recalculate next_run_at if schedule changes
    """
    # Find task
    task = db.query(ScheduledTask).filter(ScheduledTask.public_id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found"
        )
    
    # Check ownership
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this task"
        )
    
    # Check if schedule is being updated
    schedule_updated = (
        task_data.cron_expression is not None or 
        task_data.interval_seconds is not None or
        task_data.is_active is not None
    )
    
    # Update task fields
    update_data = task_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    # Recalculate next run if schedule was updated and task is active
    if schedule_updated and task.is_active:
        if task_data.cron_expression is not None or task_data.interval_seconds is not None:
            task.next_run_at = calculate_next_run(
                task.cron_expression,
                task.interval_seconds
            )
    
    db.commit()
    db.refresh(task)
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete scheduled task.
    
    Rules:   must verify ownership; must cancel any pending executions
    """
    # Find task
    task = db.query(ScheduledTask).filter(ScheduledTask.public_id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found"
        )
    
    # Check ownership
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this task"
        )
    
    # Soft delete (set inactive)
    task.is_active = False
    db.commit()


@router.post("/{task_id}/run-now", response_model=TaskRunResponse)
async def run_task_now(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute scheduled task immediately.
    
    Rules:   must verify credits available; must not affect regular schedule
    """
    # Find task
    task = db.query(ScheduledTask).filter(
        ScheduledTask.public_id == task_id,
        ScheduledTask.is_active == True
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found or inactive"
        )
    
    # Check ownership
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to run this task"
        )
    
    # Get agent
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
    if not agent or not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or inactive"
        )
    
    # Check credits
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == current_user.id
    ).first()
    
    if not credit_account or credit_account.balance < agent.price_per_run:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {agent.price_per_run}"
        )
    
    # Create manual run record (simplified - in production would have separate model)
    manual_run = {
        "id": len(db.query(AgentRun).all()) + 1,  # Temporary ID
        "task_id": task.id,
        "agent_run_id": None,
        "status": "pending",
        "scheduled_at": datetime.utcnow(),
        "started_at": None,
        "completed_at": None,
        "error_message": None,
        "credits_used": agent.price_per_run,
        "created_at": datetime.utcnow()
    }
    
    # Start execution in background
    background_tasks.add_task(execute_scheduled_task, task.id, manual_run["id"], db, is_manual=True)
    
    return manual_run


@router.get("/{task_id}/runs", response_model=List[TaskRunResponse])
async def get_task_run_history(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """Get execution history for a scheduled task.
    
    Rules:   must include status, timestamps, and results
    """
    # Find task
    task = db.query(ScheduledTask).filter(ScheduledTask.public_id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found"
        )
    
    # Check ownership
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this task's history"
        )
    
    # In production, you would have a separate TaskRun model
    # For now, we'll return agent runs associated with this task
    agent_runs = db.query(AgentRun).filter(
        AgentRun.agent_id == task.agent_id,
        AgentRun.user_id == current_user.id
    ).order_by(desc(AgentRun.created_at))\
     .offset(offset)\
     .limit(limit)\
     .all()
    
    # Convert to TaskRunResponse format
    task_runs = []
    for run in agent_runs:
        task_runs.append({
            "id": run.id,
            "task_id": task.id,
            "agent_run_id": run.id,
            "status": run.status,
            "scheduled_at": run.created_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "error_message": run.error_message,
            "credits_used": run.credits_used,
            "created_at": run.created_at
        })
    
    return task_runs


@router.get("/{task_id}/next-runs")
async def get_next_scheduled_runs(
    task_id: str,
    count: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get next scheduled run times for a task."""
    # Find task
    task = db.query(ScheduledTask).filter(ScheduledTask.public_id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found"
        )
    
    # Check ownership
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this task"
        )
    
    if not task.cron_expression:
        return {"next_runs": [task.next_run_at.isoformat()]}
    
    # Calculate next runs from cron expression
    next_runs = []
    cron = croniter(task.cron_expression, datetime.utcnow())
    
    for _ in range(count):
        next_run = cron.get_next(datetime)
        next_runs.append(next_run.isoformat())
    
    return {"next_runs": next_runs}


async def execute_scheduled_task(task_id: int, run_id: int, db: Session, is_manual: bool = False):
    """Execute scheduled task in background."""
    from sqlalchemy.orm import Session as DBSession
    
    # Create new session for background task
    session = DBSession(bind=db.bind)
    
    try:
        # Get task
        task = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task or not task.is_active:
            return
        
        # Get agent
        agent = session.query(Agent).filter(Agent.id == task.agent_id).first()
        if not agent or not agent.is_active:
            task.last_run_status = "failed"
            task.metadata["error"] = "Agent not found or inactive"
            session.commit()
            return
        
        # Get user's credit account
        credit_account = session.query(CreditAccount).filter(
            CreditAccount.user_id == task.user_id
        ).first()
        
        if not credit_account or credit_account.balance < agent.price_per_run:
            task.last_run_status = "failed"
            task.metadata["error"] = "Insufficient credits"
            session.commit()
            return
        
        # Create agent run
        agent_run = AgentRun(
            user_id=task.user_id,
            agent_id=task.agent_id,
            input_data=task.input_data,
            metadata={**task.metadata, "scheduled_task_id": task.id, "is_manual": is_manual},
            status="pending",
            credits_used=agent.price_per_run
        )
        
        session.add(agent_run)
        
        # Deduct credits
        credit_account.balance -= agent.price_per_run
        
        # Update task status
        task.last_run_at = datetime.utcnow()
        task.last_run_status = "running"
        
        session.commit()
        session.refresh(agent_run)
        
        # Execute agent (simplified - would call actual agent execution)
        agent_run.status = "running"
        agent_run.started_at = datetime.utcnow()
        session.commit()
        
        # Simulate agent execution
        # In production: result = await execute_agent(agent_run)
        import time
        time.sleep(2)  # Simulate processing time
        
        agent_run.output_data = {"result": "Task executed successfully"}
        agent_run.status = "completed"
        agent_run.completed_at = datetime.utcnow()
        
        # Update task status
        task.last_run_status = "completed"
        
        # Calculate next run if not manual
        if not is_manual and task.is_active:
            task.next_run_at = calculate_next_run(
                task.cron_expression,
                task.interval_seconds
            )
        
    except Exception as e:
        # Handle execution failure
        if 'agent_run' in locals():
            agent_run.status = "failed"
            agent_run.error_message = str(e)
            agent_run.completed_at = datetime.utcnow()
        
        if 'task' in locals():
            task.last_run_status = "failed"
            task.metadata["error"] = str(e)
        
    finally:
        session.commit()
        session.close()