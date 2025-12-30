# -*- coding: utf-8 -*-
"""
Dart/Flutter syntax validation tool using regex-based analysis.

This module provides syntax validation for Dart code using:
- Regex-based property name validation (snake_case detection)
- Pattern matching for common Flutter mistakes
- No SDK dependencies - works purely with pattern matching

Since Codi is a cloud-based AI platform that works via GitHub,
there's no local Dart SDK available. All validation is done
through pattern matching and LLM-based review.
"""

import re
from typing import Dict, List, Any

from app.utils.logging import get_logger

logger = get_logger(__name__)


# Common Flutter widget property mappings (wrong -> correct)
SNAKE_TO_CAMEL_FIXES = {
    "app_bar": "appBar",
    "floating_action_button": "floatingActionButton",
    "background_color": "backgroundColor",
    "main_axis_alignment": "mainAxisAlignment",
    "cross_axis_alignment": "crossAxisAlignment",
    "text_style": "textStyle",
    "font_size": "fontSize",
    "font_weight": "fontWeight",
    "on_pressed": "onPressed",
    "on_tap": "onTap",
    "on_changed": "onChanged",
    "on_submitted": "onSubmitted",
    "child_widget": "child",
    "text_align": "textAlign",
    "max_lines": "maxLines",
    "soft_wrap": "softWrap",
    "bottom_navigation_bar": "bottomNavigationBar",
    "persistent_footer_buttons": "persistentFooterButtons",
    "border_radius": "borderRadius",
    "box_shadow": "boxShadow",
    "letter_spacing": "letterSpacing",
    "word_spacing": "wordSpacing",
    "line_height": "height",
    "text_decoration": "decoration",
    "text_overflow": "overflow",
    "keyboard_type": "keyboardType",
    "text_input_action": "textInputAction",
    "max_length": "maxLength",
    "obscure_text": "obscureText",
    "auto_focus": "autofocus",
    "decoration_box": "decoration",
    "content_padding": "contentPadding",
    "input_decoration": "decoration",
    "label_text": "labelText",
    "hint_text": "hintText",
    "helper_text": "helperText",
    "error_text": "errorText",
    "prefix_icon": "prefixIcon",
    "suffix_icon": "suffixIcon",
    "axis_alignment": "alignment",
    "scroll_direction": "scrollDirection",
    "shrink_wrap": "shrinkWrap",
    "item_count": "itemCount",
    "item_builder": "itemBuilder",
    "separator_builder": "separatorBuilder",
    "initial_value": "initialValue",
    "on_saved": "onSaved",
    "validator_func": "validator",
    "auto_validate": "autovalidateMode",
    "form_key": "key",
    "drawer_width": "width",
    "end_drawer": "endDrawer",
    "bottom_sheet": "bottomSheet",
    "floating_action_button_location": "floatingActionButtonLocation",
    "primary_color": "primaryColor",
    "secondary_color": "secondaryColor",
    "surface_color": "surfaceColor",
    "error_color": "errorColor",
}


