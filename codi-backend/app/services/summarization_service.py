"""Chain of Density summarization service using Opik tracking."""
import logging
from typing import Optional
from uuid import UUID

from opik import track
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.trace_persistence import track_and_persist
from app.services.opik_service import get_opik_service
from app.services.prompt_service import PromptService

logger = logging.getLogger(__name__)


class SummarizationService:
    """
    Provides Chain of Density summarization for code and documentation.
    
    Uses Opik's @track decorator for automatic tracing when enabled.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.prompt_service = PromptService(db)
        self.opik_service = get_opik_service()
    
    @track
    async def summarize_current_summary(
        self,
        document: str,
        instruction: str,
        current_summary: str,
        user_opik_enabled: bool,
        model: str = settings.gemini_model
    ) -> str:
        """
        Single iteration of summary refinement.
        
        This function is automatically traced by Opik when user has tracing enabled.
        """
        # Get Gemini client (tracked or untracked based on user preference)
        gemini_client = self.opik_service.get_gemini_client(user_opik_enabled)
        
        # Get prompt template
        prompt_template = await self.prompt_service.get_prompt("iteration_summary_prompt")
        if not prompt_template:
            # Fallback if prompt not in DB yet
            prompt = f"""
Document: {document}
Current summary: {current_summary}
Instruction to focus on: {instruction}

Generate a concise, entity-dense, and highly technical summary from the provided Document that specifically addresses the given Instruction.

Guidelines:
- Make every word count: If there is a current summary re-write it to improve flow, density and conciseness.
- Remove uninformative phrases like "the article discusses".
- The summary should become highly dense and concise yet self-contained, e.g., easily understood without the Document.
- Make sure that the summary specifically addresses the given Instruction
"""
        else:
            prompt = prompt_template.format(
                document=document,
                current_summary=current_summary,
                instruction=instruction
            )
        
        # Call Gemini
        response = gemini_client.models.generate_content(
            model=model,
            contents=prompt
        )
        
        return response.text
    
    @track
    async def iterative_density_summarization(
        self,
        document: str,
        instruction: str,
        density_iterations: int,
        user_opik_enabled: bool,
        model: str = settings.gemini_model
    ) -> str:
        """
        Iteratively refine summary through multiple passes.
        
        Each iteration is automatically tracked as a nested span.
        """
        summary = ""
        
        for iteration in range(1, density_iterations + 1):
            logger.debug(f"Summarization iteration {iteration}/{density_iterations}")
            summary = await self.summarize_current_summary(
                document=document,
                instruction=instruction,
                current_summary=summary,
                user_opik_enabled=user_opik_enabled,
                model=model
            )
        
        return summary
    
    @track
    async def final_summary(
        self,
        instruction: str,
        current_summary: str,
        user_opik_enabled: bool,
        model: str = settings.gemini_model
    ) -> str:
        """Generate final polished summary."""
        gemini_client = self.opik_service.get_gemini_client(user_opik_enabled)
        
        # Get prompt template
        prompt_template = await self.prompt_service.get_prompt("final_summary_prompt")
        if not prompt_template:
            # Fallback
            prompt = f"""
Given this summary: {current_summary}
And this instruction to focus on: {instruction}
Create an extremely dense, final summary that captures all key technical information in the most concise form possible, while specifically addressing the given instruction.
"""
        else:
            prompt = prompt_template.format(
                current_summary=current_summary,
                instruction=instruction
            )
        
        response = gemini_client.models.generate_content(
            model=model,
            contents=prompt
        )
        
        return response.text
    
    @track_and_persist(project_name="codi-summarization", trace_type="summarization")
    async def chain_of_density_summarization(
        self,
        document: str,
        instruction: str,
        user_opik_enabled: bool,
        user_id: int,
        project_id: Optional[int] = None,
        model: str = settings.gemini_model,
        density_iterations: int = 2
    ) -> str:
        """
        Main entry point for Chain of Density summarization.
        
        Args:
            document: The code or text to summarize
            instruction: What to focus on (e.g., "explain the algorithm")
            user_opik_enabled: Whether user has Opik tracing enabled
            user_id: User ID for trace persistence
            project_id: Optional project ID for project-level filtering
            model: Gemini model to use
            density_iterations: Number of refinement passes
            
        Returns:
            Dense, technical summary
        """
        logger.info(f"Starting Chain of Density summarization with {density_iterations} iterations")
        
        # Iterative refinement
        summary = await self.iterative_density_summarization(
            document=document,
            instruction=instruction,
            density_iterations=density_iterations,
            user_opik_enabled=user_opik_enabled,
            model=model
        )
        
        # Final polish
        final_result = await self.final_summary(
            instruction=instruction,
            current_summary=summary,
            user_opik_enabled=user_opik_enabled,
            model=model
        )
        
        logger.info("Chain of Density summarization complete")
        return final_result
