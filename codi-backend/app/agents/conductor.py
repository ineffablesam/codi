"""Conductor Agent - Master Orchestrator.

Model: claude-opus-4-5 (or gemini-3-pro-preview when FORCE_GEMINI_OVERALL=true)
Role: Main orchestrator that plans, delegates, and executes complex tasks
"""
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.base import AgentContext, BaseAgent
from app.agents.types import AgentCategory, CATEGORIES, DelegationContext
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


CONDUCTOR_SYSTEM_PROMPT = """You are "Conductor" - Codi's Master Orchestrator.

## IDENTITY
You are the team lead orchestrating Codi's multi-agent system. You plan obsessively,
delegate strategically, and execute complex tasks through intelligent coordination
of specialized agents.

## SPECIALIZED AGENTS AT YOUR DISPOSAL

| Agent | Role | When to Delegate |
|-------|------|------------------|
| **Sage** | Strategic advisor | Architecture decisions, complex debugging after 2+ failed attempts |
| **Scholar** | Research specialist | External docs, library research, examples |
| **Scout** | Fast reconnaissance | Codebase search, pattern matching, file discovery |
| **Artisan** | UI/UX specialist | Beautiful UI, visual design, animations |
| **Scribe** | Documentation expert | README, API docs, technical writing |
| **Vision** | Multimodal analysis | Screenshot, PDF, diagram analysis |
| **FlutterEngineer** | Flutter implementation | Dart code, widgets, mobile app logic |
| **ReactEngineer** | React implementation | Web apps, React components |
| **NextjsEngineer** | Next.js implementation | Server-side React, full-stack web |
| **CodeReviewer** | Code review | Pre-commit validation, quality checks |
| **GitOperator** | Git operations | Commits, branches, PRs |
| **BuildDeploy** | Build & deploy | CI/CD, deployment pipelines |

## PHASE 0 - INTENT GATE (EVERY MESSAGE)

### Step 1: Classify Request Type
- **Trivial**: Direct questions, simple lookups → Answer directly
- **Explicit**: Clear implementation request → Execute or delegate
- **Exploratory**: Needs codebase understanding → Scout first
- **Open-ended**: Large creative tasks → Strategist then parallel execution
- **Ambiguous**: Unclear requirements → Ask for clarification

### Step 2: Check for Ambiguity
If request is ambiguous, ask clarifying questions:
- What is the expected behavior?
- Which files/components are involved?
- Are there constraints (platform, dependencies)?

### Step 3: Validate Before Acting
Before implementation:
- [ ] Understand the full scope
- [ ] Know which files to modify
- [ ] Have clear success criteria

## DELEGATION PRINCIPLES

### When to Delegate
- **Sage**: Architecture decisions, stuck after 2+ attempts, security concerns
- **Scholar**: Unknown libraries, need external docs, best practices
- **Scout** (background): Codebase exploration, pattern discovery
- **Artisan**: Visual design, UI polish, animations
- **Platform Engineers**: Feature implementation in their domain

### Delegation Format
When delegating, provide:
1. **TASK**: Clear, atomic task description
2. **EXPECTED OUTCOME**: Specific deliverables
3. **CONTEXT**: Relevant information from prior work
4. **CONSTRAINTS**: What to avoid, boundaries

### Parallel Execution
Fire multiple Scout tasks in parallel for:
- Cross-layer pattern discovery
- Multi-file impact analysis
- Unfamiliar codebase exploration

## IMPLEMENTATION WORKFLOW

### Phase 1: Understanding
1. Classify intent
2. Consult Sage for complex architecture decisions
3. Fire Scout for codebase exploration (background)

### Phase 2: Planning
1. Break into atomic tasks
2. Assign to appropriate agents
3. Set execution order

### Phase 3: Execution
1. Delegate tasks
2. Monitor progress
3. Handle failures and retry with adjusted approach

### Phase 4: Verification
1. Run tests/builds
2. Code review via CodeReviewer
3. Commit via GitOperator

## OUTPUT FORMAT

For complex tasks, structure your response:

```
## Understanding
[What I understand about the request]

## Plan
1. [First step] → [Agent]
2. [Second step] → [Agent]
...

## Execution
[What I'm doing now]

## Next Steps
[What happens next]
```

## CONSTRAINTS
- NEVER skip the intent classification
- ALWAYS delegate UI work to Artisan
- CONSULT Sage for architecture, not implementation
- USE Scout for exploration, Scholar for external research
- VERIFY changes before committing
"""


# Available agents for delegation
AVAILABLE_AGENTS = {
    "sage": "Strategic advisor for architecture and debugging",
    "scholar": "Research specialist for external docs and examples",
    "scout": "Fast reconnaissance for codebase exploration",
    "artisan": "UI/UX specialist for beautiful interfaces",
    "scribe": "Documentation expert for technical writing",
    "vision": "Multimodal analysis for images and PDFs",
    "flutter_engineer": "Flutter/Dart implementation",
    "react_engineer": "React web implementation",
    "nextjs_engineer": "Next.js full-stack implementation",
    "react_native_engineer": "React Native mobile implementation",
    "code_reviewer": "Pre-commit code review",
    "git_operator": "Git operations (commit, branch, PR)",
    "build_deploy": "Build and deployment",
}


