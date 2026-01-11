"""Platform-specific engineering agents for various frameworks.

Platform agents handle code generation for specific frameworks:
- Flutter/Dart
- React
- Next.js
- React Native
- Backend Integration
"""
from app.agents.platform.flutter_engineer import FlutterEngineerAgent
from app.agents.platform.react_engineer import ReactEngineerAgent
from app.agents.platform.nextjs_engineer import NextjsEngineerAgent
from app.agents.platform.react_native_engineer import ReactNativeEngineerAgent
from app.agents.platform.backend_integration import BackendIntegrationAgent

__all__ = [
    "FlutterEngineerAgent",
    "ReactEngineerAgent",
    "NextjsEngineerAgent",
    "ReactNativeEngineerAgent",
    "BackendIntegrationAgent",
]
