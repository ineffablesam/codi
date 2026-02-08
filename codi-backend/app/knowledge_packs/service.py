"""Service layer for knowledge pack system - provides high-level API for agents."""

from typing import Dict, List, Optional
from pathlib import Path
import logging

from .loader import load_packs
from .schema import KnowledgePack, PackTemplate, PackExample

logger = logging.getLogger(__name__)


class KnowledgePackService:
    """Service layer for accessing knowledge packs from agents."""
    
    @staticmethod
    def get_context_for_stack(
        tech_stack: Dict[str, str],
        include_rules: Optional[List[str]] = None,
        include_examples: bool = False,
        include_pitfalls: bool = True,
    ) -> str:
        """Get aggregated context from all packs in tech stack.
        
        Args:
            tech_stack: Dict mapping stack type to technology
                       e.g., {"frontend": "nextjs", "backend": "supabase"}
            include_rules: Optional list of rule categories to include
            include_examples: Whether to include code examples
            include_pitfalls: Whether to include common pitfalls
            
        Returns:
            Formatted context string for agent
        """
        packs = load_packs(tech_stack)
        
        if not packs:
            logger.warning(f"No packs loaded for tech stack: {tech_stack}")
            return ""
        
        # Combine contexts from all packs
        contexts = []
        
        contexts.append("# PROJECT TECHNOLOGY STACK\n")
        for stack_type, technology in tech_stack.items():
            contexts.append(f"- **{stack_type.title()}**: {technology}")
        contexts.append("\n---\n")
        
        for pack in packs:
            context = pack.get_context_for_agent(
                include_rules=include_rules,
                include_examples=include_examples,
                include_pitfalls=include_pitfalls,
            )
            contexts.append(context)
            contexts.append("\n---\n")
        
        return "\n".join(contexts)
    
    @staticmethod
    def get_templates(
        tech_stack: Dict[str, str],
        template_type: Optional[str] = None,
    ) -> Dict[str, PackTemplate]:
        """Get all available templates for tech stack.
        
        Args:
            tech_stack: Tech stack dictionary
            template_type: Optional filter by template name
            
        Returns:
            Dictionary of templates by name
        """
        packs = load_packs(tech_stack)
        
        all_templates = {}
        
        for pack in packs:
            for name, template in pack.templates.items():
                if template_type is None or name == template_type:
                    # Prefix with pack name to avoid conflicts
                    key = f"{pack.metadata.name.lower()}_{name}"
                    all_templates[key] = template
        
        return all_templates
    
    @staticmethod
    def get_examples(
        tech_stack: Dict[str, str],
        category: Optional[str] = None,
    ) -> List[PackExample]:
        """Get code examples from tech stack.
        
        Args:
            tech_stack: Tech stack dictionary
            category: Optional filter by category
            
        Returns:
            List of examples
        """
        packs = load_packs(tech_stack)
        
        all_examples = []
        
        for pack in packs:
            if category:
                examples = pack.get_examples_by_category(category)
            else:
                examples = pack.examples
            
            all_examples.extend(examples)
        
        return all_examples
    
    @staticmethod
    def get_template_by_name(
        tech_stack: Dict[str, str],
        template_name: str,
    ) -> Optional[PackTemplate]:
        """Get a specific template by name.
        
        Args:
            tech_stack: Tech stack dictionary
            template_name: Name of template to retrieve
            
        Returns:
            Template if found, None otherwise
        """
        packs = load_packs(tech_stack)
        
        for pack in packs:
            template = pack.get_template(template_name)
            if template:
                return template
        
        return None
    
    @staticmethod
    def render_template(
        tech_stack: Dict[str, str],
        template_name: str,
        **variables,
    ) -> Optional[str]:
        """Render a template with variables.
        
        Args:
            tech_stack: Tech stack dictionary
            template_name: Name of template
            **variables: Variables to substitute
            
        Returns:
            Rendered template or None if not found
        """
        template = KnowledgePackService.get_template_by_name(tech_stack, template_name)
        
        if not template:
            logger.warning(f"Template '{template_name}' not found in tech stack")
            return None
        
        return template.render(**variables)
