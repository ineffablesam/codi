"""Validation utilities for knowledge packs."""

import yaml
from pathlib import Path
from typing import List, Optional, Tuple
import logging

from .schema import PackMetadata, PackType

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Pack validation error."""
    pass


class PackValidator:
    """Validates knowledge pack structure and content."""
    
    @staticmethod
    def validate_pack_directory(pack_path: Path) -> List[str]:
        """Validate pack directory structure.
        
        Args:
            pack_path: Path to pack directory
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check pack.yaml exists
        pack_yaml = pack_path / "pack.yaml"
        if not pack_yaml.exists():
            errors.append("pack.yaml not found")
            return errors  # Can't continue without pack.yaml
        
        # Validate pack.yaml schema
        try:
            with open(pack_yaml, "r") as f:
                pack_data = yaml.safe_load(f)
            
            # Try to parse as PackMetadata
            PackMetadata(**pack_data)
        
        except Exception as e:
            errors.append(f"Invalid pack.yaml: {e}")
        
        # Check recommended directories
        recommended = ["rules", "templates", "examples", "pitfalls"]
        for dir_name in recommended:
            if not (pack_path / dir_name).exists():
                logger.warning(f"Recommended directory '{dir_name}' not found in {pack_path}")
        
        return errors
    
    @staticmethod
    def validate_template(template_content: str) -> Tuple[bool, Optional[str]]:
        """Validate template syntax.
        
        Args:
            template_content: Template file content
            
        Returns:
            (is_valid, error_message)
        """
        # Check for unmatched braces
        open_count = template_content.count("{{")
        close_count = template_content.count("}}")
        
        if open_count != close_count:
            return False, f"Unmatched braces: {open_count} {{ vs {close_count} }}"
        
        # Check for nested braces (not supported)
        import re
        nested = re.search(r'\{\{[^}]*\{\{', template_content)
        if nested:
            return False, "Nested braces not supported"
        
        return True, None
    
    @staticmethod
    def validate_pack(pack_path: Path) -> bool:
        """Validate entire pack.
        
        Args:
            pack_path: Path to pack directory
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        errors = PackValidator.validate_pack_directory(pack_path)
        
        if errors:
            raise ValidationError(f"Pack validation failed: {', '.join(errors)}")
        
        # Validate all templates
        templates_dir = pack_path / "templates"
        if templates_dir.exists():
            for template_file in templates_dir.glob("*.tpl"):
                content = template_file.read_text()
                is_valid, error = PackValidator.validate_template(content)
                if not is_valid:
                    raise ValidationError(f"Template {template_file.name} invalid: {error}")
        
        return True
