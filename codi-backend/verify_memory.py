
import asyncio
import os
import sys
from pathlib import Path

# Add app to path
sys.path.append(os.getcwd())

from app.services.infrastructure.memory import MemoryService
from app.core.config import settings

async def test_memory_init():
    # Setup test params
    user_id = 1
    project_slug = "test-init-project"
    project_id = 999
    
    # Mock REPOS_BASE_PATH for local test
    import app.services.infrastructure.git as git_service
    import app.services.infrastructure.memory as memory_service
    test_repo_root = Path("./test_repos").absolute()
    git_service.REPOS_BASE_PATH = test_repo_root
    memory_service.REPOS_BASE_PATH = test_repo_root
    
    print(f"Testing MemoryService init with path: {test_repo_root}")
    
    try:
        service = MemoryService(project_id, user_id, project_slug)
        print(f"Memory directory: {service.memory_dir}")
        
        # This will trigger lazy initialization
        mem = service.mem
        print("✅ MemoryService initialized successfully!")
        
        # Test basic add/search if possible (might need API key)
        if settings.gemini_api_key and settings.gemini_api_key != "your-gemini-api-key":
            print("Storing test memory...")
            await service.store_memory("This is a test memory.")
            print("Recalling test memory...")
            results = await service.recall_memory("test memory")
            print(f"Recalled: {results}")
        else:
            print("⚠️ Skipping semantic test (GEMINI_API_KEY not set)")
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    finally:
        # Cleanup
        import shutil
        if test_repo_root.exists():
            shutil.rmtree(test_repo_root)

if __name__ == "__main__":
    asyncio.run(test_memory_init())
