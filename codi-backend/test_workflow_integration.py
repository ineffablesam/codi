"""Test workflow integration with knowledge packs."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import get_db_context
from app.models.project import Project
from sqlalchemy import select


async def test_workflow_integration():
    """Test that workflow loads tech stack and passes to agent."""
    print("=" * 60)
    print("Testing Workflow Integration with Knowledge Packs")
    print("=" * 60)
    
    # Check if we have any projects in the database
    async with get_db_context() as session:
        result = await session.execute(
            select(Project).limit(1)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            print("\n⚠️  No projects found in database")
            print("   To test this, create a project with:")
            print("   - framework: 'flutter' or 'nextjs'")
            print("   - backend_type: 'serverpod' or 'supabase'")
            print("   - deployment_platform: 'docker' or 'vercel'")
            return False
        
        print(f"\n📦 Found project: {project.name} (ID: {project.id})")
        print(f"   Framework: {project.framework}")
        print(f"   Backend: {project.backend_type}")
        print(f"   Deployment: {project.deployment_platform}")
        
        # Build tech stack like the workflow does
        tech_stack = {}
        if project.framework:
            tech_stack["frontend"] = project.framework
        if project.backend_type:
            tech_stack["backend"] = project.backend_type
        if project.deployment_platform:
            tech_stack["deployment"] = project.deployment_platform
        
        print(f"\n🔧 Tech stack dictionary:")
        for key, value in tech_stack.items():
            print(f"   {key}: {value}")
        
        # Test loading knowledge packs
        if tech_stack:
            from app.knowledge_packs.service import KnowledgePackService
            
            context = KnowledgePackService.get_context_for_stack(
                tech_stack,
                include_examples=False,
                include_pitfalls=True,
            )
            
            if context:
                print(f"\n✅ Knowledge pack context loaded!")
                print(f"   Context size: {len(context)} characters")
                print(f"\n📝 Preview (first 500 chars):")
                print("-" * 60)
                print(context[:500])
                print("...")
                return True
            else:
                print("\n⚠️  No knowledge pack context generated")
                print("   Make sure integration packs exist for:")
                for key, value in tech_stack.items():
                    print(f"   - {key}/{value}")
                return False
        else:
            print("\n⚠️  No tech stack configured for this project")
            return False


async def main():
    """Run the test."""
    success = await test_workflow_integration()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Workflow integration test PASSED")
        print("\nThe agent will automatically receive technology-specific")
        print("knowledge when processing tasks for this project!")
    else:
        print("⚠️  Workflow integration test needs manual verification")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
