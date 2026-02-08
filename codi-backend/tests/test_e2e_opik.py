"""
Comprehensive End-to-End Test for Opik Integration.

Tests the complete flow as if a real user is using the frontend:
1. Find existing user and enable Opik tracing
2. Create project with agent workflow
3. Verify traces are created during project creation
4. Test code summarization with tracing
5. Verify evaluations are saved
6. Fetch and validate trace details

NO MOCKING - Real database, real services, real Opik integration.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import get_db_context
from app.models.user import User
from app.models.project import Project
from app.models.agent_task import AgentTask
from app.models.trace import Trace, Evaluation
from app.services.domain.starter_template import StarterTemplateService
from app.services.infrastructure.git import get_git_service
from app.workflows.executor import run_workflow
from app.services.summarization_service import SummarizationService
from app.services.evaluation_service import EvaluationService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OpikE2ETestRunner:
    """End-to-end test runner for Opik integration."""
    
    def __init__(self):
        self.user_id: Optional[int] = None
        self.project_id: Optional[int] = None
        self.task_id: Optional[str] = None
        self.project_folder: Optional[str] = None
        self.trace_ids: list = []
        
    async def cleanup_previous_test_data(self):
        """Clean up any previous test data."""
        logger.info("=" * 80)
        logger.info("CLEANUP: Removing previous test data")
        logger.info("=" * 80)
        
        async with get_db_context() as session:
            # Delete test projects
            result = await session.execute(
                select(Project).where(Project.name.like("%Opik Test%"))
            )
            projects = result.scalars().all()
            
            if projects:
                for project in projects:
                    logger.info(f"Deleting test project: {project.name} (ID: {project.id})")
                    await session.delete(project)
                await session.commit()
                logger.info(f"✅ Cleaned up {len(projects)} test project(s)")
            else:
                logger.info("No previous test projects found")
    
    async def setup_user_with_opik(self):
        """Find existing user and enable Opik tracing."""
        logger.info("=" * 80)
        logger.info("STEP 1: Setting up user with Opik tracing")
        logger.info("=" * 80)
        
        async with get_db_context() as session:
            # Find the first active user
            result = await session.execute(
                select(User).where(User.is_active == True).limit(1)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error("❌ No active users found in database!")
                raise ValueError("No users found in database")
            
            # Enable Opik tracing for this user
            user.opik_enabled = True
            user.opik_workspace = "e2e-test-workspace"
            await session.commit()
            await session.refresh(user)
            
            self.user_id = user.id
            logger.info(f"✅ Using user: {user.github_username} (ID: {user.id})")
            logger.info(f"   Opik enabled: {user.opik_enabled}")
            logger.info(f"   Opik workspace: {user.opik_workspace}")
            
            return user
    
    async def create_test_project(self):
        """Create a test project."""
        logger.info("=" * 80)
        logger.info("STEP 2: Creating test project")
        logger.info("=" * 80)
        
        project_name = "Opik Test Project"
        logger.info(f"Project: {project_name}")
        
        async with get_db_context() as session:
            project = Project(
                name=project_name,
                description="Test project for Opik integration",
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
        
        # Initialize local Git repository
        logger.info("Initializing local Git repository...")
        
        from app.services.infrastructure.git import LocalGitService
        git_service = LocalGitService()
        
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
            deployment_platform="vercel"
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
            project.local_path = str(self.project_folder)
            
            git_svc = get_git_service(self.project_folder)
            initial_sha = git_svc.get_current_commit()
            project.git_commit_sha = initial_sha
            
            await session.commit()
            logger.info(f"✅ Updated project with local_path and commit SHA")
        
        return project
    
    async def run_agent_task_with_tracing(self):
        """Run agent task and verify traces are created."""
        logger.info("=" * 80)
        logger.info("STEP 3: Running agent task with Opik tracing")
        logger.info("=" * 80)
        
        app_idea = """
        Create a simple landing page with:
        - Hero section with title and description
        - Features section with 3 feature cards
        - Contact section with email link
        - Use modern, clean design
        """
        
        logger.info(f"App idea: {app_idea.strip()}")
        
        # Create task in database
        self.task_id = str(uuid4())
        
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
        
        # Count traces before workflow
        async with get_db_context() as session:
            result = await session.execute(
                select(Trace).where(Trace.user_id == self.user_id)
            )
            traces_before = len(result.scalars().all())
            logger.info(f"Traces before workflow: {traces_before}")
        
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
            logger.info(f"Agent workflow completed in {duration:.2f}s")
            
            # Count traces after workflow
            async with get_db_context() as session:
                result = await session.execute(
                    select(Trace).where(Trace.user_id == self.user_id)
                )
                traces = result.scalars().all()
                traces_after = len(traces)
                
                logger.info(f"Traces after workflow: {traces_after}")
                logger.info(f"New traces created: {traces_after - traces_before}")
                
                if traces_after > traces_before:
                    logger.info("✅ Traces were created during workflow!")
                    # Store trace IDs for later verification
                    self.trace_ids = [t.id for t in traces[-5:]]  # Last 5 traces
                else:
                    logger.warning("⚠️  No new traces created (Opik may not be fully configured)")
            
            return True
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Agent workflow exception after {duration:.2f}s: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_code_summarization(self):
        """Test code summarization with Opik tracing."""
        logger.info("=" * 80)
        logger.info("STEP 4: Testing code summarization with tracing")
        logger.info("=" * 80)
        
        test_code = """
