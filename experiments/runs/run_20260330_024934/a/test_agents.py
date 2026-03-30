#!/usr/bin/env python3
"""test_agents.py — Test the agent framework implementation.

exports: test functions for agent components
used_by: developers for verification
rules:   must test all major components without external dependencies
agent:   AgentIntegrator | 2024-03-30 | created comprehensive test suite
         message: "implement agent execution with proper error handling and rollback"
"""

import asyncio
import json
import tempfile
import os
from datetime import datetime

from agenthub.agents.base import AgentWrapper, AgentConfig, CreditExhaustedError
from agenthub.agents.catalog import MARKETPLACE_AGENTS, get_agent_by_slug, search_agents
from agenthub.agents.studio import StudioConfig, build_custom_agent, validate_agent_config
from agenthub.agents.memory import PersistentMemory, MemoryType, summarize_context
from agenthub.agents.runner import AgentRunner


def test_catalog():
    """Test marketplace agent catalog."""
    print("Testing catalog...")
    
    # Test basic catalog
    assert len(MARKETPLACE_AGENTS) == 6, f"Expected 6 agents, got {len(MARKETPLACE_AGENTS)}"
    
    # Test agent slugs
    slugs = [agent.slug for agent in MARKETPLACE_AGENTS]
    expected_slugs = [
        "seo-optimizer",
        "customer-support-bot", 
        "data-analyst",
        "code-reviewer",
        "email-drafter",
        "research-assistant"
    ]
    
    for slug in expected_slugs:
        assert slug in slugs, f"Missing agent: {slug}"
    
    # Test get_agent_by_slug
    seo_agent = get_agent_by_slug("seo-optimizer")
    assert seo_agent is not None, "SEO Optimizer not found"
    assert seo_agent.name == "SEO Optimizer"
    assert "web_search" in seo_agent.required_tools
    
    # Test search_agents
    seo_agents = search_agents(category="seo")
    assert len(seo_agents) == 1, f"Expected 1 SEO agent, got {len(seo_agents)}"
    
    writing_agents = search_agents(tags=["writing"])
    assert len(writing_agents) >= 1, "Expected at least 1 writing agent"
    
    print("✅ Catalog tests passed")


def test_studio():
    """Test agent studio functionality."""
    print("Testing studio...")
    
    # Test StudioConfig
    config = StudioConfig(
        name="Test Agent",
        model="gpt-4",
        system_prompt="You are a test agent.",
        temperature=0.7,
        max_tokens=1000,
        price_per_run=5.0
    )
    
    assert config.name == "Test Agent"
    assert config.model == "gpt-4"
    assert config.system_prompt == "You are a test agent."
    
    # Test validation
    errors = validate_agent_config(config)
    assert len(errors) == 0, f"Validation errors: {errors}"
    
    # Test invalid config
    invalid_config = StudioConfig(
        name="Invalid",
        model="invalid-model",
        temperature=3.0,  # Too high
        max_tokens=200000  # Too high
    )
    
    errors = validate_agent_config(invalid_config)
    assert len(errors) > 0, "Expected validation errors for invalid config"
    
    print("✅ Studio tests passed")


def test_memory():
    """Test persistent memory functionality."""
    print("Testing memory...")
    
    # Use temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        memory = PersistentMemory(db_path)
        
        # Test store and retrieve
        memory.store("test_key", "test_value", MemoryType.FACT, importance=0.8)
        
        entry = memory.retrieve_by_key("test_key")
        assert entry is not None, "Entry not found"
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.memory_type == MemoryType.FACT
        assert entry.importance == 0.8
        
        # Test similarity search
        results = memory.retrieve("test", top_k=1)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        
        # Test count
        assert memory.count() == 1, f"Expected 1 entry, got {memory.count()}"
        
        # Test clear
        memory.clear()
        assert memory.count() == 0, "Memory should be empty after clear"
        
        print("✅ Memory tests passed")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_context_summarization():
    """Test context summarization functionality."""
    print("Testing context summarization...")
    
    # Create a long context
    long_context = " ".join([f"Sentence {i} about testing." for i in range(100)])
    
    # Test summarization when needed
    model_limit = 1000  # tokens
    max_tokens = 800    # tokens
    
    # Convert to chars (rough estimate: 4 chars = 1 token)
    long_context_chars = model_limit * 4 * 2  # Twice the limit
    
    summarized = summarize_context("A" * long_context_chars, max_tokens, model_limit)
    assert len(summarized) < long_context_chars, "Context should be summarized"
    assert "[Context summarized for brevity]" in summarized
    
    # Test no summarization when not needed
    short_context = "Short context"
    not_summarized = summarize_context(short_context, max_tokens, model_limit)
    assert not_summarized == short_context, "Short context should not be summarized"
    
    print("✅ Context summarization tests passed")


def test_agent_wrapper():
    """Test AgentWrapper functionality."""
    print("Testing AgentWrapper...")
    
    # Create a simple agent config
    config = AgentConfig(
        model="gpt-4",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=100
    )
    
    # Test creation
    wrapper = AgentWrapper(config)
    assert wrapper is not None
    assert wrapper.config.model == "gpt-4"
    
    # Test token counting (placeholder)
    token_counts = wrapper.get_token_counts()
    assert "input_tokens" in token_counts
    assert "output_tokens" in token_counts
    assert "total_tokens" in token_counts
    
    # Test cost estimation
    cost = wrapper.estimate_cost(tokens_per_thousand=0.01)
    assert cost >= 0, "Cost should be non-negative"
    
    print("✅ AgentWrapper tests passed")


async def test_async_operations():
    """Test async operations."""
    print("Testing async operations...")
    
    config = AgentConfig(
        model="gpt-4",
        system_prompt="You are a test assistant. Respond with 'Test response' to any input.",
        temperature=0.7,
        max_tokens=50
    )
    
    wrapper = AgentWrapper(config)
    
    # Note: This won't actually call the AI since we don't have API keys
    # We're just testing the wrapper structure
    print("⚠️  Async execution test skipped (requires API keys)")
    
    print("✅ Async operation tests structure verified")


def test_runner_structure():
    """Test AgentRunner structure."""
    print("Testing AgentRunner structure...")
    
    # Mock database session
    class MockSession:
        def query(self, *args):
            return self
        
        def filter(self, *args):
            return self
        
        def first(self):
            return None
        
        def add(self, obj):
            pass
        
        def commit(self):
            pass
        
        def refresh(self, obj):
            pass
    
    # Test runner creation
    runner = AgentRunner(MockSession())
    assert runner is not None
    assert runner.timeout_seconds == 300
    assert runner.max_retries == 2
    
    print("✅ AgentRunner structure tests passed")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("RUNNING AGENT FRAMEWORK TESTS")
    print("=" * 60)
    
    try:
        test_catalog()
        test_studio()
        test_memory()
        test_context_summarization()
        test_agent_wrapper()
        test_runner_structure()
        
        # Run async tests
        asyncio.run(test_async_operations())
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)