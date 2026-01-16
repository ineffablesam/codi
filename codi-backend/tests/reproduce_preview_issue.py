import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import httpx
from websockets import connect as ws_connect

# Base URLs (adjust if needed)
API_BASE_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"
PROJECT_ID = 3
PROJECT_SLUG = "test-3-codi"
PREVIEW_URL = f"http://{PROJECT_SLUG}.codi.local"

async def get_initial_state():
    print(f"Checking initial state of {PREVIEW_URL}...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(PREVIEW_URL)
            print(f"Status: {resp.status_code}")
            return resp.text
        except Exception as e:
            print(f"Error getting initial state: {e}")
            return None

async def run_reproduction():
    # 1. Get initial state
    html = await get_initial_state()
    if html:
        if "Samuel" in html:
            print("Found 'Samuel' in initial HTML. We will change it to 'Codi Tester'.")
            target_text = "Codi Tester"
        else:
            print("Did not find 'Samuel'. We will change heading to 'Samuel Portfolio'.")
            target_text = "Samuel Portfolio"
    else:
        target_text = "Samuel Portfolio"

    # 2. Get token for project (using the DB trick since we are on the host)
    # We'll just use the E2E user if it exists or admin
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from app.models.user import User
    from app.utils.security import create_access_token

    db_url = "postgresql+asyncpg://codi:codi_password@localhost:5433/codi_db"
    engine = create_async_engine(db_url)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one()
        token = create_access_token(data={"sub": str(user.id), "user_id": user.id})
        print(f"Using token for user: {user.github_username}")

    # 3. Send message via WS
    ws_url = f"{WS_BASE_URL}/api/v1/agents/{PROJECT_ID}/ws?token={token}"
    message = f"Please change the main heading text to '{target_text}' and change the background 'blue' glow color to 'red'. Then commit and rebuild the preview."
    
    print(f"Sending message: {message}")
    
    async with ws_connect(ws_url) as websocket:
        await websocket.send(json.dumps({
            "type": "user_message",
            "message": message,
        }))
        
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=300)
                data = json.loads(response)
                msg_type = data.get("type")
                
                if msg_type == "agent_status":
                    print(f"  [Status] {data.get('message')} ({data.get('status')})")
                    if data.get("status") in ["completed", "failed"]:
                        break
                elif msg_type == "tool_execution":
                    tool = data.get('tool')
                    msg = data.get('message')
                    tool_input = data.get('input', {})
                    print(f"  [Tool] {tool}: {msg} (Input: {tool_input})")
                elif msg_type == "tool_result":
                    tool = data.get('tool')
                    result = data.get('result', '')
                    # Truncate result for console output
                    display_result = result[:200].replace('\n', ' ') + "..." if len(result) > 200 else result
                    print(f"  [Result] {tool}: {display_result}")
                elif msg_type == "deployment_complete":
                    print(f"  [Deploy] Deployment finished: {data.get('preview_url')}")
                elif msg_type == "agent_response":
                    print(f"  [Response] {data.get('message')}")
                elif msg_type == "agent_error":
                    print(f"  [Error] {data.get('message')}")
                    break
            except asyncio.TimeoutError:
                print("Timeout waiting for agent response")
                break

    # 4. Verify post-state
    print("Waiting 5 seconds for deployment to settle...")
    await asyncio.sleep(5)
    
    new_html = await get_initial_state()
    if new_html:
        if target_text in new_html:
            print(f"SUCCESS: Found '{target_text}' in new HTML!")
        else:
            print(f"FAILURE: Did not find '{target_text}' in new HTML.")
    else:
        print("FAILURE: Could not get new HTML.")

if __name__ == "__main__":
    # Add project root to sys.path
    project_root = str(Path(__file__).parent.parent)
    sys.path.append(project_root)
    
    asyncio.run(run_reproduction())
