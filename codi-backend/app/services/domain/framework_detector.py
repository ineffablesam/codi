"""Framework detection service.

Auto-detects project framework from file signatures.
"""
import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


class Framework(str, Enum):
    """Supported frameworks."""
    FLUTTER = "flutter"
    NEXTJS = "nextjs"
    REACT = "react"
    REACT_NATIVE = "react_native"
    VITE = "vite"
    UNKNOWN = "unknown"


@dataclass
class FrameworkInfo:
    """Framework detection result."""
    framework: Framework
    confidence: float  # 0.0 to 1.0
    version: Optional[str]
    details: Dict[str, str]


class FrameworkDetector:
    """Auto-detect project framework from files."""
    
    # File signatures for each framework
    SIGNATURES = {
        Framework.FLUTTER: {
            "required": ["pubspec.yaml"],
            "optional": ["lib/main.dart", ".metadata"],
        },
        Framework.NEXTJS: {
            "required": [],  # package.json check handles this
            "markers": ["next.config.js", "next.config.ts", "next.config.mjs"],
            "package_deps": ["next"],
        },
        Framework.REACT_NATIVE: {
            "required": ["app.json"],
            "package_deps": ["react-native", "expo"],
        },
        Framework.VITE: {
            "required": [],
            "markers": ["vite.config.js", "vite.config.ts"],
            "package_deps": ["vite"],
        },
        Framework.REACT: {
            "required": ["package.json"],
            "package_deps": ["react", "react-dom"],
        },
    }
    
    def __init__(self, project_path: str) -> None:
        """Initialize detector with project path.
        
        Args:
            project_path: Path to project root
        """
        self.project_path = project_path
        self._package_json: Optional[Dict] = None
    
    def _file_exists(self, relative_path: str) -> bool:
        """Check if a file exists in the project."""
        return os.path.exists(os.path.join(self.project_path, relative_path))
    
    def _get_package_json(self) -> Optional[Dict]:
        """Load and cache package.json."""
        if self._package_json is not None:
            return self._package_json
        
        package_path = os.path.join(self.project_path, "package.json")
        if not os.path.exists(package_path):
            return None
        
        try:
            with open(package_path, "r") as f:
                self._package_json = json.load(f)
            return self._package_json
        except (json.JSONDecodeError, IOError):
            return None
    
    def _has_dependency(self, dep_name: str) -> bool:
        """Check if package.json has a dependency."""
        pkg = self._get_package_json()
        if not pkg:
            return False
        
        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        return dep_name in deps or dep_name in dev_deps
    
    def _get_dependency_version(self, dep_name: str) -> Optional[str]:
        """Get version of a dependency."""
        pkg = self._get_package_json()
        if not pkg:
            return None
        
        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        return deps.get(dep_name) or dev_deps.get(dep_name)
    
    def detect(self) -> FrameworkInfo:
        """Detect the framework used in the project.
        
        Returns:
            FrameworkInfo with detected framework and confidence
        """
        # Check Flutter first (distinctive pubspec.yaml)
        if self._file_exists("pubspec.yaml"):
            version = self._get_flutter_version()
            return FrameworkInfo(
                framework=Framework.FLUTTER,
                confidence=1.0,
                version=version,
                details={"sdk": "flutter"},
            )
        
        # Check for Next.js config files
        for marker in ["next.config.js", "next.config.ts", "next.config.mjs"]:
            if self._file_exists(marker):
                version = self._get_dependency_version("next")
                return FrameworkInfo(
                    framework=Framework.NEXTJS,
                    confidence=1.0,
                    version=version,
                    details={"config_file": marker},
                )
        
        # Check for Next.js via package.json
        if self._has_dependency("next"):
            version = self._get_dependency_version("next")
            return FrameworkInfo(
                framework=Framework.NEXTJS,
                confidence=0.9,
                version=version,
                details={"detected_via": "package.json"},
            )
        
        # Check for Expo/React Native
        if self._file_exists("app.json") or self._has_dependency("expo"):
            version = self._get_dependency_version("expo") or self._get_dependency_version("react-native")
            return FrameworkInfo(
                framework=Framework.REACT_NATIVE,
                confidence=0.95,
                version=version,
                details={"runtime": "expo" if self._has_dependency("expo") else "react-native"},
            )
        
        # Check for Vite
        for marker in ["vite.config.js", "vite.config.ts"]:
            if self._file_exists(marker):
                version = self._get_dependency_version("vite")
                return FrameworkInfo(
                    framework=Framework.VITE,
                    confidence=1.0,
                    version=version,
                    details={"config_file": marker},
                )
        
        if self._has_dependency("vite"):
            version = self._get_dependency_version("vite")
            return FrameworkInfo(
                framework=Framework.VITE,
                confidence=0.9,
                version=version,
                details={"detected_via": "package.json"},
            )
        
        # Check for plain React
        if self._has_dependency("react"):
            version = self._get_dependency_version("react")
            return FrameworkInfo(
                framework=Framework.REACT,
                confidence=0.8,
                version=version,
                details={"detected_via": "package.json"},
            )
        
        # Unknown framework
        return FrameworkInfo(
            framework=Framework.UNKNOWN,
            confidence=0.0,
            version=None,
            details={},
        )
    
    def _get_flutter_version(self) -> Optional[str]:
        """Get Flutter SDK version from pubspec.yaml."""
        try:
            import yaml
            pubspec_path = os.path.join(self.project_path, "pubspec.yaml")
            with open(pubspec_path, "r") as f:
                pubspec = yaml.safe_load(f)
            
            env = pubspec.get("environment", {})
            return env.get("sdk")
        except Exception:
            return None
    
    def get_build_command(self) -> str:
        """Get the build command for the detected framework.
        
        Returns:
            Shell command to build the project
        """
        info = self.detect()
        
        commands = {
            Framework.FLUTTER: "flutter build web --release",
            Framework.NEXTJS: "npm run build",
            Framework.REACT: "npm run build",
            Framework.VITE: "npm run build",
            Framework.REACT_NATIVE: "npx expo export -p web",
        }
        
        return commands.get(info.framework, "npm run build")
    
    def get_output_directory(self) -> str:
        """Get the build output directory for the detected framework.
        
        Returns:
            Relative path to build output
        """
        info = self.detect()
        
        outputs = {
            Framework.FLUTTER: "build/web",
            Framework.NEXTJS: ".next/standalone",  # For standalone output
            Framework.REACT: "dist",
            Framework.VITE: "dist",
            Framework.REACT_NATIVE: "dist",
        }
        
        return outputs.get(info.framework, "dist")
    
    def get_dev_command(self) -> str:
        """Get the development server command.
        
        Returns:
            Shell command to run dev server
        """
        info = self.detect()
        
        commands = {
            Framework.FLUTTER: "flutter run -d web-server --web-port 8080",
            Framework.NEXTJS: "npm run dev",
            Framework.REACT: "npm run dev",
            Framework.VITE: "npm run dev",
            Framework.REACT_NATIVE: "npx expo start --web",
        }
        
        return commands.get(info.framework, "npm run dev")


def detect_framework(project_path: str) -> FrameworkInfo:
    """Convenience function to detect framework.
    
    Args:
        project_path: Path to project root
        
    Returns:
        FrameworkInfo with detection results
    """
    detector = FrameworkDetector(project_path)
    return detector.detect()