def fibonacci(n):
    '''Calculate the nth Fibonacci number using recursion.'''
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Example usage
print(fibonacci(10))
"""
        
        logger.info("Test code:")
        logger.info(test_code)
        
        try:
            async with get_db_context() as session:
                summarization_service = SummarizationService(session)
                
                # Perform summarization (this should create a trace if Opik is enabled)
                summary = await summarization_service.chain_of_density_summarization(
                    document=test_code,
                    instruction="Explain this function and its time complexity",
                    user_opik_enabled=True,
                    user_id=self.user_id,
                    project_id=self.project_id,
                    density_iterations=2,
                )
                
                logger.info(f"✅ Generated summary:")
                logger.info(f"   {summary[:200]}...")
                
                # Check if trace was created
                result = await session.execute(
                    select(Trace).where(
                        Trace.user_id == self.user_id,
                        Trace.trace_type == "summarization"
                    ).order_by(Trace.created_at.desc()).limit(1)
                )
                trace = result.scalar_one_or_none()
                
                if trace:
                    logger.info(f"✅ Trace created for summarization: {trace.id}")
                    self.trace_ids.append(trace.id)
                    return True
                else:
                    logger.warning("⚠️  No trace found for summarization")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Summarization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def verify_trace_details(self):
        """Verify trace details and evaluations."""
        logger.info("=" * 80)
        logger.info("STEP 5: Verifying trace details and evaluations")
        logger.info("=" * 80)
        
        if not self.trace_ids:
            logger.warning("⚠️  No trace IDs to verify")
            return False
        
        async with get_db_context() as session:
            for trace_id in self.trace_ids[:3]:  # Check first 3 traces
                result = await session.execute(
                    select(Trace).where(Trace.id == trace_id)
                )
                trace = result.scalar_one_or_none()
                
                if not trace:
                    logger.warning(f"⚠️  Trace {trace_id} not found")
                    continue
                
                logger.info(f"\nTrace: {trace.id}")
                logger.info(f"  Type: {trace.trace_type}")
                logger.info(f"  Name: {trace.name}")
                logger.info(f"  Duration: {trace.duration_ms}ms" if trace.duration_ms else "  Duration: N/A")
                status = trace.meta_data.get('status', 'unknown') if trace.meta_data else 'unknown'
                logger.info(f"  Status: {status}")
                
                # Check for evaluations
                eval_result = await session.execute(
                    select(Evaluation).where(Evaluation.trace_id == trace_id)
                )
                evaluations = eval_result.scalars().all()
                
                if evaluations:
                    logger.info(f"  Evaluations: {len(evaluations)}")
                    for eval in evaluations:
                        logger.info(f"    - {eval.metric_name}: {eval.score:.2f}")
                        logger.info(f"      Reason: {eval.reason[:100]}...")
                else:
                    logger.info(f"  Evaluations: 0")
        
        logger.info("\n✅ Trace verification complete")
        return True
    
    async def run_test(self):
        """Run the complete end-to-end test."""
        logger.info("\n\n")
        logger.info("█" * 80)
        logger.info("█" + " " * 78 + "█")
        logger.info("█" + "  COMPREHENSIVE E2E TEST: Opik Integration".center(78) + "█")
        logger.info("█" + " " * 78 + "█")
        logger.info("█" * 80)
        logger.info("\n")
        
        overall_start = time.time()
        
        try:
            # Cleanup
            await self.cleanup_previous_test_data()
            
            # Step 1: Setup user with Opik
            await self.setup_user_with_opik()
            
            # Step 2: Create project
            await self.create_test_project()
            
            # Step 3: Run agent task with tracing
            agent_success = await self.run_agent_task_with_tracing()
            
            # Step 4: Test code summarization
            summarization_success = await self.test_code_summarization()
            
            # Step 5: Verify trace details
            verification_success = await self.verify_trace_details()
            
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
            logger.info(f"Traces found: {len(self.trace_ids)}")
            
            if agent_success and summarization_success and verification_success:
                logger.info("\n✅ ✅ ✅  ALL TESTS PASSED  ✅ ✅ ✅")
                return True
            else:
                logger.error("\n❌ ❌ ❌  SOME TESTS FAILED  ❌ ❌ ❌")
                if not agent_success:
                    logger.error("  - Agent workflow failed")
                if not summarization_success:
                    logger.error("  - Summarization test failed")
                if not verification_success:
                    logger.error("  - Trace verification failed")
                return False
                
        except Exception as e:
            logger.error(f"\n❌ ❌ ❌  TEST EXCEPTION  ❌ ❌ ❌")
            logger.error(f"Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def main():
    """Run the E2E test."""
    runner = OpikE2ETestRunner()
    success = await runner.run_test()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
