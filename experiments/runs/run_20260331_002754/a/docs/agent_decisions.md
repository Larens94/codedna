# Agent Integration Layer Design Decisions

## Overview
Date: 2024-12-05
Agent: AgentIntegrator
Purpose: Document architectural decisions for the AI agent integration layer

## 1. AgentWrapper Design

### Decision: Token Counting Strategy
- **Problem**: Need to track token usage for billing and rate limiting
- **Solution**: Extract token counts from agno response metadata
- **Implementation**: `AgentWrapper._extract_tokens_from_response()` method
- **Fallback**: When metadata not available, estimate tokens using character count (1 token ≈ 4 chars)
- **Rationale**: Must support both exact counting (when available) and estimation

### Decision: Credit Enforcement
- **Problem**: Prevent execution when organization lacks credits
- **Solution**: `CreditExhaustedError` (HTTP 402) raised before execution
- **Implementation**: `AgentWrapper.check_credits()` method with estimated cost check
- **Rationale**: Better to fail fast than incur debt

### Decision: Instruction Sanitization
- **Problem**: Prevent injection attacks via agent prompts
- **Solution**: Strip HTML tags and limit length to 10k characters
- **Implementation**: `AgentWrapper._sanitize_instruction()` using html.escape and regex
- **Rationale**: Basic security measure for user-generated content

## 2. Marketplace Catalog

### Decision: AgentSpec Dataclass Structure
- **Problem**: Need consistent agent specifications for marketplace
- **Solution**: `AgentSpec` dataclass with validation
- **Fields**: name, slug, description, system_prompt, model_provider, model_name, temperature, max_tokens, tools list, memory_type, pricing_tier, tags
- **Rationale**: Comprehensive but extensible specification

### Decision: Pre-built Agents
- **Selection**: 6 agents covering common use cases:
  1. SEO Optimizer - content optimization
  2. Customer Support Bot - empathetic support
  3. Data Analyst - data analysis and visualization
  4. Code Reviewer - security and best practices
  5. Email Drafter - professional communication
  6. Research Assistant - research and summarization
- **Rationale**: Balanced mix of business, technical, and creative use cases

## 3. Agent Builder

### Decision: Configuration Validation
- **Problem**: Ensure agent configurations are valid before creation
- **Solution**: `AgentConfig` dataclass with `__post_init__` validation
- **Validation**: Required fields, temperature range, tool existence, token limits
- **Rationale**: Fail early with clear error messages

### Decision: Multi-provider Support
- **Problem**: Support different LLM providers
- **Solution**: `ModelProvider` enum and provider-specific model classes
- **Providers**: OpenAI, Anthropic, Azure, Google, Custom
- **Rationale**: Flexibility for users and future expansion

## 4. Tool Integrations

### Decision: Security Sandboxing
- **Problem**: Tools need to be secure, especially code execution and file access
- **Solution**: Each tool implements security checks
  - File tools: restrict to allowed directories
  - Code execution: timeout, dangerous pattern detection
  - Calculator: safe character set only
  - API calls: rate limiting and timeout
- **Rationale**: Security is non-negotiable for multi-tenant SaaS

### Decision: Tool Dictionary
- **Problem**: Need central registry of available tools
- **Solution**: `dict_tools_available_from_agno` global dictionary
- **Keys**: Tool names (web_search, file_read, etc.)
- **Values**: Tool instances
- **Rationale**: Easy lookup and dependency injection

## 5. Memory Management

### Decision: Dual Storage Strategy
- **Problem**: Need both key-value storage and semantic search
- **Solution**: SQLite for key-value with embeddings, in-memory vectors for similarity search
- **Implementation**: `MemoryManager` with SQLite backend and `VectorMemory` for vectors
- **Rationale**: SQLite provides persistence, vectors enable semantic search

### Decision: Namespace Isolation
- **Problem**: Memories must be isolated per organization/agent
- **Solution**: Namespace = `organization_id[:agent_id]`
- **Implementation**: All operations scoped to namespace
- **Rationale**: Multi-tenancy requirement

## 6. Agent Runner

### Decision: Streaming Architecture
- **Problem**: Need real-time streaming for better UX
- **Solution**: `run_agent_stream()` yielding SSE-compatible chunks
- **Chunk types**: "chunk", "complete", "error", "stats"
- **Rationale**: Standard format for frontend consumption

### Decision: Run Tracking
- **Problem**: Need to track agent executions for monitoring and debugging
- **Solution**: `AgentRunRecord` dataclass with comprehensive fields
- **Storage**: In-memory for now, database-backed in production
- **Rationale**: Essential for operational visibility

### Decision: Concurrency Control
- **Problem**: Prevent system overload from concurrent agent runs
- **Solution**: `asyncio.Semaphore` for limiting concurrent executions
- **Implementation**: `AgentRunner.semaphore` with configurable limit
- **Rationale**: Simple but effective rate limiting

## 7. Integration with Existing Services

### Decision: Service Container Integration
- **Problem**: Need to integrate with existing service architecture
- **Solution**: `AgnoIntegrationService` uses `ServiceContainer` for dependencies
- **Dependencies**: Redis for conversation state, billing service for credits
- **Rationale**: Leverage existing infrastructure

## 8. Error Handling

### Decision: Exception Hierarchy
- **Problem**: Need granular error handling for different failure modes
- **Solution**: Custom exceptions extending `AgentHubError`:
  - `CreditExhaustedError` (402) - insufficient credits
  - `AgentError` (500) - general agent failure
  - `AgentTimeoutError` (504) - execution timeout
  - `ServiceUnavailableError` (503) - external service down
- **Rationale**: Appropriate HTTP status codes and client handling

## 9. Performance Considerations

### Decision: Agent Caching
- **Problem**: Agent initialization can be expensive
- **Solution**: Cache initialized agents by agent_id
- **Implementation**: `_agent_cache` dictionary in `AgnoIntegrationService`
- **Rationale**: Reduce latency for repeated use

### Decision: Vector Store Loading
- **Problem**: Loading all embeddings from SQLite on every search is inefficient
- **Solution**: Lazy load vector stores per namespace
- **Implementation**: Load from DB only when first searched
- **Rationale**: Memory efficiency for infrequently accessed namespaces

## Future Considerations

1. **Memory Summarization**: Implement when context exceeds model limits
2. **More Tool Integrations**: Add vertical-specific tools
3. **Advanced Rate Limiting**: Token-based rate limiting, not just request count
4. **Distributed Execution**: Support for distributed agent execution across workers
5. **Model Fine-tuning**: Integration with fine-tuning pipelines
6. **Evaluation Framework**: Automated agent performance evaluation
7. **Cost Optimization**: Smart model selection based on task complexity
8. **Real-time Monitoring**: Live dashboards of agent performance metrics