"""
Quick test for Computer Use Agent.

Tests that the new Gemini 2.5 Computer Use implementation works.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

async def main():
    """Run a quick Computer Use agent test."""
    print("=" * 60)
    print("COMPUTER USE AGENT TEST")
    print("=" * 60)
    
    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ No GEMINI_API_KEY or GOOGLE_API_KEY found in environment")
        return 1
    
    print(f"✅ API key found (length: {len(api_key)})")
    
    # Import and test
    from app.agent.computer_use_agent import ComputerUseAgent
    
    print("\nInitializing Computer Use Agent (headless=False for visibility)...")
    
    agent = ComputerUseAgent(
        project_id=999,  # Test project ID
        user_id=1,
        max_iterations=1,  # Force hit limit immediately
        headless=False,
    )
    
    try:
        # Complex prompt that definitely takes more than 1 step
        user_prompt = "Go to python.org, click on Downloads, then search for 'release notes', and finally tell me the latest version."
        
        print(f"\nPrompt: {user_prompt}")
        print("-" * 40)
        
        response = await agent.run(user_prompt, initial_url="https://google.com")
        
        print("-" * 40)
        print(f"Response: {response[:500]}..." if len(response) > 500 else f"Response: {response}")
        print("=" * 60)
        print("✅ Computer Use Agent test completed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await agent.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
