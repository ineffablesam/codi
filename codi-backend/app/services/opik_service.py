"""Opik integration service for AI operation tracking with Gemini."""
import os
import logging
from typing import Optional

import opik
from google import genai
from opik.integrations.genai import track_genai

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpikService:
    """
    Manages Opik integration with Gemini for AI operation tracking.
    
    This service handles:
    - Opik client configuration
    - Gemini client wrapping for automatic tracing
    - User-level tracing enablement
    """
    
    _instance: Optional["OpikService"] = None
    _initialized: bool = False
    
    def __init__(self):
        """Initialize Opik service."""
        self.gemini_client = None
        self.tracked_gemini_client = None
        
        # Configure Opik if API key is available
        if settings.opik_api_key:
            try:
                opik.configure(
                    api_key=settings.opik_api_key,
                    workspace=settings.opik_workspace,
                )
                logger.info(f"Opik configured with workspace: {settings.opik_workspace}")
                self._initialized = True
                
                # Set default project name
                os.environ["OPIK_PROJECT_NAME"] = settings.opik_project_name
                
            except Exception as e:
                logger.warning(f"Failed to configure Opik: {e}. Tracing will be disabled.")
                self._initialized = False
        else:
            logger.info("Opik API key not configured. Tracing disabled by default.")
            self._initialized = False
        
        # Initialize Gemini client
        try:
            self.gemini_client = genai.Client(api_key=settings.gemini_api_key)
            
            # Create tracked version if Opik is initialized
            if self._initialized:
                self.tracked_gemini_client = track_genai(self.gemini_client)
                logger.info("Gemini client wrapped with Opik tracking")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    @classmethod
    def get_instance(cls) -> "OpikService":
        """Get singleton instance of OpikService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_gemini_client(self, user_opik_enabled: bool = False) -> genai.Client:
        """
        Get Gemini client with or without tracking based on user preference.
        
        Args:
            user_opik_enabled: Whether the user has enabled Opik tracing
            
        Returns:
            Tracked Gemini client if user has tracing enabled and Opik is configured,
            otherwise regular Gemini client
        """
        if user_opik_enabled and self._initialized and self.tracked_gemini_client:
            logger.debug("Returning tracked Gemini client (tracing enabled)")
            return self.tracked_gemini_client
        
        logger.debug("Returning regular Gemini client (tracing disabled)")
        return self.gemini_client
    
    def is_available(self) -> bool:
        """Check if Opik tracing is available."""
        return self._initialized
    
    def set_project_name(self, project_name: str):
        """
        Set the Opik project name for subsequent traces.
        
        Args:
            project_name: Name of the project for organizing traces
        """
        if self._initialized:
            os.environ["OPIK_PROJECT_NAME"] = project_name
            logger.debug(f"Set Opik project name to: {project_name}")


# Global instance
_opik_service: Optional[OpikService] = None


def get_opik_service() -> OpikService:
    """Get the global OpikService instance."""
    global _opik_service
    if _opik_service is None:
        _opik_service = OpikService.get_instance()
    return _opik_service
