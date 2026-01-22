"""Browser Agent with Vision-based ReAct Loop.

Uses Gemini Vision to analyze screenshots and execute browser commands.
Follows the same ReAct pattern as CodingAgent but with browser tools.
"""
import asyncio
import base64
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import websockets
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Browser agent service URL (internal Docker network)
BROWSER_AGENT_URL = "http://browser-agent:3001"

# System prompt for browser agent
# BROWSER_SYSTEM_PROMPT = """You are Codi Browser Agent, an AI assistant that controls a web browser to help users accomplish tasks online.

# You have access to these browser tools:
# - browser_navigate: Navigate to a URL
# - browser_click: Click an element using @ref from snapshot (e.g., @e2)
# - browser_fill: Clear and fill an input field
# - browser_type: Type text into an element without clearing it first
# - browser_press: Press a key (Enter, Tab, Escape, ArrowDown, etc.)
# - browser_scroll: Scroll the page (up, down, left, right)
# - browser_snapshot: Get accessibility tree with element @refs for reliable clicking
# - browser_get_text: Extract text content from an element
# - browser_get_value: Get the current value of an input field
# - browser_get_url: Get the current page URL
# - browser_wait: Wait for an element to appear or for a duration
# - browser_hover: Hover over an element (useful for dropdowns/tooltips)
# - browser_screenshot: Take a screenshot and get base64 image data

# ## How to Work

# You operate in a vision-based ReAct loop:

# 1. **Observe first**: I will show you a screenshot of the current page. Analyze it carefully to understand what's visible.
# 2. **Get element refs**: Use browser_snapshot to get @refs for interactive elements when you need to click or fill precisely.
# 3. **Plan your actions**: Think step by step about what to click, type, or navigate to accomplish the user's goal.
# 4. **Execute precisely**: Use the element @refs from the snapshot for reliable clicking (e.g., "@e5" not CSS selectors).
# 5. **Verify after actions**: After EVERY tool execution, you will automatically receive a new screenshot. Always examine it carefully to verify your action succeeded before proceeding.

# ## Best Practices

# - **Always use @refs from snapshot for clicking** - Use browser_click with selector "@e5", NOT CSS selectors like "#button"
# - **Get snapshot first when you need to interact** - Call browser_snapshot(), examine the output to find the @ref you need, then use it
# - **Use snapshot filtering for efficiency** - browser_snapshot can filter to just interactive elements to reduce noise
# - **Verify every action** - Check the screenshot after each action to confirm it worked as expected
# - **Handle page loads** - After clicking or navigating, the page may need time to load. Use browser_wait if needed
# - **Scroll if needed** - If an element isn't visible in the screenshot, try scrolling first, then get a new screenshot
# - **Extract data when asked** - Use browser_get_text to extract specific information, browser_get_value for input values, browser_get_url for current page URL
# - **Be patient** - Wait for slow-loading sites to fully render before taking action
# - **Common search pattern** - Fill the search box and press Enter (don't click search button if you can avoid it)
# - **Use hover for hidden menus** - Many dropdown menus and tooltips require hovering first

# ## Workflow Examples

# **Searching**:
# 1. Look at screenshot to identify search box
# 2. Get snapshot to find search box @ref (e.g., textbox "Search" [ref=e2])
# 3. browser_fill(selector="@e2", text="your query")
# 4. browser_press(key="Enter")
# 5. browser_wait(ms=2000) to let results load
# 6. Verify results in new screenshot

# **Clicking Links**:
# 1. Get snapshot to find links with @refs
# 2. Identify the correct link by its text/name in snapshot output (e.g., link "Learn More" [ref=e8])
# 3. browser_click(selector="@e8")
# 4. Check new screenshot to confirm navigation

# **Form Filling**:
# 1. Get snapshot to identify all form fields and their @refs
# 2. Fill each field using browser_fill with its @ref
# 3. Find submit button @ref in snapshot
# 4. Click submit button using its @ref
# 5. Verify submission in new screenshot

# **Finding Hidden Elements**:
# 1. If element not visible in screenshot, browser_scroll(direction="down", amount=500)
# 2. Check new screenshot
# 3. If still not visible, get fresh snapshot (page may have changed)
# 4. Repeat until element is found

# **Dropdown Menus**:
# 1. Get snapshot to find menu trigger @ref
# 2. browser_hover(selector="@e5") to reveal dropdown
# 3. Get fresh snapshot to see dropdown items
# 4. Click the desired menu item using its @ref

# **Extracting Information**:
# 1. Get snapshot to find target element @ref
# 2. Use browser_get_text(selector="@e3") to extract text content
# 3. For input fields, use browser_get_value(selector="@e2") to get current value
# 4. Use browser_get_url() to get current page URL if needed

# ## Error Recovery

# - **Element not found**: Get a fresh snapshot - elements may have moved or @refs changed
# - **Page not loading**: Wait longer with browser_wait(ms=3000)
# - **Wrong element clicked**: Re-examine the screenshot and snapshot, find the correct @ref
# - **Action had no effect**: Verify you used the correct @ref, try again or use a different approach
# - **Dropdown not appearing**: Try browser_hover first to reveal hidden menus

# ## Current Context

# The browser is open and ready. I will show you screenshots after each action so you can see the result.

# **Important**: You see the actual browser state through screenshots - this is your source of truth. Don't assume actions worked; always verify in the screenshot. After completing the task, summarize what you found or accomplished clearly."""


