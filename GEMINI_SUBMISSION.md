
<a href="https://youtu.be/MwM1N8Ch0u8" target="_blank">
  <img src="https://i.postimg.cc/rVFfs5zf/slide-0.png" alt="Watch Yelpable in action" width="100%"/>
</a>

**Team**: Samuel Philip  
**One-Liner**: Full-stack development on smartphones for 6 billion mobile-first users, powered entirely by Gemini 3.

---

## Problem

Current AI coding tools (Cursor, GitHub Copilot, Windsurf) require laptops and desktop IDEs. **6 billion people** access the internet primarily through mobile devices and are completely excluded from AI-assisted development. Students in bootcamps, builders in emerging markets, and anyone without access to powerful desktop hardware cannot use these tools.

## Solution

CODI brings Gemini 3 to smartphones:
- **AI App Builder**: Chat → Full-stack apps (Flutter, Next.js, React)
- **Browser Automation**: Gemini vision navigates websites, fills forms, extracts data
- **Instant Deployment**: Preview URLs in seconds

Everything runs server-side and streams to mobile devices in real-time.

<br>
<img src="https://i.postimg.cc/FNcV9TD9/Slide-1.webp" alt="slide-1" width="100%"/>
<img src="https://i.postimg.cc/tpPNXB2R/Slide-2.webp" alt="slide-2" width="100%"/>
<img src="https://i.postimg.cc/9CTYWLJc/slide-3.webp" alt="slide-3" width="100%"/>
<img src="https://i.postimg.cc/B4DBqmMf/Slide-4.webp" alt="slide-4" width="100%"/>


## Why Gemini 3?

### Speed + Intelligence Combination

- **Flash (gemini-3-flash-preview)**: Real-time tool execution (\<1s response), streaming to mobile
- **Pro (gemini-2.0-flash)**: Complex planning, architecture decisions (when depth matters)
- **Function Calling**: Orchestrates 11 development tools seamlessly
- **Long Context**: Understands entire codebases at once
- **Vision (gemini-2.5-computer-use)**: Browser automation via screenshot analysis

### Why Not Other Models

**GPT-4**: No vision-based computer use API, expensive at scale, slower for tool calling  
**Claude**: Strong on code, but no mobile-first streaming optimization, limited tool support  
**Gemini**: Unmatched speed-to-quality ratio for production AI coding, native function calling, computer use vision

## Demo Screens

|                                                                                                                                                                         |                                                                                                                                                                         |                                                                                                                                                                         |
| :---------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
| <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/sfS6FVBd/1.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/kM81rn2H/2.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/ZnrV6ckH/3.png"> |
| <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/prDqKZNJ/4.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/5ywn83cY/5.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/D0qB1gVz/6.png"> |
| <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/8chtLH8p/7.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/J7J6w1s9/8.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/j2zZyXVv/9.png"> |
| <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/QCp0cbLk/10.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/2y42nwp1/11.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/Y01bQ3c0/12.png"> |
| <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/ZnrV6ckT/13.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/PJGSL77J/14.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/nr83sWWM/15.png"> |
| <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/hvF2JYYB/16.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/gj9gw77p/17.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/wMKwtrrd/18.png"> |
| <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/FztTf66h/19.png"> | <img width="1604" alt="screen shot 2017-08-07 at 12 18 15 pm" src="https://i.postimg.cc/nr83sWPW/20.png"> |                                                                                                                                                                         |

## Architecture

### Gemini at the Core

```
User (Mobile) → WebSocket → FastAPI Backend → Gemini 3 → Tools → Code/Deploy
                              ↓                    ↓
                         Gemini Flash        Gemini Pro
                         (Tool Exec)         (Planning)
```

**Tech Stack:**

- **Backend**: FastAPI + PostgreSQL + Redis + Docker
- **Frontend**: Flutter (iOS/Android)
- **AI**: Gemini 3 Flash + Pro with function calling
- **Deploy**: Vercel, Docker previews, GitHub Pages

## How It Works

### 1. ReAct Agent Loop (Gemini-Powered)

```python
class CodingAgent:
    def __init__(self, model="gemini-3-flash-preview"):
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=1.0,  # Creative for code generation
            convert_system_message_to_human=False,
        )
        self.max_iterations = 50
```

**Flow:**

1. **User**: "Add login page to my Flutter app"
2. **Gemini (Flash)**: Reasons → Calls `write_file` tool → Creates `login_page.dart`
3. **Gemini**: Calls `edit_file` → Updates routing in `main.dart`
4. **Gemini**: Calls `docker_preview` → Deploys preview URL
5. **User**: Sees live app in 15 seconds

### 2. Function Calling (11 Tools)

**Tool Schema** (JSON format for Gemini):

