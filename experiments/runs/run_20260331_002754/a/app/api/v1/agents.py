"""app/api/v1/agents.py — Agent management and execution endpoints.

exports: router (agent endpoints)
used_by: app/api/v1/router.py → router inclusion
rules:   agent execution deducts credits; public agents are read-only for non-members
agent:   BackendEngineer | 2024-03-31 | created agent management endpoints
         message: "implement streaming response for agent execution with token counting"
"""

import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Header
from fastapi.responses import StreamingResponse

from app.services import ServiceContainer
from app.dependencies import get_services
from app.dependencies import get_current_user
from app.api.v1.schemas import (
    AgentCreate, AgentUpdate, AgentResponse, AgentListResponse,
    AgentRunRequest, AgentRunResponse, AgentSessionCreate, AgentSessionResponse,
    SessionMessageCreate, SessionMessageResponse, AgentSessionListResponse,
    SessionMessageListResponse, PaginationParams, ModelProvider
)

# Create router
router = APIRouter(tags=["agents"])


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    organization_id: int = Query(None, description="Filter by organization"),
    pagination: PaginationParams = Depends(),
    search: str = Query(None, description="Search by name or description"),
    model_provider: ModelProvider = Query(None, description="Filter by model provider"),
    is_public: bool = Query(None, description="Filter by public status"),
    is_active: bool = Query(None, description="Filter by active status"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """List agents.
    
    Rules:
        Returns agents from user's organizations
        Public agents are visible to all authenticated users
        Private agents only visible to organization members
    """
    try:
        result = await services.agents.list_agents(
            user_id=current_user.id,
            organization_id=organization_id,
            page=pagination.page,
            per_page=pagination.per_page,
            search=search,
            model_provider=model_provider,
            is_public=is_public,
            is_active=is_active,
        )
        return AgentListResponse(
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


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    organization_id: int = Query(..., description="Organization ID"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Create new agent.
    
    Rules:
        User must be organization member with create permissions
        Slug must be unique within organization
        Credits are checked before creation
    """
    try:
        # Check organization membership and permissions
        member = await services.organizations.get_organization_member(
            organization_id=organization_id,
            user_id=current_user.id,
        )
        if not member or not member.can_create_agents:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create agents",
            )
        
        agent = await services.agents.create_agent(
            organization_id=organization_id,
            creator_id=current_user.id,
            name=agent_data.name,
            slug=agent_data.slug,
            description=agent_data.description,
            system_prompt=agent_data.system_prompt,
            config=agent_data.config,
            model_provider=agent_data.model_provider,
            model_name=agent_data.model_name,
            max_tokens_per_session=agent_data.max_tokens_per_session,
            temperature=agent_data.temperature,
            is_public=agent_data.is_public,
        )
        return AgentResponse(**agent.dict() if hasattr(agent, 'dict') else agent)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Get agent details.
    
    Rules:
        Public agents are visible to all authenticated users
        Private agents only visible to organization members
    """
    try:
        agent = await services.agents.get_agent(agent_id)
        
        # Check permissions
        if not agent.is_public:
            # Check if user is member of agent's organization
            member = await services.organizations.get_organization_member(
                organization_id=agent.organization_id,
                user_id=current_user.id,
            )
            if not member and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this agent",
                )
        
        return AgentResponse(**agent.dict() if hasattr(agent, 'dict') else agent)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Update agent.
    
    Rules:
        User must be organization admin or agent creator
        Cannot change slug
    """
    try:
        agent = await services.agents.get_agent(agent_id)
        
        # Check permissions
        member = await services.organizations.get_organization_member(
            organization_id=agent.organization_id,
            user_id=current_user.id,
        )
        if not member or not member.can_create_agents:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update agent",
            )
        
        updated_agent = await services.agents.update_agent(
            agent_id=agent_id,
            updates=agent_data.dict(exclude_unset=True),
            updated_by=current_user.id,
        )
        return AgentResponse(**updated_agent.dict() if hasattr(updated_agent, 'dict') else updated_agent)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> None:
    """Delete agent (soft delete).
    
    Rules:
        User must be organization admin or agent creator
        Only soft delete (preserves data)
    """
    try:
        agent = await services.agents.get_agent(agent_id)
        
        # Check permissions
        member = await services.organizations.get_organization_member(
            organization_id=agent.organization_id,
            user_id=current_user.id,
        )
        if not member or not member.can_create_agents:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete agent",
            )
        
        await services.agents.delete_agent(
            agent_id=agent_id,
            deleted_by=current_user.id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{agent_id}/run", response_model=AgentRunResponse)
async def run_agent(
    agent_id: int,
    run_data: AgentRunRequest,
    x_organization_id: Optional[int] = Header(None, description="Organization ID for billing"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Run agent (non-streaming).
    
    Rules:
        User must have access to agent
        Credits are deducted before execution
        Returns complete response
    """
    try:
        # Determine organization for billing
        organization_id = x_organization_id
        if not organization_id:
            agent = await services.agents.get_agent(agent_id)
            organization_id = agent.organization_id
        
        # Check permissions
        if not agent.is_public:
            member = await services.organizations.get_organization_member(
                organization_id=organization_id,
                user_id=current_user.id,
            )
            if not member and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to run this agent",
                )
        
        # Run agent
        result = await services.agents.run_agent(
            agent_id=agent_id,
            organization_id=organization_id,
            user_id=current_user.id,
            prompt=run_data.prompt,
            session_id=run_data.session_id,
            parameters=run_data.parameters,
            stream=False,
        )
        
        return AgentRunResponse(
            response=result["response"],
            session_id=result["session_id"],
            message_id=result["message_id"],
            token_count=result["token_count"],
            credits_used=result["credits_used"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{agent_id}/run/stream")
async def run_agent_stream(
    agent_id: int,
    run_data: AgentRunRequest,
    x_organization_id: Optional[int] = Header(None, description="Organization ID for billing"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> StreamingResponse:
    """Run agent (streaming).
    
    Rules:
        User must have access to agent
        Credits are deducted before execution
        Streams response via SSE
    """
    try:
        # Determine organization for billing
        organization_id = x_organization_id
        if not organization_id:
            agent = await services.agents.get_agent(agent_id)
            organization_id = agent.organization_id
        
        # Check permissions
        if not agent.is_public:
            member = await services.organizations.get_organization_member(
                organization_id=organization_id,
                user_id=current_user.id,
            )
            if not member and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to run this agent",
                )
        
        # Generate streaming response
        async def event_generator():
            async for chunk in services.agents.run_agent_stream(
                agent_id=agent_id,
                organization_id=organization_id,
                user_id=current_user.id,
                prompt=run_data.prompt,
                session_id=run_data.session_id,
                parameters=run_data.parameters,
            ):
                yield chunk
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{agent_id}/sessions", response_model=AgentSessionListResponse)
async def list_agent_sessions(
    agent_id: int,
    pagination: PaginationParams = Depends(),
    is_active: bool = Query(None, description="Filter by active status"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """List agent sessions.
    
    Rules:
        User must have access to agent
        Returns user's own sessions only (unless admin)
    """
    try:
        agent = await services.agents.get_agent(agent_id)
        
        # Check permissions
        if not agent.is_public:
            member = await services.organizations.get_organization_member(
                organization_id=agent.organization_id,
                user_id=current_user.id,
            )
            if not member and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view agent sessions",
                )
        
        result = await services.agents.list_agent_sessions(
            agent_id=agent_id,
            user_id=current_user.id if not current_user.is_superuser else None,
            page=pagination.page,
            per_page=pagination.per_page,
            is_active=is_active,
        )
        
        return AgentSessionListResponse(
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


@router.post("/{agent_id}/sessions", response_model=AgentSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_session(
    agent_id: int,
    session_data: AgentSessionCreate = None,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Create agent session.
    
    Rules:
        User must have access to agent
        Creates new conversation session
    """
    try:
        agent = await services.agents.get_agent(agent_id)
        
        # Check permissions
        if not agent.is_public:
            member = await services.organizations.get_organization_member(
                organization_id=agent.organization_id,
                user_id=current_user.id,
            )
            if not member and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to create sessions",
                )
        
        session = await services.agents.create_agent_session(
            agent_id=agent_id,
            organization_id=agent.organization_id,
            user_id=current_user.id,
            title=session_data.title if session_data else None,
            metadata=session_data.metadata if session_data else {},
        )
        return AgentSessionResponse(**session.dict() if hasattr(session, 'dict') else session)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/sessions/{session_id}", response_model=AgentSessionResponse)
async def get_agent_session(
    session_id: uuid.UUID,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Get agent session details.
    
    Rules:
        User must own the session or be organization admin
    """
    try:
        session = await services.agents.get_agent_session(session_id)
        
        # Check permissions
        if session.user_id != current_user.id and not current_user.is_superuser:
            # Check if user is admin in organization
            member = await services.organizations.get_organization_member(
                organization_id=session.organization_id,
                user_id=current_user.id,
            )
            if not member or not member.can_create_agents:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this session",
                )
        
        return AgentSessionResponse(**session.dict() if hasattr(session, 'dict') else session)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/sessions/{session_id}/end", status_code=status.HTTP_204_NO_CONTENT)
async def end_agent_session(
    session_id: uuid.UUID,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> None:
    """End agent session.
    
    Rules:
        User must own the session or be organization admin
    """
    try:
        session = await services.agents.get_agent_session(session_id)
        
        # Check permissions
        if session.user_id != current_user.id and not current_user.is_superuser:
            member = await services.organizations.get_organization_member(
                organization_id=session.organization_id,
                user_id=current_user.id,
            )
            if not member or not member.can_create_agents:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to end this session",
                )
        
        await services.agents.end_agent_session(session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/sessions/{session_id}/messages", response_model=SessionMessageListResponse)
async def list_session_messages(
    session_id: uuid.UUID,
    pagination: PaginationParams = Depends(),
    role: str = Query(None, description="Filter by message role"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """List session messages.
    
    Rules:
        User must have access to session
        Returns paginated messages
    """
    try:
        session = await services.agents.get_agent_session(session_id)
        
        # Check permissions
        if session.user_id != current_user.id and not current_user.is_superuser:
            member = await services.organizations.get_organization_member(
                organization_id=session.organization_id,
                user_id=current_user.id,
            )
            if not member or not member.can_create_agents:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view session messages",
                )
        
        result = await services.agents.list_session_messages(
            session_id=session_id,
            page=pagination.page,
            per_page=pagination.per_page,
            role=role,
        )
        
        return SessionMessageListResponse(
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


@router.post("/sessions/{session_id}/messages", response_model=SessionMessageResponse, status_code=status.HTTP_201_CREATED)
async def create_session_message(
    session_id: uuid.UUID,
    message_data: SessionMessageCreate,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Add message to session.
    
    Rules:
        User must have access to session
        Session must be active
    """
    try:
        session = await services.agents.get_agent_session(session_id)
        
        # Check permissions
        if session.user_id != current_user.id and not current_user.is_superuser:
            member = await services.organizations.get_organization_member(
                organization_id=session.organization_id,
                user_id=current_user.id,
            )
            if not member or not member.can_create_agents:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to add messages",
                )
        
        # Check session is active
        if not session.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session is not active",
            )
        
        message = await services.agents.create_session_message(
            session_id=session_id,
            role=message_data.role,
            content=message_data.content,
            tool_calls=message_data.tool_calls,
            tool_call_id=message_data.tool_call_id,
            metadata=message_data.metadata,
        )
        return SessionMessageResponse(**message.dict() if hasattr(message, 'dict') else message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )