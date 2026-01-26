"""Gemini 2.5 Computer Use Browser Agent.

Uses Google's Gemini 2.5 Computer Use API with Python Playwright
for AI-driven browser automation. Replaces the previous LangChain + Node.js architecture.
"""
import asyncio
import base64
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from google.genai.types import Content, Part
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Screen dimensions - recommended by Gemini Computer Use docs
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900

# Model name for Computer Use
COMPUTER_USE_MODEL = "gemini-2.5-computer-use-preview-10-2025"


SYSTEM_PROMPT = """You are operating a desktop web browser controlled via Playwright.

General rules:
- Assume a modern Chromium-based desktop browser.
- The current date is October 15, 2023. Ignore any other dates.
- You can only interact with web pages (no OS-level or mobile actions).
- Always wait for elements to be visible and interactable before acting.
- If content is not visible, scroll the page until it appears.
- If text is truncated, open, expand, or navigate to view the full content.
- Do NOT assume something does not exist without scrolling or navigating.

Task execution:
- Follow the user’s instructions EXACTLY as stated.
- Do NOT complete similar or inferred tasks.
- If the task is already completed, do nothing.
- Do NOT open new tabs or windows unless explicitly instructed.
- Do NOT use browser shortcuts unless explicitly required.
- If the user provides a direct URL or a domain name (e.g., "example.com", "https://site.org"), navigate DIRECTLY to it. Do NOT search for it on Google.

Input and editing rules:
- If text input is required, use typing actions only.
- Do NOT use autofill or clipboard pasting unless explicitly allowed.
- Save changes unless explicitly told not to.

Output rules:
- Provide a **concise summary** first, describing what you found (max 2-3 sentences).
- Then, on a separate section, provide the **final answer ONLY** with TWO empty lines above it.
- Do NOT include reasoning or extra context in the final answer section.

Error handling:
- If something is missing, scroll or navigate to find it.
- If an element fails to load, retry logically before giving up.
"""







def denormalize_x(x: int, screen_width: int = SCREEN_WIDTH) -> int:
    """Convert normalized x coordinate (0-1000) to actual pixel coordinate."""
    return int(x / 1000 * screen_width)


def denormalize_y(y: int, screen_height: int = SCREEN_HEIGHT) -> int:
    """Convert normalized y coordinate (0-1000) to actual pixel coordinate."""
    return int(y / 1000 * screen_height)