```python
TOOLS = [
    {
        "name": "read_file",
        "description": "Read file contents with line numbers",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "offset": {"type": "integer"},
                "limit": {"type": "integer"}
            },
            "required": ["path"]
        }
    },
    # ... 10 more tools
]
```

**Tool Execution**:

```python
# Bind tools to Gemini model
llm_with_tools = self.llm.bind_tools(tool_schemas)
response = await llm_with_tools.ainvoke(messages)

# Extract function calls from response
for tool_call in response.tool_calls:
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    
    # Execute tool
    result = await execute_tool(tool_name, tool_args, context)
    
    # Send result back to Gemini
    messages.append(ToolMessage(content=result, tool_call_id=tool_id))
```

**Tools Gemini Uses:**

- `read_file`, `write_file`, `edit_file` - Code manipulation
- `run_bash` - Testing, building, npm install
- `git_commit` - Version control
- `docker_preview` - Instant deployment
- `serverpod_*` - Backend (models, APIs, migrations)

### 3. Streaming to Mobile

**WebSocket Streaming** (Real-time updates):

```python
async def _broadcast_tool_execution(self, tool_name: str, message: str):
    await self.connection_manager.broadcast_to_project(
        self.project_id,
        {
            "type": "tool_execution",
            "tool": tool_name,
            "message": f"Writing to {path}",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
```

**Optimizations for Mobile:**

- Token streaming (progressive rendering)
- JPEG compression for browser screenshots (60% quality for 30 FPS)
- Backpressure handling for slow networks

### 4. Browser Automation (Gemini Vision)

**Computer Use Agent** (Gemini 2.5):

```python
class ComputerUseAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-computer-use-preview-10-2025"
    
    async def run(self, user_message: str):
        # Capture screenshot (PNG for model)
        screenshot_png = await self._page.screenshot(type="png")
        
        # Send to Gemini with Computer Use tool
        config = types.GenerateContentConfig(
            tools=[
                types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER
                    )
                )
            ],
            thinking_config=types.ThinkingConfig(include_thoughts=True),
        )
        
        # Gemini analyzes screenshot and executes actions
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                Content(
                    role="user",
                    parts=[
                        Part(text=user_message),
                        Part.from_bytes(data=screenshot_png, mime_type="image/png")
                    ]
                )
            ],
            config=config,
        )
        
        # Execute actions (click, type, scroll)
        for part in response.candidates[0].content.parts:
            if part.function_call:
                await self._execute_action(part.function_call)
```

**What It Does:**

- Screenshots webpage → Gemini analyzes layout → Identifies elements → Executes actions
- Use cases: "Find cheapest flights NYC→Tokyo", "Download my transcript from portal"

**Mobile Streaming Optimization**:

```python
async def _stream_loop(self):
    """30 FPS streaming to mobile"""
    while not self._stop_requested:
        # Capture JPEG for mobile (fast)
        screenshot_bytes = await self._get_screenshot(format="jpeg", quality=60)
        
        # Broadcast frame
        await self._broadcast("browser_frame", {
            "image": base64.b64encode(screenshot_bytes).decode(),
            "format": "jpeg",
        })
        
        # 30 FPS = 33ms per frame
        await asyncio.sleep(0.033)
```

## Key Innovations

### 1. Flash/Pro Model Switching

**Flash (80% of tasks)**: Tool execution, chat, edits - speed critical  
**Pro (20% of tasks)**: Initial planning, complex debugging - depth critical

```python
# Flash for fast tool execution
agent = CodingAgent(model="gemini-3-flash-preview", temperature=1.0)

# Pro for status messages (creative, natural)
status_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
```

**Why This Works:**

- Flash: 0.5-1.5s latency → users see instant responses
- Pro: 2-5s latency when quality matters more than speed

### 2. Mobile-First Streaming

Gemini Flash's speed + WebSocket = real-time coding on 4G networks

**Optimizations:**

1. **Token streaming**: Partial responses render immediately
2. **JPEG compression**: 60% quality maintains clarity, 3x smaller than PNG
3. **30 FPS streaming**: Smooth browser automation feels native

### 3. Automatic Tracing (Production-Ready)

Every tool execution automatically traced with Opik:

```python
from opik import track

def track_tool(tool_name: str):
    def decorator(func: Callable):
        # Apply Opik cloud tracking
        opik_tracked_func = track(name=f"tool_{tool_name}")(func)
        
        async def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            try:
                result = await opik_tracked_func(*args, **kwargs)
                # Save to database for user-facing queries
                await _save_tool_trace_to_db(
                    tool_name=tool_name,
                    status='success',
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )
                return result
            except Exception as e:
                await _save_tool_trace_to_db(status='error', error=str(e))
                raise
        return wrapper
    return decorator

# Usage
@track_tool("write_file")
async def write_file_impl(path: str, content: str, context: AgentContext):
    # Implementation
    return f"Wrote {len(content)} bytes to {path}"
```

