"""Pack loader - loads and parses knowledge packs from disk."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
import logging
from functools import lru_cache

from .schema import (
    KnowledgePack,
    PackMetadata,
    PackRules,
    PackRule,
    PackTemplate,
    PackExample,
    PackPitfall,
    RulePriority,
)

logger = logging.getLogger(__name__)


class PackLoader:
    """Loads knowledge packs from disk."""
    
    def __init__(self, base_path: Path):
        """Initialize pack loader.
        
        Args:
            base_path: Base path to integrations directory
        """
        self.base_path = Path(base_path)
    
    def load(self, pack_path: str) -> Optional[KnowledgePack]:
        """Load a single knowledge pack.
        
        Args:
            pack_path: Relative path to pack directory (e.g., "backends/serverpod")
            
        Returns:
            Loaded KnowledgePack or None if loading fails
        """
        full_path = self.base_path / pack_path
        
        if not full_path.exists():
            logger.error(f"Pack not found: {full_path}")
            return None
        
        try:
            # Load pack.yaml
            pack_yaml_path = full_path / "pack.yaml"
            if not pack_yaml_path.exists():
                logger.error(f"pack.yaml not found in {full_path}")
                return None
            
            with open(pack_yaml_path, "r") as f:
                pack_data = yaml.safe_load(f)
            
            # Parse metadata
            metadata = PackMetadata(**pack_data)
            
            # Load rules
            rules = self._load_rules(full_path / "rules")
            
            # Load templates
            templates = self._load_templates(full_path / "templates")
            
            # Load examples
            examples = self._load_examples(full_path / "examples")
            
            # Load pitfalls
            pitfalls = self._load_pitfalls(full_path / "pitfalls")
            
            return KnowledgePack(
                metadata=metadata,
                rules=rules,
                templates=templates,
                examples=examples,
                pitfalls=pitfalls,
            )
        
        except Exception as e:
            logger.error(f"Failed to load pack {pack_path}: {e}")
            return None
    
    def _load_rules(self, rules_path: Path) -> PackRules:
        """Load all rule files from rules directory."""
        if not rules_path.exists():
            return PackRules()
        
        all_rules = []
        
        for rule_file in rules_path.glob("*.md"):
            category = rule_file.stem
            
            try:
                content = rule_file.read_text()
                
                # Parse frontmatter if exists
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        rule_content = parts[2].strip()
                        
                        # Extract rules from frontmatter
                        if isinstance(frontmatter, list):
                            for rule_data in frontmatter:
                                all_rules.append(PackRule(
                                    title=rule_data.get("title", category),
                                    content=rule_content,
                                    priority=RulePriority(rule_data.get("priority", "medium")),
                                    category=category,
                                ))
                        else:
                            # Single rule with frontmatter
                            all_rules.append(PackRule(
                                title=frontmatter.get("title", category),
                                content=rule_content,
                                priority=RulePriority(frontmatter.get("priority", "medium")),
                                category=category,
                            ))
                else:
                    # No frontmatter, treat entire file as one rule
                    all_rules.append(PackRule(
                        title=category.replace("_", " ").title(),
                        content=content.strip(),
                        priority=RulePriority.MEDIUM,
                        category=category,
                    ))
            
            except Exception as e:
                logger.error(f"Failed to load rule file {rule_file}: {e}")
        
        return PackRules(rules=all_rules)
    
    def _load_templates(self, templates_path: Path) -> Dict[str, PackTemplate]:
        """Load all template files."""
        if not templates_path.exists():
            return {}
        
        templates = {}
        
        for template_file in templates_path.glob("*.tpl"):
            name = template_file.stem
            
            try:
                content = template_file.read_text()
                
                # Extract variables (anything in {{variable}} format)
                import re
                variables = list(set(re.findall(r'\{\{(\w+)\}\}', content)))
                
                # Try to load metadata from .meta.yaml if exists
                meta_file = template_file.with_suffix(".meta.yaml")
                description = f"{name} template"
                
                if meta_file.exists():
                    with open(meta_file, "r") as f:
                        meta = yaml.safe_load(f)
                        description = meta.get("description", description)
                
                templates[name] = PackTemplate(
                    name=name,
                    path=template_file,
                    description=description,
                    variables=variables,
                    content=content,
                )
            
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
        
        return templates
    
    def _load_examples(self, examples_path: Path) -> List[PackExample]:
        """Load all example files."""
        if not examples_path.exists():
            return []
        
        examples = []
        
        # Examples are organized in subdirectories by category
        for category_dir in examples_path.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            
            for example_file in category_dir.glob("*.md"):
                try:
                    content = example_file.read_text()
                    
                    # Parse frontmatter
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            frontmatter = yaml.safe_load(parts[1])
                            code = parts[2].strip()
                            
                            examples.append(PackExample(
                                name=frontmatter.get("name", example_file.stem),
                                category=category,
                                description=frontmatter.get("description", ""),
                                code=code,
                                tags=frontmatter.get("tags", []),
                            ))
                
                except Exception as e:
                    logger.error(f"Failed to load example {example_file}: {e}")
        
        return examples
    
    def _load_pitfalls(self, pitfalls_path: Path) -> List[PackPitfall]:
        """Load pitfall documentation."""
        if not pitfalls_path.exists():
            return []
        
        pitfalls = []
        
        for pitfall_file in pitfalls_path.glob("*.md"):
            try:
                content = pitfall_file.read_text()
                
                # Determine if this is agent_traps
                is_agent_trap = "agent" in pitfall_file.stem.lower()
                
                # Parse frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        
                        # Can be list of pitfalls or single pitfall
                        if isinstance(frontmatter, list):
                            for pitfall_data in frontmatter:
                                pitfalls.append(PackPitfall(
                                    title=pitfall_data.get("title", ""),
                                    description=pitfall_data.get("description", ""),
                                    wrong_approach=pitfall_data.get("wrong"),
                                    correct_approach=pitfall_data.get("correct"),
                                    is_agent_trap=is_agent_trap,
                                ))
                        else:
                            pitfalls.append(PackPitfall(
                                title=frontmatter.get("title", pitfall_file.stem),
                                description=parts[2].strip(),
                                wrong_approach=frontmatter.get("wrong"),
                                correct_approach=frontmatter.get("correct"),
                                is_agent_trap=is_agent_trap,
                            ))
            
            except Exception as e:
                logger.error(f"Failed to load pitfall file {pitfall_file}: {e}")
        
        return pitfalls


# Global loader instance
_loader: Optional[PackLoader] = None


def get_loader(base_path: Optional[Path] = None) -> PackLoader:
    """Get or create global PackLoader instance."""
    global _loader
    
    if _loader is None or base_path is not None:
        if base_path is None:
            # Default to integrations directory
            from pathlib import Path
            base_path = Path(__file__).parent.parent.parent / "integrations"
        _loader = PackLoader(base_path)
    
    return _loader


@lru_cache(maxsize=32)
def load_pack(pack_path: str, base_path: Optional[str] = None) -> Optional[KnowledgePack]:
    """Load a single knowledge pack (cached).
    
    Args:
        pack_path: Relative path to pack (e.g., "backends/serverpod")
        base_path: Optional custom base path
        
    Returns:
        Loaded KnowledgePack or None
    """
    loader = get_loader(Path(base_path) if base_path else None)
    return loader.load(pack_path)


def load_packs(tech_stack: Dict[str, str]) -> List[KnowledgePack]:
    """Load multiple packs based on tech stack selection.
    
    Args:
        tech_stack: Dictionary with keys like "frontend", "backend", "deployment"
                   and values like "nextjs", "serverpod", "docker"
    
    Returns:
        List of loaded KnowledgePacks
    """
    packs = []
    
    # Map tech stack to pack paths
    pack_mapping = {
        "frontend": "frontends",
        "backend": "backends",
        "deployment": "deployment",
    }
    
    for stack_type, technology in tech_stack.items():
        if stack_type in pack_mapping:
            pack_path = f"{pack_mapping[stack_type]}/{technology}"
            pack = load_pack(pack_path)
            if pack:
                packs.append(pack)
            else:
                logger.warning(f"Failed to load pack for {stack_type}={technology}")
    
    return packs
