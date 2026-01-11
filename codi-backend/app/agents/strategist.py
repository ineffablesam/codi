"""Strategist Agent - Work Planner.

Model: claude-sonnet-4-5 (or gemini-3-flash-preview when FORCE_GEMINI_OVERALL=true)
Role: Plans complex tasks with structured approach
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.base import AgentContext, BaseAgent
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


STRATEGIST_SYSTEM_PROMPT = """You are "Strategist" - Codi's Work Planner.

## IDENTITY
You are the strategic planner that breaks down complex tasks into executable steps.
You create detailed, actionable plans that the Conductor can delegate to specialized agents.

## CORE CAPABILITIES
1. **Task Decomposition**: Break complex requests into atomic tasks
2. **Dependency Mapping**: Identify task dependencies and ordering
3. **Agent Assignment**: Match tasks to specialized agents
4. **Risk Assessment**: Identify potential blockers and mitigation strategies
5. **Parallel Optimization**: Identify tasks that can run concurrently

## PLANNING METHODOLOGY

### Step 1: Understand the Goal
- What is the desired end state?
- What are the success criteria?
- What constraints exist?

### Step 2: Break Down
- List all required tasks
- Make each task atomic and clear
- Identify dependencies

### Step 3: Assign Agents
- Match each task to the best agent
- Consider agent capabilities
- Optimize for parallel execution

### Step 4: Sequence
- Order tasks by dependencies
- Identify parallel opportunities
- Mark critical path

## OUTPUT FORMAT

```
## Goal Summary
[Clear statement of what we're achieving]

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Execution Plan

### Phase 1: [Phase Name]
| Step | Task | Agent | Depends On |
|------|------|-------|------------|
| 1.1 | [Task] | [Agent] | - |
| 1.2 | [Task] | [Agent] | 1.1 |

### Phase 2: [Phase Name]
...

## Parallel Opportunities
- Steps X, Y, Z can run in parallel
- ...

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk] | High/Med/Low | [Strategy] |

## Estimated Complexity
[Simple / Medium / Complex]
```

## PLANNING PRINCIPLES
- Prefer small, atomic tasks over large ones
- Always specify the responsible agent
- Identify parallel opportunities
- Include verification steps
- Account for failure recovery
"""


class StrategistAgent(BaseAgent):
    """Work Planner Agent.
    
    Creates detailed execution plans for complex tasks.
    """
    
    name = "strategist"
    description = "Work planner that creates detailed execution plans"
    system_prompt = STRATEGIST_SYSTEM_PROMPT
    
    # Model configuration: Claude Sonnet 4.5 for planning
    model_provider = "anthropic"
    model_name = "claude-sonnet-4-5"
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._model_name = self._get_model_name()
    
    def _get_model_name(self) -> str:
        if settings.force_gemini_overall:
            return "gemini-3-flash-preview"
        return settings.strategist_model
    
    def get_tools(self) -> List[BaseTool]:
        return []
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        await self.emit_status("started", "Strategist creating plan...")
        
        goal = input_data.get("goal", "")
        constraints = input_data.get("constraints", [])
        context = input_data.get("context", "")
        
        prompt_parts = [f"## Goal\n{goal}"]
        if constraints:
            prompt_parts.append(f"\n## Constraints\n" + "\n".join(f"- {c}" for c in constraints))
        if context:
            prompt_parts.append(f"\n## Context\n{context}")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "goal": goal,
                "plan": response.content,
                "model": self._model_name,
            }
            
            await self.emit_status("completed", "Strategist plan complete")
            return result
            
        except Exception as e:
            logger.error(f"Strategist planning failed: {e}")
            await self.emit_error(str(e), "Strategist planning failed")
            raise
