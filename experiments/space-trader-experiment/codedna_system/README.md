# CodeDNA Trading System

A distributed trading system built using the CodeDNA protocol with microservices architecture and complex distributed patterns.

## Architecture Overview

The system consists of 3 independent microservices:

### 1. API Gateway Service (`api_gateway/main.py`)
- **Port**: 8000
- **Patterns**: Circuit Breaker, Rate Limiting
- **Features**:
  - Request routing to downstream services
  - Circuit breaker for fault tolerance
  - Rate limiting (1000 requests/minute)
  - Correlation ID tracking for distributed tracing
  - Health check aggregation

### 2. Order Service (`services/order_service/main.py`)
- **Port**: 8001
- **Pattern**: Event Sourcing
- **Features**:
  - Order creation, retrieval, and management
  - Event stream storage (immutable events)
  - State reconstruction from events
  - Event replay capability
  - Correlation ID propagation

### 3. Inventory Service (`services/inventory_service/main.py`)
- **Port**: 8002
- **Pattern**: CQRS (Command Query Responsibility Segregation)
- **Features**:
  - Separate write and read models
  - Stock management with reservation system
  - Low stock warnings
  - Stock history tracking
  - Fast query optimization

## CodeDNA Protocol Compliance

All Python files include CodeDNA v0.8 annotations:

```python
"""filename.py — <purpose ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
rules:   <architectural constraints>
agent:   <model-id> | <YYYY-MM-DD> | <implementation notes>
"""
```

### Key CodeDNA Features:
1. **Self-documenting architecture**: Each file declares its exports and dependencies
2. **Architectural constraints**: `rules:` field enforces design patterns
3. **Agent history**: `agent:` field tracks AI development sessions
4. **Semantic naming**: Variables follow `<type>_<shape>_<domain>_<origin>` convention

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Services
Open three terminal windows and run:

**Terminal 1 - API Gateway:**
```bash
cd api_gateway
python main.py
```

**Terminal 2 - Order Service:**
```bash
cd services/order_service
python main.py
```

**Terminal 3 - Inventory Service:**
```bash
cd services/inventory_service
python main.py
```

### 3. Test the System

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Create Order:**
```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "items": [
      {"product_id": 101, "quantity": 2, "unit_price": 29.99},
      {"product_id": 102, "quantity": 1, "unit_price": 99.99}
    ]
  }'
```

**Check Inventory:**
```bash
curl "http://localhost:8000/inventory/101/check?quantity=5"
```

## Distributed Patterns Implemented

### Circuit Breaker Pattern (API Gateway)
- **Purpose**: Prevent cascading failures
- **Implementation**: `CircuitBreaker` class with OPEN/CLOSED/HALF-OPEN states
- **Configuration**: 5 failure threshold, 30-second recovery timeout

### Rate Limiting Pattern (API Gateway)
- **Purpose**: Protect services from overload
- **Implementation**: `RateLimiter` class with sliding window algorithm
- **Configuration**: 1000 requests per minute per client IP

### Event Sourcing Pattern (Order Service)
- **Purpose**: Maintain complete audit trail
- **Implementation**: `EventStore` with immutable event storage
- **Features**: Event replay, state reconstruction, temporal queries

### CQRS Pattern (Inventory Service)
- **Purpose**: Optimize read and write operations separately
- **Implementation**: `InventoryWriteModel` (commands) and `InventoryReadModel` (queries)
- **Benefits**: Scalability, performance optimization, separation of concerns

## Development Metrics

### CodeDNA System:
- **Services**: 3 independent microservices
- **Patterns**: 4 distributed patterns implemented
- **Files**: 4 Python files with 100% CodeDNA annotation coverage
- **Lines of Code**: ~1800 LOC
- **Development Time**: ~45 minutes (AI-assisted)

### Traditional System (for comparison):
- **Architecture**: Monolithic single file
- **Patterns**: 0 distributed patterns
- **Files**: 1 Python file
- **Lines of Code**: ~600 LOC
- **Development Time**: ~20 minutes

## Benefits of CodeDNA Approach

1. **Architectural Guidance**: CodeDNA annotations provide clear architectural constraints
2. **Self-Documentation**: Each file explains its purpose, exports, and dependencies
3. **Pattern Enforcement**: Distributed patterns are explicitly required and documented
4. **AI Assistance**: CodeDNA helps AI agents implement complex patterns correctly
5. **Maintainability**: Clear separation of concerns and documented dependencies

## Testing

Run the experiment test script:
```bash
cd /Users/fabriziocorpora/Desktop/automation-lab/dynamic-bi-factory/codedna/experiments/space-trader-experiment
python3 setup_experiment_simple.py test
```

## Notes

- This is a demonstration system for the CodeDNA vs Traditional experiment
- In production, services would use message queues, service discovery, and proper monitoring
- The CodeDNA annotations help ensure architectural consistency across distributed teams
- The system demonstrates how CodeDNA can guide AI agents in implementing complex distributed systems