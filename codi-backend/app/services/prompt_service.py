"""Prompt template management service."""
import logging
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trace import Prompt

logger = logging.getLogger(__name__)


class PromptService:
    """Manages versioned prompt templates for AI operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_prompt(self, name: str, version: Optional[int] = None) -> Optional[Prompt]:
        """
        Get a prompt template by name and version.
        
        Args:
            name: Name of the prompt template
            version: Version number, or None for latest
            
        Returns:
            Prompt object or None if not found
        """
        if version is not None:
            # Get specific version
            result = await self.db.execute(
                select(Prompt).where(
                    Prompt.name == name,
                    Prompt.version == version
                )
            )
        else:
            # Get latest version
            result = await self.db.execute(
                select(Prompt)
                .where(Prompt.name == name)
                .order_by(Prompt.version.desc())
                .limit(1)
            )
        
        return result.scalar_one_or_none()
    
    async def create_prompt(
        self,
        name: str,
        version: int,
        template: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Prompt:
        """
        Create a new prompt template.
        
        Args:
            name: Name of the prompt
            version: Version number
            template: Template string with {{variable}} placeholders
            variables: Optional metadata about variables
            
        Returns:
            Created Prompt object
        """
        prompt = Prompt(
            id=str(uuid4()),
            name=name,
            version=version,
            template=template,
            variables=variables or {}
        )
        
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        
        logger.info(f"Created prompt: {name} v{version}")
        return prompt
    
    async def format_prompt(self, name: str, **kwargs) -> str:
        """
        Get and format a prompt template with variables.
        
        Args:
            name: Name of the prompt template
            **kwargs: Variables to substitute in template
            
        Returns:
            Formatted prompt string
        """
        prompt = await self.get_prompt(name)
        if not prompt:
            raise ValueError(f"Prompt '{name}' not found")
        
        return prompt.format(**kwargs)
