"""Test script for knowledge pack system."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.knowledge_packs import load_pack, load_packs
from app.knowledge_packs.service import KnowledgePackService


async def test_load_serverpod():
    """Test loading Serverpod pack."""
    print("=" * 60)
    print("Testing Serverpod Pack Loading")
    print("=" * 60)
    
    pack = load_pack("backends/serverpod")
    
    if pack:
        print(f"✅ Loaded pack: {pack.metadata.name} v{pack.metadata.version}")
        print(f"   Description: {pack.metadata.description}")
        print(f"   Type: {pack.metadata.pack_type}")
        print(f"   Rules: {len(pack.rules.rules)}")
        print(f"   Templates: {len(pack.templates)}")
        print(f"   Examples: {len(pack.examples)}")
        print(f"   Pitfalls: {len(pack.pitfalls)}")
        
        # Show rules by priority
        print("\n📋 Rules by priority:")
        for priority in ["critical", "high", "medium", "low"]:
            rules = pack.rules.get_by_priority(priority)
            if rules:
                print(f"   {priority.upper()}: {len(rules)} rules")
        
        # Show pitfalls
        print("\n⚠️  Pitfalls:")
        agent_traps = [p for p in pack.pitfalls if p.is_agent_trap]
        print(f"   Agent-specific traps: {len(agent_traps)}")
        print(f"   General pitfalls: {len(pack.pitfalls) - len(agent_traps)}")
        
        return True
    else:
        print("❌ Failed to load Serverpod pack")
        return False


async def test_multi_pack_loading():
    """Test loading multiple packs."""
    print("\n" + "=" * 60)
    print("Testing Multi-Pack Loading")
    print("=" * 60)
    
    tech_stack = {
        "frontend": "nextjs",
        "backend": "serverpod",
    }
    
    print(f"Tech stack: {tech_stack}")
    
    packs = load_packs(tech_stack)
    
    print(f"\n✅ Loaded {len(packs)} packs:")
    for pack in packs:
        print(f"   - {pack.metadata.name} ({pack.metadata.pack_type})")
    
    return len(packs) > 0


async def test_service_layer():
    """Test knowledge pack service."""
    print("\n" + "=" * 60)
    print("Testing Knowledge Pack Service")
    print("=" * 60)
    
    tech_stack = {
        "frontend": "flutter",
        "backend": "serverpod",
    }
    
    print(f"Tech stack: {tech_stack}")
    
    # Get context
    context = KnowledgePackService.get_context_for_stack(
        tech_stack,
        include_examples=False,
        include_pitfalls=True,
    )
    
    print(f"\n✅ Generated context ({len(context)} characters)")
    print("\nPreview:")
    print("-" * 60)
    print(context[:500])
    print("...")
    print("-" * 60)
    
    # Get templates
    templates = KnowledgePackService.get_templates(tech_stack)
    print(f"\n✅ Available templates: {len(templates)}")
    for name in templates.keys():
        print(f"   - {name}")
    
    return len(context) > 0


async def test_agent_integration():
    """Test agent integration."""
    print("\n" + "=" * 60)
    print("Testing Agent Integration")
    print("=" * 60)
    
    # This simulates what the agent does
    from app.knowledge_packs.service import KnowledgePackService
    
    tech_stack = {
        "backend": "serverpod",
    }
    
    pack_context = KnowledgePackService.get_context_for_stack(
        tech_stack,
        include_examples=False,
        include_pitfalls=True,
    )
    
    if pack_context:
        print("✅ Agent would receive technology-specific context")
        print(f"   Context size: {len(pack_context)} characters")
        print("\n📝 Sample (first 1000 chars):")
        print("-" * 60)
        print(pack_context[:1000])
        print("...")
        return True
    else:
        print("❌ No context generated")
        return False


async def main():
    """Run all tests."""
    results = []
    
    results.append(("Load Serverpod Pack", await test_load_serverpod()))
    results.append(("Multi-Pack Loading", await test_multi_pack_loading()))
    results.append(("Service Layer", await test_service_layer()))
    results.append(("Agent Integration", await test_agent_integration()))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
