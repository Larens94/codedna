#!/usr/bin/env python3
"""Test imports for agent integration layer."""

import sys
sys.path.insert(0, '.')

try:
    from app.agents import (
        AgentWrapper,
        AgentSpec,
        AgentConfig,
        build_custom_agent,
        dict_tools_available_from_agno,
        memory_manager,
        agent_runner,
        CreditExhaustedError,
    )
    print("✓ All imports successful")
    
    # Test AgentSpec
    spec = AgentSpec(
        name="Test Agent",
        slug="test-agent",
        description="Test",
        system_prompt="You are a test agent.",
        tools=["calculator"]
    )
    print(f"✓ AgentSpec created: {spec.name}")
    
    # Test dict_tools_available_from_agno
    print(f"✓ Available tools: {list(dict_tools_available_from_agno.keys())}")
    
    # Test memory_manager
    print(f"✓ MemoryManager: {type(memory_manager).__name__}")
    
    # Test agent_runner
    print(f"✓ AgentRunner: {type(agent_runner).__name__}")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"❌ Import test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)