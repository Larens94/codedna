"""test_console.py — Live test console interface for Agent Studio.

exports: run_test_console, test_agent_interactively
used_by: cli.py → agent studio command, developers for testing
rules:   Must provide interactive testing of all 6 marketplace agents
         Must demonstrate memory functionality with SQLite storage
         Must show token counting and cost estimation
         Must handle errors gracefully with user-friendly messages
agent:   AgentIntegrator | 2024-03-30 | implemented interactive test console
         message: "implement agent execution with proper error handling and rollback"
"""

import asyncio
import json
import sys
import sqlite3
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import AgentWrapper, AgentConfig
from .catalog import MARKETPLACE_AGENTS, get_agent_by_slug
from .studio import AgentFactory, StudioConfig, build_custom_agent
from .memory import PersistentMemory, MemoryType
from .runner import execute_agent_sync


class AgentTestConsole:
    """Interactive console for testing agents."""
    
    def __init__(self):
        self.memory = PersistentMemory("test_memory.db")
        self.current_agent: Optional[AgentWrapper] = None
        self.agent_history: List[Dict[str, Any]] = []
    
    def print_header(self, text: str):
        """Print formatted header."""
        print("\n" + "=" * 60)
        print(f" {text}")
        print("=" * 60)
    
    def print_menu(self, title: str, options: List[tuple]):
        """Print menu with options."""
        self.print_header(title)
        for i, (key, description) in enumerate(options, 1):
            print(f"{i}. {key}: {description}")
        print()
    
    def get_choice(self, prompt: str, min_val: int, max_val: int) -> int:
        """Get validated user choice."""
        while True:
            try:
                choice = input(f"{prompt} [{min_val}-{max_val}]: ").strip()
                if not choice:
                    return -1
                choice_int = int(choice)
                if min_val <= choice_int <= max_val:
                    return choice_int
                print(f"Please enter a number between {min_val} and {max_val}")
            except ValueError:
                print("Please enter a valid number")
    
    def get_input(self, prompt: str, default: str = "") -> str:
        """Get user input with optional default."""
        if default:
            full_prompt = f"{prompt} [{default}]: "
        else:
            full_prompt = f"{prompt}: "
        
        result = input(full_prompt).strip()
        return result if result else default
    
    async def main_menu(self):
        """Main menu loop."""
        while True:
            self.print_menu("Agent Studio Test Console", [
                ("Marketplace Agents", "Test pre-built agents"),
                ("Custom Agent", "Build and test custom agent"),
                ("Memory Test", "Test memory storage and retrieval"),
                ("Agent History", "View previous agent runs"),
                ("Exit", "Exit the test console")
            ])
            
            choice = self.get_choice("Select option", 1, 5)
            
            if choice == 1:
                await self.marketplace_menu()
            elif choice == 2:
                await self.custom_agent_menu()
            elif choice == 3:
                await self.memory_test_menu()
            elif choice == 4:
                self.show_agent_history()
            elif choice == 5:
                print("\nGoodbye!")
                break
    
    async def marketplace_menu(self):
        """Marketplace agents menu."""
        while True:
            options = [(agent.name, agent.description[:50] + "...") 
                      for agent in MARKETPLACE_AGENTS]
            options.append(("Back", "Return to main menu"))
            
            self.print_menu("Marketplace Agents", options)
            
            choice = self.get_choice("Select agent", 1, len(options))
            
            if choice == len(options):
                break
            
            if 1 <= choice <= len(MARKETPLACE_AGENTS):
                agent_spec = MARKETPLACE_AGENTS[choice - 1]
                await self.test_agent(agent_spec)
    
    async def test_agent(self, agent_spec):
        """Test a specific agent."""
        self.print_header(f"Testing: {agent_spec.name}")
        print(f"Description: {agent_spec.description}")
        print(f"Model: {agent_spec.model}")
        print(f"Temperature: {agent_spec.temperature}")
        print(f"Max Tokens: {agent_spec.max_tokens}")
        print(f"Price per run: ${agent_spec.price_per_run}")
        print(f"Required Tools: {', '.join(agent_spec.required_tools)}")
        print()
        
        # Create agent
        try:
            self.current_agent = AgentFactory.from_spec(agent_spec)
            print("✓ Agent created successfully")
        except Exception as e:
            print(f"✗ Failed to create agent: {e}")
            return
        
        # Test loop
        while True:
            print("\n" + "-" * 40)
            prompt = self.get_input("Enter prompt (or 'back' to return)", "")
            
            if prompt.lower() == 'back':
                break
            
            if not prompt:
                print("Prompt cannot be empty")
                continue
            
            print("\n" + "=" * 40)
            print("Agent Response:")
            print("=" * 40)
            
            try:
                # Run agent
                start_time = datetime.now()
                response = await self.current_agent.run(prompt)
                elapsed = (datetime.now() - start_time).total_seconds()
                
                print(response)
                print("\n" + "-" * 40)
                
                # Show token counts
                token_counts = self.current_agent.get_token_counts()
                print(f"Token Usage:")
                print(f"  Input: {token_counts['input_tokens']}")
                print(f"  Output: {token_counts['output_tokens']}")
                print(f"  Total: {token_counts['total_tokens']}")
                
                # Estimate cost
                cost = self.current_agent.estimate_cost(tokens_per_thousand=0.01)
                print(f"Estimated Cost: ${cost:.4f}")
                print(f"Execution Time: {elapsed:.2f} seconds")
                
                # Store in history
                self.agent_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "agent": agent_spec.name,
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "response": response[:200] + "..." if len(response) > 200 else response,
                    "tokens": token_counts,
                    "cost": cost,
                    "time": elapsed
                })
                
            except Exception as e:
                print(f"✗ Agent execution failed: {e}")
    
    async def custom_agent_menu(self):
        """Build and test custom agent."""
        self.print_header("Build Custom Agent")
        
        # Get agent configuration
        name = self.get_input("Agent name", "Custom Assistant")
        model = self.get_input("Model (gpt-4, gpt-3.5-turbo)", "gpt-4")
        system_prompt = self.get_input("System prompt", "You are a helpful AI assistant.")
        
        try:
            temperature = float(self.get_input("Temperature (0.0-2.0)", "0.7"))
            max_tokens = int(self.get_input("Max tokens", "2000"))
            price = float(self.get_input("Price per run ($)", "0.0"))
        except ValueError:
            print("Invalid numeric input")
            return
        
        # Create config
        config = StudioConfig(
            name=name,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            price_per_run=price
        )
        
        # Build agent
        try:
            self.current_agent = build_custom_agent(config)
            print("✓ Custom agent created successfully")
        except Exception as e:
            print(f"✗ Failed to create agent: {e}")
            return
        
        # Test the agent
        await self.test_current_agent()
    
    async def test_current_agent(self):
        """Test the currently loaded agent."""
        if not self.current_agent:
            print("No agent loaded. Please create or select an agent first.")
            return
        
        print("\n" + "=" * 40)
        print("Testing Current Agent")
        print("=" * 40)
        
        while True:
            prompt = self.get_input("\nEnter prompt (or 'back' to return)", "")
            
            if prompt.lower() == 'back':
                break
            
            if not prompt:
                print("Prompt cannot be empty")
                continue
            
            print("\n" + "=" * 40)
            print("Agent Response:")
            print("=" * 40)
            
            try:
                start_time = datetime.now()
                response = await self.current_agent.run(prompt)
                elapsed = (datetime.now() - start_time).total_seconds()
                
                print(response)
                print("\n" + "-" * 40)
                
                # Show token counts
                token_counts = self.current_agent.get_token_counts()
                print(f"Token Usage: {token_counts['total_tokens']} total")
                print(f"Execution Time: {elapsed:.2f} seconds")
                
            except Exception as e:
                print(f"✗ Agent execution failed: {e}")
    
    async def memory_test_menu(self):
        """Test memory functionality."""
        self.print_header("Memory Test")
        
        while True:
            self.print_menu("Memory Operations", [
                ("Store Memory", "Store key-value pair in memory"),
                ("Retrieve Memory", "Search memory by query"),
                ("View All", "View all memory entries"),
                ("Clear Memory", "Clear all memory"),
                ("Back", "Return to main menu")
            ])
            
            choice = self.get_choice("Select operation", 1, 5)
            
            if choice == 1:
                await self.store_memory()
            elif choice == 2:
                await self.retrieve_memory()
            elif choice == 3:
                self.view_all_memory()
            elif choice == 4:
                self.clear_memory()
            elif choice == 5:
                break
    
    async def store_memory(self):
        """Store memory entry."""
        print("\n--- Store Memory ---")
        key = self.get_input("Memory key", "")
        value = self.get_input("Memory value", "")
        memory_type = self.get_input("Memory type (conversation/fact/preference/context/summary)", "fact")
        importance = self.get_input("Importance (0.0-1.0)", "1.0")
        
        try:
            importance_float = float(importance)
            if not 0.0 <= importance_float <= 1.0:
                print("Importance must be between 0.0 and 1.0")
                return
        except ValueError:
            print("Invalid importance value")
            return
        
        try:
            mem_type = MemoryType(memory_type.lower())
        except ValueError:
            print(f"Invalid memory type. Must be one of: {[t.value for t in MemoryType]}")
            return
        
        self.memory.store(key, value, mem_type, importance=importance_float)
        print(f"✓ Memory stored: {key} = {value[:50]}...")
    
    async def retrieve_memory(self):
        """Retrieve memory entries."""
        print("\n--- Retrieve Memory ---")
        query = self.get_input("Search query", "")
        top_k = self.get_input("Number of results", "5")
        
        try:
            top_k_int = int(top_k)
        except ValueError:
            print("Invalid number")
            return
        
        results = self.memory.retrieve(query, top_k=top_k_int)
        
        if not results:
            print("No results found")
            return
        
        print(f"\nFound {len(results)} results:")
        for i, entry in enumerate(results, 1):
            print(f"\n{i}. Key: {entry.key}")
            print(f"   Value: {entry.value[:100]}...")
            print(f"   Type: {entry.memory_type.value}")
            print(f"   Importance: {entry.importance}")
            print(f"   Timestamp: {entry.timestamp}")
    
    def view_all_memory(self):
        """View all memory entries."""
        print("\n--- All Memory Entries ---")
        
        entries = self.memory.get_all(limit=20)
        
        if not entries:
            print("No memory entries")
            return
        
        print(f"Total entries: {self.memory.count()}")
        print(f"Showing {len(entries)} most recent:")
        
        for i, entry in enumerate(entries, 1):
            print(f"\n{i}. Key: {entry.key}")
            print(f"   Value: {entry.value[:80]}...")
            print(f"   Type: {entry.memory_type.value}")
            print(f"   Timestamp: {entry.timestamp}")
    
    def clear_memory(self):
        """Clear all memory."""
        confirm = self.get_input("Are you sure you want to clear ALL memory? (yes/no)", "no")
        if confirm.lower() == "yes":
            self.memory.clear()
            print("✓ Memory cleared")
        else:
            print("Memory clear cancelled")
    
    def show_agent_history(self):
        """Show agent run history."""
        self.print_header("Agent Run History")
        
        if not self.agent_history:
            print("No agent runs yet")
            return
        
        print(f"Total runs: {len(self.agent_history)}")
        print()
        
        for i, run in enumerate(reversed(self.agent_history), 1):
            print(f"Run #{i}:")
            print(f"  Agent: {run['agent']}")
            print(f"  Time: {run['timestamp']}")
            print(f"  Prompt: {run['prompt']}")
            print(f"  Response: {run['response']}")
            print(f"  Tokens: {run['tokens']['total_tokens']}")
            print(f"  Cost: ${run['cost']:.4f}")
            print(f"  Duration: {run['time']:.2f}s")
            print()


async def run_test_console():
    """Run the test console."""
    console = AgentTestConsole()
    
    print("\n" + "=" * 60)
    print("  AGENT STUDIO TEST CONSOLE")
    print("=" * 60)
    print("  Test marketplace agents, build custom agents,")
    print("  and experiment with memory functionality.")
    print("=" * 60)
    
    try:
        await console.main_menu()
    except KeyboardInterrupt:
        print("\n\nTest console interrupted")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def test_agent_interactively(agent_slug: str):
    """Test a specific agent interactively.
    
    Args:
        agent_slug: Slug of the agent to test
    """
    agent_spec = get_agent_by_slug(agent_slug)
    if not agent_spec:
        print(f"Agent not found: {agent_slug}")
        return
    
    console = AgentTestConsole()
    
    print(f"\nTesting agent: {agent_spec.name}")
    print(f"Description: {agent_spec.description}")
    print()
    
    # Run in async context
    asyncio.run(console.test_agent(agent_spec))


if __name__ == "__main__":
    # Run the test console
    asyncio.run(run_test_console())