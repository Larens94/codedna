#!/usr/bin/env python3
"""
agno_workflow_traditional.py — Agno AI workflow for Traditional approach.

exports: main() -> None
used_by: experiment_runner.py → run_traditional_workflow
rules:   Must guide AI to create monolithic system without CodeDNA annotations, keep it simple
agent:   deepseek-chat | 2026-03-29 | Created Agno workflow for Traditional approach
"""

import os
import sys
from pathlib import Path

def main():
    """Main workflow for Traditional approach."""
    print("=" * 80)
    print("AGNO AI WORKFLOW - TRADITIONAL APPROACH")
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
    
    # Extract Traditional task requirements
    print("\n🎯 TASK 1: Traditional Trading System (Monolithic)")
    print("-" * 60)
    
    # Traditional approach philosophy
    traditional_approach = """
    TRADITIONAL DEVELOPMENT APPROACH - KEEP IT SIMPLE:
    
    Principles:
    1. Single file design (monolithic)
    2. SQLite database for persistence
    3. Simple, straightforward code
    4. No complex patterns needed
    5. Focus on functionality over architecture
    6. Minimal dependencies
    7. Immediate execution
    8. Easy to understand and maintain
    
    NO CodeDNA annotations required.
    NO complex distributed patterns.
    NO microservices architecture.
    
    Just make it work simply and effectively.
    """
    
    print(traditional_approach)
    
    # System requirements
    requirements = """
    📋 SYSTEM REQUIREMENTS:
    
    1. Single Python file: traditional_system/trading_system.py
    2. Complete trading functionality:
       - User registration and management
       - Product inventory with stock tracking
       - Order creation and processing
       - Sales analytics and reporting
       - System health monitoring
    3. SQLite database (trading.db)
    4. No external dependencies beyond SQLite
    5. Demo sequence showing all features
    
    EXPECTED FEATURES:
    - Single executable file (~500-600 LOC)
    - SQLite database (trading.db)
    - Immediate execution: python3 trading_system.py
    - Clean, maintainable code
    - No complex patterns needed
    """
    
    print(requirements)
    
    # Success criteria
    success_criteria = """
    ✅ SUCCESS CRITERIA:
    
    1. Single file created: trading_system.py
    2. All 5 features implemented:
       - User management
       - Product inventory
       - Order processing
       - Sales analytics
       - Health monitoring
    3. SQLite database working
    4. System runs without errors
    5. Demo shows all functionality
    6. Development time: Target 15-30 minutes
    7. Code is simple and functional
    """
    
    print(success_criteria)
    
    # Instructions for Agno AI
    instructions = """
    🚀 INSTRUCTIONS FOR AGNO AI:
    
    1. CREATE single file:
       traditional_system/trading_system.py
    
    2. IMPLEMENT TradingSystem class with:
       - __init__ method (initialize SQLite)
       - register_user method
       - add_product method
       - create_order method
       - get_sales_summary method
       - health_check method
    
    3. USE SQLite for persistence:
       - Create tables: users, products, orders, order_items
       - Use simple SQL queries
       - Handle errors gracefully
    
    4. ADD demo main() function:
       - Show all features in sequence
       - Print clear output
       - Demonstrate system working
    
    5. KEEP it simple:
       - No complex patterns
       - No external dependencies
       - Straightforward code
       - Easy to read and understand
    
    Remember: This is TRADITIONAL development.
    Focus on making it WORK, not on architecture.
    """
    
    print(instructions)
    
    print("=" * 80)
    print("WORKFLOW READY FOR AGNO AI EXECUTION")
    print("=" * 80)
    
    # Create output directory structure
    output_dir = Path(__file__).parent.parent / "traditional_system"
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n📁 Output directory: {output_dir}")
    print("🎯 Agno AI should now execute this workflow to create the Traditional system.")

if __name__ == "__main__":
    main()