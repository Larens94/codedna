#!/usr/bin/env python3
"""run_frontend_designer.py — Runs FrontendDesigner agent to complete AgentHub frontend.

exports: FRONTEND_DIR | INSTRUCTIONS | main()
used_by: none
rules:   writes only inside frontend/ directory; never touches backend files
agent:   claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_001 | created to complete missing frontend pages
"""

import os
import sys
from pathlib import Path

from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from agno.tools.file import FileTools
from agno.tools.shell import ShellTools

FRONTEND_DIR = Path(__file__).parent / "runs/run_20260331_002754/a/frontend"

INSTRUCTIONS = """You are an expert React/TypeScript frontend developer.

You are working on AgentHub — a SaaS platform where users can rent, configure and deploy
AI agents. The backend API runs at http://localhost:8000/api/v1 (FastAPI).

════════════════════════════════════════════════════════════════════
TECH STACK (already configured — do not change package.json or config)
════════════════════════════════════════════════════════════════════
- React 18 + TypeScript + Vite
- TailwindCSS (dark theme preferred)
- React Router v6 (routes already defined in App.tsx)
- Zustand for global state
- Chart.js + react-chartjs-2 for charts
- React Hook Form + Yup for forms
- Axios (apiClient already configured in src/api/client.ts)

════════════════════════════════════════════════════════════════════
EXISTING FILES (DO NOT MODIFY)
════════════════════════════════════════════════════════════════════
- src/App.tsx              — routing (already complete)
- src/main.tsx             — entry point
- src/index.css            — base styles
- src/contexts/AuthContext.tsx   — auth state (useAuth hook)
- src/components/ProtectedRoute.tsx
- src/api/client.ts        — axios instance (baseURL = /api/v1)
- src/api/auth.ts          — auth API calls

════════════════════════════════════════════════════════════════════
FILES YOU MUST CREATE
════════════════════════════════════════════════════════════════════

1. src/layouts/Layout.tsx
   - Dark sidebar (bg-gray-900) with navigation links
   - Links: Dashboard, Marketplace, Studio, Scheduler, Workspace, Billing, Memories
   - Show current user email + logout button at bottom
   - Use <Outlet /> from react-router-dom for page content
   - Active link highlighted

2. src/pages/Login.tsx
   - Email + password form with React Hook Form + Yup validation
   - Calls useAuth().login()
   - Link to /register

3. src/pages/Register.tsx
   - Email + password + confirm password form
   - Calls useAuth().register()
   - Link to /login

4. src/pages/Dashboard.tsx
   - Token usage line chart (Chart.js) — mock data ok for now
   - Stats cards: Total Agents, Active Sessions, Credits Used, Monthly Cost
   - Recent agent runs table (last 10)
   - Use apiClient.get('/usage') for real data, fallback to mock if error

5. src/pages/Marketplace.tsx
   - Grid of agent cards (bg-gray-800, rounded-xl)
   - Each card: name, description, category badge, pricing tier, "Rent Agent" button
   - Fetch from apiClient.get('/agents/?is_public=true') — fallback to 6 hardcoded agents
   - Categories: SEO, Support, Data, Code, Email, Research

6. src/pages/Studio.tsx
   - Split pane: left = config panel, right = chat console
   - Config: agent name, system prompt textarea, model selector, tools checkboxes
   - Chat: message input + send button + streaming response display
   - Use EventSource for SSE streaming from /api/v1/agents/{id}/stream

7. src/pages/Scheduler.tsx
   - Table of scheduled tasks with status badges
   - "New Task" button → modal with cron expression input + agent selector
   - Use apiClient for CRUD on /tasks/

8. src/pages/Workspace.tsx
   - Organisation name + member list table
   - Invite member form (email + role selector)
   - Role badges: Admin (blue), Member (green), Viewer (gray)

9. src/pages/Billing.tsx
   - Current plan card with credits bar
   - Usage chart (bar chart by day, Chart.js)
   - Invoice table with download buttons

10. src/pages/Memories.tsx
    - Table of agent memory entries (key, value preview, created_at)
    - Delete button per row
    - Export JSON button

11. src/pages/Home.tsx
    - Landing/welcome page for authenticated users
    - Hero with quick action cards linking to main sections

════════════════════════════════════════════════════════════════════
STYLE GUIDELINES
════════════════════════════════════════════════════════════════════
- Dark theme throughout: bg-gray-900, bg-gray-800, text-white
- Accent color: indigo-500 / indigo-600
- Cards: bg-gray-800 rounded-xl p-6 shadow-lg
- Buttons primary: bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg px-4 py-2
- All pages must be functional (no placeholder "coming soon" pages)
- Handle loading states with a spinner
- Handle API errors with a toast or error message

════════════════════════════════════════════════════════════════════
IMPORTANT
════════════════════════════════════════════════════════════════════
- Start by listing existing files to understand what's already there
- Create ALL 11 files listed above
- After creating all files, run: npm install && npm run build
  to verify the build succeeds. Fix any TypeScript errors.
- Log your decisions in docs/frontend_decisions.md (append, don't overwrite)
"""


def main():
    print(f"\n{'='*60}")
    print("  AgentHub FrontendDesigner")
    print(f"  Target: {FRONTEND_DIR}")
    print(f"{'='*60}\n")

    if not FRONTEND_DIR.exists():
        print(f"ERROR: frontend dir not found: {FRONTEND_DIR}")
        sys.exit(1)

    os.chdir(FRONTEND_DIR)

    agent = Agent(
        name="FrontendDesigner",
        role="Complete AgentHub React/TypeScript frontend — all missing pages and layout",
        instructions=INSTRUCTIONS,
        model=DeepSeek(id="deepseek-reasoner"),
        tools=[
            FileTools(base_dir=FRONTEND_DIR),
            ShellTools(),
        ],
        tool_call_limit=80,
    )

    print("FrontendDesigner starting...\n")
    for event in agent.run(
        "Build all missing frontend files for AgentHub as described in your instructions. "
        "Start by listing existing files, then create Layout.tsx and all 11 pages. "
        "After all files are created run npm install && npm run build to verify.",
        stream=True,
    ):
        event_type = type(event).__name__
        if event_type in {"RunContentEvent", "RunResponseContentEvent"}:
            continue
        tool = getattr(event, "tool_name", None)
        if tool:
            args = getattr(event, "tool_args", {}) or {}
            first = str(next(iter(args.values()), ""))[:60] if args else ""
            print(f"  → {tool}({first})")
        else:
            content = getattr(event, "content", None)
            if content and len(str(content)) > 30:
                print(f"  {str(content)[:120].replace(chr(10), ' ')}")

    print(f"\n{'='*60}")
    print("  FrontendDesigner completed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
