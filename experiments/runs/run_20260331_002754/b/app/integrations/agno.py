"""Agno framework integration for AgentHub."""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests

from flask import current_app

from app.models.agent import Agent, AgentVersion, AgentRun, AgentRunLog, AgentRunStatus


logger = logging.getLogger(__name__)


class AgnoClient:
    """Client for interacting with Agno AI Agent framework."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize Agno client.
        
        Args:
            api_key: Agno API key
            base_url: Agno API base URL
        """
        self.api_key = api_key or current_app.config.get('AGNO_API_KEY')
        self.base_url = base_url or current_app.config.get('AGNO_BASE_URL')
        
        if not self.api_key:
            raise ValueError('AGNO_API_KEY is required')
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        })
    
    def create_agent(self, name: str, config: Dict[str, Any], description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new agent in Agno.
        
        Args:
            name: Agent name
            config: Agent configuration
            description: Agent description
            
        Returns:
            Created agent data
        """
        url = f'{self.base_url}/v1/agents'
        
        payload = {
            'name': name,
            'config': config,
        }
        
        if description:
            payload['description'] = description
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to create agent in Agno: {e}')
            raise
    
    def update_agent(self, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing agent in Agno.
        
        Args:
            agent_id: Agno agent ID
            config: Updated agent configuration
            
        Returns:
            Updated agent data
        """
        url = f'{self.base_url}/v1/agents/{agent_id}'
        
        payload = {
            'config': config,
        }
        
        try:
            response = self.session.patch(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to update agent in Agno: {e}')
            raise
    
    def execute_agent(self, agent_id: str, input_data: Dict[str, Any], 
                     timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute an agent in Agno.
        
        Args:
            agent_id: Agno agent ID
            input_data: Input data for agent
            timeout: Execution timeout in seconds
            
        Returns:
            Agent execution result
        """
        url = f'{self.base_url}/v1/agents/{agent_id}/execute'
        
        payload = {
            'input': input_data,
        }
        
        if timeout:
            payload['timeout'] = timeout
        
        try:
            response = self.session.post(url, json=payload, timeout=timeout or 300)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f'Agent execution timeout: {agent_id}')
            raise TimeoutError(f'Agent execution timeout after {timeout or 300} seconds')
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to execute agent in Agno: {e}')
            raise
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get agent status from Agno.
        
        Args:
            agent_id: Agno agent ID
            
        Returns:
            Agent status data
        """
        url = f'{self.base_url}/v1/agents/{agent_id}/status'
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to get agent status from Agno: {e}')
            raise
    
    def list_agents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all agents in Agno.
        
        Args:
            limit: Maximum number of agents to return
            offset: Pagination offset
            
        Returns:
            List of agents
        """
        url = f'{self.base_url}/v1/agents'
        params = {'limit': limit, 'offset': offset}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json().get('agents', [])
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to list agents from Agno: {e}')
            raise
    
    def delete_agent(self, agent_id: str) -> bool:
        """Delete agent from Agno.
        
        Args:
            agent_id: Agno agent ID
            
        Returns:
            True if successful
        """
        url = f'{self.base_url}/v1/agents/{agent_id}'
        
        try:
            response = self.session.delete(url)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to delete agent from Agno: {e}')
            raise


class AgentExecutor:
    """Orchestrator for executing agents in AgentHub."""
    
    def __init__(self, agno_client: Optional[AgnoClient] = None):
        """Initialize agent executor.
        
        Args:
            agno_client: Agno client instance
        """
        self.agno_client = agno_client or AgnoClient()
    
    def execute_agent_run(self, agent_run: AgentRun) -> AgentRun:
        """Execute an agent run.
        
        Args:
            agent_run: AgentRun instance to execute
            
        Returns:
            Updated AgentRun instance
        """
        # Mark run as started
        agent_run.start()
        
        try:
            # Get agent version
            agent_version = agent_run.agent_version
            
            if not agent_version:
                raise ValueError('No active agent version found')
            
            # Parse input data
            input_data = agent_run.get_input()
            
            # Create run log
            start_log = AgentRunLog(
                run_id=agent_run.id,
                level='info',
                message=f'Starting execution of agent {agent_run.agent.name}',
                metadata=json.dumps({'input_data': input_data})
            )
            
            # Execute agent in Agno
            result = self.agno_client.execute_agent(
                agent_id=agent_version.agno_agent_id,
                input_data=input_data,
                timeout=current_app.config.get('AGENT_TIMEOUT_SECONDS', 300)
            )
            
            # Mark run as completed
            agent_run.complete(result.get('output', {}))
            
            # Calculate cost (simplified - could be based on execution time, tokens, etc.)
            cost = self._calculate_cost(agent_run.agent.price_per_run, result)
            agent_run.cost_usd = cost
            
            # Create completion log
            completion_log = AgentRunLog(
                run_id=agent_run.id,
                level='info',
                message=f'Agent execution completed successfully',
                metadata=json.dumps({
                    'execution_time_ms': agent_run.execution_time_ms,
                    'cost_usd': float(cost),
                    'result_summary': self._summarize_result(result)
                })
            )
            
            # Update agent run count
            agent_run.agent.run_count += 1
            
            return agent_run
            
        except TimeoutError:
            agent_run.timeout()
            timeout_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Agent execution timeout after {current_app.config.get("AGENT_TIMEOUT_SECONDS", 300)} seconds',
            )
            return agent_run
            
        except Exception as e:
            agent_run.fail(str(e))
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Agent execution failed: {str(e)}',
                metadata=json.dumps({'error_type': type(e).__name__})
            )
            return agent_run
    
    def _calculate_cost(self, base_price: float, result: Dict[str, Any]) -> float:
        """Calculate cost for agent execution.
        
        Args:
            base_price: Base price per run
            result: Agent execution result
            
        Returns:
            Calculated cost
        """
        # Simple implementation: use base price
        # Could be enhanced with usage-based pricing (tokens, execution time, etc.)
        return float(base_price)
    
    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Create a summary of agent execution result.
        
        Args:
            result: Agent execution result
            
        Returns:
            Result summary
        """
        output = result.get('output', {})
        
        if isinstance(output, dict):
            # Try to extract text summary
            if 'text' in output:
                return str(output['text'])[:100] + '...' if len(str(output['text'])) > 100 else str(output['text'])
            elif 'result' in output:
                return str(output['result'])[:100] + '...' if len(str(output['result'])) > 100 else str(output['result'])
        
        return 'Execution completed'
    
    def create_agent_version(self, agent: Agent, config: Dict[str, Any], 
                           version: str = '1.0.0') -> AgentVersion:
        """Create a new agent version in Agno.
        
        Args:
            agent: Agent instance
            config: Agent configuration
            version: Version string
            
        Returns:
            Created AgentVersion instance
        """
        # Create agent in Agno
        agno_agent = self.agno_client.create_agent(
            name=agent.name,
            config=config,
            description=agent.description
        )
        
        # Create agent version in database
        agent_version = AgentVersion(
            agent_id=agent.id,
            version=version,
            config=json.dumps(config),
            agno_agent_id=agno_agent['id'],
            is_active=True
        )
        
        # Deactivate previous versions
        for old_version in agent.versions:
            if old_version.is_active:
                old_version.is_active = False
        
        return agent_version