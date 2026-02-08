"""
Comprehensive End-to-End Test for Project Creation and Deployment.

Tests the complete flow as if a real user is using the frontend:
1. Find existing user
2. Create project
3. Run agent task with app idea
4. Build and deploy to containerized preview
5. Verify deployment

NO MOCKING - Real database, real services, real Docker builds.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, delete
from app.core.database import get_db_context
from app.models.user import User
from app.models.project import Project
from app.models.agent_task import AgentTask
from app.services.domain.starter_template import StarterTemplateService
from app.services.infrastructure.git import get_git_service
from app.workflows.executor import run_workflow
from app.utils.logging import get_logger

logger = get_logger(__name__)


class E2ETestRunner:
    """End-to-end test runner with detailed logging."""
    
    def __init__(self):
        self.user_id: Optional[int] = None
        self.project_id: Optional[int] = None
        self.task_id: Optional[str] = None
        self.project_folder: Optional[str] = None
        
    async def cleanup_previous_test_data(self):
        """Clean up any previous test data."""
        logger.info("=" * 80)
        logger.info("CLEANUP: Removing previous test projects")
        logger.info("=" * 80)
        
        async with get_db_context() as session:
            # Delete any projects with "Hoboken Grace" in the name (our test project)
            result = await session.execute(
                select(Project).where(Project.name.like("%Hoboken Grace%"))
            )
            projects = result.scalars().all()
            
            if projects:
                for project in projects:
                    logger.info(f"Deleting previous test project: {project.name} (ID: {project.id})")
                    await session.delete(project)
                await session.commit()
                logger.info(f"✅ Cleaned up {len(projects)} test project(s)")
            else:
                logger.info("No previous test projects found")
    
    async def find_existing_user(self):
        """Find an existing user from the database."""
        logger.info("=" * 80)
        logger.info("STEP 1: Finding existing user")
        logger.info("=" * 80)
        
        async with get_db_context() as session:
            # Find the first active user
            result = await session.execute(
                select(User).where(User.is_active == True).limit(1)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error("❌ No active users found in database!")
                logger.error("Please create a user first or check your database")
                raise ValueError("No users found in database")
            
            self.user_id = user.id
            logger.info(f"✅ Using existing user: {user.github_username} (ID: {user.id})")
            logger.info(f"   Email: {user.email}")
            logger.info(f"   GitHub ID: {user.github_id}")
            
            return user
    
    async def create_test_project(self):
        """Create a test project."""
        logger.info("=" * 80)
        logger.info("STEP 2: Creating project")
        logger.info("=" * 80)
        
        project_name = "Hoboken Grace Website"
        logger.info(f"Project: {project_name}")
        logger.info(f"Framework: nextjs")
        logger.info(f"Backend: none")
        logger.info(f"Deployment: containerized")
        
        async with get_db_context() as session:
            # Create project in database
            project = Project(
                name=project_name,
                description="Website for church Hoboken Grace",
                owner_id=self.user_id,
                framework="nextjs",
                backend_type=None,
                deployment_platform=None,
                platform_type="web",
                git_branch="main",
                status="active",
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            
            self.project_id = project.id
            logger.info(f"✅ Created project in database (ID: {project.id})")
        
        # Initialize local Git repository with Next.js template
        logger.info("Initializing local Git repository...")
        
        from app.services.infrastructure.git import LocalGitService
        git_service = LocalGitService()
        
        # Get project path
        project_slug = git_service.slugify(project_name)
        self.project_folder = git_service.get_project_path(project_slug, self.user_id)
        
        logger.info(f"Project folder: {self.project_folder}")
        
        # Initialize repo
        git_service.init_repository(project_slug, self.user_id)
        logger.info(f"✅ Initialized Git repository")
        
        # Push Next.js starter template
        logger.info("Loading Next.js starter template...")
        template_service = StarterTemplateService(
            framework="nextjs",
            deployment_platform="vercel"  # Use vercel for Docker/standalone builds (not github_pages which uses export)
        )
        
        await template_service.push_template_to_repo(
            project_path=self.project_folder,
            project_name=project_slug,
            project_title=project_name,
        )
        
        logger.info(f"✅ Pushed starter template to repository")
        
        # Update project with local path
        async with get_db_context() as session:
            result = await session.execute(
                select(Project).where(Project.id == self.project_id)
            )
            project = result.scalar_one()
            project.local_path = str(self.project_folder)  # Convert Path to string
            
            # Get initial commit SHA
            git_svc = get_git_service(self.project_folder)
            initial_sha = git_svc.get_current_commit()
            project.git_commit_sha = initial_sha
            
            await session.commit()
            
            logger.info(f"✅ Updated project with local_path and commit SHA: {initial_sha}")
        
        return project
    
    async def run_agent_task(self):
        """Run agent task with app idea."""
        logger.info("=" * 80)
        logger.info("STEP 3: Running agent task")
        logger.info("=" * 80)
        
        app_idea = """
        Create a sophisticated website for Hoboken Grace church with:
        - Homepage with hero section and mission statement
        - Events page showing upcoming church events
        - Donations page with donation form
        - Contact Us page with contact form and location map
        - Use a light, sophisticated theme with professional typography
        - Make it fully responsive and modern
        """
        
        logger.info(f"App idea: {app_idea.strip()}")
        
        # Create task in database
        import uuid
        self.task_id = str(uuid.uuid4())
        
        async with get_db_context() as session:
            task = AgentTask(
                id=self.task_id,
                project_id=self.project_id,
                user_id=self.user_id,
                message=app_idea,
                status="queued",
            )
            session.add(task)
            await session.commit()
            
            logger.info(f"✅ Created agent task (ID: {self.task_id})")
        
        # Run workflow
        logger.info("Starting agent workflow...")
        start_time = time.time()
        
        try:
            result = await run_workflow(
                project_id=self.project_id,
                user_id=self.user_id,
                task_id=self.task_id,
                user_message=app_idea,
                project_folder=self.project_folder,
            )
            
            duration = time.time() - start_time
            
            logger.info("=" * 80)
            logger.info(f"Agent workflow completed in {duration:.2f}s")
            logger.info(f"Result type: {result.get('type')}")
            logger.info(f"Has error: {result.get('has_error')}")
            logger.info(f"Is complete: {result.get('is_complete')}")
            
            if result.get('has_error'):
                logger.error(f"❌ Agent workflow failed: {result.get('error')}")
                return False
            else:
                logger.info(f"✅ Agent workflow succeeded")
                logger.info(f"Response preview: {result.get('response', '')[:200]}...")
                return True
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Agent workflow exception after {duration:.2f}s: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def verify_deployment(self):
        """Verify the deployment was successful."""
        logger.info("=" * 80)
        logger.info("STEP 4: Verifying deployment")
        logger.info("=" * 80)
        
        # Check project status
        async with get_db_context() as session:
            result = await session.execute(
                select(Project).where(Project.id == self.project_id)
            )
            project = result.scalar_one()
            
            logger.info(f"Project status: {project.status}")
            logger.info(f"Last build status: {project.last_build_status}")
            logger.info(f"Deployment URL: {project.deployment_url}")
            
            if project.deployment_url:
                logger.info(f"✅ Deployment URL available: {project.deployment_url}")
                return True
            else:
                logger.warning("⚠️  No deployment URL set")
                return False
    
    async def run_test(self):
        """Run the complete end-to-end test."""
        logger.info("\n\n")
        logger.info("█" * 80)
        logger.info("█" + " " * 78 + "█")
        logger.info("█" + "  COMPREHENSIVE E2E TEST: Project Creation & Deployment".center(78) + "█")
        logger.info("█" + " " * 78 + "█")
        logger.info("█" * 80)
        logger.info("\n")
        
        overall_start = time.time()
        
        try:
            # Cleanup
            await self.cleanup_previous_test_data()
            
            # Step 1: Find existing user
            await self.find_existing_user()
            
            # Step 2: Create project
            await self.create_test_project()
            
            # Step 3: Run agent task
            agent_success = await self.run_agent_task()
            
            if not agent_success:
                logger.error("❌ Agent task failed - skipping deployment verification")
                return False
            
            # Step 4: Verify deployment
            deployment_success = await self.verify_deployment()
            
            overall_duration = time.time() - overall_start
            
            # Final summary
            logger.info("\n")
            logger.info("=" * 80)
            logger.info("TEST SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total duration: {overall_duration:.2f}s")
            logger.info(f"User ID: {self.user_id}")
            logger.info(f"Project ID: {self.project_id}")
            logger.info(f"Task ID: {self.task_id}")
            logger.info(f"Project folder: {self.project_folder}")
            
            if agent_success and deployment_success:
                logger.info("\n✅ ✅ ✅  ALL TESTS PASSED  ✅ ✅ ✅")
                return True
            else:
                logger.error("\n❌ ❌ ❌  TESTS FAILED  ❌ ❌ ❌")
                if not agent_success:
                    logger.error("  - Agent workflow failed")
                if not deployment_success:
                    logger.error("  - Deployment verification failed")
                return False
                
        except Exception as e:
            logger.error(f"\n❌ ❌ ❌  TEST EXCEPTION  ❌ ❌ ❌")
            logger.error(f"Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def main():
    """Run the E2E test."""
    runner = E2ETestRunner()
    success = await runner.run_test()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