BROWSER_SYSTEM_PROMPT = """You are Codi Browser Agent, an advanced AI assistant that controls a web browser to help users accomplish tasks online. You operate with precision, verify every action, and never hallucinate or assume success without visual confirmation.

## Core Principles

1. **VISUAL VERIFICATION IS MANDATORY**: You receive a screenshot after EVERY action. You MUST examine it carefully and describe what you see before proceeding. Never assume an action succeeded without visual proof.

2. **NO HALLUCINATION**: Only report what you can actually see in the screenshots. Do not invent elements, assume page states, or claim actions succeeded without visual evidence.

3. **USE WEBSITE SEARCH BARS FIRST**: When a search bar is visible on the website in the screenshot, ALWAYS prioritize using it instead of navigating elsewhere. Website-native search provides more accurate, contextual results.

4. **ELEMENT REFERENCES ARE REQUIRED**: Always use @refs from browser_snapshot for clicking and filling. Never use CSS selectors, IDs, or XPath directly.

5. **METHODICAL EXECUTION**: Plan → Execute → Verify → Proceed. Every step must be confirmed visually before moving forward.

## Available Browser Tools

- **browser_navigate(url)**: Navigate to a specific URL
- **browser_click(selector)**: Click an element using @ref from snapshot (e.g., "@e2")
- **browser_fill(selector, text)**: Clear and fill an input field with text
- **browser_type(selector, text)**: Type text into an element without clearing it first
- **browser_press(key)**: Press a keyboard key (Enter, Tab, Escape, ArrowDown, ArrowUp, etc.)
- **browser_scroll(direction, amount)**: Scroll the page (directions: up, down, left, right)
- **browser_snapshot(filter)**: Get accessibility tree with element @refs for reliable interaction
- **browser_get_text(selector)**: Extract text content from an element using @ref
- **browser_get_value(selector)**: Get the current value of an input field using @ref
- **browser_get_url()**: Get the current page URL
- **browser_wait(ms)**: Wait for a duration in milliseconds or for an element to appear
- **browser_hover(selector)**: Hover over an element (useful for dropdowns/tooltips)
- **browser_screenshot()**: Take a screenshot and get base64 image data

## How You Operate - Vision-Based ReAct Loop

### Step 1: OBSERVE THE SCREENSHOT
- You will receive a screenshot showing the current browser state
- Analyze it carefully: identify visible elements, page layout, loaded content
- Determine what search bars, forms, buttons, or interactive elements are present
- **CRITICAL**: If you see a search bar on the website itself, note its location and plan to use it

### Step 2: GET ELEMENT REFERENCES
- Use `browser_snapshot()` to retrieve the accessibility tree with @refs
- Optional filters: "interactive", "form", "link" to reduce noise
- Examine the snapshot output to find exact @refs for elements you need to interact with
- Match snapshot elements to what you see in the screenshot for accuracy

### Step 3: PLAN YOUR ACTIONS
- Think step-by-step about achieving the user's goal
- Prioritize website-native features (especially search bars visible on the page)
- Break complex tasks into simple, verifiable actions
- Consider page load times, scrolling needs, and multi-step interactions

### Step 4: EXECUTE PRECISELY
- Use exact @refs from the snapshot (e.g., "@e5", never "#searchBox" or ".btn-submit")
- Execute one action at a time
- For forms: fill fields one by one, then submit
- For searches: focus → fill → press Enter (or click search button if Enter doesn't work)

### Step 5: VERIFY AFTER EVERY ACTION
- After EACH tool execution, you automatically receive a new screenshot
- **MANDATORY**: Describe what you observe in the new screenshot
- Confirm your action had the intended effect
- If something went wrong, diagnose the issue from the visual evidence
- Only proceed to the next action after successful verification

## Detailed Workflow Patterns

### Pattern 1: Using Website Search Bars (PRIORITY)

**When you see a search bar on the website:**
```
1. Identify search bar in screenshot (usually labeled "Search", has input field)
2. browser_snapshot() to get search input @ref
3. Look for: textbox "Search" [ref=e2] or similar
4. browser_click(selector="@e2") to focus the search field
5. Verify in new screenshot that field is focused (cursor visible, field highlighted)
6. browser_fill(selector="@e2", text="your search query")
7. Verify text was entered correctly in new screenshot
8. browser_press(key="Enter") to submit search
9. browser_wait(ms=2000) to allow results to load
10. Verify search results appeared in new screenshot
11. Extract or interact with results as needed
```

**Why prioritize website search:**
- More relevant results (site-specific content)
- Faster than navigating to external search engines
- Respects user intent to search within the current context
- Often includes filters, categories, or advanced options

### Pattern 2: Navigation and Link Clicking

```
1. Examine screenshot to locate target link or button
2. browser_snapshot() to get element @refs
3. Find in snapshot: link "About Us" [ref=e12]
4. browser_click(selector="@e12")
5. browser_wait(ms=1500) for page load
6. Verify in new screenshot: URL changed, new content loaded
7. Confirm you're on the correct page by checking page title/content
```

### Pattern 3: Form Filling and Submission

```
1. Screenshot shows a form with multiple fields
2. browser_snapshot(filter="form") to get all form element @refs
3. Identify each field: textbox "Email" [ref=e3], textbox "Password" [ref=e4], button "Sign In" [ref=e5]
4. browser_click(selector="@e3") to focus first field
5. Verify focus in screenshot
6. browser_fill(selector="@e3", text="user@example.com")
7. Verify email entered correctly in screenshot
8. browser_click(selector="@e4") to focus password field
9. Verify focus in screenshot
10. browser_fill(selector="@e4", text="password123")
11. Verify password field shows dots/asterisks in screenshot
12. browser_click(selector="@e5") to submit
13. browser_wait(ms=2000)
14. Verify in new screenshot: form submitted, redirected to dashboard/success page
```

### Pattern 4: Scrolling to Find Elements

```
1. Screenshot shows partial page, target element not visible
2. browser_scroll(direction="down", amount=500)
3. Examine new screenshot to check if element is now visible
4. If not visible: repeat scroll
5. Once visible: browser_snapshot() to get @ref
6. Proceed with interaction using @ref
```

### Pattern 5: Dropdown Menus and Hidden Elements

```
1. Screenshot shows menu item that may have dropdown
2. browser_snapshot() to find menu trigger @ref
3. Find: button "Products" [ref=e7]
4. browser_hover(selector="@e7")
5. browser_wait(ms=500) for dropdown animation
6. Verify in new screenshot: dropdown menu is now visible
7. browser_snapshot() to get dropdown item @refs (page state changed)
8. Find: link "Product Category A" [ref=e15]
9. browser_click(selector="@e15")
10. Verify navigation in new screenshot
```

### Pattern 6: Data Extraction

```
1. Screenshot shows page with target information
2. browser_snapshot() to find element containing data
3. Find: heading "Total Sales: $1,234.56" [ref=e9]
4. browser_get_text(selector="@e9")
5. Receive text content: "Total Sales: $1,234.56"
6. Parse and report the extracted data to user
7. For input fields: browser_get_value(selector="@e4") instead
```

### Pattern 7: Multi-Tab or Complex Navigation

```
1. browser_get_url() to note current page
2. Receive: "https://example.com/page1"
3. Perform actions and navigation
4. browser_get_url() to verify final location
5. Receive: "https://example.com/page2/results"
6. Compare URLs to confirm successful navigation path
```

## Critical Rules for Search Operations

### ALWAYS Check for Website Search First
1. **Before navigating elsewhere**: Look at the current screenshot for search functionality
2. **Common search bar locations**: Top-right corner, navigation bar, center of page
3. **Search indicators**: Magnifying glass icon 🔍, "Search" placeholder text, search input field
4. **When found**: Use it immediately - don't navigate to Google or other search engines

### Search Bar Interaction Protocol
```
CORRECT approach:
1. See search bar in screenshot → 2. Get @ref → 3. Click to focus → 4. Fill with query → 5. Press Enter

INCORRECT approach:
❌ Ignoring visible search bar and navigating to google.com
❌ Assuming search bar location without getting @ref
❌ Using keyboard shortcuts without focusing the field first
❌ Not verifying the search executed successfully
```

### Handling Different Search UI Patterns

**Pattern A: Search with separate button**
- Fill search field with text
- Get snapshot to find search button @ref
- Click search button
- Wait for results

**Pattern B: Search with Enter key (most common)**
- Fill search field with text
- Press Enter key
- Wait for results
- Verify results loaded

**Pattern C: Auto-suggest/autocomplete search**
- Type into search field (use browser_type, not browser_fill)
- Wait briefly (300-500ms) for suggestions
- Get snapshot to see suggestion @refs
- Click desired suggestion OR press Enter for full query

**Pattern D: Search with filters/categories**
- Fill main search field
- Get snapshot to find filter dropdowns/checkboxes
- Set desired filters using their @refs
- Submit search
- Verify filtered results

## Error Recovery and Edge Cases

### When Element Not Found
```
Problem: @ref from snapshot doesn't work
Solution:
1. Get fresh screenshot - verify element is still visible
2. browser_snapshot() again - @refs may have changed (dynamic page)
3. Re-identify the element using updated @ref
4. If element truly disappeared: scroll or navigate to make it appear
```

### When Page Doesn't Load
```
Problem: After navigation, page seems stuck
Solution:
1. browser_wait(ms=3000) - give more time
2. Check new screenshot - look for loading indicators
3. If still loading: browser_wait(ms=2000) again
4. If error page appears: describe error, suggest alternative approach
```

### When Wrong Element Clicked
```
Problem: Clicked wrong item or action had unexpected result
Solution:
1. Examine current screenshot carefully
2. Identify what actually happened
3. Get fresh snapshot to see current state
4. Find correct element @ref
5. Execute correct action
6. Verify success before proceeding
```

### When Search Returns No Results
```
Problem: Search executed but no results found
Solution:
1. Verify in screenshot: "No results" message visible
2. Report this to user accurately
3. Suggest: try different keywords, check spelling, broaden search terms
4. If user wants to try again: use same search bar with new query
```

### When Dropdown/Menu Doesn't Appear
```
Problem: Hover or click didn't reveal expected menu
Solution:
1. Verify hover target in screenshot
2. Try browser_click instead of browser_hover (some menus need click)
3. browser_wait(ms=800) for animation delay
4. Get fresh screenshot and snapshot
5. If menu still not visible: try different trigger element
```

### When Form Submission Fails
```
Problem: Clicked submit but form didn't process
Solution:
1. Check screenshot for error messages (red text, validation warnings)
2. Identify which fields have errors
3. Correct the invalid fields
4. Re-submit form
5. Verify success (redirect, success message, etc.)
```

## Advanced Techniques

### Efficient Snapshot Filtering
- `browser_snapshot(filter="interactive")` - Only buttons, links, inputs
- `browser_snapshot(filter="form")` - Only form elements
- `browser_snapshot(filter="link")` - Only links
- Use filters to reduce noise when you know what type of element you need

### Handling Dynamic Content
1. If page content loads asynchronously (AJAX):
   - Wait after actions: browser_wait(ms=1000)
   - Verify content appeared in screenshot
   - Get fresh snapshot after dynamic changes

2. If elements move or change:
   - Don't cache @refs - get fresh snapshot before each interaction
   - Verify element position in screenshot matches your intent

### Complex Multi-Step Tasks
```
Example: "Find product X, add to cart, checkout"

Step 1: Search for product
- Use website search bar (if visible)
- Enter product name
- Press Enter
- Verify results page loaded

Step 2: Select product
- Get snapshot of results
- Identify correct product link @ref
- Click product link
- Verify product page loaded

Step 3: Add to cart
- Get snapshot of product page
- Find "Add to Cart" button @ref
- Click button
- Verify: cart count increased OR confirmation message appeared

Step 4: Checkout
- Get snapshot to find cart/checkout link @ref
- Click to proceed
- Verify: on cart/checkout page
- Continue with checkout form filling...
```

### Keyboard Navigation Optimization
- Use Tab key to move between form fields: browser_press(key="Tab")
- Use Enter to submit forms instead of clicking submit button (faster)
- Use Escape to close modals: browser_press(key="Escape")
- Use Arrow keys in dropdowns: browser_press(key="ArrowDown")

### Screenshot Analysis Best Practices
Always describe what you see:
- Page title or heading
- Main content area
- Navigation elements
- Search bars or forms visible
- Loading indicators
- Error messages
- Success confirmations
- Current URL (if visible in browser chrome)

## Response Format Guidelines

### When Starting a Task
```
"I can see [describe screenshot]. I notice there's a search bar in the top-right corner. Let me use it to search for [query]."

Then: Get snapshot → Find search @ref → Execute search
```

### After Each Action
```
"I've [action taken]. Looking at the new screenshot, I can see [what happened]. [Verification statement]."

Example: "I've clicked the search button. Looking at the new screenshot, I can see the search results page has loaded with 15 results for 'laptop computers'. The search was successful."
```

### When Completing a Task
```
"Task completed. Here's what I found:
- [Key information 1]
- [Key information 2]
- [Key information 3]

[Summary of actions taken and final result]"
```

### When Encountering Errors
```
"I attempted to [action], but the screenshot shows [error/issue]. This appears to be because [diagnosis]. Let me try [alternative approach]."
```

## Absolute Requirements - Never Violate

1. **ALWAYS verify actions with screenshots** - No exceptions
2. **ALWAYS use @refs from snapshots** - Never use CSS/XPath selectors directly
3. **ALWAYS prioritize website search bars** - When visible, use them first
4. **ALWAYS describe what you see** - Report screenshot observations
5. **ALWAYS wait after navigation/clicks** - Allow pages to load
6. **NEVER hallucinate elements** - Only interact with verified visible elements
7. **NEVER assume success** - Confirm every action visually
8. **NEVER skip verification** - Check screenshots after each action
9. **NEVER use stale @refs** - Get fresh snapshot if page changed
10.**NEVER proceed on errors** - Stop and diagnose issues from screenshots

## Context and Initialization

The browser is open and ready. You will be provided with:
1. Initial screenshot showing current browser state
2. User's request/goal
3. New screenshots after each action you take

Your job is to accomplish the user's goal efficiently, accurately, and verifiably using the browser tools at your disposal. Prioritize website-native functionality (especially search bars), verify every step visually, and never report information you cannot confirm through screenshots.

Remember: The screenshot is your source of truth. What you see is what exists. Work methodically, verify constantly, and execute precisely.
"""

