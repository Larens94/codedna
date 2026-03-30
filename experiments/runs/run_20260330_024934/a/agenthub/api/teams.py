"""teams.py — Team collaboration and organization management API.

exports: router
used_by: main.py
rules:   must enforce role-based permissions; must handle team credit pools
agent:   DataEngineer | 2024-01-15 | created team management with role-based access control
         message: "implement team-level analytics and credit sharing"
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from agenthub.db.session import get_db
from agenthub.db.models import User, OrgMembership, Agent, AgentRun, CreditAccount
from agenthub.auth.dependencies import get_current_user
from agenthub.schemas.users import TeamMember, TeamInvite, TeamResponse

router = APIRouter()


@router.get("/teams", response_model=List[TeamResponse])
async def list_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all teams the user belongs to.
    
    Rules:   must include role and membership details
    """
    memberships = db.query(OrgMembership).filter(
        OrgMembership.user_id == current_user.id
    ).all()
    
    teams = []
    for membership in memberships:
        org = db.query(User).filter(User.id == membership.org_id).first()
        if org:
            # Get team statistics
            member_count = db.query(OrgMembership).filter(
                OrgMembership.org_id == org.id
            ).count()
            
            agent_count = db.query(Agent).filter(Agent.owner_id == org.id).count()
            
            teams.append({
                "id": str(org.public_id),
                "name": org.full_name or org.email.split('@')[0],
                "email": org.email,
                "role": membership.role,
                "member_count": member_count,
                "agent_count": agent_count,
                "created_at": org.created_at,
                "is_active": org.is_active
            })
    
    return teams


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new team/organization.
    
    Rules:   creator becomes owner; must create team credit account
    """
    try:
        # Create team user account
        team_user = User(
            public_id=str(uuid.uuid4()),
            email=f"team_{uuid.uuid4().hex[:8]}@teams.agenthub.ai",  # Placeholder email
            password_hash="",  # Teams don't login directly
            full_name=team_data.get("name", f"Team {uuid.uuid4().hex[:4]}"),
            is_active=True
        )
        db.add(team_user)
        db.flush()  # Get the ID
        
        # Create owner membership
        membership = OrgMembership(
            user_id=current_user.id,
            org_id=team_user.id,
            role="owner"
        )
        db.add(membership)
        
        # Create team credit account
        credit_account = CreditAccount(
            user_id=team_user.id,
            balance=0.0,
            currency="USD"
        )
        db.add(credit_account)
        
        db.commit()
        db.refresh(team_user)
        
        return {
            "id": str(team_user.public_id),
            "name": team_user.full_name,
            "email": team_user.email,
            "role": "owner",
            "member_count": 1,
            "agent_count": 0,
            "created_at": team_user.created_at,
            "is_active": team_user.is_active
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create team: {str(e)}"
        )


@router.get("/teams/{team_id}/members", response_model=List[TeamMember])
async def list_team_members(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all members of a team.
    
    Rules:   must verify user has access to team
    """
    # Find team
    team = db.query(User).filter(User.public_id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Verify user has access to team
    membership = db.query(OrgMembership).filter(
        OrgMembership.user_id == current_user.id,
        OrgMembership.org_id == team.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this team"
        )
    
    # Get all members
    memberships = db.query(OrgMembership).filter(
        OrgMembership.org_id == team.id
    ).all()
    
    members = []
    for mem in memberships:
        user = db.query(User).filter(User.id == mem.user_id).first()
        if user:
            members.append({
                "id": str(user.public_id),
                "email": user.email,
                "full_name": user.full_name,
                "role": mem.role,
                "joined_at": mem.created_at,
                "is_active": user.is_active
            })
    
    return members


@router.post("/teams/{team_id}/invite", response_model=TeamInvite)
async def invite_to_team(
    team_id: str,
    invite_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a user to join a team.
    
    Rules:   only admins/owners can invite; must validate email
    """
    # Find team
    team = db.query(User).filter(User.public_id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Verify user has permission to invite
    membership = db.query(OrgMembership).filter(
        OrgMembership.user_id == current_user.id,
        OrgMembership.org_id == team.id
    ).first()
    
    if not membership or membership.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to invite members"
        )
    
    # Check if user exists
    invitee = db.query(User).filter(User.email == invite_data["email"]).first()
    
    if invitee:
        # Check if already a member
        existing = db.query(OrgMembership).filter(
            OrgMembership.user_id == invitee.id,
            OrgMembership.org_id == team.id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a team member"
            )
    
    # Create invitation (in production, would send email)
    # For now, just return success
    
    return {
        "team_id": team_id,
        "team_name": team.full_name,
        "invitee_email": invite_data["email"],
        "invited_by": current_user.email,
        "role": invite_data.get("role", "member"),
        "invited_at": datetime.utcnow().isoformat(),
        "status": "pending"
    }


@router.post("/teams/{team_id}/members/{user_id}/role")
async def update_member_role(
    team_id: str,
    user_id: str,
    role_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a team member's role.
    
    Rules:   only owners can change roles; owners cannot demote themselves
    """
    # Find team
    team = db.query(User).filter(User.public_id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Find member
    member = db.query(User).filter(User.public_id == user_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Verify current user is owner
    current_membership = db.query(OrgMembership).filter(
        OrgMembership.user_id == current_user.id,
        OrgMembership.org_id == team.id,
        OrgMembership.role == "owner"
    ).first()
    
    if not current_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owners can change roles"
        )
    
    # Check if trying to demote self
    if member.id == current_user.id and role_data["role"] != "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself from owner"
        )
    
    # Update role
    membership = db.query(OrgMembership).filter(
        OrgMembership.user_id == member.id,
        OrgMembership.org_id == team.id
    ).first()
    
    if membership:
        membership.role = role_data["role"]
        db.commit()
        
        return {"success": True, "new_role": role_data["role"]}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Member not found in team"
    )


@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a team.
    
    Rules:   only admins/owners can remove; cannot remove last owner
    """
    # Find team
    team = db.query(User).filter(User.public_id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Find member
    member = db.query(User).filter(User.public_id == user_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Verify current user has permission
    current_membership = db.query(OrgMembership).filter(
        OrgMembership.user_id == current_user.id,
        OrgMembership.org_id == team.id,
        OrgMembership.role.in_(["admin", "owner"])
    ).first()
    
    if not current_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove members"
        )
    
    # Check if trying to remove self
    if member.id == current_user.id:
        # Count owners
        owner_count = db.query(OrgMembership).filter(
            OrgMembership.org_id == team.id,
            OrgMembership.role == "owner"
        ).count()
        
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove yourself as the last owner"
            )
    
    # Remove membership
    membership = db.query(OrgMembership).filter(
        OrgMembership.user_id == member.id,
        OrgMembership.org_id == team.id
    ).first()
    
    if membership:
        db.delete(membership)
        db.commit()
        
        return {"success": True}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Member not found in team"
    )


@router.get("/teams/{team_id}/usage")
async def get_team_usage(
    team_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get team usage statistics.
    
    Rules:   must verify user has access to team
    """
    # Find team
    team = db.query(User).filter(User.public_id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Verify user has access to team
    membership = db.query(OrgMembership).filter(
        OrgMembership.user_id == current_user.id,
        OrgMembership.org_id == team.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view team usage"
        )
    
    # Get team agents
    team_agents = db.query(Agent).filter(Agent.owner_id == team.id).all()
    agent_ids = [agent.id for agent in team_agents]
    
    # Build query for agent runs
    from sqlalchemy import func
    
    query = db.query(
        func.count(AgentRun.id).label("total_runs"),
        func.sum(AgentRun.credits_used).label("total_credits"),
        func.avg(AgentRun.credits_used).label("avg_credits_per_run")
    ).filter(AgentRun.agent_id.in_(agent_ids))
    
    if start_date:
        query = query.filter(AgentRun.created_at >= start_date)
    if end_date:
        query = query.filter(AgentRun.created_at <= end_date)
    
    stats = query.first()
    
    # Get member count
    member_count = db.query(OrgMembership).filter(
        OrgMembership.org_id == team.id
    ).count()
    
    # Get credit balance
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == team.id
    ).first()
    
    return {
        "team_id": team_id,
        "team_name": team.full_name,
        "member_count": member_count,
        "agent_count": len(agent_ids),
        "total_runs": stats.total_runs or 0,
        "total_credits_used": float(stats.total_credits or 0),
        "avg_credits_per_run": float(stats.avg_credits_per_run or 0),
        "credit_balance": credit_account.balance if credit_account else 0,
        "currency": credit_account.currency if credit_account else "USD"
    }