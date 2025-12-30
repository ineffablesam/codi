"""Flutter code analysis and generation utilities."""
from typing import Any, Dict, List, Optional
import re

from app.utils.logging import get_logger

logger = get_logger(__name__)


def analyze_dart_code(code: str) -> Dict[str, Any]:
    """Analyze Dart code structure.

    Args:
        code: Dart source code

    Returns:
        Dictionary with code analysis results
    """
    lines = code.split("\n")

    # Count various code elements
    imports = [line for line in lines if line.strip().startswith("import ")]
    classes = re.findall(r"class\s+(\w+)", code)
    functions = re.findall(r"(?:void|Future|Widget|String|int|bool|dynamic)\s+(\w+)\s*\(", code)
    widgets = re.findall(r"class\s+(\w+)\s+extends\s+(?:Stateless|Stateful)Widget", code)

    return {
        "lines_of_code": len(lines),
        "import_count": len(imports),
        "class_count": len(classes),
        "function_count": len(functions),
        "widget_count": len(widgets),
        "classes": classes,
        "widgets": widgets,
        "functions": functions[:10],  # Limit to first 10
        "imports": imports[:10],  # Limit to first 10
    }


def extract_widgets_from_code(code: str) -> List[str]:
    """Extract widget names used in Dart code.

    Args:
        code: Dart source code

    Returns:
        List of widget names found in the code
    """
    # Common Flutter widgets
    common_widgets = [
        "Scaffold", "AppBar", "Container", "Column", "Row", "Text",
        "ElevatedButton", "TextButton", "IconButton", "TextField",
        "TextFormField", "Form", "ListView", "GridView", "Card",
        "Icon", "Image", "CircularProgressIndicator", "SizedBox",
        "Padding", "Center", "Expanded", "Flexible", "Stack",
        "Positioned", "GestureDetector", "InkWell", "AlertDialog",
        "BottomNavigationBar", "Drawer", "FloatingActionButton",
        "Obx", "GetBuilder", "SingleChildScrollView", "SafeArea",
    ]

    found_widgets = []
    for widget in common_widgets:
        if widget in code:
            found_widgets.append(widget)

    return found_widgets


def extract_dependencies_from_pubspec(pubspec_content: str) -> Dict[str, List[str]]:
    """Extract dependencies from pubspec.yaml content.

    Args:
        pubspec_content: pubspec.yaml file content

    Returns:
        Dictionary with dependencies and dev_dependencies lists
    """
    import yaml

    try:
        data = yaml.safe_load(pubspec_content)
        dependencies = list((data.get("dependencies") or {}).keys())
        dev_dependencies = list((data.get("dev_dependencies") or {}).keys())

        return {
            "dependencies": dependencies,
            "dev_dependencies": dev_dependencies,
        }
    except Exception as e:
        logger.error(f"Failed to parse pubspec.yaml: {e}")
        return {"dependencies": [], "dev_dependencies": []}


def generate_import_statements(
    package_name: str,
    imports: List[str],
) -> str:
    """Generate Dart import statements.

    Args:
        package_name: Name of the package
        imports: List of relative paths to import

    Returns:
        Formatted import statements
    """
    statements = []

    for import_path in imports:
        if import_path.startswith("package:"):
            statements.append(f"import '{import_path}';")
        else:
            statements.append(f"import 'package:{package_name}/{import_path}';")

    return "\n".join(sorted(statements))


def format_dart_class_name(name: str) -> str:
    """Convert a string to PascalCase for Dart class names.

    Args:
        name: Input string

    Returns:
        PascalCase formatted string
    """
    # Split by spaces, underscores, and hyphens
    words = re.split(r"[\s_-]+", name)
    # Capitalize each word
    return "".join(word.capitalize() for word in words)


def format_dart_variable_name(name: str) -> str:
    """Convert a string to camelCase for Dart variable names.

    Args:
        name: Input string

    Returns:
        camelCase formatted string
    """
    pascal_case = format_dart_class_name(name)
    if pascal_case:
        return pascal_case[0].lower() + pascal_case[1:]
    return name


def generate_getx_controller_template(
    class_name: str,
    state_variables: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Generate a GetX controller template.

    Args:
        class_name: Name of the controller class
        state_variables: List of state variables with 'name', 'type', and 'initial' keys

    Returns:
        Generated Dart code for the controller
    """
    state_variables = state_variables or []

    # Generate state variable declarations
    state_declarations = []
    for var in state_variables:
        var_name = var.get("name", "value")
        var_type = var.get("type", "dynamic")
        initial = var.get("initial", "null")
        state_declarations.append(f"  final {var_name} = Rx<{var_type}>({initial});")

    state_code = "\n".join(state_declarations) if state_declarations else "  // Add your state variables here"

    template = f'''import 'package:get/get.dart';

class {class_name} extends GetxController {{
{state_code}

  @override
  void onInit() {{
    super.onInit();
    // Initialize your controller
  }}

  @override
  void onReady() {{
    super.onReady();
    // Called after the widget is rendered on screen
  }}

  @override
  void onClose() {{
    // Clean up resources
    super.onClose();
  }}
}}
'''
    return template


def generate_screen_template(
    screen_name: str,
    controller_name: str,
    title: str,
) -> str:
    """Generate a Flutter screen template with GetX.

    Args:
        screen_name: Name of the screen class
        controller_name: Name of the GetX controller
        title: Screen title

    Returns:
        Generated Dart code for the screen
    """
    template = f'''import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

class {screen_name} extends StatelessWidget {{
  const {screen_name}({{super.key}});

  @override
  Widget build(BuildContext context) {{
    final controller = Get.find<{controller_name}>();

    return Scaffold(
      appBar: AppBar(
        title: Text(
          '{title}',
          style: GoogleFonts.inter(
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(16.r),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Welcome to {title}',
                style: GoogleFonts.inter(
                  fontSize: 24.sp,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 16.h),
              // Add your widgets here
            ],
          ),
        ),
      ),
    );
  }}
}}
'''
    return template


def parse_route_from_code(code: str) -> List[Dict[str, str]]:
    """Parse GetX routes from Dart code.

    Args:
        code: Dart source code containing route definitions

    Returns:
        List of route dictionaries with 'path' and 'page' keys
    """
    routes = []

    # Match GetPage definitions
    get_page_pattern = r"GetPage\s*\(\s*name:\s*['\"]([^'\"]+)['\"].*?page:\s*\(\)\s*=>\s*(\w+)"
    matches = re.findall(get_page_pattern, code, re.DOTALL)

    for path, page in matches:
        routes.append({
            "path": path,
            "page": page,
        })

    return routes


def count_lines_of_code(code: str) -> Dict[str, int]:
    """Count lines of code statistics.

    Args:
        code: Source code

    Returns:
        Dictionary with line count statistics
    """
    lines = code.split("\n")
    total = len(lines)
    blank = sum(1 for line in lines if not line.strip())
    comments = sum(1 for line in lines if line.strip().startswith("//"))

    return {
        "total": total,
        "blank": blank,
        "comments": comments,
        "code": total - blank - comments,
    }