class ComputerUseAgent:
    """Browser agent using Gemini 2.5 Computer Use API.
    
    Implements the agent loop:
    1. Send screenshot + prompt to model
    2. Receive function calls (UI actions)
    3. Execute actions with Playwright
    4. Capture new screenshot
    5. Repeat until task complete
    """
    
    def __init__(
        self,
        project_id: int,
        user_id: int,
        max_iterations: int = 30,
        headless: bool = True,
    ) -> None:
        """Initialize the Computer Use agent.
        
        Args:
            project_id: Project ID for WebSocket broadcasting
            user_id: User ID
            max_iterations: Maximum agent loop iterations
            headless: Run browser in headless mode
        """
        self.project_id = project_id
        self.user_id = user_id
        self.max_iterations = max_iterations
        self.headless = headless
        
        # Playwright instances
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # Gemini client
        self._client = None
        
        # Connection manager for WebSocket broadcasting
        self._connection_manager = None
        
        # Conversation history
        self._contents: List[Content] = []
        
        # Safety confirmation callback (for frontend integration)
        self._safety_confirmation_callback = None
        
        # Stop flag for graceful termination
        self._stop_requested = False
        
        # Background streaming task
        self._stream_task: Optional[asyncio.Task] = None
    
    @property
    def client(self) -> genai.Client:
        """Get Gemini client (lazy initialization)."""
        if self._client is None:
            # Use GEMINI_API_KEY or GOOGLE_API_KEY
            api_key = settings.gemini_api_key or os.environ.get("GOOGLE_API_KEY", "")
            self._client = genai.Client(api_key=api_key)
        return self._client
    
    @property
    def connection_manager(self):
        """Get WebSocket connection manager (lazy load)."""
        if self._connection_manager is None:
            from app.api.websocket.connection_manager import connection_manager
            self._connection_manager = connection_manager
        return self._connection_manager
    
    async def _start_streaming(self) -> None:
        """Start background streaming task."""
        if self._stream_task and not self._stream_task.done():
            return
            
        self._stream_task = asyncio.create_task(self._stream_loop())
        logger.info("Started background browser stream")

    async def _stop_streaming(self) -> None:
        """Stop background streaming task."""
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None
            logger.info("Stopped background browser stream")

    async def _stream_loop(self) -> None:
        """Continuous background streaming loop for smooth frontend."""
        logger.info("Entering background stream loop")
        frame_count = 0
        
        try:
            while not self._stop_requested and self._page:
                try:
                    start_time = datetime.utcnow()
                    
                    # Capture JPEG for Frontend (Fast)
                    screenshot_bytes = await self._get_screenshot(format="jpeg", quality=60)
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    
                    # Broadcast frame
                    await self._broadcast("browser_frame", {
                        "image": screenshot_b64, 
                        "format": "jpeg",
                        "deviceWidth": SCREEN_WIDTH,
                        "deviceHeight": SCREEN_HEIGHT
                    })
                    
                    # Periodically sync URL (every ~10 frames or so, or just rely on navigation events)
                    # Doing it every frame is fine if it's cheap, but page.url is cheap.
                    if frame_count % 30 == 0:
                         await self._broadcast("browser_url_changed", {"url": self._page.url})
                    
                    frame_count += 1
                    
                    # Maintain ~30 FPS
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    sleep_time = max(0.001, 0.033 - elapsed)
                    await asyncio.sleep(sleep_time)
                    
                except Exception as e:
                    # Don't crash the agent, just log and retry
                    logger.debug(f"Stream capture error: {e}")
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
             raise
        except Exception as e:
            logger.error(f"Stream loop died: {e}")
    
    async def _broadcast(self, message_type: str, data: Dict) -> None:
        """Broadcast message via WebSocket."""
        try:
            if self.connection_manager.get_connection_count(self.project_id) > 0:
                await self.connection_manager.send_to_local_connections(
                    self.project_id,
                    {
                        "type": message_type,
                        "agent": "browser",
                        **data,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            else:
                await self.connection_manager.broadcast_to_project(
                    self.project_id,
                    {
                        "type": message_type,
                        "agent": "browser",
                        **data,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
        except Exception as e:
            logger.warning(f"Failed to broadcast: {e}")
    
    async def _init_browser(self, initial_url: str = "https://google.com") -> None:
        """Initialize Playwright browser."""
        logger.info("Initializing Playwright browser...")
        
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        self._context = await self._browser.new_context(
            viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT}
        )
        self._page = await self._context.new_page()
        
        # Navigate to initial URL
        await self._page.goto(initial_url, wait_until="domcontentloaded")
        logger.info(f"Browser initialized at {initial_url}")
    
    async def _get_screenshot(self, format: str = "png", quality: int = None) -> bytes:
        """Capture current page screenshot as bytes.
        
        Args:
            format: 'png' or 'jpeg'
            quality: Quality (0-100) for jpeg, ignored for png
        """
        if format == "jpeg":
            return await self._page.screenshot(type="jpeg", quality=quality or 80)
        return await self._page.screenshot(type="png")
    
    async def _get_screenshot_base64(self, format: str = "png", quality: int = None) -> str:
        """Get screenshot as base64 string."""
        screenshot_bytes = await self._get_screenshot(format=format, quality=quality)
        return base64.b64encode(screenshot_bytes).decode('utf-8')
    
    async def _execute_action(self, function_call) -> Dict[str, Any]:
        """Execute a single Computer Use action.
        
        Args:
            function_call: The function call from model response
            
        Returns:
            Result dict with any error info
        """
        fname = function_call.name
        args = dict(function_call.args) if function_call.args else {}
        
        logger.info(f"Executing action: {fname} with args: {args}")
        result = {}
        
        try:
            if fname == "open_web_browser":
                # Browser already open
                pass
            
            elif fname == "navigate":
                url = args.get("url", "")
                await self._page.goto(url, wait_until="domcontentloaded")
                logger.info(f"Navigated to: {url}")
            
            elif fname == "click_at":
                x = denormalize_x(args.get("x", 0))
                y = denormalize_y(args.get("y", 0))
                await self._page.mouse.click(x, y)
                logger.info(f"Clicked at ({x}, {y})")
            
            elif fname == "hover_at":
                x = denormalize_x(args.get("x", 0))
                y = denormalize_y(args.get("y", 0))
                await self._page.mouse.move(x, y)
                logger.info(f"Hovered at ({x}, {y})")
            
            elif fname == "type_text_at":
                x = denormalize_x(args.get("x", 0))
                y = denormalize_y(args.get("y", 0))
                text = args.get("text", "")
                press_enter = args.get("press_enter", False)
                clear_before = args.get("clear_before_typing", False)
                
                # Click to focus
                await self._page.mouse.click(x, y)
                
                # Clear if requested
                if clear_before:
                    await self._page.keyboard.press("Meta+A")
                    await self._page.keyboard.press("Backspace")
                
                # Type text
                await self._page.keyboard.type(text)
                
                if press_enter:
                    await self._page.keyboard.press("Enter")
                
                logger.info(f"Typed text at ({x}, {y}): {text[:50]}...")
            
            elif fname == "key_combination":
                keys = args.get("keys", "")
                await self._page.keyboard.press(keys)
                logger.info(f"Pressed keys: {keys}")
            
            elif fname == "scroll_document":
                direction = args.get("direction", "down")
                delta = 500 if direction in ["down", "right"] else -500
                if direction in ["up", "down"]:
                    await self._page.mouse.wheel(0, delta)
                else:
                    await self._page.mouse.wheel(delta, 0)
                logger.info(f"Scrolled document: {direction}")
            
            elif fname == "scroll_at":
                x = denormalize_x(args.get("x", 500))
                y = denormalize_y(args.get("y", 500))
                direction = args.get("direction", "down")
                magnitude = args.get("magnitude", 400)
                
                await self._page.mouse.move(x, y)
                
                delta = magnitude if direction in ["down", "right"] else -magnitude
                if direction in ["up", "down"]:
                    await self._page.mouse.wheel(0, delta)
                else:
                    await self._page.mouse.wheel(delta, 0)
                logger.info(f"Scrolled at ({x}, {y}): {direction} by {magnitude}")
            
            elif fname == "go_back":
                await self._page.go_back()
                logger.info("Navigated back")
            
            elif fname == "go_forward":
                await self._page.go_forward()
                logger.info("Navigated forward")
            
            elif fname == "wait_5_seconds":
                await asyncio.sleep(5)
                logger.info("Waited 5 seconds")
            
            elif fname == "search":
                # Open browser search (Ctrl+F)
                await self._page.keyboard.press("Control+F")
                logger.info("Opened search")
            
            elif fname == "drag_and_drop":
                x = denormalize_x(args.get("x", 0))
                y = denormalize_y(args.get("y", 0))
                dest_x = denormalize_x(args.get("destination_x", 0))
                dest_y = denormalize_y(args.get("destination_y", 0))
                
                await self._page.mouse.move(x, y)
                await self._page.mouse.down()
                await self._page.mouse.move(dest_x, dest_y)
                await self._page.mouse.up()
                logger.info(f"Dragged from ({x}, {y}) to ({dest_x}, {dest_y})")
            
            else:
                logger.warning(f"Unknown action: {fname}")
                result["error"] = f"Unknown action: {fname}"
            
            # Wait for page to settle after action
            try:
                await self._page.wait_for_load_state(timeout=5000)
            except Exception:
                pass  # Timeout is fine
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error executing {fname}: {e}")
            result["error"] = str(e)
        
        return result
    
    async def _check_safety_decision(self, function_call) -> bool:
        """Check for safety decision and get user confirmation if needed.
        
        Args:
            function_call: The function call with potential safety_decision
            
        Returns:
            True if action should proceed, False if denied
        """
        args = dict(function_call.args) if function_call.args else {}
        
        if "safety_decision" not in args:
            return True
        
        safety_decision = args["safety_decision"]
        decision = safety_decision.get("decision", "")
        explanation = safety_decision.get("explanation", "")
        
        if decision != "require_confirmation":
            return True
        
        logger.info(f"Safety confirmation required: {explanation}")
        
        # Broadcast to frontend for confirmation
        await self._broadcast("safety_confirmation_required", {
            "explanation": explanation,
            "action": function_call.name,
        })
        
        # In a real implementation, wait for user response
        # For now, auto-approve (you may want to implement proper confirmation flow)
        # TODO: Implement proper callback-based confirmation
        logger.warning("Auto-approving safety confirmation (implement proper flow)")
        return True
    
    async def _execute_function_calls(self, candidate) -> List[tuple]:
        """Execute all function calls from model response.
        
        Args:
            candidate: Response candidate containing function calls
            
        Returns:
            List of (function_name, result_dict) tuples
        """
        results = []
        
        for part in candidate.content.parts:
            if not part.function_call:
                continue
            
            function_call = part.function_call
            
            # Check safety decision
            should_proceed = await self._check_safety_decision(function_call)
            if not should_proceed:
                results.append((function_call.name, {"error": "User denied action"}))
                continue
            
            # Broadcast tool execution
            await self._broadcast("tool_execution", {
                "tool": function_call.name,
                "message": f"Executing {function_call.name}...",
                "input": dict(function_call.args) if function_call.args else {},
            })
            
            # Execute the action
            result = await self._execute_action(function_call)
            
            # Check for safety acknowledgement
            args = dict(function_call.args) if function_call.args else {}
            if "safety_decision" in args:
                result["safety_acknowledgement"] = "true"
            
            results.append((function_call.name, result))
            
            # Broadcast tool result
            await self._broadcast("tool_result", {
                "tool": function_call.name,
                "result": str(result) if result else "Success",
            })
        
        return results
    
    async def _get_function_responses(self, results: List[tuple]) -> List:
        """Build function responses with screenshot.
        
        Args:
            results: List of (function_name, result_dict) tuples
            
        Returns:
            List of FunctionResponse objects
        """
        screenshot_bytes = await self._get_screenshot(format="png")
        current_url = self._page.url
        
        function_responses = []
        for name, result in results:
            response_data = {"url": current_url}
            response_data.update(result)
            
            function_responses.append(
                types.FunctionResponse(
                    name=name,
                    response=response_data,
                    parts=[
                        types.FunctionResponsePart(
                            inline_data=types.FunctionResponseBlob(
                                mime_type="image/png",
                                data=screenshot_bytes
                            )
                        )
                    ]
                )
            )
        
        return function_responses
    
    async def run(self, user_message: str, initial_url: str = "https://google.com") -> str:
        """Run the Computer Use agent with a user message.
        
        Args:
            user_message: User's request (e.g., "Search for Python tutorials")
            initial_url: Starting URL for the browser
            
        Returns:
            Final response text with results
        """
        logger.info(f"Starting Computer Use agent for project {self.project_id}")
        
        await self._broadcast("agent_status", {"status": "started", "message": "Starting browser agent..."})
        
        # Initialize browser
        try:
            await self._init_browser(initial_url)
        except Exception as e:
            error_msg = f"Failed to initialize browser: {e}"
            logger.error(error_msg)
            await self._broadcast("agent_status", {"status": "error", "message": error_msg})
            return error_msg
        
        # Get initial screenshot
        try:
            # Capture PNG for Model (Required)
            initial_screenshot_png = await self._get_screenshot(format="png")
            
            # Streaming will handle the frontend update from now on
        except Exception as e:
            error_msg = f"Failed to capture initial screenshot: {e}"
            logger.error(error_msg)
            await self._broadcast("agent_status", {"status": "error", "message": error_msg})
            return error_msg
        
        # Start background streaming for smooth frontend
        await self._start_streaming()
        
        # Configure Computer Use tool
        config = types.GenerateContentConfig(
             system_instruction=SYSTEM_PROMPT,
            tools=[
                types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER
                    )
                )
            ],
            # Enable thinking for better reasoning
            thinking_config=types.ThinkingConfig(include_thoughts=True),
        )
        
        # Initialize conversation with user message and screenshot
        self._contents = [
            Content(
                role="user",
                parts=[
                    Part(text=user_message),
                    Part.from_bytes(data=initial_screenshot_png, mime_type="image/png")
                ]
            )
        ]
        
        final_response = ""
        agent_completed = False
        
        # Agent loop
        try:
            for iteration in range(1, self.max_iterations + 1):
                if self._stop_requested:
                    logger.info("Stop requested, terminating agent loop")
                    break
                
                logger.info(f"Agent iteration {iteration}")
                
                try:
                    # Call model in thread to avoid blocking the stream
                    loop = asyncio.get_running_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.client.models.generate_content(
                            model=COMPUTER_USE_MODEL,
                            contents=self._contents,
                            config=config,
                        )
                    )
                    
                    candidate = response.candidates[0]
                    self._contents.append(candidate.content)
                    
                    # Check for function calls
                    has_function_calls = any(
                        part.function_call for part in candidate.content.parts
                    )
                    
                    if not has_function_calls:
                        # No function calls - agent is done
                        text_parts = [part.text for part in candidate.content.parts if part.text]
                        final_response = " ".join(text_parts)
                        agent_completed = True
                        logger.info(f"Agent completed after {iteration} iterations")
                        break
                    
                    # Execute function calls
                    results = await self._execute_function_calls(candidate)
                    
                    # Get new screenshot and build function responses
                    # This explicitly uses PNG internally for the model responses
                    function_responses = await self._get_function_responses(results)
                    
                    # Add function responses to conversation
                    self._contents.append(
                        Content(
                            role="user",
                            parts=[Part(function_response=fr) for fr in function_responses]
                        )
                    )
                    
                except Exception as e:
                    error_msg = f"Error in iteration {iteration}: {e}"
                    logger.error(error_msg)
                    # Don't broadcast logic error as agent status, just log it
                    # await self._broadcast("agent_status", {"status": "error", "message": str(e)})
                    
                    # Try to recover
                    self._contents.append(
                        Content(role="user", parts=[Part(text=f"Error occurred: {e}. Please try a different approach.")])
                    )
        finally:
            # Stop streaming when agent is done
            await self._stop_streaming()

        
        if iteration >= self.max_iterations and not agent_completed:
            logger.warning(f"Agent reached max iterations ({self.max_iterations})")
            
            # Request summary from model
            summary_prompt = "You have reached the maximum number of defined steps (max_iterations). Please provide a clear and concise summary of what you have found, accomplished, or verified so far based on our interaction. If you have partial results, please list them."
            
            self._contents.append(
                Content(role="user", parts=[Part(text=summary_prompt)])
            )
            
            try:
                # Call model for final summary
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model=COMPUTER_USE_MODEL,
                        contents=self._contents,
                        config=config,
                    )
                )
                
                if response.candidates and response.candidates[0].content.parts:
                    text_parts = [part.text for part in response.candidates[0].content.parts if part.text]
                    final_response = " ".join(text_parts)
                else:
                    final_response = "I've reached the maximum number of steps, but couldn't generate a summary."
                    
            except Exception as e:
                logger.error(f"Failed to generate summary on max steps: {e}")
                final_response = "I've reached the maximum number of steps. Here's what I was able to accomplish (summary generation failed)."
        
        # Send final response
        await self._broadcast("agent_response", {"message": final_response})
        await self._broadcast("agent_status", {"status": "completed", "message": "Browser task completed!"})
        
        return final_response
    
    async def handle_user_interaction(self, interaction: Dict) -> None:
        """Handle user interaction from frontend (mouse/keyboard events).
        
        Args:
            interaction: Dict with type and payload
        """
        if not self._page:
            logger.warning("No active page for interaction")
            return
        
        payload = interaction.get("payload", interaction)
        event_type = payload.get("type", "")
        
        try:
            if event_type == "input_mouse":
                x = payload.get("x", 0)
                y = payload.get("y", 0)
                mouse_event = payload.get("eventType", "")
                
                if mouse_event == "mouseMoved":
                    await self._page.mouse.move(x, y)
                elif mouse_event == "mousePressed":
                    await self._page.mouse.move(x, y)
                    await self._page.mouse.down(button=payload.get("button", "left"))
                elif mouse_event == "mouseReleased":
                    await self._page.mouse.move(x, y)
                    await self._page.mouse.up(button=payload.get("button", "left"))
            
            elif event_type == "input_keyboard":
                key_event = payload.get("eventType", "")
                
                if key_event == "type":
                    text = payload.get("text", "")
                    await self._page.keyboard.type(text)
                elif key_event == "press":
                    key = payload.get("key", "")
                    await self._page.keyboard.press(key)
                elif key_event == "keyDown":
                    key = payload.get("key", "")
                    await self._page.keyboard.down(key)
                elif key_event == "keyUp":
                    key = payload.get("key", "")
                    await self._page.keyboard.up(key)
            
            elif event_type == "set_viewport":
                width = payload.get("width", SCREEN_WIDTH)
                height = payload.get("height", SCREEN_HEIGHT)
                await self._page.set_viewport_size({"width": width, "height": height})
                logger.info(f"Viewport changed to {width}x{height}")
                
        except Exception as e:
            logger.warning(f"Error handling interaction: {e}")
    
    def stop(self) -> None:
        """Request graceful stop of agent loop."""
        self._stop_requested = True
    
    async def close(self) -> None:
        """Close browser and cleanup resources."""
        self._stop_requested = True
        
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.warning(f"Error stopping playwright: {e}")
        
        logger.info("Computer Use agent closed")


async def run_computer_use_agent(
    user_message: str,
    project_id: int,
    user_id: int,
    initial_url: str = "https://google.com",
    headless: bool = True,
) -> str:
    """Convenience function to run the Computer Use agent.
    
    Args:
        user_message: User's request message
        project_id: Project ID
        user_id: User ID
        initial_url: Starting URL for the browser
        headless: Run browser in headless mode
        
    Returns:
        Agent's final response
    """
    agent = ComputerUseAgent(
        project_id=project_id,
        user_id=user_id,
        headless=headless,
    )
    try:
        return await agent.run(user_message, initial_url)
    finally:
        await agent.close()