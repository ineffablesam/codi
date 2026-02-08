"""Seed initial prompt templates for Opik summarization."""
import asyncio
import logging
from uuid import uuid4

from app.core.database import async_session_factory
from app.services.prompt_service import PromptService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Prompt templates
ITERATION_SUMMARY_PROMPT = """
You are summarizing code or documentation.

Document:
{{document}}

Instruction: {{instruction}}

Current summary (if any):
{{current_summary}}

Generate a concise, information-dense summary that:
1. Captures the key technical details
2. Uses precise terminology
3. Focuses on what the user asked for in the instruction
4. Builds upon the current summary if provided

Return ONLY the summary text, no preamble.
""".strip()

FINAL_SUMMARY_PROMPT = """
Refine this summary to be maximally concise while preserving all key information:

{{summary}}

Return ONLY the refined summary, no preamble.
""".strip()


async def main():
    """Seed prompts into the database."""
    print("🌱 Seeding Opik prompts...")
    
    async with async_session_factory() as session:
        prompt_service = PromptService(session)
        
        # Check if prompts already exist
        existing = await prompt_service.get_prompt("iteration_summary_prompt", version=1)
        if existing:
            print("✅ Prompts already seeded, skipping...")
            return
        
        # Seed iteration summary prompt
        await prompt_service.create_prompt(
            name="iteration_summary_prompt",
            version=1,
            template=ITERATION_SUMMARY_PROMPT,
            variables={
                "document": "string",
                "instruction": "string",
                "current_summary": "string"
            }
        )
        print("✅ Created iteration_summary_prompt v1")
        
        # Seed final summary prompt
        await prompt_service.create_prompt(
            name="final_summary_prompt",
            version=1,
            template=FINAL_SUMMARY_PROMPT,
            variables={"summary": "string"}
        )
        print("✅ Created final_summary_prompt v1")
        
        await session.commit()
        print("🎉 Successfully seeded all prompts!")


if __name__ == "__main__":
    asyncio.run(main())