**Result**: Zero-overhead observability when disabled, automatic quality tracking when enabled.

## Real-World Impact

### Target Users

- Students in coding bootcamps (no laptop access)
- Developers in emerging markets (India, SE Asia, Africa)
- 6 billion mobile-first internet users

### Example Use Cases

**Student in Mumbai**: Practices Flutter during train commute  
**Entrepreneur in Lagos**: Builds delivery app MVP without technical co-founder  
**Freelancer in Manila**: Rapid prototypes for clients, shows live previews instantly

## Challenges Solved

### 1. Streaming Latency

**Challenge**: Mobile networks are slow, users need instant feedback  
**Solution**: Gemini Flash (0.5-1.5s) + chunked tokens + progressive UI

### 2. Context Management

**Challenge**: Agents forget previous conversations  
**Solution**: Gemini long context window + Mem0 vector memory

```python
async def _load_memories(self, user_message: str):
    memories = await self.mem0_service.search_memories(
        query=user_message,
        user_id=f"user_{self.context.user_id}_project_{self.context.project_id}",
        limit=10,
    )
    return "\n".join([f"- {m['content']}" for m in memories])
```

### 3. Tool Reliability

**Challenge**: Function calls fail with ambiguous schemas  
**Solution**: Clear JSON schemas + error handling + retry logic

### 4. Bandwidth

**Challenge**: Sending full-resolution screenshots crashes mobile  
**Solution**: JPEG compression (60% quality) + efficient prompts + caching

## What Makes This Special

**First mobile-first AI coding platform on Gemini 3**  
**Production-ready** (not a demo - full auth, projects, deployment)  
**Advanced Gemini features** (function calling, streaming, vision, dual models)  
**Massive market** (6B underserved mobile users)  
**Open source** (reusable for community)

## Try It
<a href="https://youtu.be/MwM1N8Ch0u8" target="_blank">
  <img src="https://i.postimg.cc/rVFfs5zf/slide-0.png" alt="Watch Yelpable in action" width="100%"/>
</a>

- **GitHub**: [github.com/ineffablesam/codi](https://github.com/ineffablesam/codi)

---

**Built with**: Gemini 3 Flash • Gemini Computer Use • Gemini 2.0 Flash • FastAPI • Flutter • Docker • PostgreSQL • Redis

---

## How to Test CODI Locally

### Prerequisites

- Docker Desktop installed and running
- Git installed
- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Quick Setup (5 minutes)

#### 1. Clone and Configure

```bash
git clone https://github.com/ineffablesam/codi.git
cd codi
```

#### 2. Configure Backend Environment

```bash
cd codi-backend
cp .env.example .env
```

Edit `codi-backend/.env` and add your keys:

```env
# Required: Get from https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: For Opik tracing (get from https://www.comet.com/signup)
OPIK_API_KEY=your_comet_opik_api_key_here
OPIK_WORKSPACE=codi

# Generate encryption key (run this command):
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your_fernet_key_here
```

#### 3. Configure Frontend Environment

```bash
cd ../codi_frontend
cp .env.example .env
```

Edit `codi_frontend/.env`:

```env
# Point to your local backend
API_BASE_URL=http://localhost:8000
```

#### 4. Start Backend (Automated)

```bash
cd ..
chmod +x codi.sh
./codi.sh
```

Select **Option 1: Start Backend** - this will automatically:
- Set up Docker network
- Start PostgreSQL, Redis, Qdrant (vector DB)
- Start FastAPI backend
- Start Celery workers
- Initialize database migrations

Wait until you see: `Backend started successfully.`

#### 5. Start Frontend

```bash
cd codi_frontend
flutter pub get
flutter run
```

Select your device (iOS simulator, Android emulator, or web browser).

### Verify Setup

1. **Backend health check**: Visit http://localhost:8000/docs (FastAPI Swagger UI)
2. **Create account**: In the Flutter app, sign up with GitHub OAuth or create account
3. **Create project**: Tap "New Project" → Select Flutter template
4. **Test AI chat**: Send message: "Add a button that says Hello World"
5. **View preview**: Gemini will write code, commit, and deploy preview URL

### Troubleshooting

**Docker issues**: Make sure Docker Desktop is running, then run `./codi.sh` → Option 8 (Setup Network)

**Port conflicts**: If port 8000 or 5432 is in use, stop conflicting services or modify `docker-compose.yml`

**Flutter errors**: Run `flutter clean && flutter pub get`

**Gemini API errors**: Verify your API key is correct in `codi-backend/.env`

---

*Making AI-assisted development accessible to the entire world, one smartphone at a time.*