class ConductorAgent(BaseAgent):
    """Master Orchestrator Agent.
    
    Plans, delegates, and executes complex tasks through intelligent
    coordination of specialized agents.
    """
    
    name = "conductor"
    description = "Master orchestrator that plans and delegates to specialized agents"
    system_prompt = CONDUCTOR_SYSTEM_PROMPT
    
    # Model configuration: Claude Opus 4.5 for orchestration
    model_provider = "anthropic"
    model_name = "claude-opus-4-5"
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._model_name = self._get_model_name()
    
    def _get_model_name(self) -> str:
        """Get the model name based on configuration."""
        if settings.force_gemini_overall:
            return "gemini-3-pro-preview"  # Use thinking model for orchestration
        return settings.conductor_model
    
    def get_tools(self) -> List[BaseTool]:
        """Conductor uses delegation and coordination tools."""
        from app.agents.tools.delegation import (
            create_delegate_task_tool,
            create_background_output_tool,
            create_background_cancel_tool,
        )
        
        return [
            create_delegate_task_tool(self.context),
            create_background_output_tool(),
            create_background_cancel_tool(),
        ]
    
    def classify_intent(self, message: str) -> str:
        """Classify the user's intent.
        
        Returns:
            One of: trivial, explicit, exploratory, open_ended, ambiguous
        """
        message_lower = message.lower()
        
        # Trivial: Questions, simple lookups
        if any(q in message_lower for q in ["what is", "how does", "explain", "?"]):
            if len(message.split()) < 20:
                return "trivial"
        
        # Explicit: Clear instructions
        if any(kw in message_lower for kw in ["create", "add", "implement", "fix", "update"]):
            return "explicit"
        
        # Open-ended: Large creative tasks
        if any(kw in message_lower for kw in ["build", "design", "refactor", "migrate"]):
            return "open_ended"
        
        # Exploratory: Needs understanding
        if any(kw in message_lower for kw in ["find", "search", "where", "look for"]):
            return "exploratory"
        
        return "ambiguous"
    
    def select_agent(self, task_type: str, context: Dict[str, Any] = None) -> str:
        """Select the best agent for a task type.
        
        Args:
            task_type: Type of task
            context: Optional context for better selection
            
        Returns:
            Agent name to delegate to
        """
        task_lower = task_type.lower()
        
        # UI/Visual tasks -> Artisan
        if any(kw in task_lower for kw in ["ui", "design", "beautiful", "style", "animation"]):
            return "artisan"
        
        # Documentation -> Scribe
        if any(kw in task_lower for kw in ["readme", "docs", "document", "guide"]):
            return "scribe"
        
        # Research -> Scholar
        if any(kw in task_lower for kw in ["research", "look up", "how to use", "library"]):
            return "scholar"
        
        # Architecture/Strategy -> Sage
        if any(kw in task_lower for kw in ["architecture", "design pattern", "strategy", "debug"]):
            return "sage"
        
        # Codebase exploration -> Scout
        if any(kw in task_lower for kw in ["find", "search", "explore", "where"]):
            return "scout"
        
        # Flutter -> FlutterEngineer
        if any(kw in task_lower for kw in ["flutter", "dart", "widget"]):
            return "flutter_engineer"
        
        # React -> ReactEngineer
        if any(kw in task_lower for kw in ["react", "component", "hook"]):
            return "react_engineer"
        
        # Default to flutter_engineer for now
        return "flutter_engineer"
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Conductor for orchestration.
        
        Args:
            input_data: Should contain 'message' from user
            
        Returns:
            Orchestration result
        """
        await self.emit_status("started", "Conductor analyzing request...")
        
        message = input_data.get("message", "")
        context = input_data.get("context", {})
        
        # Classify intent
        intent = self.classify_intent(message)
        logger.info(f"Conductor classified intent as: {intent}")
        
        await self.emit_status("in_progress", f"Intent: {intent}, planning execution...")
        
        # Build orchestration prompt
        prompt_parts = [
            f"## User Request\n{message}",
            f"\n## Intent Classification: {intent}",
            f"\n## Available Agents\n" + "\n".join(
                f"- **{name}**: {desc}" for name, desc in AVAILABLE_AGENTS.items()
            ),
        ]
        
        if context:
            prompt_parts.append(f"\n## Context\n{context}")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            # Use LLM with tools for delegation
            if self.tools:
                llm_with_tools = self.llm.bind_tools(self.tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await self.llm.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "intent": intent,
                "plan": response.content,
                "model": self._model_name,
            }
            
            await self.emit_status("completed", "Conductor orchestration complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Conductor orchestration failed: {e}")
            await self.emit_error(str(e), "Conductor orchestration failed")
            raise
    
    async def delegate(
        self,
        agent: str,
        task: str,
        expected_outcome: str,
        context: str = "",
        background: bool = False,
    ) -> DelegationContext:
        """Delegate a task to another agent.
        
        Args:
            agent: Agent name to delegate to
            task: Task description
            expected_outcome: Expected deliverable
            context: Additional context
            background: Run as background task
            
        Returns:
            DelegationContext with delegation info
        """
        delegation = DelegationContext(
            from_agent=self.name,
            to_agent=agent,
            reason=task,
            expected_outcome=expected_outcome,
        )
        
        await self.emit_status(
            "in_progress",
            f"Delegating to {agent}: {task[:50]}..."
        )
        
        # TODO: Actually invoke the target agent
        # This will be connected to the workflow graph
        
        return delegation
