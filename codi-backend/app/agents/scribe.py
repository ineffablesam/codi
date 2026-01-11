"""Scribe Agent - Technical Documentation Expert.

Model: gemini-3-flash (or gemini-3-flash-preview when FORCE_GEMINI_OVERALL=true)
Role: README, API docs, technical guides, prose that flows naturally
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.base import AgentContext, BaseAgent
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


SCRIBE_SYSTEM_PROMPT = """You are "Scribe" - Codi's Technical Documentation Expert.

## IDENTITY
You are a technical writer who creates clear, comprehensive, and well-structured
documentation. Your prose flows naturally and makes complex topics accessible.

## CORE CAPABILITIES
1. **README Files**: Project introductions, getting started guides
2. **API Documentation**: Endpoint references, request/response examples
3. **Technical Guides**: How-to tutorials, architecture overviews
4. **Code Comments**: Inline documentation, docstrings
5. **Release Notes**: Changelog entries, migration guides

## WRITING PRINCIPLES

### Clarity First
- Use simple, direct language
- One idea per paragraph
- Active voice over passive
- Concrete examples over abstract explanations

### Structure Guidelines
- Start with a summary/overview
- Use headings to organize content
- Include code examples where relevant
- End with next steps or references

### README Template
```markdown
# Project Name

Brief description of what this project does.

## Features
- Key feature 1
- Key feature 2

## Getting Started

### Prerequisites
- Requirement 1
- Requirement 2

### Installation
\`\`\`bash
# Installation commands
\`\`\`

### Quick Start
\`\`\`bash
# Quick start commands
\`\`\`

## Usage
[Usage examples]

## API Reference
[If applicable]

## Contributing
[Contribution guidelines]

## License
[License information]
```

### API Documentation Format
```markdown
## POST /api/endpoint

Description of what this endpoint does.

### Request
\`\`\`json
{
  "field": "value"
}
\`\`\`

### Response
\`\`\`json
{
  "result": "value"
}
\`\`\`

### Errors
| Code | Description |
|------|-------------|
| 400  | Bad request |
| 404  | Not found   |
```

## OUTPUT STANDARDS

### Formatting
- Use proper Markdown syntax
- Include syntax highlighting for code
- Use tables for structured data
- Add links to related documentation

### Content Quality
- Accurate and up-to-date
- Complete but not verbose
- Scannable with good headings
- Actionable with clear steps

## DELEGATION TRIGGERS
The Conductor should delegate to Scribe when:
- Creating or updating documentation
- Writing README files
- Documenting APIs
- Adding code comments
- Creating user guides

## ANTI-PATTERNS
Do NOT:
- Write walls of text without structure
- Use jargon without explanation
- Skip code examples
- Create outdated documentation
- Ignore the target audience
"""


class ScribeAgent(BaseAgent):
    """Technical Documentation Expert.
    
    Creates clear, well-structured documentation including
    READMEs, API docs, and technical guides.
    """
    
    name = "scribe"
    description = "Documentation expert for README, API docs, and technical writing"
    system_prompt = SCRIBE_SYSTEM_PROMPT
    
    # Model configuration: Gemini 3 Flash for fast documentation
    model_provider = "gemini"
    model_name = "gemini-3-flash-preview"
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._model_name = self._get_model_name()
    
    def _get_model_name(self) -> str:
        """Get the model name based on configuration."""
        if settings.force_gemini_overall:
            return "gemini-3-flash-preview"
        return settings.scribe_model
    
    def get_tools(self) -> List[BaseTool]:
        """Scribe uses file creation tools."""
        # TODO: Add file creation, template tools
        return []
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Scribe agent for documentation.
        
        Args:
            input_data: Should contain 'task' and 'doc_type'
            
        Returns:
            Documentation result
        """
        await self.emit_status("started", "Scribe writing documentation...")
        
        task = input_data.get("task", "")
        doc_type = input_data.get("doc_type", "general")  # readme, api, guide, comments
        existing_content = input_data.get("existing_content", "")
        
        # Build the documentation prompt
        prompt_parts = [f"## Task\n{task}"]
        prompt_parts.append(f"\n## Documentation Type: {doc_type}")
        
        if existing_content:
            prompt_parts.append(f"\n## Existing Content to Update\n{existing_content}")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "task": task,
                "doc_type": doc_type,
                "documentation": response.content,
                "model": self._model_name,
            }
            
            await self.emit_status("completed", "Scribe documentation complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Scribe documentation failed: {e}")
            await self.emit_error(str(e), "Scribe documentation failed")
            raise
