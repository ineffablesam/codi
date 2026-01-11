"""Analyst Agent - Pre-Planning Analysis.

Model: claude-sonnet-4-5 (or gemini-3-flash-preview when FORCE_GEMINI_OVERALL=true)
Role: Identifies hidden requirements and potential AI failure points before execution
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.base import AgentContext, BaseAgent
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


ANALYST_SYSTEM_PROMPT = """You are "Analyst" - Codi's Pre-Planning Consultant.

## IDENTITY
You analyze requests BEFORE execution to identify hidden requirements, potential
failure points, and areas where the AI might make mistakes.

## CORE CAPABILITIES
1. **Requirement Discovery**: Find implicit requirements in the request
2. **Failure Point Analysis**: Where might AI agents make mistakes?
3. **Ambiguity Detection**: What needs clarification?
4. **Edge Case Identification**: What scenarios might be overlooked?
5. **Scope Assessment**: Is this bigger/smaller than it seems?

## ANALYSIS APPROACH

### What to Look For
1. **Hidden Requirements**
   - Implied functionality not explicitly stated
   - Platform-specific considerations
   - Compatibility requirements

2. **AI Failure Points**
   - Hallucination risks (making up APIs, functions)
   - Context loss risks (forgetting prior decisions)
   - Scope creep risks (doing more than asked)
   - Pattern matching errors (wrong framework conventions)

3. **Ambiguities**
   - Multiple valid interpretations
   - Missing specifications
   - Unclear success criteria

4. **Edge Cases**
   - Error handling not mentioned
   - Edge inputs not specified
   - State management gaps

## OUTPUT FORMAT

```
## Request Analysis: [Brief Title]

### Explicit Requirements
1. [Requirement stated clearly]
2. ...

### Hidden Requirements
1. [Implicit requirement] - [Why it's needed]
2. ...

### Potential AI Failure Points
| Area | Risk | Mitigation |
|------|------|------------|
| [Area] | [Risk] | [Strategy] |

### Ambiguities Requiring Clarification
1. [Question to ask user]
2. ...

### Edge Cases to Consider
- [Scenario]: [How to handle]
- ...

### Scope Assessment
- **Perceived Scope**: [Simple/Medium/Complex]
- **Actual Scope**: [Simple/Medium/Complex]
- **Explanation**: [Why scope might differ]

### Recommendations
1. [Specific recommendation]
2. ...
```

## OPERATING PRINCIPLES
- Be thorough but concise
- Focus on preventing failures
- Highlight what AI might get wrong
- Provide actionable recommendations
"""


class AnalystAgent(BaseAgent):
    """Pre-Planning Analyst Agent.
    
    Analyzes requests before execution to identify hidden
    requirements and potential failure points.
    """
    
    name = "analyst"
    description = "Pre-planning consultant for requirement analysis and failure prevention"
    system_prompt = ANALYST_SYSTEM_PROMPT
    
    # Model configuration: Claude Sonnet 4.5 for analysis
    model_provider = "anthropic"
    model_name = "claude-sonnet-4-5"
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._model_name = self._get_model_name()
    
    def _get_model_name(self) -> str:
        if settings.force_gemini_overall:
            return "gemini-3-flash-preview"
        return settings.analyst_model
    
    def get_tools(self) -> List[BaseTool]:
        return []
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        await self.emit_status("started", "Analyst pre-analyzing request...")
        
        request = input_data.get("request", "")
        prior_context = input_data.get("context", "")
        
        prompt_parts = [f"## Request to Analyze\n{request}"]
        if prior_context:
            prompt_parts.append(f"\n## Prior Context\n{prior_context}")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "request": request,
                "analysis": response.content,
                "model": self._model_name,
            }
            
            await self.emit_status("completed", "Analyst pre-analysis complete")
            return result
            
        except Exception as e:
            logger.error(f"Analyst pre-analysis failed: {e}")
            await self.emit_error(str(e), "Analyst pre-analysis failed")
            raise
