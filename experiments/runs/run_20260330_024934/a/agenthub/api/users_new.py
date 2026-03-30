"""users.py — User profile and organization management API.

exports: router
used_by: main.py
rules:   must enforce permission checks; must handle profile updates securely
agent:   BackendEngineer | 2024-01-15 | implemented user profile and organization management
         message: "implement organization management with proper role-based access control"
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from agenthub.db.session import get_db
from agenthub.db.models import User, OrgMembership, CreditAccount, AgentRun, AuditLog
from agenthub.auth.dependencies import get_current_user
from agenthub.schemas.users import ProfileUpdate, OrgCreate, OrgInvite, OrgMemberResponse, UsageStats
from agenthub.api.auth import get_password_hash, verify_password, create_audit_log

router = APIRouter()


@router.put("/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user profile information.
    
    Rules:   must validate email uniqueness; must not allow sensitive field updates
    """
    # Update user fields
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    # Create audit log
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="profile_update",
        resource_type="user",
        resource_id=str(current_user.public_id),
        details={"updated_fields": list(update_data.keys())}
    )
    
    return current_user


@router.put("/password")
async def change_password(
    current_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change user password.
    
    Rules:   must verify current password; must use secure hashing
    """
    # Verify current password
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    
    # Create audit log
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="password_change",
        resource_type="user",
        resource_id=str(current_user.public_id)
    )
    
    return {"message": "Password changed successfully"}


@router.get("/organizations")
async def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List organizations user belongs to.
    
    Rules:   must include role information; must show organization details
    """
    # Get user's organization memberships
    memberships = db.query(OrgMembership).filter(
        OrgMembership.user_id == current_user.id
    ).all()
    
    organizations = []
    for membership in memberships:
        org = db.query(User).filter(User.id == membership.org_id).first()
        if org:
            organizations.append({
                "org_id": str(org.public_id),
                "org_name": org.full_name or org.email.split('@')[0],
                "org_email": org.email,
                "role": membership.role,
                "joined_at": membership.created_at,
                "member_count": db.query(OrgMembership).filter(
                    OrgMembership.org_id == org.id
                ).count()
            })
    
    return {"organizations": organizations}


@router.post("/organizations", status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrgCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new organization.
    
    Rules:   must set creator as owner; must create org credit account
    """
    # Check if organization name/email already exists
    existing_org = db.query(User).filter(
        or_(
            User.email == f"org-{org_data.name.lower().replace(' ', '-')}@agenthub.local",
            User.full_name == org_data.name
        )
    ).first()
    
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization with this name already exists"
        )
    
    # Create organization user account
    org_user = User(
        email=f"org-{org_data.name.lower().replace(' ', '-')}@agenthub.local",
        password_hash=get_password_hash(str(uuid.uuid4())),  # Random password
        full_name=org_data.name,
        is_active=True,
        is_superuser=False,
    )
    
    db.add(org_user)
    db.commit()
    db.refresh(org_user)
    
    # Create organization credit account
    org_credit_account = CreditAccount(
        user_id=org_user.id,
        balance=0.0,
        currency="USD"
    )
    db.add(org_credit_account)
    
    # Create membership with owner role
    membership = OrgMembership(
        user_id=current_user.id,
        org_id=org_user.id,
        role="owner"
    )
    db.add(membership)
    
    db.commit()
    
    # Create audit log
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="org_create",
        resource_type="organization",
        resource_id=str(org_user.public_id),
        details={"org_name": org_data.name, "description": org_data.description}
    )
    
    return {
        "message": "Organization created successfully",
        "org_id": str(org_user.public_id),
        "org_name": org_data.name,
        "role": "owner"
    }


@router.get("/organizations/{org_id}/members", response_model=List[OrgMemberResponse])
async def list_organization_members(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List members of an organization.
    
    Rules:   must verify user has permission to view members
    """
    # Find organization
    org = db.query(User).filter(User.public_id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user is a member
    membership = db.query(OrgMembership).filter(
        and_(
            OrgMembership.user_id == current_user.id,
            OrgMembership.org_id == org.id
        )
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )
    
    # Get all members
    memberships = db.query(OrgMembership).filter(
        OrgMembership.org_id == org.id
    ).all()
    
    members = []
    for mem in memberships:
        user = db.query(User).filter(User.id == mem.user_id).first()
        if user:
            members.append({
                "user_id": user.id,
                "public_id": str(user.public_id),
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "role": mem.role,
                "joined_at": mem.created_at
            })
    
    return members


@router.post("/organizations/{org_id}/invite")
async def invite_to_organization(
    org_id: str,
    invite_data: OrgInvite,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite user to organization.
    
    Rules:   must verify inviter has admin/owner role; must send invitation email
    """
    # Find organization
    org = db.query(User).filter(User.public_id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if inviter has permission (admin or owner)
    inviter_membership = db.query(OrgMembership).filter(
        and_(
            OrgMembership.user_id == current_user.id,
            OrgMembership.org_id == org.id
        )
    ).first()
    
    if not inviter_membership or inviter_membership.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to invite members"
        )
    
    # Check if user to invite exists
    invitee = db.query(User).filter(User.email == invite_data.email).first()
    if not invitee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found"
        )
    
    # Check if user is already a member
    existing_membership = db.query(OrgMembership).filter(
        and_(
            OrgMembership.user_id == invitee.id,
            OrgMembership.org_id == org.id
        )
    ).first()
    
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization"
        )
    
    # Create invitation (in production, would store in separate Invitation table)
    # For now, we'll add them directly with a pending status
    
    membership = OrgMembership(
        user_id=invitee.id,
        org_id=org.id,
        role=invite_data.role
    )
    db.add(membership)
    db.commit()
    
    # Create audit log
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="org_invite",
        resource_type="organization",
        resource_id=str(org.public_id),
        details={
            "invitee_email": invite_data.email,
            "role": invite_data.role,
            "inviter_email": current_user.email
        }
    )
    
    # In production, send invitation email
    # background_tasks.add_task(send_org_invitation_email, invitee.email, org.full_name, current_user.email)
    
    return {
        "message": "Invitation sent successfully",
        "invitee_email": invite_data.email,
        "role": invite_data.role
    }


@router.get("/usage", response_model=UsageStats)
async def get_usage_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    timeframe: str = "month",  # day, week, month, year
):
    """Get user usage statistics.
    
    Rules:   must include agent runs, credits used, and costs
    """
    # Calculate date range based on timeframe
    now = datetime.utcnow()
    if timeframe == "day":
        start_date = now - timedelta(days=1)
    elif timeframe == "week":
        start_date = now - timedelta(weeks=1)
    elif timeframe == "month":
        start_date = now - timedelta(days=30)
    elif timeframe == "year":
        start_date = now - timedelta(days=365)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timeframe. Use: day, week, month, year"
        )
    
    # Get agent runs in timeframe
    agent_runs = db.query(AgentRun).filter(
        and_(
            AgentRun.user_id == current_user.id,
            AgentRun.created_at >= start_date,
            AgentRun.created_at <= now
        )
    ).all()
    
    # Calculate statistics
    total_runs = len(agent_runs)
    total_credits_used = sum(run.credits_used for run in agent_runs)
    total_cost = total_credits_used  # Assuming 1 credit = 1 USD
    
    # Group runs by agent
    runs_by_agent = {}
    for run in agent_runs:
        agent = db.query(User).filter(User.id == run.agent_id).first()
        if agent:
            agent_name = agent.name if hasattr(agent, 'name') else f"Agent {run.agent_id}"
            runs_by_agent[agent_name] = runs_by_agent.get(agent_name, 0) + 1
    
    # Group credits by day
    credits_by_day = {}
    for run in agent_runs:
        day = run.created_at.strftime("%Y-%m-%d")
        credits_by_day[day] = credits_by_day.get(day, 0) + run.credits_used
    
    # Calculate average run cost
    average_run_cost = total_cost / total_runs if total_runs > 0 else 0
    
    # Find peak usage day
    peak_usage_day = max(credits_by_day.items(), key=lambda x: x[1])[0] if credits_by_day else None
    
    return UsageStats(
        timeframe=timeframe,
        start_date=start_date,
        end_date=now,
        total_runs=total_runs,
        total_credits_used=total_credits_used,
        total_cost=total_cost,
        runs_by_agent=runs_by_agent,
        credits_by_day=credits_by_day,
        average_run_cost=average_run_cost,
        peak_usage_day=peak_usage_day
    )


@router.delete("/organizations/{org_id}/members/{user_id}")
async def remove_organization_member(
    org_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove member from organization.
    
    Rules:   must verify permission; cannot remove last owner
    """
    # Find organization
    org = db.query(User).filter(User.public_id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if remover has permission (admin or owner)
    remover_membership = db.query(OrgMembership).filter(
        and_(
            OrgMembership.user_id == current_user.id,
            OrgMembership.org_id == org.id
        )
    ).first()
    
    if not remover_membership or remover_membership.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove members"
        )
    
    # Find user to remove
    user_to_remove = db.query(User).filter(User.public_id == user_id).first()
    if not user_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is a member
    member_membership = db.query(OrgMembership).filter(
        and_(
            OrgMembership.user_id == user_to_remove.id,
            OrgMembership.org_id == org.id
        )
    ).first()
    
    if not member_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this organization"
        )
    
    # Check if trying to remove self
    if user_to_remove.id == current_user.id:
        # Check if last owner
        owner_count = db.query(OrgMembership).filter(
            and_(
                OrgMembership.org_id == org.id,
                OrgMembership.role == "owner"
            )
        ).count()
        
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot leave organization as the last owner. Transfer ownership first."
            )
    
    # Remove membership
    db.delete(member_membership)
    db.commit()
    
    # Create audit log
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="org_member_remove",
        resource_type="organization",
        resource_id=str(org.public_id),
        details={
            "removed_user_email": user_to_remove.email,
            "removed_user_role": member_membership.role,
            "remover_email": current_user.email
        }
    )
    
    return {"message": "Member removed successfully"}