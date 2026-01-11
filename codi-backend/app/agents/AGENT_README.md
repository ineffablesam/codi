# Codi Agent Architecture

## Overview

Codi uses a multi-agent orchestration system for intelligent task delegation and parallel execution.

## Directory Structure

```
app/agents/
├── __init__.py              # Main exports
├── AGENT_README.md          # This file
├── types.py                 # Core types
├── background_manager.py    # Parallel task execution
├── session_manager.py       # Context tracking
├── conductor.py             # Master orchestrator
├── sage.py                  # Strategic advisor
├── scholar.py               # Research specialist
├── scout.py                 # Codebase search
├── artisan.py               # UI/UX specialist
├── scribe.py                # Technical docs
├── vision.py                # Multimodal analysis
├── strategist.py            # Task planner
├── analyst.py               # Pre-planning
├── planner.py               # Legacy planner
├── code_reviewer.py         # Code review
├── git_operator.py          # Git operations
├── build_deploy.py          # CI/CD
├── memory.py                # Context memory
├── platform/                # Platform-specific agents
│   ├── __init__.py
│   ├── flutter_engineer.py
│   ├── react_engineer.py
│   ├── nextjs_engineer.py
│   ├── react_native_engineer.py
│   └── backend_integration.py
└── tools/                   # Agent tools
    ├── __init__.py
    └── delegation.py
```

## Agent Reference

| Agent | Model | Role |
|-------|-------|------|
| **Conductor** | claude-opus-4-5 | Master orchestrator - plans, delegates, coordinates |
| **Sage** | gpt-5.2 | Strategic advisor - architecture, debugging |
| **Scholar** | claude-sonnet-4-5 | Research specialist - docs, examples |
| **Scout** | gemini-3-flash | Fast reconnaissance - codebase search |
| **Artisan** | gemini-3-pro-high | UI/UX specialist - beautiful interfaces |
| **Scribe** | gemini-3-flash | Documentation expert - README, API docs |
| **Vision** | gemini-3-flash | Multimodal analysis - images, PDFs |
| **Strategist** | claude-sonnet-4-5 | Work planner - task decomposition |
| **Analyst** | claude-sonnet-4-5 | Pre-planning - requirement analysis |

## Model Configuration

```python
# .env
FORCE_GEMINI_OVERALL=true   # All agents use Gemini
FORCE_GEMINI_OVERALL=false  # Agents use preferred models
```

When `FORCE_GEMINI_OVERALL=true`:
- Conductor, Sage → `gemini-3-pro-preview`
- All others → `gemini-3-flash-preview`

> ⚠️ **Gemini 3 Temperature**: Always use `temperature=1.0` (default). Lower values cause looping/degraded performance in reasoning tasks.

## Delegation Flow

1. **User Request** → Conductor
2. **Intent Classification**: trivial, explicit, exploratory, open_ended, ambiguous
3. **Pre-Analysis** (complex tasks): Analyst → requirements + failure points
4. **Planning** (complex tasks): Strategist → execution plan
5. **Execution**: Conductor delegates to specialized agents
6. **Background Tasks**: Scout exploration runs in parallel
7. **Verification**: CodeReviewer → GitOperator → BuildDeploy

## Background Tasks

Use `delegate_task(agent="scout", run_in_background=True)` for parallel execution:
- Codebase exploration
- Multi-file pattern search
- Long-running research

Tools:
- `background_output(task_id)` - Get results
- `background_cancel(task_id)` - Cancel task
- `background_status()` - List all running tasks

## Categories

```python
CATEGORIES = {
    "visual": {"model": "artisan", "temp": 0.7},   # UI/UX
    "logic": {"model": "sage", "temp": 0.1},       # Backend
    "mobile": {"model": "artisan", "temp": 0.5},   # Flutter/RN
}
```

## Adding New Agents

1. Create `app/agents/new_agent.py`:
```python
class NewAgent(BaseAgent):
    name = "new_agent"
    description = "..."
    system_prompt = "..."
    
    def get_tools(self) -> List[BaseTool]:
        return []
    
    async def run(self, input_data: Dict) -> Dict:
        ...
```

2. Add to `app/agents/__init__.py`
3. Add to Conductor's `AVAILABLE_AGENTS`