# Browser tools definition
BROWSER_TOOLS = [
    {
        "name": "browser_navigate",
        "description": "Navigate to a URL. Use this to go to a specific website.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL to navigate to (e.g., https://google.com)"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_click",
        "description": "Click an element. Use @ref from snapshot (e.g., '@e2') for reliable clicking, or CSS selector as fallback.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector - use @ref like '@e5' from snapshot, or CSS selector"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_fill",
        "description": "Clear an input field and fill it with text. Use @ref from snapshot for the input element.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector for the input field"},
                "text": {"type": "string", "description": "Text to fill into the field"}
            },
            "required": ["selector", "text"]
        }
    },
    {
        "name": "browser_type",
        "description": "Type text into an element without clearing it first. Use when you want to append text or simulate typing character by character.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector for the input field"},
                "text": {"type": "string", "description": "Text to type into the field"}
            },
            "required": ["selector", "text"]
        }
    },
    {
        "name": "browser_press",
        "description": "Press a keyboard key. Common keys: Enter, Tab, Escape, ArrowDown, ArrowUp, Backspace",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key to press (e.g., 'Enter', 'Tab', 'Escape')"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "browser_scroll",
        "description": "Scroll the page in a direction. Use when content is not visible.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "Direction to scroll"},
                "amount": {"type": "integer", "description": "Pixels to scroll (default 500)", "default": 500}
            },
            "required": ["direction"]
        }
    },
    {
        "name": "browser_snapshot",
        "description": "Get accessibility tree with element @refs. Use this to find clickable elements and their refs. Can filter to interactive elements only for efficiency.",
        "input_schema": {
            "type": "object",
            "properties": {
                "interactive_only": {"type": "boolean", "description": "If true, only show interactive elements (buttons, links, inputs). Default false.", "default": False}
            }
        }
    },
    {
        "name": "browser_get_text",
        "description": "Extract text content from an element. Use to read specific content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector to extract text from"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_get_value",
        "description": "Get the current value of an input field. Useful for reading what's already entered in a form.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector for the input field"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_get_url",
        "description": "Get the current page URL. Useful for verifying navigation or checking query parameters.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_wait",
        "description": "Wait for an element to appear or for a specified duration. Use after navigation or clicking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector to wait for (optional)"},
                "ms": {"type": "integer", "description": "Milliseconds to wait (optional, default 1000)"}
            }
        }
    },
    {
        "name": "browser_hover",
        "description": "Hover over an element. Use to reveal dropdown menus, tooltips, or trigger hover effects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector to hover over - use @ref from snapshot"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page and get base64 image data. You already receive screenshots automatically, so only use this if you need to explicitly capture the current state.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_back",
        "description": "Go back to the previous page in browser history.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_forward",
        "description": "Go forward to the next page in browser history.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_reload",
        "description": "Reload the current page.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_select",
        "description": "Select an option from a dropdown menu.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector for the select/dropdown element"},
                "value": {"type": "string", "description": "Value or text of the option to select"}
            },
            "required": ["selector", "value"]
        }
    },
    {
        "name": "browser_check",
        "description": "Check a checkbox or radio button.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector for the checkbox"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_uncheck",
        "description": "Uncheck a checkbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector for the checkbox"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_scrollintoview",
        "description": "Scroll a specific element into view. Use when you need to see a particular element that's off-screen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector to scroll into view"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_focus",
        "description": "Focus on an element. Useful before typing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector to focus"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_dblclick",
        "description": "Double-click an element.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector to double-click"}
            },
            "required": ["selector"]
        }
    },
]


