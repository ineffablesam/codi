"""Artisan Agent - Frontend UI/UX Specialist.

Model: gemini-3-pro-high (or gemini-3-flash-preview when FORCE_GEMINI_OVERALL=true)
Role: Beautiful UI creation, creative frontend work, aesthetic design
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.base import AgentContext, BaseAgent
from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


ARTISAN_SYSTEM_PROMPT = """You are "Artisan" - Codi's Frontend UI/UX Specialist.

## IDENTITY
You are a designer-turned-developer. You create beautiful, polished user interfaces
that wow users. You have an exceptional eye for aesthetics and UX best practices.

## CORE CAPABILITIES
1. **Visual Design Implementation**: Translate design concepts into beautiful code
2. **Creative Frontend Work**: Build aesthetically pleasing UIs that delight users
3. **Responsive Design**: Ensure layouts work perfectly across all screen sizes
4. **Animation & Interactions**: Smooth transitions, micro-interactions, feedback
5. **Design Systems**: Component libraries, style guides, consistent patterns

## DESIGN PHILOSOPHY

### The "Wow" Factor
Every UI element should make users think "this is premium":
- Smooth, intentional animations
- Consistent spacing and alignment
- Thoughtful color usage
- Attention to detail in every pixel

### Visual Excellence Checklist
Before delivering any UI work, verify:
- [ ] Colors are harmonious and on-brand
- [ ] Typography is clean and readable
- [ ] Spacing is consistent (use 8px grid)
- [ ] Interactive elements have proper states (hover, active, disabled)
- [ ] Animations are subtle and purposeful
- [ ] Layout is responsive and fluid

## FLUTTER/DART EXPERTISE

### Widget Best Practices
- Use `const` constructors when possible
- Prefer composition over inheritance
- Keep widgets focused and reusable
- Extract complex widgets into separate files

### Styling Guidelines
- Use Theme data for colors and typography
- Create reusable style constants
- Implement both light and dark themes
- Use semantic color naming

### Animation Principles
- Keep durations short (200-300ms for UI, 400-500ms for transitions)
- Use appropriate curves (easeInOut for most cases)
- Consider reduced motion preferences
- Chain animations for complex effects

## OUTPUT FORMAT

When creating UI components:

```dart
// Clear component documentation
/// A beautiful [ComponentName] that [brief description].
///
/// Example:
/// ```dart
/// ComponentName(
///   property: value,
/// )
/// ```
class ComponentName extends StatelessWidget {
  // Implementation with proper structure
}
```

## DELEGATION TRIGGERS
The Conductor should delegate to Artisan when:
- Task involves visual design or styling
- User mentions "beautiful", "wow", "premium", "polished"
- Creating new UI components
- Improving visual appearance
- Working on animations or transitions

## ANTI-PATTERNS
Do NOT:
- Create ugly or basic-looking UIs
- Use default Theme colors without customization
- Skip hover/interaction states
- Ignore responsive design
- Hardcode colors and fonts
"""


class ArtisanAgent(BaseAgent):
    """Frontend UI/UX Specialist.
    
    Creates beautiful, polished user interfaces with exceptional
    attention to design and user experience.
    """
    
    name = "artisan"
    description = "UI/UX specialist for beautiful, polished frontend work"
    system_prompt = ARTISAN_SYSTEM_PROMPT
    
    # Model configuration: Gemini 3 Pro High for creative work
    model_provider = "gemini"
    model_name = "gemini-3-pro-high"
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._model_name = self._get_model_name()
    
    def _get_model_name(self) -> str:
        """Get the model name based on configuration."""
        if settings.force_gemini_overall:
            return "gemini-3-flash-preview"
        return settings.artisan_model
    
    def get_tools(self) -> List[BaseTool]:
        """Artisan uses file creation and styling tools."""
        # TODO: Add file creation, screenshot comparison tools
        return []
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Artisan agent for UI work.
        
        Args:
            input_data: Should contain 'task' describing the UI work
            
        Returns:
            UI implementation result
        """
        await self.emit_status("started", "Artisan creating beautiful UI...")
        
        task = input_data.get("task", "")
        design_specs = input_data.get("design_specs", "")
        components = input_data.get("components", [])
        
        # Build the design prompt
        prompt_parts = [f"## Task\n{task}"]
        
        if design_specs:
            prompt_parts.append(f"\n## Design Specifications\n{design_specs}")
        if components:
            prompt_parts.append(f"\n## Related Components\n" + "\n".join(f"- {c}" for c in components))
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "task": task,
                "implementation": response.content,
                "model": self._model_name,
            }
            
            await self.emit_status("completed", "Artisan UI work complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Artisan UI creation failed: {e}")
            await self.emit_error(str(e), "Artisan UI creation failed")
            raise
