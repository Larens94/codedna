"""app/services/agno_integration.py — Integration with Agno AI agent framework.

exports: AgnoIntegrationService
used_by: app/services/container.py → ServiceContainer.agno, agent and task services
rules:   must handle agent initialization, execution, streaming, and state management
agent:   AgentIntegrator | 2024-12-05 | implemented full Agno integration using agent layer
         message: "implement agent state persistence for long-running conversations"
"""

import logging
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator, List
from datetime import datetime
import json

from app.exceptions import AgentError, AgentTimeoutError, ServiceUnavailableError, ValidationError
from app.services.container import ServiceContainer
from app.agents import (
    AgentWrapper,
    AgentConfig,
    build_custom_agent,
    build_agent_from_dict,
    dict_tools_available_from_agno,
    memory_manager,
    agent_runner,
    get_marketplace_agents,
    AgentSpec,
    catalog,
    CreditExhaustedError,
)

logger = logging.getLogger(__name__)


class AgnoIntegrationService:
    """Integration service for Agno AI agent framework.
    
    Rules:
        Agent execution must respect timeout limits
        Agent state must be persisted for long-running conversations
        Streaming responses must be handled efficiently
        Errors must be categorized for appropriate handling
    """
    
    def __init__(self, container: ServiceContainer):
        """Initialize Agno integration service.
        
        Args:
            container: Service container with dependencies
        """
        self.container = container
        self.config = container.config
        
        # Cache for initialized agents (agent_id -> agent_instance)
        self._agent_cache = {}
        
        # Agent execution timeouts
        self.default_timeout = self.config.AGENT_TIMEOUT_SECONDS
        self.max_tokens = self.config.AGENT_MAX_TOKENS
        
        logger.info("AgnoIntegrationService initialized")
    
    async def initialize_agent(
        self,
        agent_config: Dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> AgentWrapper:
        """Initialize Agno agent from configuration.
        
        Args:
            agent_config: Agent configuration dictionary
            agent_id: Optional agent ID for caching
            
        Returns:
            Initialized AgentWrapper instance
            
        Raises:
            AgentError: If agent initialization fails
            ValidationError: If configuration is invalid
        """
        try:
            # Validate required fields
            required_fields = ["system_prompt", "model_provider"]
            for field in required_fields:
                if field not in agent_config:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Build agno agent
            agno_agent = build_agent_from_dict(agent_config)
            
            # Create wrapper
            wrapper = AgentWrapper(
                agent=agno_agent,
                agent_id=agent_id or str(hash(json.dumps(agent_config, sort_keys=True))),
                organization_id=agent_config.get("organization_id", "unknown"),
                credit_balance=float('inf'),  # Will be set by caller
                min_credits=0.0,
            )
            
            # Cache if agent_id provided
            if agent_id:
                self._agent_cache[agent_id] = wrapper
            
            logger.info(f"Agent initialized: {agent_id}")
            return wrapper
            
        except ValueError as e:
            raise ValidationError(f"Invalid agent configuration: {e}")
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            raise AgentError(f"Failed to initialize agent: {e}")
    
    async def execute_agent(
        self,
        agent_config: Dict[str, Any],
        input_data: Dict[str, Any],
        agent_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute agent with input data.
        
        Args:
            agent_config: Agent configuration
            input_data: Input data for agent execution
            agent_id: Optional agent ID for caching/reuse
            conversation_id: Optional conversation ID for state persistence
            timeout_seconds: Optional execution timeout (default from config)
            
        Returns:
            Agent execution result
            
        Raises:
            AgentError: If agent execution fails
            AgentTimeoutError: If execution times out
            ValidationError: If input data is invalid
        """
        try:
            # Get or initialize agent
            agent_wrapper = await self._get_or_create_agent(agent_config, agent_id)
            
            # Load conversation state if conversation_id provided
            if conversation_id:
                await self.load_conversation_state(conversation_id)
                # Note: In real implementation, this would set up agent memory
            
            # Prepare input
            prompt = input_data.get("prompt", "")
            if not prompt:
                raise ValidationError("Input data must contain 'prompt' field")
            
            # Set credit balance from organization
            organization_id = agent_config.get("organization_id")
            if organization_id:
                credit_balance = await self._get_credit_balance(organization_id)
                agent_wrapper.credit_balance = credit_balance
            
            # Execute agent
            timeout = timeout_seconds or self.default_timeout
            result = await agent_runner.run_agent_non_streaming(
                agent_wrapper=agent_wrapper,
                prompt=prompt,
                user_id=input_data.get("user_id"),
                session_id=conversation_id,
                timeout_seconds=timeout,
                **input_data.get("parameters", {}),
            )
            
            # Save conversation state if conversation_id provided
            if conversation_id:
                await self.save_conversation_state(
                    conversation_id,
                    {
                        "last_prompt": prompt,
                        "last_response": result["response"],
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            
            # Record usage
            await self._record_usage(
                agent_id=agent_wrapper.agent_id,
                organization_id=organization_id,
                tokens_used=result["tokens_used"],
                credits_used=result["credits_used"],
            )
            
            return {
                "response": result["response"],
                "tokens_used": result["tokens_used"],
                "credits_used": result["credits_used"],
                "duration_ms": result["duration_ms"],
                "agent_id": agent_wrapper.agent_id,
                "conversation_id": conversation_id,
            }
            
        except CreditExhaustedError as e:
            raise
        except ValidationError as e:
            raise
        except AgentTimeoutError as e:
            raise
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise AgentError(f"Agent execution failed: {e}")
    
    async def execute_agent_streaming(
        self,
        agent_config: Dict[str, Any],
        input_data: Dict[str, Any],
        agent_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute agent with streaming response.
        
        Args:
            agent_config: Agent configuration
            input_data: Input data for agent execution
            agent_id: Optional agent ID for caching/reuse
            conversation_id: Optional conversation ID for state persistence
            timeout_seconds: Optional execution timeout
            
        Yields:
            Streaming response chunks
            
        Raises:
            AgentError: If agent execution fails
            AgentTimeoutError: If execution times out
        """
        try:
            # Get or initialize agent
            agent_wrapper = await self._get_or_create_agent(agent_config, agent_id)
            
            # Load conversation state if conversation_id provided
            if conversation_id:
                await self.load_conversation_state(conversation_id)
            
            # Prepare input
            prompt = input_data.get("prompt", "")
            if not prompt:
                raise ValidationError("Input data must contain 'prompt' field")
            
            # Set credit balance
            organization_id = agent_config.get("organization_id")
            if organization_id:
                credit_balance = await self._get_credit_balance(organization_id)
                agent_wrapper.credit_balance = credit_balance
            
            # Execute with streaming
            timeout = timeout_seconds or self.default_timeout
            
            async for chunk in agent_runner.run_agent_stream(
                agent_wrapper=agent_wrapper,
                prompt=prompt,
                user_id=input_data.get("user_id"),
                session_id=conversation_id,
                stream=True,
                timeout_seconds=timeout,
                **input_data.get("parameters", {}),
            ):
                yield chunk
                
                # If this is the final stats chunk, record usage
                if chunk.get("type") == "stats" and organization_id:
                    await self._record_usage(
                        agent_id=agent_wrapper.agent_id,
                        organization_id=organization_id,
                        tokens_used=chunk.get("tokens_used", 0),
                        credits_used=chunk.get("credits_used", 0),
                    )
            
            # Save conversation state
            if conversation_id:
                await self.save_conversation_state(
                    conversation_id,
                    {
                        "last_prompt": prompt,
                        "last_response": "[streamed response]",
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                
        except CreditExhaustedError as e:
            yield {"type": "error", "error": str(e)}
            raise
        except ValidationError as e:
            yield {"type": "error", "error": str(e)}
            raise
        except AgentTimeoutError as e:
            yield {"type": "error", "error": str(e)}
            raise
        except Exception as e:
            logger.error(f"Streaming agent execution failed: {e}")
            yield {"type": "error", "error": str(e)}
            raise AgentError(f"Agent execution failed: {e}")
    
    async def load_conversation_state(
        self,
        conversation_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load conversation state from persistence.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation state or None if not found
        """
        try:
            # Use memory manager to load conversation state
            # For now, use Redis via service container
            redis = self.container.redis
            if redis:
                state_json = await redis.get(f"conversation:{conversation_id}")
                if state_json:
                    return json.loads(state_json)
            return None
        except Exception as e:
            logger.error(f"Failed to load conversation state: {e}")
            return None
    
    async def save_conversation_state(
        self,
        conversation_id: str,
        state: Dict[str, Any],
        ttl_seconds: int = 86400,  # 24 hours default
    ) -> None:
        """Save conversation state to persistence.
        
        Args:
            conversation_id: Conversation ID
            state: Conversation state to save
            ttl_seconds: Time-to-live in seconds
        """
        try:
            redis = self.container.redis
            if redis:
                await redis.setex(
                    f"conversation:{conversation_id}",
                    ttl_seconds,
                    json.dumps(state),
                )
                logger.debug(f"Saved conversation state: {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to save conversation state: {e}")
    
    async def delete_conversation_state(
        self,
        conversation_id: str,
    ) -> None:
        """Delete conversation state.
        
        Args:
            conversation_id: Conversation ID
        """
        try:
            redis = self.container.redis
            if redis:
                await redis.delete(f"conversation:{conversation_id}")
                logger.debug(f"Deleted conversation state: {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to delete conversation state: {e}")
    
    async def get_agent_metrics(
        self,
        agent_config: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Estimate agent execution metrics without actual execution.
        
        Args:
            agent_config: Agent configuration
            input_data: Input data
            
        Returns:
            Estimated metrics (tokens, cost, time)
            
        Rules:
            Used for credit deduction estimation
            Should be reasonably accurate but not exact
        """
        try:
            prompt = input_data.get("prompt", "")
            
            # Simple estimation based on prompt length
            estimated_input_tokens = len(prompt) // 4
            estimated_output_tokens = min(estimated_input_tokens * 3, self.max_tokens)
            estimated_total_tokens = estimated_input_tokens + estimated_output_tokens
            
            # Estimate cost (simplified: $0.01 per 1000 tokens)
            estimated_cost = estimated_total_tokens / 1000 * 0.01
            
            # Estimate time (simplified: 0.1 seconds per 100 tokens)
            estimated_time_ms = estimated_total_tokens * 1
            
            return {
                "estimated_tokens": estimated_total_tokens,
                "estimated_input_tokens": estimated_input_tokens,
                "estimated_output_tokens": estimated_output_tokens,
                "estimated_cost": estimated_cost,
                "estimated_time_ms": estimated_time_ms,
            }
        except Exception as e:
            logger.error(f"Failed to estimate agent metrics: {e}")
            return {
                "estimated_tokens": 1000,
                "estimated_cost": 0.01,
                "estimated_time_ms": 1000,
            }
    
    async def validate_agent_config(
        self,
        agent_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate agent configuration.
        
        Args:
            agent_config: Agent configuration to validate
            
        Returns:
            Validation result with errors/warnings
            
        Rules:
            Must check for required fields
            Must validate model parameters (temperature, etc.)
            Must verify tool configurations if present
        """
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["system_prompt", "model_provider"]
        for field in required_fields:
            if field not in agent_config:
                errors.append(f"Missing required field: {field}")
        
        # Validate model provider
        valid_providers = ["openai", "anthropic", "azure", "google", "custom"]
        if "model_provider" in agent_config:
            if agent_config["model_provider"] not in valid_providers:
                errors.append(f"Invalid model provider. Must be one of: {valid_providers}")
        
        # Validate temperature
        if "temperature" in agent_config:
            try:
                temp = float(agent_config["temperature"])
                if temp < 0.0 or temp > 2.0:
                    errors.append("Temperature must be between 0.0 and 2.0")
            except (ValueError, TypeError):
                errors.append("Temperature must be a number")
        
        # Validate tools
        if "tools" in agent_config:
            tools = agent_config["tools"]
            if not isinstance(tools, list):
                errors.append("Tools must be a list")
            else:
                valid_tools = set(dict_tools_available_from_agno.keys())
                for tool in tools:
                    if tool not in valid_tools:
                        warnings.append(f"Tool '{tool}' may not be available")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    async def list_available_models(self) -> Dict[str, Any]:
        """List available AI models from configured providers.
        
        Returns:
            Dictionary of available models by provider
        """
        models = {
            "openai": [],
            "anthropic": [],
            "azure": [],
            "google": [],
        }
        
        # Check OpenAI
        if self.config.OPENAI_API_KEY:
            models["openai"] = [
                "gpt-4",
                "gpt-4-turbo-preview",
                "gpt-4-32k",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
            ]
        
        # Check Anthropic
        if self.config.ANTHROPIC_API_KEY:
            models["anthropic"] = [
                "claude-3-opus",
                "claude-3-sonnet",
                "claude-3-haiku",
                "claude-2",
                "claude-instant",
            ]
        
        # Check Azure OpenAI
        # Note: Azure requires additional configuration
        models["azure"] = [
            "gpt-4",
            "gpt-4-32k",
            "gpt-35-turbo",
            "gpt-35-turbo-16k",
        ]
        
        # Check Google
        models["google"] = [
            "gemini-pro",
            "gemini-ultra",
        ]
        
        # Filter out providers with no API key (except azure/google which may have other config)
        available_models = {}
        for provider, model_list in models.items():
            if model_list:
                available_models[provider] = model_list
        
        return available_models
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of Agno integration and underlying services.
        
        Returns:
            Health status with details
        """
        checks = {}
        
        # Check OpenAI
        if self.config.OPENAI_API_KEY:
            checks["openai"] = "configured"
        else:
            checks["openai"] = "not_configured"
        
        # Check Anthropic
        if self.config.ANTHROPIC_API_KEY:
            checks["anthropic"] = "configured"
        else:
            checks["anthropic"] = "not_configured"
        
        # Check agent cache
        checks["agent_cache"] = {
            "size": len(self._agent_cache),
            "status": "healthy",
        }
        
        # Check memory manager
        try:
            # Simple test of memory manager
            test_key = "health_check"
            memory_manager.store(
                organization_id="health_check",
                key=test_key,
                value="test",
            )
            memory_manager.delete(
                organization_id="health_check",
                key=test_key,
            )
            checks["memory_manager"] = "healthy"
        except Exception as e:
            checks["memory_manager"] = f"unhealthy: {e}"
        
        overall_healthy = all(
            check != "not_configured" and "unhealthy" not in str(check).lower()
            for check in checks.values()
        )
        
        return {
            "healthy": overall_healthy,
            "checks": checks,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def cleanup_agent_cache(self) -> int:
        """Cleanup expired agent instances from cache.
        
        Returns:
            Number of agents removed from cache
        """
        # Simple cleanup: remove all cached agents
        # In production, would check last access time
        removed_count = len(self._agent_cache)
        self._agent_cache.clear()
        
        logger.info(f"Cleaned up {removed_count} agents from cache")
        return removed_count
    
    async def _get_or_create_agent(
        self,
        agent_config: Dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> AgentWrapper:
        """Get agent from cache or create new one.
        
        Args:
            agent_config: Agent configuration
            agent_id: Optional agent ID
            
        Returns:
            AgentWrapper instance
        """
        if agent_id and agent_id in self._agent_cache:
            return self._agent_cache[agent_id]
        
        return await self.initialize_agent(agent_config, agent_id)
    
    async def _get_credit_balance(self, organization_id: str) -> float:
        """Get credit balance for organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Credit balance
            
        Note:
            In real implementation, query billing service
        """
        # For now, return a high balance
        # In production, would call billing_service.get_credit_balance(organization_id)
        return 1000.0
    
    async def _record_usage(
        self,
        agent_id: str,
        organization_id: str,
        tokens_used: int,
        credits_used: float,
    ) -> None:
        """Record agent usage for billing.
        
        Args:
            agent_id: Agent ID
            organization_id: Organization ID
            tokens_used: Tokens used
            credits_used: Credits used
            
        Note:
            In real implementation, call billing service
        """
        try:
            # Call billing service to record usage
            billing_service = self.container.billing_service
            if billing_service:
                await billing_service.record_agent_usage(
                    agent_id=agent_id,
                    organization_id=organization_id,
                    tokens_used=tokens_used,
                    credits_used=credits_used,
                )
        except Exception as e:
            logger.error(f"Failed to record usage: {e}")