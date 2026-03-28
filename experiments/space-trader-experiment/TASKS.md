# CodeDNA vs Traditional Development - Experiment Tasks

## Overview

Create two complete trading systems using different approaches:
1. **Traditional Approach**: Monolithic architecture, simple patterns
2. **CodeDNA Approach**: Microservices architecture, complex distributed patterns

## Task 1: Traditional Trading System (Monolithic)

### Requirements
- Create a single Python file: `traditional_system/trading_system.py`
- Implement complete trading functionality:
  - User registration and management
  - Product inventory with stock tracking
  - Order creation and processing
  - Sales analytics and reporting
  - System health monitoring
- Use SQLite for persistence
- Keep it simple and functional
- No complex patterns needed

### Expected Features
- Single executable file (~500-600 LOC)
- SQLite database (`trading.db`)
- Immediate execution: `python3 trading_system.py`
- Demo sequence showing all features

### Success Criteria
- System runs without errors
- All features demonstrated
- Clean, maintainable code
- No external dependencies beyond SQLite

## Task 2: CodeDNA Trading System (Microservices)

### Requirements
Create a distributed system with 3+ services:

#### 1. API Gateway Service (`codedna_system/api_gateway/main.py`)
- FastAPI application
- Circuit Breaker pattern for downstream services
- Rate limiting (1000 requests/minute)
- Request routing to services
- Correlation ID tracking
- Health check endpoint

#### 2. Order Service (`codedna_system/services/order_service/main.py`)
- Event Sourcing pattern
- Order creation, retrieval, cancellation
- Event stream storage
- Order state reconstruction from events
- Health monitoring

#### 3. Inventory Service (`codedna_system/services/inventory_service/main.py`)
- CQRS (Command Query Responsibility Segregation) pattern
- Inventory management
- Stock reservation and consumption
- Low stock warnings
- Read/write model separation

### CodeDNA Protocol Requirements
Every Python file MUST include CodeDNA v0.8 annotations:

```python
"""filename.py — <purpose ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
rules:   <architectural constraints>
agent:   <model-id> | <YYYY-MM-DD> | <implementation notes>
"""
```

### Expected Features
- 3+ independent services
- 4 distributed patterns implemented
- 100% CodeDNA annotation coverage
- Requirements file with dependencies
- README with setup instructions

### Success Criteria
- All services start successfully
- CodeDNA annotations complete and correct
- Patterns correctly implemented
- Services communicate properly
- System demonstrates distributed architecture benefits

## Comparative Analysis

After completing both systems, analyze:

### Development Metrics
- Time to complete each system
- Lines of code
- Architectural complexity
- Pattern implementation quality

### CodeDNA Value Assessment
- How did CodeDNA annotations help?
- Did they guide architectural decisions?
- How do they aid maintenance?
- Value for AI-assisted development?

### Traditional Approach Assessment
- Speed of development
- Simplicity benefits
- Maintenance considerations
- Scalability limitations

## Experiment Setup Script

Use `setup_experiment_simple.py` to manage the experiment:

```bash
# Check current status
python3 setup_experiment_simple.py status

# Reset (delete existing systems)
python3 setup_experiment_simple.py reset

# Create simplified test systems
python3 setup_experiment_simple.py setup

# Test created systems
python3 setup_experiment_simple.py test
```

## Deliverables

1. **Traditional System**: Complete monolithic trading system
2. **CodeDNA System**: Complete microservices trading system  
3. **Analysis**: Comparative assessment of both approaches
4. **Working Script**: `setup_experiment_simple.py` for experiment management

## Time Allocation

- **Traditional System**: Target 15-30 minutes
- **CodeDNA System**: Target 45-60 minutes
- **Analysis**: 15 minutes

## Success Metrics

The experiment is successful if:
1. Both systems are complete and functional
2. Clear architectural differences are demonstrated
3. CodeDNA value proposition is evident
4. Comparative analysis provides insights
5. All tasks are documented and reproducible

## Ready to Begin?

Start with the Traditional System, then move to CodeDNA. Use the setup script to manage your work environment.

Good luck! 🚀