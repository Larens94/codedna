#!/usr/bin/env python3
"""
agno_workflow_codedna.py — Agno AI workflow for CodeDNA approach.

exports: main() -> None
used_by: experiment_runner.py → run_codedna_workflow
rules:   Must guide AI to create distributed system with CodeDNA annotations, implement 4 patterns
agent:   deepseek-chat | 2026-03-29 | Created Agno workflow for CodeDNA approach
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def main():
    """Main workflow for CodeDNA approach."""
    print("=" * 80)
    print("AGNO AI WORKFLOW - CODEDNA APPROACH")
    print("=" * 80)
    print()
    
    # Read experiment tasks
    tasks_file = Path(__file__).parent.parent / "TASKS.md"
    if tasks_file.exists():
        with open(tasks_file, 'r') as f:
            tasks_content = f.read()
        print("📋 Tasks loaded from TASKS.md")
    else:
        print("❌ TASKS.md not found")
        return
    
    # Extract CodeDNA task requirements
    print("\n🎯 TASK 2: CodeDNA Trading System (Microservices)")
    print("-" * 60)
    
    # CodeDNA protocol requirements
    codedna_protocol = """
    CODE DNA PROTOCOL v0.8 - MUST FOLLOW FOR ALL PYTHON FILES:
    
    Every Python file MUST begin with:
    \"\"\"
    filename.py — <purpose ≤15 words>.
    
    exports: public_function(arg) -> return_type
    used_by: consumer_file.py → consumer_function
    rules:   <architectural constraints>
    agent:   <model-id> | <YYYY-MM-DD> | <implementation notes>
    \"\"\"
    
    Additional rules:
    1. For critical functions, add Rules: docstring
    2. Use semantic naming: <type>_<shape>_<domain>_<origin>
    3. Update agent: field after each edit (keep last 5 entries)
    4. Never remove exports: symbols
    5. Check used_by: targets before making changes
    """
    
    print(codedna_protocol)
    
    # System architecture
    architecture = """
    🏗️ SYSTEM ARCHITECTURE:
    
    1. API Gateway Service (codedna_system/api_gateway/main.py)
       - FastAPI application
       - Circuit Breaker pattern
       - Rate limiting (1000 requests/minute)
       - Request routing
       - Correlation ID tracking
       - Health check endpoint
    
    2. Order Service (codedna_system/services/order_service/main.py)
       - Event Sourcing pattern
       - Order creation, retrieval, cancellation
       - Event stream storage
       - Order state reconstruction
       - Health monitoring
    
    3. Inventory Service (codedna_system/services/inventory_service/main.py)
       - CQRS pattern (Command Query Responsibility Segregation)
       - Inventory management
       - Stock reservation and consumption
       - Low stock warnings
       - Read/write model separation
    
    4. Requirements (codedna_system/requirements.txt)
       - FastAPI, uvicorn, SQLAlchemy, Pydantic, httpx
    
    5. README (codedna_system/README.md)
       - System documentation
       - Setup instructions
       - Architecture overview
    """
    
    print(architecture)
    
    # Success criteria
    success_criteria = """
    ✅ SUCCESS CRITERIA:
    
    1. All 3+ services created with CodeDNA annotations
    2. 4 distributed patterns implemented:
       - Circuit Breaker (API Gateway)
       - Rate Limiting (API Gateway)
       - Event Sourcing (Order Service)
       - CQRS (Inventory Service)
    3. 100% CodeDNA annotation coverage
    4. Services communicate properly
    5. System demonstrates distributed architecture benefits
    6. Development time: Target 45-60 minutes
    """
    
    print(success_criteria)
    
    # Instructions for Agno AI
    instructions = """
    🚀 INSTRUCTIONS FOR AGNO AI:
    
    1. CREATE directory structure:
       mkdir -p codedna_system/api_gateway
       mkdir -p codedna_system/services/order_service
       mkdir -p codedna_system/services/inventory_service
    
    2. CREATE each service with complete CodeDNA annotations
    
    3. IMPLEMENT patterns as specified
    
    4. TEST system functionality
    
    5. DOCUMENT everything with CodeDNA protocol
    
    Remember: Every Python file MUST have CodeDNA header!
    CodeDNA annotations are NOT optional - they're REQUIRED.
    """
    
    print(instructions)
    
    print("=" * 80)
    print("WORKFLOW READY FOR AGNO AI EXECUTION")
    print("=" * 80)
    
    # Create output directory structure
    output_dir = Path(__file__).parent.parent / "codedna_system"
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n📁 Output directory: {output_dir}")
    print("🎯 Agno AI should now execute this workflow to create the CodeDNA system.")

if __name__ == "__main__":
    main()