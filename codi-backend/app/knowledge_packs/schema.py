"""Schema definitions for knowledge packs."""

from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum


class RulePriority(str, Enum):
    """Priority levels for rules."""
    CRITICAL = "critical"  # Hard constraints - blocks generation if violated
    HIGH = "high"          # Strong recommendations
    MEDIUM = "medium"      # Best practices
    LOW = "low"           # Suggestions


class PackType(str, Enum):
    """Type of integration pack."""
    FRONTEND = "frontend"
    BACKEND = "backend"
    DEPLOYMENT = "deployment"


class PackMetadata(BaseModel):
    """Metadata for a knowledge pack."""
    name: str
    version: str
    pack_type: PackType
    description: str
    compatibility: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class PackRule(BaseModel):
    """A single rule within a knowledge pack."""
    title: str
    content: str
    priority: RulePriority = RulePriority.MEDIUM
    category: str  # e.g., "architecture", "codegen", "orm"
    
    class Config:
        use_enum_values = True


class PackRules(BaseModel):
    """Collection of rules from different categories."""
    rules: List[PackRule] = Field(default_factory=list)
    
    def get_by_category(self, category: str) -> List[PackRule]:
        """Get all rules for a specific category."""
        return [r for r in self.rules if r.category == category]
    
    def get_by_priority(self, priority: RulePriority) -> List[PackRule]:
        """Get all rules of a specific priority."""
        return [r for r in self.rules if r.priority == priority]
    
    def format_for_agent(self, categories: Optional[List[str]] = None) -> str:
        """Format rules as markdown for agent consumption."""
        rules_to_format = self.rules
        if categories:
            rules_to_format = [r for r in self.rules if r.category in categories]
        
        if not rules_to_format:
            return ""
        
        # Group by priority
        critical = [r for r in rules_to_format if r.priority == RulePriority.CRITICAL]
        high = [r for r in rules_to_format if r.priority == RulePriority.HIGH]
        medium = [r for r in rules_to_format if r.priority == RulePriority.MEDIUM]
        low = [r for r in rules_to_format if r.priority == RulePriority.LOW]
        
        output = []
        
        if critical:
            output.append("## CRITICAL RULES (MUST FOLLOW)")
            for rule in critical:
                output.append(f"### {rule.title}")
                output.append(rule.content)
                output.append("")
        
        if high:
            output.append("## HIGH PRIORITY RULES")
            for rule in high:
                output.append(f"### {rule.title}")
                output.append(rule.content)
                output.append("")
        
        if medium:
            output.append("## BEST PRACTICES")
            for rule in medium:
                output.append(f"### {rule.title}")
                output.append(rule.content)
                output.append("")
        
        if low:
            output.append("## SUGGESTIONS")
            for rule in low:
                output.append(f"### {rule.title}")
                output.append(rule.content)
                output.append("")
        
        return "\n".join(output)


class PackTemplate(BaseModel):
    """A code template within a knowledge pack."""
    name: str
    path: Path
    description: str
    variables: List[str] = Field(default_factory=list)
    content: str
    
    def render(self, **kwargs) -> str:
        """Render template with provided variables."""
        result = self.content
        for var in self.variables:
            placeholder = f"{{{{{var}}}}}"
            if var in kwargs:
                result = result.replace(placeholder, str(kwargs[var]))
        return result


class PackExample(BaseModel):
    """An example code snippet."""
    name: str
    category: str  # e.g., "endpoints", "models", "client"
    description: str
    code: str
    tags: List[str] = Field(default_factory=list)


class PackPitfall(BaseModel):
    """Common pitfall or mistake to avoid."""
    title: str
    description: str
    wrong_approach: Optional[str] = None
    correct_approach: Optional[str] = None
    is_agent_trap: bool = False  # Specifically targets LLM mistakes


class KnowledgePack(BaseModel):
    """Complete knowledge pack for a technology."""
    metadata: PackMetadata
    rules: PackRules = Field(default_factory=PackRules)
    templates: Dict[str, PackTemplate] = Field(default_factory=dict)
    examples: List[PackExample] = Field(default_factory=list)
    pitfalls: List[PackPitfall] = Field(default_factory=list)
    
    def get_context_for_agent(
        self,
        include_rules: Optional[List[str]] = None,
        include_examples: bool = False,
        include_pitfalls: bool = True,
    ) -> str:
        """Generate context string for agent."""
        sections = []
        
        # Header
        sections.append(f"# {self.metadata.name} Integration Guide")
        sections.append(f"{self.metadata.description}\n")
        
        # Rules
        if self.rules.rules:
            rules_text = self.rules.format_for_agent(categories=include_rules)
            if rules_text:
                sections.append(rules_text)
        
        # Pitfalls
        if include_pitfalls and self.pitfalls:
            sections.append("## COMMON PITFALLS - AVOID THESE")
            
            # Agent-specific traps first
            agent_traps = [p for p in self.pitfalls if p.is_agent_trap]
            if agent_traps:
                sections.append("### Agent-Specific Traps (LLMs commonly get these wrong)")
                for pitfall in agent_traps:
                    sections.append(f"#### {pitfall.title}")
                    sections.append(pitfall.description)
                    if pitfall.wrong_approach:
                        sections.append(f"❌ **Wrong:** {pitfall.wrong_approach}")
                    if pitfall.correct_approach:
                        sections.append(f"✅ **Correct:** {pitfall.correct_approach}")
                    sections.append("")
            
            # General pitfalls
            general_pitfalls = [p for p in self.pitfalls if not p.is_agent_trap]
            if general_pitfalls:
                sections.append("### General Common Mistakes")
                for pitfall in general_pitfalls:
                    sections.append(f"#### {pitfall.title}")
                    sections.append(pitfall.description)
                    if pitfall.wrong_approach:
                        sections.append(f"❌ **Wrong:** {pitfall.wrong_approach}")
                    if pitfall.correct_approach:
                        sections.append(f"✅ **Correct:** {pitfall.correct_approach}")
                    sections.append("")
        
        # Examples (optional, can be heavy)
        if include_examples and self.examples:
            sections.append("## EXAMPLES")
            for example in self.examples[:3]:  # Limit to first 3 to avoid context bloat
                sections.append(f"### {example.name}")
                sections.append(example.description)
                sections.append(f"```\n{example.code}\n```")
                sections.append("")
        
        # Available templates
        if self.templates:
            sections.append("## AVAILABLE TEMPLATES")
            for name, template in self.templates.items():
                sections.append(f"- **{name}**: {template.description}")
            sections.append("")
        
        return "\n".join(sections)
    
    def get_template(self, name: str) -> Optional[PackTemplate]:
        """Get a specific template by name."""
        return self.templates.get(name)
    
    def get_examples_by_category(self, category: str) -> List[PackExample]:
        """Get all examples for a specific category."""
        return [e for e in self.examples if e.category == category]