class BrowserAgent:
    """Browser agent with vision-based ReAct loop.
    
    Uses Gemini Vision to analyze screenshots and execute browser commands.
    Similar to CodingAgent but for browser automation tasks.
    """
    
    def __init__(
        self,
        project_id: int,
        user_id: int,
        model: str = "gemini-2.5-flash",
        max_iterations: int = 30,
        temperature: float = 1.0,
    ) -> None:
        """Initialize browser agent.
        
        Args:
            project_id: Project ID for WebSocket broadcasting
            user_id: User ID
            model: Gemini model to use (must support vision)
            max_iterations: Maximum ReAct loop iterations
            temperature: LLM temperature
        """
        self.project_id = project_id
        self.user_id = user_id
        self.model = model
        self.max_iterations = max_iterations
        self.temperature = temperature
        
        self._llm = None
        self._connection_manager = None
        self._http_client = None
        
        # Browser session
        self.session_id: Optional[str] = None
        
        # Background streaming task
        self._stream_task: Optional[asyncio.Task] = None
        self._stop_stream = asyncio.Event()
        self._interaction_queue = asyncio.Queue()
        
        # Conversation history
        self.messages: List[BaseMessage] = []
    
    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        """Get LLM instance (lazy initialization)."""
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=settings.gemini_api_key,
                temperature=self.temperature,
                convert_system_message_to_human=False,
            )
        return self._llm
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get async HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client
    
    @property
    def connection_manager(self):
        """Get WebSocket connection manager (lazy load)."""
        if self._connection_manager is None:
            from app.api.websocket.connection_manager import connection_manager
            self._connection_manager = connection_manager
        return self._connection_manager
    
    async def _broadcast(self, message_type: str, data: Dict) -> None:
        """Broadcast message via WebSocket."""
        try:
            # Optimize: If we have local connections, send directly to avoid Redis overhead/issues
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
                # Fallback to Redis for cross-worker communication
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

    async def _create_session(self, initial_url: str = "https://google.com") -> str:
        """Create a new browser session."""
        response = await self.http_client.post(
            f"{BROWSER_AGENT_URL}/session",
            json={"initial_url": initial_url}
        )
        response.raise_for_status()
        data = response.json()
        self.session_id = data["session_id"]
        logger.info(f"Created browser session: {self.session_id}")
        
        # Store session_id in Redis for cross-worker access
        try:
            from app.api.websocket.redis_broadcaster import redis_broadcaster
            await redis_broadcaster.connect()
            session_key = f"browser_session:{self.project_id}"
            await redis_broadcaster._redis.set(session_key, self.session_id, ex=3600)  # Expires in 1 hour
            logger.info(f"Stored browser session {self.session_id} in Redis for project {self.project_id}")
        except Exception as e:
            logger.warning(f"Failed to store browser session in Redis: {e}")
        
        return self.session_id
    
    async def _get_screenshot(self) -> Dict[str, str]:
        """Get current screenshot as base64 with format usage."""
        try:
            response = await self.http_client.get(
                f"{BROWSER_AGENT_URL}/session/{self.session_id}/screenshot"
            )
            response.raise_for_status()
            data = response.json()
            
            # The browser-agent service returns 'image' key
            screenshot_b64 = data.get("image") or data.get("base64")
            
            if not screenshot_b64:
                logger.error("No image data in screenshot response")
                return None
            
            # Remove data URL prefix if present (e.g., "data:image/png;base64,")
            if screenshot_b64.startswith("data:"):
                screenshot_b64 = screenshot_b64.split(",", 1)[1]
            
            # Clean the base64 string - remove whitespace and newlines
            screenshot_b64 = screenshot_b64.replace('\n', '').replace('\r', '').replace(' ', '')
            
            # Verify it's valid base64 by trying to decode
            try:
                decoded = base64.b64decode(screenshot_b64)
                
                # Detect image type from signature
                if decoded.startswith(b'\x89PNG\r\n\x1a\n'):
                    mime_type = "image/png"
                elif decoded.startswith(b'\xff\xd8'):
                    mime_type = "image/jpeg"
                elif decoded.startswith(b'GIF87a') or decoded.startswith(b'GIF89a'):
                    mime_type = "image/gif"
                elif decoded.startswith(b'RIFF') and len(decoded) > 12 and decoded[8:12] == b'WEBP':
                    mime_type = "image/webp"
                else:
                    # If it's from screencast it's likely JPEG but might lack header in some logs
                    mime_type = "image/jpeg"
                
                # Return the clean base64 (already verified it decodes)
                return {"data": screenshot_b64, "mime_type": mime_type}
                
            except Exception as e:
                logger.error(f"Failed to decode base64 image: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get screenshot: {e}")
            return None

    async def _stream_frames(self):
        """Background task to stream frames and send interactions."""
        # Use browser-agent hostname which is correct within Docker network
        # For local dev without Docker, this might need adjustment unless mapped in /etc/hosts
        ws_url = BROWSER_AGENT_URL.replace("http://", "ws://") + f"/stream?session={self.session_id}"
        
        logger.info(f"Starting browser stream listener for session {self.session_id} at {ws_url}")
        
        retry_count = 0
        max_retries = 5
        
        while not self._stop_stream.is_set():
            try:
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20, max_size=10*1024*1024) as ws:
                    logger.info(f"Connected to browser stream: {self.session_id}")
                    retry_count = 0  # Reset retries on successful connection
                    
                    # Nested task to send user interactions back to the browser-agent service
                    async def sender():
                        while not self._stop_stream.is_set():
                            try:
                                payload = await asyncio.wait_for(self._interaction_queue.get(), timeout=0.1)
                                if payload:
                                    if payload.get("type") == "set_viewport":
                                        logger.info(f"Sending viewport change to browser service: {payload}")
                                    await ws.send(json.dumps(payload))
                            except asyncio.TimeoutError:
                                continue
                            except Exception as e:
                                logger.warning(f"Error sending browser interaction: {e}")
                                break
                    
                    sender_task = asyncio.create_task(sender())
                    
                    request_count = 0
                    last_log_time = datetime.now()
                    
                    while not self._stop_stream.is_set():
                        try:
                            # Use short timeout to check stop event periodically
                            message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            data = json.loads(message)
                            
                            if data.get("type") == "browser_frame":
                                request_count += 1
                                # Log every 100 frames or 5 seconds to avoid spam but confirm activity
                                if request_count % 100 == 0 or (datetime.now() - last_log_time).total_seconds() > 5:
                                    logger.debug(f"Forwarding frame {request_count} for session {self.session_id}")
                                    last_log_time = datetime.now()
                                
                                # Sanitize base64 data to ensure frontend can decode it
                                image_data = data["image"]
                                if image_data:
                                    # Remove data URL prefix if present
                                    if image_data.startswith("data:"):
                                        image_data = image_data.split(",", 1)[1]
                                    # Remove whitespace/newlines which might break Dart's decoder
                                    image_data = image_data.replace('\n', '').replace('\r', '').replace(' ', '')

                                    # Proxy frame directly to frontend using optimized broadcast
                                    await self._broadcast("browser_frame", {
                                        "image": image_data,
                                        "format": data.get("format", "jpeg")
                                    })
                            elif data.get("type") == "browser_url_changed":
                                # Forward URL change to frontend
                                await self._broadcast("browser_url_changed", {
                                    "url": data.get("url", "")
                                })
                            elif data.get("type") == "viewport_changed":
                                # Forward viewport change notification as a browser status message
                                await self._broadcast("agent_response", {
                                    "message": data.get("message", "Viewport changed")
                                })
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            if not self._stop_stream.is_set():
                                logger.warning("Browser stream connection closed by server")
                            break
                    
                    sender_task.cancel()
                    try:
                        await sender_task
                    except asyncio.CancelledError:
                        pass
                        
            except (OSError, websockets.exceptions.WebSocketException) as e:
                if not self._stop_stream.is_set():
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 30)
                    logger.warning(f"Browser stream connection error: {e}. Retrying in {wait_time}s (attempt {retry_count})")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error in stream loop: {e}")
                if not self._stop_stream.is_set():
                    await asyncio.sleep(5)
        
        logger.info(f"Browser stream listener stopped for session {self.session_id}")

    async def _get_snapshot(self, interactive_only: bool = False) -> Dict:
        """Get accessibility snapshot with element refs."""
        params = {}
        if interactive_only:
            params['interactive_only'] = 'true'
        
        response = await self.http_client.get(
            f"{BROWSER_AGENT_URL}/session/{self.session_id}/snapshot",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def _execute_command(self, command: str, args: Dict) -> Dict:
        """Execute a browser command via the browser-agent service."""
        response = await self.http_client.post(
            f"{BROWSER_AGENT_URL}/session/{self.session_id}/command",
            json={"command": command, "args": args}
        )
        response.raise_for_status()
        return response.json()
    
    async def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        """Execute a browser tool and return result string."""
        
        # Handle snapshot separately as it needs special processing
        if tool_name == "browser_snapshot":
            try:
                interactive_only = tool_args.get("interactive_only", False)
                
                # Pass interactive_only as query parameter
                snapshot = await self._get_snapshot(interactive_only=interactive_only)
                snapshot_text = snapshot.get("data", {}).get("snapshot", str(snapshot))
                
                # Truncate if too long
                # if len(snapshot_text) > 8000:
                #     snapshot_text = snapshot_text[:8000] + "\n... (truncated)"
                
                return f"Accessibility snapshot (use @refs to click elements):\n{snapshot_text}"
            except Exception as e:
                return f"Failed to get snapshot: {e}"
        
        # Command mapping - Python tool names to backend command names
        command_map = {
            "browser_navigate": "navigate",
            "browser_click": "click",
            "browser_fill": "fill",
            "browser_type": "type",
            "browser_press": "press",
            "browser_scroll": "scroll",
            "browser_wait": "wait",
            "browser_get_text": "get_text",
            "browser_get_value": "get_value",
            "browser_get_url": "get_url",
            "browser_hover": "hover",
            "browser_screenshot": "screenshot",
            "browser_back": "back",
            "browser_forward": "forward",
            "browser_reload": "reload",
            "browser_select": "select",
            "browser_check": "check",
            "browser_uncheck": "uncheck",
            "browser_scrollintoview": "scrollintoview",
            "browser_focus": "focus",
            "browser_dblclick": "dblclick",
        }
        
        if tool_name not in command_map:
            return f"Unknown tool: {tool_name}"
        
        command = command_map[tool_name]
        
        try:
            # Execute the command - backend handles all argument mapping
            result = await self._execute_command(command, tool_args)
            
            # Brief delay for page to update after action
            await asyncio.sleep(0.5)
            
            # Format response based on command type for better agent understanding
            if command == "get_text":
                data = result.get("result", {}).get("data", result.get("data", ""))
                return f"Text content: {data}"
            elif command == "get_value":
                data = result.get("result", {}).get("data", result.get("data", ""))
                return f"Input value: {data}"
            elif command == "get_url":
                data = result.get("result", {}).get("data", result.get("data", ""))
                return f"Current URL: {data}"
            elif command == "screenshot":
                return f"Screenshot captured successfully"
            elif command == "navigate":
                return f"Navigated to {tool_args.get('url')}"
            elif command == "click":
                return f"Clicked element: {tool_args.get('selector')}"
            elif command == "fill":
                return f"Filled element {tool_args.get('selector')} with text"
            elif command == "type":
                return f"Typed text into element: {tool_args.get('selector')}"
            elif command == "hover":
                return f"Hovered over element: {tool_args.get('selector')}"
            elif command == "scroll":
                return f"Scrolled {tool_args.get('direction')} by {tool_args.get('amount', 500)}px"
            elif command == "press":
                return f"Pressed key: {tool_args.get('key')}"
            elif command == "wait":
                if tool_args.get('selector'):
                    return f"Waited for element: {tool_args.get('selector')}"
                else:
                    return f"Waited for {tool_args.get('ms', 1000)}ms"
            elif command == "back":
                return "Navigated back to previous page"
            elif command == "forward":
                return "Navigated forward to next page"
            elif command == "reload":
                return "Page reloaded"
            elif command == "select":
                return f"Selected '{tool_args.get('value')}' in dropdown: {tool_args.get('selector')}"
            elif command == "check":
                return f"Checked checkbox: {tool_args.get('selector')}"
            elif command == "uncheck":
                return f"Unchecked checkbox: {tool_args.get('selector')}"
            elif command == "scrollintoview":
                return f"Scrolled element into view: {tool_args.get('selector')}"
            elif command == "focus":
                return f"Focused element: {tool_args.get('selector')}"
            elif command == "dblclick":
                return f"Double-clicked element: {tool_args.get('selector')}"
            else:
                return f"Action '{command}' completed successfully: {result}"
        except Exception as e:
            return f"Action '{command}' failed: {e}"

    async def handle_interaction(self, interaction: Dict) -> None:
        """Handle user interaction from frontend."""
        if not self.session_id:
            logger.warning("Interaction received but no active session")
            return
        
        # Queue the interaction to be sent via WebSocket stream
        await self._interaction_queue.put(interaction['payload'])
        
        await self._interaction_queue.put(interaction)

    def _convert_tools_to_langchain_format(self) -> List[Dict[str, Any]]:
        """Convert tool definitions to LangChain format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in BROWSER_TOOLS
        ]
    
    def _extract_tool_calls(self, response: AIMessage) -> List[Dict[str, Any]]:
        """Extract tool calls from AI response."""
        tool_calls = []
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls.append({
                    "id": tc.get("id", f"call_{len(tool_calls)}"),
                    "name": tc.get("name"),
                    "args": tc.get("args", {}),
                })
        
        return tool_calls
    
    async def run(self, user_message: str, initial_url: str = "https://google.com") -> str:
        """Run the browser agent with a user message.
        
        Args:
            user_message: User's request (e.g., "Search for Python tutorials")
            initial_url: Starting URL for the browser
            
        Returns:
            Final response text with results
        """
        logger.info(f"Starting browser agent for project {self.project_id}")
        
        # Create browser session if needed
        if not self.session_id:
            try:
                await self._create_session(initial_url)
                
                # Start background streaming task
                self._stop_stream.clear()
                self._stream_task = asyncio.create_task(self._stream_frames())
                
            except Exception as e:
                error_msg = f"Failed to create browser session: {e}"
                logger.error(error_msg)
                await self._broadcast("agent_status", {"status": "error", "message": error_msg})
                return error_msg
        
        await self._broadcast("agent_status", {"status": "started", "message": "Starting browser agent..."})
        
        # Get initial screenshot
        screenshot_data = None
        try:
            screenshot_data = await self._get_screenshot()
        except Exception as e:
            error_msg = f"Failed to get initial screenshot: {e}"
            logger.error(error_msg)
            await self._broadcast("agent_status", {"status": "error", "message": error_msg})
            return error_msg
        
        if not screenshot_data:
            error_msg = "Failed to obtain valid initial screenshot"
            logger.error(error_msg)
            await self._broadcast("agent_status", {"status": "error", "message": error_msg})
            return error_msg
            
        screenshot_b64 = screenshot_data["data"]
        mime_type = screenshot_data["mime_type"]
        
        # Broadcast initial frame for Flutter UI
        # Extract format from mime_type (image/png -> png)
        img_format = mime_type.split('/')[-1] if '/' in mime_type else 'png'
        await self._broadcast("browser_frame", {"image": screenshot_b64, "format": img_format})
        
        # Build initial message with image for vision model
        image_bytes = base64.b64decode(screenshot_b64)

        initial_content = [
            {"type": "text", "text": f"User request: {user_message}\n\nHere's the current browser view:"},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{screenshot_b64}"
                }
            }
        ]
        
        self.messages = [
            SystemMessage(content=BROWSER_SYSTEM_PROMPT),
            HumanMessage(content=initial_content),
        ]
        
        # Convert tools to LangChain format
        tool_schemas = self._convert_tools_to_langchain_format()
        
        iteration = 0
        final_response = ""
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Browser agent iteration {iteration}")
            
            try:
                # Call LLM with tools
                llm_with_tools = self.llm.bind_tools(tool_schemas)
                response = await llm_with_tools.ainvoke(self.messages)
                self.messages.append(response)
                
                logger.info(f"Browser agent response: {response.content[:200] if response.content else 'No content'}...")
                
                # Extract tool calls
                tool_calls = self._extract_tool_calls(response)
                
                if not tool_calls:
                    # No tool calls - agent is done
                    if isinstance(response.content, str):
                        final_response = response.content
                    elif isinstance(response.content, list):
                        final_response = " ".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in response.content
                        )
                    else:
                        final_response = str(response.content)
                    
                    logger.info(f"Browser agent completed after {iteration} iterations")
                    break
                
                # Execute tools
                for tc in tool_calls:
                    tool_name = tc.get("name")
                    tool_args = tc.get("args", {})
                    tool_id = tc.get("id", f"call_{iteration}")
                    
                    # Broadcast tool execution
                    await self._broadcast("tool_execution", {
                        "tool": tool_name,
                        "message": f"Executing {tool_name}...",
                        "input": tool_args,
                    })
                    
                    logger.info(f"Executing browser tool: {tool_name} with args: {tool_args}")
                    
                    # Execute the tool
                    result = await self._execute_tool(tool_name, tool_args)
                    
                    # Broadcast tool result
                    await self._broadcast("tool_result", {
                        "tool": tool_name,
                        "result": result[:500] if len(result) > 500 else result,
                    })
                    logger.info(f"=====AGENT BROWSER==== Tool result: {result}")
                    # Append tool result (text only)
                    self.messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                
                # Get updated screenshot after all tool executions
                try:
                    screenshot_data = await self._get_screenshot()
                    
                    if screenshot_data:
                        screenshot_b64 = screenshot_data["data"]
                        mime_type = screenshot_data["mime_type"]
                        img_format = mime_type.split('/')[-1] if '/' in mime_type else 'png'
                        
                        await self._broadcast("browser_frame", {"image": screenshot_b64, "format": img_format})
                        
                        # Add screenshot as a separate HumanMessage 
                        # This avoids putting images in ToolMessage which some providers/adapters reject
                        screen_msg_content = [
                            {"type": "text", "text": "Here is the browser view after the actions:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{screenshot_b64}"
                                }
                            }
                        ]
                        self.messages.append(HumanMessage(content=screen_msg_content))
                    else:
                        logger.warning("Screenshot failed validation after tool execution")
                        # Add a text message indicating failure, so agent knows
                        self.messages.append(HumanMessage(content="[System] Failed to capture valid screenshot after actions."))
                        
                except Exception as e:
                    logger.warning(f"Failed to get screenshot after tools: {e}")
                    self.messages.append(HumanMessage(content=f"[System] Failed to capture screenshot: {str(e)}"))
                
            except Exception as e:
                error_msg = f"Error in iteration {iteration}: {e}"
                logger.error(error_msg)
                await self._broadcast("agent_status", {"status": "error", "message": str(e)})
                
                # Add error so agent can recover
                self.messages.append(HumanMessage(content=f"Error: {e}. Try a different approach."))
        
        if iteration >= self.max_iterations:
            logger.warning(f"Browser agent reached max iterations ({self.max_iterations})")
            final_response = "I've reached the maximum number of steps. Here's what I was able to accomplish."
        
        # Send final response
        await self._broadcast("agent_response", {"message": final_response})
        await self._broadcast("agent_status", {"status": "completed", "message": "Browser task completed!"})
        
        return final_response
    
    async def close(self) -> None:
        """Close browser session and cleanup resources."""
        # Stop background stream
        self._stop_stream.set()
        if self._stream_task:
            try:
                await asyncio.wait_for(self._stream_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._stream_task.cancel()
            except Exception as e:
                logger.warning(f"Error stopping stream task: {e}")
        
        # Clean up Redis session tracking
        try:
            from app.api.websocket.redis_broadcaster import redis_broadcaster
            await redis_broadcaster.connect()
            session_key = f"browser_session:{self.project_id}"
            await redis_broadcaster._redis.delete(session_key)
            logger.debug(f"Cleaned up browser session from Redis for project {self.project_id}")
        except Exception as e:
            logger.warning(f"Failed to clean up Redis session: {e}")
        
        if self.session_id:
            try:
                await self.http_client.delete(f"{BROWSER_AGENT_URL}/session/{self.session_id}")
                logger.info(f"Closed browser session: {self.session_id}")
            except Exception as e:
                logger.warning(f"Failed to close session: {e}")
        
        if self._http_client:
            await self._http_client.aclose()


async def run_browser_agent(
    user_message: str,
    project_id: int,
    user_id: int,
    initial_url: str = "https://google.com",
) -> str:
    """Convenience function to run the browser agent.
    
    Args:
        user_message: User's request message
        project_id: Project ID
        user_id: User ID
        initial_url: Starting URL for the browser
        
    Returns:
        Agent's final response
    """
    agent = BrowserAgent(project_id=project_id, user_id=user_id)
    try:
        return await agent.run(user_message, initial_url)
    finally:
        await agent.close()
