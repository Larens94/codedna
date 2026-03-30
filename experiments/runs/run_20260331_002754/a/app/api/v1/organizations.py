"""app/api/v1/organizations.py — Organization management endpoints.

exports: router (organization endpoints)
used_by: app/api/v1/router.py → router inclusion
rules:   organization memberships enforce RBAC; slug must be unique
agent:   BackendEngineer | 2024-03-31 | created organization management endpoints
         message: "verify organization slug uniqueness across tenants"
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from pydantic import EmailStr

from app.services import ServiceContainer, get_services
from app.dependencies import get_current_user
from app.api.v1.schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationWithStatsResponse, OrganizationListResponse,
    OrganizationMemberCreate, OrganizationMemberInvite, OrganizationMemberUpdate,
    OrganizationMemberResponse, OrganizationMemberListResponse, PaginationParams
)

# Create router
router = APIRouter(tags=["organizations"])


@router.get("/", response_model=OrganizationListResponse)
async def list_organizations(
    pagination: PaginationParams = Depends(),
    search: str = Query(None, description="Search by name or slug"),
    is_active: bool = Query(None, description="Filter by active status"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """List organizations (admin only).
    
    Rules:
        Requires superuser privileges
        Returns paginated list of organizations
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    try:
        result = await services.organizations.list_organizations(
            page=pagination.page,
            per_page=pagination.per_page,
            search=search,
            is_active=is_active,
        )
        return OrganizationListResponse(
            items=result["items"],
            total=result["total"],
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=(result["total"] + pagination.per_page - 1) // pagination.per_page,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Create new organization.
    
    Rules:
        Requires authentication
        Creator becomes organization owner
        Slug must be globally unique
    """
    try:
        organization = await services.organizations.create_organization(
            creator_id=current_user.id,
            name=org_data.name,
            slug=org_data.slug,
            description=org_data.description,
            billing_email=org_data.billing_email,
            plan_tier=org_data.plan_tier,
            monthly_credit_limit=org_data.monthly_credit_limit,
        )
        return OrganizationResponse(**organization.dict() if hasattr(organization, 'dict') else organization)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/my", response_model=List[OrganizationResponse])
async def get_my_organizations(
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Get current user's organizations.
    
    Rules:
        Returns all organizations where user is a member
        Includes role information
    """
    try:
        organizations = await services.users.get_user_organizations(current_user.id)
        return organizations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{organization_id}", response_model=OrganizationWithStatsResponse)
async def get_organization(
    organization_id: int = Path(..., description="Organization ID"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Get organization details.
    
    Rules:
        User must be organization member
        Returns organization with statistics
    """
    try:
        # Check membership
        member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not member and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )
        
        organization = await services.organizations.get_organization(organization_id)
        stats = await services.organizations.get_organization_stats(organization_id)
        
        return OrganizationWithStatsResponse(
            **organization.dict() if hasattr(organization, 'dict') else organization,
            stats=stats,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: int,
    org_data: OrganizationUpdate,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Update organization.
    
    Rules:
        User must be organization owner or admin
        Slug cannot be changed
    """
    try:
        # Check permissions
        member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not member or not member.can_manage_organization:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        organization = await services.organizations.update_organization(
            organization_id=organization_id,
            updates=org_data.dict(exclude_unset=True),
            updated_by=current_user.id,
        )
        return OrganizationResponse(**organization.dict() if hasattr(organization, 'dict') else organization)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> None:
    """Delete organization (soft delete).
    
    Rules:
        User must be organization owner
        Only soft delete (preserves data)
    """
    try:
        # Check permissions
        member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not member or member.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owner can delete organization",
            )
        
        await services.organizations.delete_organization(
            organization_id=organization_id,
            deleted_by=current_user.id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{organization_id}/members", response_model=OrganizationMemberListResponse)
async def list_organization_members(
    organization_id: int,
    pagination: PaginationParams = Depends(),
    role: str = Query(None, description="Filter by role"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """List organization members.
    
    Rules:
        User must be organization member
        Returns paginated list of members
    """
    try:
        # Check membership
        member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not member and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )
        
        result = await services.organizations.list_organization_members(
            organization_id=organization_id,
            page=pagination.page,
            per_page=pagination.per_page,
            role=role,
        )
        
        return OrganizationMemberListResponse(
            items=result["items"],
            total=result["total"],
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=(result["total"] + pagination.per_page - 1) // pagination.per_page,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{organization_id}/members", response_model=OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    organization_id: int,
    member_data: OrganizationMemberCreate,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Add member to organization.
    
    Rules:
        User must be organization owner or admin
        Cannot add duplicate members
        Role must be valid
    """
    try:
        # Check permissions
        member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not member or not member.can_manage_members:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to manage members",
            )
        
        new_member = await services.organizations.add_organization_member(
            organization_id=organization_id,
            user_id=member_data.user_id,
            role=member_data.role,
            invited_by=current_user.id,
        )
        return OrganizationMemberResponse(**new_member.dict() if hasattr(new_member, 'dict') else new_member)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{organization_id}/members/invite", status_code=status.HTTP_201_CREATED)
async def invite_organization_member(
    organization_id: int,
    invite_data: OrganizationMemberInvite,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Invite member to organization via email.
    
    Rules:
        User must be organization owner or admin
        Sends invitation email
        Creates invitation record
    """
    try:
        # Check permissions
        member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not member or not member.can_manage_members:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to invite members",
            )
        
        invitation = await services.organizations.invite_organization_member(
            organization_id=organization_id,
            email=invite_data.email,
            role=invite_data.role,
            invited_by=current_user.id,
        )
        return {"message": "Invitation sent", "invitation_id": invitation.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{organization_id}/members/{user_id}", response_model=OrganizationMemberResponse)
async def update_organization_member(
    organization_id: int,
    user_id: int,
    member_data: OrganizationMemberUpdate,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Update organization member role.
    
    Rules:
        User must be organization owner or admin
        Cannot change owner role unless transferring ownership
        Cannot downgrade own role below admin
    """
    try:
        # Check permissions
        requester = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not requester or not requester.can_manage_members:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to manage members",
            )
        
        # Cannot change owner role unless transferring ownership
        target_member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=user_id,
        )
        if target_member.role == "owner" and member_data.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change owner role. Transfer ownership first.",
            )
        
        updated_member = await services.organizations.update_organization_member(
            organization_id=organization_id,
            user_id=user_id,
            role=member_data.role,
            updated_by=current_user.id,
        )
        return OrganizationMemberResponse(**updated_member.dict() if hasattr(updated_member, 'dict') else updated_member)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{organization_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    organization_id: int,
    user_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> None:
    """Remove member from organization.
    
    Rules:
        User must be organization owner or admin
        Cannot remove owner
        Cannot remove yourself unless owner
    """
    try:
        # Check permissions
        requester = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not requester or not requester.can_manage_members:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to remove members",
            )
        
        # Cannot remove owner
        target_member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=user_id,
        )
        if target_member.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove organization owner",
            )
        
        # Cannot remove yourself unless you're the owner
        if user_id == current_user.id and requester.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove yourself as non-owner",
            )
        
        await services.organizations.remove_organization_member(
            organization_id=organization_id,
            user_id=user_id,
            removed_by=current_user.id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{organization_id}/transfer-ownership", response_model=OrganizationMemberResponse)
async def transfer_organization_ownership(
    organization_id: int,
    new_owner_user_id: int = Query(..., description="New owner user ID"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Transfer organization ownership.
    
    Rules:
        Current user must be organization owner
        New owner must already be organization member
        Current owner becomes admin
    """
    try:
        # Check current user is owner
        current_member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not current_member or current_member.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owner can transfer ownership",
            )
        
        # Check new owner is member
        new_owner_member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=new_owner_user_id,
        )
        if not new_owner_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New owner must already be organization member",
            )
        
        transferred = await services.organizations.transfer_organization_ownership(
            organization_id=organization_id,
            current_owner_id=current_user.id,
            new_owner_id=new_owner_user_id,
        )
        return OrganizationMemberResponse(**transferred.dict() if hasattr(transferred, 'dict') else transferred)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )