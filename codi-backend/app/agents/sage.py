"""Sage Agent - Strategic Advisor & Debugging Expert.

Model: gpt-5.2 (or gemini-3-pro-preview when FORCE_GEMINI_OVERALL=true)
Role: Architecture design, code review, high-IQ logical reasoning, strategic problem-solving
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.base import AgentContext, BaseAgent
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


SAGE_SYSTEM_PROMPT = """You are "Sage" - Codi's Strategic Advisor & Debugging Expert.

## IDENTITY
You are the senior engineering advisor that other agents consult for complex decisions.
Read-only consultation mode - you ANALYZE, ADVISE, and RECOMMEND but do NOT implement.

## CORE CAPABILITIES
1. **Architecture Design**: Multi-system tradeoffs, design patterns, scalability analysis
2. **High-IQ Debugging**: Root cause analysis after multiple failed fix attempts
3. **Strategic Reasoning**: Technology choices, implementation approaches, risk assessment
4. **Code Review**: Security, performance, maintainability evaluation
5. **Pattern Recognition**: Identify anti-patterns and suggest improvements

## OPERATING PRINCIPLES

### When Consulted
You are expensive and high-quality. Agents should only consult you for:
- Complex architecture decisions affecting multiple systems
- After 2+ failed attempts at fixing an issue
- Unfamiliar code patterns needing explanation
- Security or performance concerns requiring deep analysis
- Multi-system tradeoffs requiring strategic thinking

### Response Format
Structure your responses clearly:

```
## Analysis
[Your detailed analysis of the problem/question]

## Recommendation
[Clear, actionable recommendation]

## Reasoning
[Why this is the right approach]

## Alternatives Considered
[Other options and why they were rejected]

## Risks & Mitigations
[Potential issues and how to handle them]
```

### Constraints
- You are READ-ONLY - never generate implementation code
- Focus on the "why" more than the "how"
- Be concise but thorough
- Acknowledge uncertainty when present
- Push back on flawed approaches

## ANTI-PATTERNS
Do NOT:
- Generate implementation code
- Answer questions you can infer from existing code patterns
- Handle trivial decisions (variable naming, formatting)
- Be consulted for simple file operations

## TONE
- Direct and confident
- Focus on substance, not pleasantries
- Challenge assumptions when needed
- Provide reasoning for all recommendations
"""


class SageAgent(BaseAgent):
    """Strategic Advisor & Debugging Expert.
    
    Consults on architecture, debugging, and strategic decisions.
    Read-only mode - analyzes and advises but does not implement.
    """
    
    name = "sage"
    description = "Strategic advisor for architecture, debugging, and high-IQ reasoning"
    system_prompt = SAGE_SYSTEM_PROMPT
    
    # Model configuration: GPT-5.2 for high-IQ reasoning
    model_provider = "openai"
    model_name = "gpt-5.2"
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._model_name = self._get_model_name()
    
    def _get_model_name(self) -> str:
        """Get the model name based on configuration."""
        if settings.force_gemini_overall:
            return "gemini-3-pro-preview"  # Use Pro model for advanced reasoning
        return settings.sage_model
    
    def get_tools(self) -> List[BaseTool]:
        """Sage is read-only - no tools needed."""
        return []
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Sage agent for consultation.
        
        Args:
            input_data: Should contain 'question' or 'problem' key
            
        Returns:
            Analysis and recommendations
        """
        await self.emit_status("started", "Sage analyzing problem...")
        
        question = input_data.get("question") or input_data.get("problem", "")
        context = input_data.get("context", "")
        
        # Build the consultation prompt
        prompt_parts = []
        if context:
            prompt_parts.append(f"## Context\n{context}\n")
        prompt_parts.append(f"## Question/Problem\n{question}")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "question": question,
                "analysis": response.content,
                "model": self._model_name,
            }
            
            await self.emit_status("completed", "Sage analysis complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Sage consultation failed: {e}")
            await self.emit_error(str(e), "Sage consultation failed")
            raise
    
    async def consult(
        self,
        question: str,
        context: str = "",
        code_snippets: List[str] = None,
    ) -> str:
        """Consult Sage for advice.
        
        Convenience method for quick consultations.
        
        Args:
            question: The question or problem to analyze
            context: Additional context
            code_snippets: Optional code snippets to analyze
            
        Returns:
            Sage's analysis as a string
        """
        input_data = {
            "question": question,
            "context": context,
        }
        
        if code_snippets:
            input_data["context"] += "\n\n## Code Snippets\n"
            for i, snippet in enumerate(code_snippets, 1):
                input_data["context"] += f"\n### Snippet {i}\n```\n{snippet}\n```\n"
        
        result = await self.run(input_data)
        return result.get("analysis", "")
