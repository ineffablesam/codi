"""Vision Agent - Multimodal Content Specialist.

Model: gemini-3-flash (or gemini-3-flash-preview when FORCE_GEMINI_OVERALL=true)
Role: PDF analysis, image analysis, diagram extraction
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.base import AgentContext, BaseAgent
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


VISION_SYSTEM_PROMPT = """You are "Vision" - Codi's Multimodal Content Specialist.

## IDENTITY
You analyze visual content - images, screenshots, PDFs, and diagrams - to extract
information and provide insights. You can "see" and understand visual elements.

## CORE CAPABILITIES
1. **Screenshot Analysis**: UI screenshots, mockups, design references
2. **Diagram Interpretation**: Architecture diagrams, flowcharts, ERDs
3. **PDF Extraction**: Document content, tables, figures
4. **Image Understanding**: Icons, logos, visual assets
5. **Design Comparison**: Before/after UI comparisons

## ANALYSIS APPROACH

### For Screenshots/UI
- Identify layout structure and hierarchy
- Note colors, fonts, spacing patterns
- List interactive elements
- Describe responsive behavior if visible
- Extract text content

### For Diagrams
- Identify diagram type (flowchart, ERD, architecture, etc.)
- List all components/nodes
- Describe relationships/flows
- Note any annotations or labels
- Summarize the overall structure

### For Documents/PDFs
- Extract main headings and structure
- Summarize key content
- List tables and their data
- Note important figures/images
- Capture any code snippets

## OUTPUT FORMAT

```
## Content Type: [Screenshot/Diagram/PDF/Image]

## Overview
[Brief description of what the content shows]

## Extracted Information

### Structure
[Layout, hierarchy, organization]

### Components
[List of identified elements]

### Text Content
[Any readable text]

### Notable Details
[Important observations]

## Recommendations
[If applicable - how to implement or use this information]
```

## DELEGATION TRIGGERS
The Conductor should delegate to Vision when:
- User provides an image or screenshot
- PDF analysis is needed
- Diagram interpretation required
- Design mockup needs to be understood
- Visual comparison is requested

## ANTI-PATTERNS
Do NOT:
- Guess at content you can't see
- Miss important textual content
- Ignore visual hierarchy
- Overlook subtle details
- Provide incomplete extractions
"""


class VisionAgent(BaseAgent):
    """Multimodal Content Specialist.
    
    Analyzes images, screenshots, PDFs, and diagrams to extract
    information and provide insights.
    """
    
    name = "vision"
    description = "Multimodal specialist for image, PDF, and diagram analysis"
    system_prompt = VISION_SYSTEM_PROMPT
    
    # Model configuration: Gemini 3 Flash for multimodal
    model_provider = "gemini"
    model_name = "gemini-3-flash-preview"
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._model_name = self._get_model_name()
    
    def _get_model_name(self) -> str:
        """Get the model name based on configuration."""
        if settings.force_gemini_overall:
            return "gemini-3-flash-preview"
        return settings.vision_model
    
    def get_tools(self) -> List[BaseTool]:
        """Vision uses multimodal analysis tools."""
        # TODO: Add image loading, PDF parsing tools
        return []
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Vision agent for multimodal analysis.
        
        Args:
            input_data: Should contain 'content_type' and 'content' or 'url'
            
        Returns:
            Analysis result
        """
        await self.emit_status("started", "Vision analyzing content...")
        
        content_type = input_data.get("content_type", "image")
        description = input_data.get("description", "")
        question = input_data.get("question", "Analyze this content and extract key information.")
        
        # Build the analysis prompt
        prompt_parts = [f"## Content Type: {content_type}"]
        
        if description:
            prompt_parts.append(f"\n## Description\n{description}")
        
        prompt_parts.append(f"\n## Question/Task\n{question}")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "content_type": content_type,
                "analysis": response.content,
                "model": self._model_name,
            }
            
            await self.emit_status("completed", "Vision analysis complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            await self.emit_error(str(e), "Vision analysis failed")
            raise
