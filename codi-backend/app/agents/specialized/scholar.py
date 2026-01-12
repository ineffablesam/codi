"""Scholar Agent - Documentation & Research Specialist.

Model: claude-sonnet-4-5 (or gemini-3-flash-preview when FORCE_GEMINI_OVERALL=true)
Role: Multi-repo analysis, official docs lookup, GitHub implementation examples
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.base import AgentContext, BaseAgent
from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


SCHOLAR_SYSTEM_PROMPT = """You are "Scholar" - Codi's Documentation & Research Specialist.

## IDENTITY
You are the research expert that finds external information, documentation, and real-world examples.
You search EXTERNAL resources (docs, OSS repos, web) - not the local codebase.

## CORE CAPABILITIES
1. **Official Documentation**: Find and extract relevant API docs, framework guides
2. **GitHub Examples**: Search for real-world implementations in open source projects
3. **Best Practices**: Research established patterns and recommendations
4. **Library Research**: Investigate unfamiliar libraries, their quirks, and usage patterns
5. **Evidence-Based Answers**: Always cite sources and provide references

## WHEN TO USE (Trigger Phrases)
- "How do I use [library]?"
- "What's the best practice for [framework feature]?"
- "Why does [external dependency] behave this way?"
- "Find examples of [library] usage"
- Working with unfamiliar npm/pip/cargo/pub packages

## OPERATING PRINCIPLES

### Search Strategy
1. Start with official documentation
2. Look for well-maintained open source examples
3. Check for common gotchas and edge cases
4. Verify information is current (check versions)

### Response Format
Structure your research clearly:

```
## Summary
[Quick answer to the question]

## Official Documentation
[Relevant excerpts from official docs]
Source: [URL or reference]

## Real-World Examples
[Code examples from reputable sources]
Source: [GitHub repo or project]

## Best Practices
[Established patterns and recommendations]

## Common Pitfalls
[Things to watch out for]

## References
- [List of sources consulted]
```

### Evidence Standards
- Always cite sources
- Prefer official docs over blog posts
- Note version compatibility
- Flag outdated information
- Distinguish between verified and speculative info

## ANTI-PATTERNS
Do NOT:
- Search the local/internal codebase (use Scout for that)
- Make up information without sources
- Provide outdated solutions without noting version issues
- Mix internal and external code patterns

## DELEGATION TRIGGER
Other agents should fire Scholar immediately when:
- Unfamiliar library or package is mentioned
- Framework documentation is needed
- Looking for production-grade examples
- Debugging behavior that might be library-specific
"""


class ScholarAgent(BaseAgent):
    """Documentation & Research Specialist.
    
    Searches external resources, documentation, and OSS repos
    for information, examples, and best practices.
    """
    
    name = "scholar"
    description = "Research specialist for documentation, examples, and best practices"
    system_prompt = SCHOLAR_SYSTEM_PROMPT
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._model_name = self._get_model_name()
    
    def _get_model_name(self) -> str:
        """Get the model name based on configuration."""
        if settings.force_gemini_overall:
            return "gemini-3-flash-preview"
        return settings.scholar_model
    
    def get_tools(self) -> List[BaseTool]:
        """Scholar can use search tools when available."""
        # TODO: Add web search tools, documentation fetching tools
        return []
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Scholar agent for research.
        
        Args:
            input_data: Should contain 'query' or 'topic'
            
        Returns:
            Research results with sources
        """
        await self.emit_status("started", "Scholar researching...")
        
        query = input_data.get("query") or input_data.get("topic", "")
        library = input_data.get("library")
        framework = input_data.get("framework")
        
        # Build the research prompt
        prompt_parts = [f"## Research Query\n{query}"]
        
        if library:
            prompt_parts.append(f"\n## Library/Package\n{library}")
        if framework:
            prompt_parts.append(f"\n## Framework\n{framework}")
        
        prompt_parts.append("\n\nProvide comprehensive research with sources.")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "query": query,
                "research": response.content,
                "model": self._model_name,
            }
            
            await self.emit_status("completed", "Scholar research complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Scholar research failed: {e}")
            await self.emit_error(str(e), "Scholar research failed")
            raise
    
    async def research(
        self,
        query: str,
        library: str = None,
        framework: str = None,
    ) -> str:
        """Research a topic.
        
        Convenience method for quick research.
        
        Args:
            query: The research query
            library: Optional library name
            framework: Optional framework name
            
        Returns:
            Research results as a string
        """
        result = await self.run({
            "query": query,
            "library": library,
            "framework": framework,
        })
        return result.get("research", "")
