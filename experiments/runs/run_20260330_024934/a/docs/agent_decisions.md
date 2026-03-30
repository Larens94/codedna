# Agent Integration Decisions

## Overview
This document captures architectural decisions and implementation details for the Agno agent wrappers and marketplace catalog.

## Date: 2024-03-30
**Agent:** AgentIntegrator
**Task:** Implement agenthub/agents/ directory with Agno framework wrappers and marketplace catalog

## Decisions Made

### 1. AgentWrapper Architecture
**Decision:** Created `AgentWrapper` class that wraps `agno.Agent` with additional functionality:
- Token counting and extraction from agno response metadata
- Credit enforcement with `CreditExhaustedError` (HTTP 402)
- Input sanitization (HTML stripping, 10k char limit)
- Cost estimation based on token usage

**Rationale:** 
- Centralizes agent execution logic
- Ensures consistent error handling
- Provides abstraction layer for future framework changes
- Enforces security through input sanitization

### 2. Marketplace Agent Catalog
**Decision:** Implemented 6 pre-built agents as `AgentSpec` dataclasses:
1. **SEO Optimizer** - Web search + content analysis tools
2. **Customer Support Bot** - Knowledge base + ticket system tools
3. **Data Analyst** - Data analysis + visualization tools
4. **Code Reviewer** - Code analysis + security scan tools
5. **Email Drafter** - Email templates + tone analysis tools
6. **Research Assistant** - Web search + summarization + citation tools

**Rationale:**
- Covers common business use cases
- Each agent has specific required tools
- Clear pricing structure per agent type
- Easy to extend with new agents

### 3. AgentFactory Pattern
**Decision:** Created `AgentFactory` class with multiple creation methods:
- `from_spec()` - From AgentSpec
- `from_slug()` - From marketplace slug
- `from_api_schema()` - From API request data
- `from_template()` - From predefined templates

**Rationale:**
- Consistent agent creation interface
- Supports multiple configuration sources
- Easy to test and mock
- Follows factory design pattern

### 4. Persistent Memory System
**Decision:** Implemented `PersistentMemory` with SQLite backend:
- Key-value storage with metadata
- Simple TF-IDF similarity search
- Embedding support for vector search
- Thread-safe operations
- Memory summarization when context exceeds 80% limit

**Rationale:**
- Lightweight, file-based storage
- No external dependencies
- Supports both exact and similarity search
- Scalable for small to medium workloads

### 5. Streaming Agent Execution
**Decision:** Created `AgentRunner` with SSE streaming:
- Real-time response streaming
- Timeout protection (5 minutes)
- Automatic credit deduction/refund
- Database integration for run tracking
- Error handling with status updates

**Rationale:**
- Better user experience with streaming
- Prevents long-running agent hangs
- Atomic credit operations
- Complete audit trail of agent runs

### 6. Test Console Interface
**Decision:** Built interactive `AgentTestConsole`:
- Test all marketplace agents
- Build and test custom agents
- Experiment with memory functionality
- View token counts and costs
- No database dependencies for testing

**Rationale:**
- Developer-friendly testing tool
- Demonstrates all framework features
- Useful for debugging and demos
- Self-contained for quick experimentation

## Implementation Details

### Token Counting Strategy
**Approach:** Placeholder implementation with extraction from agno metadata
**Future:** Need to implement actual token counting based on agno's response format

### Credit System Integration
**Approach:** Database-level credit checking and deduction
**Future:** Consider distributed locking for high-concurrency scenarios

### Memory Summarization
**Approach:** Simple sentence scoring based on word frequency
**Future:** Implement more sophisticated summarization using LLM

### Tool Integration
**Approach:** Placeholder tool creation methods
**Future:** Need to implement actual tool integrations with agno

## Security Considerations

1. **Input Sanitization:** All prompts and inputs are HTML-escaped and length-limited
2. **Credit Enforcement:** Credits checked before execution, refunded on errors
3. **Memory Isolation:** Each agent run has isolated context
4. **Timeout Protection:** 5-minute timeout prevents infinite loops

## Performance Considerations

1. **Memory Caching:** Consider adding LRU cache for frequent memory queries
2. **Connection Pooling:** SQLite connections managed per-thread
3. **Streaming Efficiency:** Chunked responses with minimal overhead
4. **Token Estimation:** Simple char-to-token ratio (4:1) for quick estimates

## Testing Strategy

1. **Unit Tests:** Individual component testing
2. **Integration Tests:** Agent creation and execution
3. **Console Testing:** Interactive testing via test console
4. **Load Testing:** Concurrent agent execution scenarios

## Future Enhancements

1. **Vector Database:** Replace simple similarity with proper vector search
2. **Tool Registry:** Dynamic tool discovery and registration
3. **Agent Chaining:** Sequential or parallel agent execution
4. **Monitoring:** Real-time metrics and alerting
5. **Caching:** Response caching for identical queries
6. **Rate Limiting:** Per-user and per-agent rate limits

## Dependencies

- `agno` - Core AI framework
- `sqlite3` - Memory storage
- `pydantic` - Configuration validation
- `fastapi` - API layer (for streaming)
- `asyncio` - Async execution

## Configuration

All agents support configuration via `StudioConfig`:
- Model selection (GPT-4, GPT-3.5, Claude models)
- Temperature (0.0-2.0)
- Max tokens (1-100,000)
- Memory type (sqlite, vector, none)
- Tool selection
- Price per run

## Error Handling

1. **CreditExhaustedError:** HTTP 402 with required/available credits
2. **ValidationError:** Configuration validation failures
3. **TimeoutError:** Execution timeout after 5 minutes
4. **ExecutionError:** Agent execution failures with automatic refund

## Logging

All agent operations are logged:
- Agent creation and configuration
- Credit operations (deduct/refund)
- Token usage and cost estimation
- Execution time and status
- Memory operations (store/retrieve)

## Migration Path

1. **Current:** Basic wrapper with SQLite memory
2. **Phase 2:** Vector memory with embeddings
3. **Phase 3:** Distributed agent execution
4. **Phase 4:** Advanced tool integrations
5. **Phase 5:** Multi-agent collaboration

## Success Metrics

1. **Agent Creation Time:** < 100ms
2. **Execution Latency:** < 30 seconds for typical queries
3. **Memory Retrieval:** < 50ms for similarity search
4. **Concurrent Runs:** Support 100+ concurrent agents
5. **Error Rate:** < 1% failed executions

## Maintenance

1. **Database Maintenance:** Regular SQLite vacuuming
2. **Memory Cleanup:** Automatic pruning of old entries
3. **Tool Updates:** Regular updates to tool integrations
4. **Security Updates:** Prompt injection protection updates
5. **Performance Monitoring:** Regular profiling and optimization