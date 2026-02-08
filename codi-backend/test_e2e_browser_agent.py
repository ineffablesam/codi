"""
End-to-End Test for Browser Agent.

Tests the high-level BrowserAgent class flow:
1. Initialize BrowserAgent
2. Run with user prompt: "Go to events.vitap.ac.in and get me latest events"
3. Verify it completes successfully

NO MOCKING - Real browser-agent service, real Chromium, Real Gemini.
"""

import asyncio
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agent.browser_agent import run_browser_agent
from app.utils.logging import get_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

async def main():
    """Run the browser agent E2E test."""
    logger.info("=" * 80)
    logger.info("BROWSER AGENT E2E TEST")
    logger.info("=" * 80)
    
    # Load environment variables (api keys etc)
    load_dotenv()
    
    user_prompt = "Go to events.vitap.ac.in and get me latest events"
    project_id = 1
    user_id = 1
    
    logger.info(f"User Prompt: {user_prompt}")
    
    try:
        logger.info("Running browser agent...")
        response = await run_browser_agent(
            user_message=user_prompt,
            project_id=project_id,
            user_id=user_id
        )
        
        logger.info("=" * 80)
        logger.info("FINAL RESPONSE:")
        logger.info("-" * 40)
        logger.info(response)
        logger.info("-" * 40)
        logger.info("=" * 80)
        
        logger.info("\n✅ Browser agent execution completed")
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Browser agent execution failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