class DartAnalyzer:
    """
    Validates Dart/Flutter code using regex-based pattern matching.
    
    This catches common syntax errors, especially property name mistakes
    like using snake_case instead of camelCase.
    
    No SDK dependencies - works purely with pattern matching.
    """
    
    async def analyze_code(
        self,
        code: str,
        file_path: str = "lib/temp.dart"
    ) -> Dict[str, Any]:
        """
        Analyze Dart code for syntax errors using regex patterns.
        
        Args:
            code: Dart source code to analyze
            file_path: Virtual file path for error reporting
            
        Returns:
            {
                "valid": bool,
                "errors": List[Dict],
                "warnings": List[Dict],
                "info": List[Dict]
            }
        """
        errors: List[Dict] = []
        warnings: List[Dict] = []
        info: List[Dict] = []
        
        # Run property name validation
        naming_issues = await self.validate_property_names(code)
        for issue in naming_issues:
            if issue["severity"] == "error":
                errors.append(issue)
            elif issue["severity"] == "warning":
                warnings.append(issue)
            else:
                info.append(issue)
        
        # Check for common Flutter mistakes
        flutter_issues = await self.check_common_flutter_mistakes(code)
        for issue in flutter_issues:
            if issue["severity"] == "error":
                errors.append(issue)
            elif issue["severity"] == "warning":
                warnings.append(issue)
            else:
                info.append(issue)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "info": info,
        }
    
    async def validate_property_names(self, code: str) -> List[Dict]:
        """
        Check for common property name mistakes (snake_case instead of camelCase).
        This is a regex-based check that detects incorrect Dart property naming.
        
        Args:
            code: Dart source code
            
        Returns:
            List of issues found
        """
        issues: List[Dict] = []
        lines = code.split('\n')
        
        # Pattern to find snake_case after a colon (property assignment)
        # Matches: "  app_bar: " or "background_color:"
        snake_case_property_pattern = re.compile(
            r'^\s*([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*:',
            re.MULTILINE
        )
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments and strings
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # Find snake_case properties
            match = snake_case_property_pattern.match(stripped)
            if match:
                prop_name = match.group(1)
                
                # Get suggested fix
                suggested = SNAKE_TO_CAMEL_FIXES.get(
                    prop_name,
                    self._to_camel_case(prop_name)
                )
                
                issues.append({
                    "severity": "error",
                    "line": line_num,
                    "message": f"Property '{prop_name}' uses snake_case. Dart properties must use camelCase.",
                    "type": "naming_convention",
                    "suggestion": f"Change '{prop_name}' to '{suggested}'",
                    "wrong_property": prop_name,
                    "correct_property": suggested,
                })
        
        # Also check for known wrong patterns anywhere in the line
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('/*'):
                continue
                
            for wrong, correct in SNAKE_TO_CAMEL_FIXES.items():
                # Look for the wrong property followed by a colon
                pattern = rf'\b{wrong}\s*:'
                if re.search(pattern, line):
                    # Only add if we haven't already found this
                    if not any(
                        i.get("wrong_property") == wrong and i.get("line") == line_num
                        for i in issues
                    ):
                        issues.append({
                            "severity": "error",
                            "line": line_num,
                            "message": f"Property '{wrong}' uses snake_case. Use '{correct}' instead.",
                            "type": "naming_convention",
                            "suggestion": f"Change '{wrong}' to '{correct}'",
                            "wrong_property": wrong,
                            "correct_property": correct,
                        })
        
        return issues
    
    async def check_common_flutter_mistakes(self, code: str) -> List[Dict]:
        """
        Check for common Flutter-specific mistakes using pattern matching.
        
        Args:
            code: Dart source code
            
        Returns:
            List of issues found
        """
        issues: List[Dict] = []
        lines = code.split('\n')
        
        # Check for unbalanced braces
        open_braces = 0
        open_parens = 0
        open_brackets = 0
        
        for line_num, line in enumerate(lines, 1):
            # Simple counting (doesn't handle strings perfectly but catches major issues)
            # Skip single-line strings
            if '"""' in line or "'''" in line:
                continue
                
            for char in line:
                if char == '{':
                    open_braces += 1
                elif char == '}':
                    open_braces -= 1
                elif char == '(':
                    open_parens += 1
                elif char == ')':
                    open_parens -= 1
                elif char == '[':
                    open_brackets += 1
                elif char == ']':
                    open_brackets -= 1
        
        if open_braces != 0:
            issues.append({
                "severity": "error",
                "line": len(lines),
                "message": f"Unbalanced curly braces: {abs(open_braces)} {'unclosed' if open_braces > 0 else 'extra closing'}",
                "type": "syntax"
            })
        
        if open_parens != 0:
            issues.append({
                "severity": "error",
                "line": len(lines),
                "message": f"Unbalanced parentheses: {abs(open_parens)} {'unclosed' if open_parens > 0 else 'extra closing'}",
                "type": "syntax"
            })
        
        if open_brackets != 0:
            issues.append({
                "severity": "error",
                "line": len(lines),
                "message": f"Unbalanced square brackets: {abs(open_brackets)} {'unclosed' if open_brackets > 0 else 'extra closing'}",
                "type": "syntax"
            })
        
        # Check for missing semicolons on import lines
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('import ') and not stripped.endswith(';'):
                issues.append({
                    "severity": "error",
                    "line": line_num,
                    "message": "Import statement missing semicolon",
                    "type": "syntax"
                })
        
        # Check for common typos in Flutter widgets
        common_widget_typos = {
            "Scaffhold": "Scaffold",
            "Contaner": "Container",
            "Colum": "Column",
            "Expanded": "Expanded",  # Often misspelled
            "TextFeild": "TextField",
            "Buttom": "Button",
            "Appbar": "AppBar",
            "ListVeiw": "ListView",
        }
        
        for line_num, line in enumerate(lines, 1):
            for typo, correct in common_widget_typos.items():
                if typo in line and correct not in line:
                    issues.append({
                        "severity": "warning",
                        "line": line_num,
                        "message": f"Possible typo: '{typo}' should be '{correct}'",
                        "type": "typo"
                    })
        
        return issues
    
    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
    
    async def full_validation(self, code: str, file_path: str = "lib/temp.dart") -> Dict[str, Any]:
        """
        Run full validation including all pattern-based checks.
        
        Args:
            code: Dart source code
            file_path: Virtual file path
            
        Returns:
            Complete validation results
        """
        # Run all validations (same as analyze_code)
        return await self.analyze_code(code, file_path)
