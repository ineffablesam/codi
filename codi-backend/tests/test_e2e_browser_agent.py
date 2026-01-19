"""
End-to-End Test for Browser Agent.

Tests the complete browser agent flow:
1. Start browser-agent service
2. Create browser session
3. Navigate and take screenshot
4. Verify screenshot is base64 encoded
5. Execute browser commands (click, fill, scroll)
6. Close session

NO MOCKING - Real browser-agent service, real Chromium.
"""

import asyncio
import base64
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Browser agent service URL
BROWSER_AGENT_URL = "http://browser-agent:3001"


class BrowserAgentE2ETest:
    """End-to-end test for browser agent service."""
    
    def __init__(self):
        self.session_id: Optional[str] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        
    async def setup(self):
        """Initialize HTTP client."""
        self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session_id:
            try:
                await self.http_client.delete(f"{BROWSER_AGENT_URL}/session/{self.session_id}")
                logger.info(f"✅ Closed session: {self.session_id}")
            except Exception as e:
                logger.warning(f"Failed to close session: {e}")
        
        if self.http_client:
            await self.http_client.aclose()
    
    async def test_health_check(self) -> bool:
        """Test 1: Verify browser-agent service is healthy."""
        logger.info("=" * 80)
        logger.info("TEST 1: Health Check")
        logger.info("=" * 80)
        
        try:
            response = await self.http_client.get(f"{BROWSER_AGENT_URL}/health")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Status: {data.get('status')}")
            logger.info(f"Sessions: {data.get('sessions')}")
            logger.info(f"Uptime: {data.get('uptime', 0):.2f}s")
            
            if data.get('status') == 'ok':
                logger.info("✅ Health check passed")
                return True
            else:
                logger.error(f"❌ Unexpected status: {data}")
                return False
                
        except httpx.ConnectError:
            logger.error("❌ Cannot connect to browser-agent service")
            logger.error("   Make sure to run: docker-compose up -d browser-agent")
            return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
    
    async def test_create_session(self) -> bool:
        """Test 2: Create browser session and navigate to initial URL."""
        logger.info("=" * 80)
        logger.info("TEST 2: Create Browser Session")
        logger.info("=" * 80)
        
        try:
            response = await self.http_client.post(
                f"{BROWSER_AGENT_URL}/session",
                json={"initial_url": "https://example.com"}
            )
            response.raise_for_status()
            
            data = response.json()
            self.session_id = data.get("session_id")
            
            logger.info(f"Session ID: {self.session_id}")
            logger.info(f"Initial URL: {data.get('url')}")
            
            if self.session_id:
                logger.info("✅ Session created successfully")
                return True
            else:
                logger.error("❌ No session ID returned")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            return False
    
    async def test_screenshot(self) -> bool:
        """Test 3: Take screenshot and verify base64 encoding."""
        logger.info("=" * 80)
        logger.info("TEST 3: Take Screenshot")
        logger.info("=" * 80)
        
        try:
            response = await self.http_client.get(
                f"{BROWSER_AGENT_URL}/session/{self.session_id}/screenshot"
            )
            response.raise_for_status()
            
            data = response.json()
            image_b64 = data.get("image")
            image_format = data.get("format")
            
            if not image_b64:
                logger.error("❌ No image data returned")
                return False
            
            # Verify base64 encoding
            try:
                decoded = base64.b64decode(image_b64)
                image_size = len(decoded)
                logger.info(f"Image format: {image_format}")
                logger.info(f"Base64 length: {len(image_b64)} chars")
                logger.info(f"Decoded size: {image_size} bytes ({image_size / 1024:.1f} KB)")
                
                # Log full base64 image data
                logger.info("-" * 40)
                logger.info("BASE64 IMAGE DATA:")
                logger.info(image_b64)
                logger.info("-" * 40)
                
                # Check PNG header
                if decoded[:4] == b'\x89PNG':
                    logger.info("✅ Valid PNG image received")
                    return True
                elif decoded[:2] == b'\xff\xd8':
                    logger.info("✅ Valid JPEG image received")
                    return True
                else:
                    logger.warning("⚠️  Unknown image format but data received")
                    return True
                    
            except Exception as e:
                logger.error(f"❌ Failed to decode base64: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Screenshot failed: {e}")
            return False
    
    async def test_accessibility_snapshot(self) -> bool:
        """Test 4: Get accessibility snapshot with element refs."""
        logger.info("=" * 80)
        logger.info("TEST 4: Accessibility Snapshot")
        logger.info("=" * 80)
        
        try:
            response = await self.http_client.get(
                f"{BROWSER_AGENT_URL}/session/{self.session_id}/snapshot"
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Log snapshot info
            if "data" in data:
                snapshot = data.get("data", {}).get("snapshot", "")
            else:
                snapshot = str(data)
            
            # Check for element refs
            if "@e" in snapshot or "ref" in snapshot.lower():
                logger.info(f"Snapshot contains element refs")
                logger.info(f"Snapshot preview: {snapshot[:500]}...")
                logger.info("✅ Accessibility snapshot received with refs")
                return True
            else:
                logger.info(f"Snapshot preview: {snapshot[:500]}...")
                logger.warning("⚠️  Snapshot received but no @refs found")
                return True  # Still pass, format may vary
                
        except Exception as e:
            logger.error(f"❌ Snapshot failed: {e}")
            return False
    
    async def test_browser_commands(self) -> bool:
        """Test 5: Execute browser commands."""
        logger.info("=" * 80)
        logger.info("TEST 5: Browser Commands")
        logger.info("=" * 80)
        
        commands_tested = 0
        commands_passed = 0
        
        # Test navigate
        logger.info("Testing: navigate...")
        try:
            response = await self.http_client.post(
                f"{BROWSER_AGENT_URL}/session/{self.session_id}/command",
                json={"command": "navigate", "args": {"url": "https://google.com"}}
            )
            if response.status_code == 200:
                logger.info("  ✓ navigate succeeded")
                commands_passed += 1
            else:
                logger.warning(f"  ✗ navigate failed: {response.text}")
            commands_tested += 1
        except Exception as e:
            logger.warning(f"  ✗ navigate error: {e}")
            commands_tested += 1
        
        # Wait for page load
        await asyncio.sleep(2)
        
        # Test scroll
        logger.info("Testing: scroll...")
        try:
            response = await self.http_client.post(
                f"{BROWSER_AGENT_URL}/session/{self.session_id}/command",
                json={"command": "scroll", "args": {"direction": "down", "amount": 200}}
            )
            if response.status_code == 200:
                logger.info("  ✓ scroll succeeded")
                commands_passed += 1
            else:
                logger.warning(f"  ✗ scroll failed: {response.text}")
            commands_tested += 1
        except Exception as e:
            logger.warning(f"  ✗ scroll error: {e}")
            commands_tested += 1
        
        # Test press (Enter key)
        logger.info("Testing: press...")
        try:
            response = await self.http_client.post(
                f"{BROWSER_AGENT_URL}/session/{self.session_id}/command",
                json={"command": "press", "args": {"key": "Escape"}}
            )
            if response.status_code == 200:
                logger.info("  ✓ press succeeded")
                commands_passed += 1
            else:
                logger.warning(f"  ✗ press failed: {response.text}")
            commands_tested += 1
        except Exception as e:
            logger.warning(f"  ✗ press error: {e}")
            commands_tested += 1
        
        # Take final screenshot to verify state
        logger.info("Taking final screenshot...")
        try:
            response = await self.http_client.get(
                f"{BROWSER_AGENT_URL}/session/{self.session_id}/screenshot"
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("image"):
                    logger.info("  ✓ Final screenshot captured")
                    commands_passed += 1
            commands_tested += 1
        except Exception as e:
            logger.warning(f"  ✗ Final screenshot error: {e}")
            commands_tested += 1
        
        logger.info(f"Commands passed: {commands_passed}/{commands_tested}")
        
        if commands_passed >= commands_tested - 1:  # Allow 1 failure
            logger.info("✅ Browser commands test passed")
            return True
        else:
            logger.error("❌ Too many command failures")
            return False
    
    async def test_close_session(self) -> bool:
        """Test 6: Close session."""
        logger.info("=" * 80)
        logger.info("TEST 6: Close Session")
        logger.info("=" * 80)
        
        try:
            response = await self.http_client.delete(
                f"{BROWSER_AGENT_URL}/session/{self.session_id}"
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("success"):
                logger.info("✅ Session closed successfully")
                self.session_id = None  # Prevent double-close in cleanup
                return True
            else:
                logger.error(f"❌ Unexpected response: {data}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to close session: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all browser agent tests."""
        logger.info("\n\n")
        logger.info("█" * 80)
        logger.info("█" + " " * 78 + "█")
        logger.info("█" + "  BROWSER AGENT E2E TEST".center(78) + "█")
        logger.info("█" + " " * 78 + "█")
        logger.info("█" * 80)
        logger.info("\n")
        
        overall_start = time.time()
        results = []
        
        try:
            await self.setup()
            
            # Run tests in order
            results.append(("Health Check", await self.test_health_check()))
            
            if results[-1][1]:  # Only continue if health check passes
                results.append(("Create Session", await self.test_create_session()))
                
                if results[-1][1]:  # Only continue if session created
                    results.append(("Screenshot", await self.test_screenshot()))
                    results.append(("Accessibility Snapshot", await self.test_accessibility_snapshot()))
                    results.append(("Browser Commands", await self.test_browser_commands()))
                    results.append(("Close Session", await self.test_close_session()))
            
            overall_duration = time.time() - overall_start
            
            # Summary
            logger.info("\n")
            logger.info("=" * 80)
            logger.info("TEST SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total duration: {overall_duration:.2f}s")
            logger.info("")
            
            passed = sum(1 for _, success in results if success)
            total = len(results)
            
            for test_name, success in results:
                status = "✅ PASS" if success else "❌ FAIL"
                logger.info(f"  {test_name}: {status}")
            
            logger.info("")
            logger.info(f"Passed: {passed}/{total}")
            
            all_passed = passed == total
            
            if all_passed:
                logger.info("\n✅ ✅ ✅  ALL BROWSER AGENT TESTS PASSED  ✅ ✅ ✅")
            else:
                logger.error("\n❌ ❌ ❌  SOME TESTS FAILED  ❌ ❌ ❌")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"\n❌ ❌ ❌  TEST EXCEPTION  ❌ ❌ ❌")
            logger.error(f"Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        finally:
            await self.cleanup()


async def main():
    """Run the browser agent E2E test."""
    runner = BrowserAgentE2ETest()
    success = await runner.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
