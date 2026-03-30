# Agent Integration Layer Decisions

## Overview
Date: 2024-03-31
Author: Agent Integrator

## Decision 1: Local Agno Framework Integration
**Context**: The existing `AgnoClient` integrates with a remote Agno API service. However, requirements call for token counting, memory management, and direct agent wrapping which suggests using the Agno framework as a Python library.

**Decision**: Implement a new local integration layer using the `agno` Python package (assumed to be available) while maintaining backward compatibility with the remote API client for existing deployments.

**Rationale**:
- Token counting and memory management require low-level access to agent execution
- Custom agent building (studio) needs direct framework integration
- Streaming output and live testing are easier with local agents
- Can still support remote Agno agents via the existing client

**Implementation Plan**:
1. Create `app/agents/` module with core components
2. Implement `AgentWrapper` that wraps `agno.Agent`
3. Add token counting via `tiktoken` or Agno's built-in token counting
4. Implement persistent memory using SQLAlchemy with vector similarity search (optional)
5. Build marketplace catalog with predefined AgentSpecs
6. Create agent studio for custom agent configuration
7. Implement streaming agent runner

## Decision 2: Token Counting Strategy
**Context**: Need to track token usage for cost calculation and credit enforcement.

**Decision**: Use `tiktoken` for OpenAI models and fallback to approximate character counting for other models. Token counting will be done in `AgentWrapper` by intercepting prompts and completions.

**Rationale**:
- `tiktoken` is the official OpenAI tokenizer
- Provides accurate token counts for GPT models
- For other models, approximate using characters (avg 4 chars per token)
- Token counts will be logged to `AgentRun` for billing

**Implementation**:
- Add `TokenCounter` utility class
- Integrate with `AgentWrapper.run()` and `AgentWrapper.stream()`
- Store token counts in `AgentRun` metadata

## Decision 3: Persistent Memory Implementation
**Context**: Agents need memory across sessions for context preservation.

**Decision**: Implement a simple key-value memory store with similarity search using SQLAlchemy and cosine similarity on sentence embeddings (via `sentence-transformers` or OpenAI embeddings).

**Rationale**:
- SQLAlchemy already used for data layer
- Embedding-based similarity provides semantic search
- Can scale to use vector databases (PGVector) in future
- Simple key-value meets basic memory needs

**Implementation**:
- `PersistentMemory` class with `set(key, value)`, `get(key)`, `search(query, limit=5)`
- Use `all-MiniLM-L6-v2` for embeddings (lightweight)
- Store embeddings in separate table with vector column (JSON array)
- Provide memory types: "none", "key_value", "semantic"

## Decision 4: Marketplace Catalog Design
**Context**: Need 6 pre-built agents for the marketplace.

**Decision**: Define `AgentSpec` dataclass with configuration for each agent type. Store specs in code (not DB) for version control.

**Rationale**:
- Easy to update and deploy
- No migration needed for spec changes
- Can be extended with user-defined agents later

**AgentSpec Fields**:
- `name`: Display name
- `slug`: URL identifier
- `description`: Marketing description
- `system_prompt`: Default system prompt
- `model`: Default model (gpt-4, gpt-3.5-turbo, claude-3, etc.)
- `tools`: List of tool names (search, calculator, etc.)
- `memory_type`: Default memory type
- `price_per_run`: Default price
- `category`: Agent category

**Pre-built Agents**:
1. SEO Optimizer - analyzes and optimizes content for SEO
2. Customer Support Bot - answers customer queries
3. Data Analyst - analyzes datasets and creates visualizations
4. Code Reviewer - reviews code for bugs and best practices
5. Email Drafter - writes professional emails
6. Research Assistant - conducts research and summarizes findings

## Decision 5: Agent Studio Architecture
**Context**: Users need to customize agents by selecting models, prompts, tools, and memory.

**Decision**: Implement `AgentConfig` dataclass that users can configure via UI. Provide `build_custom_agent(config: AgentConfig) -> agno.Agent` factory function.

**Rationale**:
- Clean separation between configuration and execution
- Validation of config before agent creation
- Easy to serialize/deserialize for saving to DB

**AgentConfig Fields**:
- `name`: Agent name
- `system_prompt`: System prompt
- `model`: LLM model identifier
- `temperature`: Creativity parameter
- `tools`: List of tool configurations
- `memory_type`: "none", "key_value", "semantic"
- `max_tokens`: Maximum tokens per response
- `streaming_enabled`: Whether to stream responses

## Decision 6: Streaming Execution
**Context**: Need live test console with streaming output.

**Decision**: Implement `run_agent_stream(agent, prompt, user_id, db) -> AsyncGenerator[str]` that yields chunks as they are generated.

**Rationale**:
- Provides real-time feedback in UI
- Reduces perceived latency
- Follows modern LLM API patterns

**Implementation**:
- Wrap Agno's streaming API if available
- Fallback to non-streaming with simulated chunks
- Track tokens as they are generated
- Handle errors gracefully

## Decision 7: Integration with Existing Models
**Context**: Existing `Agent`, `AgentVersion`, `AgentRun` models need to work with new local agents.

**Decision**: Extend `AgentVersion.config` to include local agent configuration (prompt, model, tools). Keep `agno_agent_id` for backward compatibility but also store `agent_type: "remote" | "local"`.

**Rationale**:
- Minimal schema changes
- Supports both remote and local agents
- Existing data remains valid

**Implementation**:
- Add `agent_type` field to `AgentVersion` (default "remote")
- Update `AgentExecutor` to use local integration when `agent_type == "local"`
- Store local config in `config` JSON field

## Decision 8: Error Handling and Logging
**Context**: All agent calls need proper error handling and usage logging.

**Decision**: Implement comprehensive error handling in `AgentWrapper` with retry logic for transient failures. Log all executions to `AgentRunLog` with token counts, duration, and errors.

**Rationale**:
- Essential for debugging and monitoring
- Required for billing accuracy
- Improves user experience with clear error messages

**Implementation**:
- Try-catch blocks around agent execution
- Exponential backoff for rate limits
- Structured logging with context
- User-friendly error messages

## Next Steps
1. Implement core `AgentWrapper` with token counting
2. Create marketplace catalog with 6 AgentSpecs
3. Build agent studio and custom agent builder
4. Implement persistent memory storage
5. Create streaming agent runner
6. Integrate with existing API endpoints
7. Update documentation and tests