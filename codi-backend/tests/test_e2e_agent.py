"""
True End-to-End Tests for Codi Agent

These tests simulate real frontend usage:
1. Create a project via API
2. Submit tasks via WebSocket (like frontend)
3. Wait for real LLM responses
4. Use LLM to validate the results

Run with: pytest tests/test_e2e_agent.py -v -s
"""
import asyncio
import json
import os
import pytest
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx
from websockets import connect as ws_connect

# Test configuration
API_BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
WS_BASE_URL = os.getenv("TEST_WS_URL", "ws://localhost:8000")
TEST_REPOS_ROOT = Path(__file__).parent.parent / "test_repos"
os.environ["CODI_REPOS_PATH"] = str(TEST_REPOS_ROOT)
TEST_TIMEOUT = 120  # 2 minutes for LLM operations


class LLMValidator:
    """Uses an LLM to validate test results."""
    
    def __init__(self):
        from langchain_google_genai import ChatGoogleGenerativeAI
        from app.core.config import settings
        
        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0,
        )
    
    async def validate(self, task: str, result: str, criteria: str) -> tuple[bool, str]:
        """
        Use LLM to validate if the result meets the criteria.
        
        Returns:
            tuple of (passed: bool, explanation: str)
        """
        prompt = f"""You are a test validator. Evaluate if the following result meets the success criteria.

TASK: {task}

RESULT:
{result}

SUCCESS CRITERIA: {criteria}

Respond in this exact JSON format:
{{"passed": true/false, "explanation": "brief explanation of why it passed or failed"}}

Be strict but fair. Only respond with the JSON, nothing else."""

        response = await asyncio.to_thread(
            self.llm.invoke, prompt
        )
        
        try:
            # Parse the JSON response
            content = response.content
            if isinstance(content, list):
                # Join parts if it's a list
                content = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in content])
            
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result_json = json.loads(content)
            return result_json["passed"], result_json["explanation"]
        except Exception as e:
            return False, f"Failed to parse LLM validation response: {e}"


class E2ETestClient:
    """Client that mimics frontend behavior."""
    
    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None
        self.token: Optional[str] = None
        self.project_id: Optional[int] = None
        self.messages: list[dict] = []
        
    async def setup(self):
        """Initialize HTTP client."""
        self.http_client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)
    
    async def teardown(self):
        """Cleanup resources."""
        if self.http_client:
            await self.http_client.aclose()
    
    async def create_test_user_and_project(self, project_name: str) -> dict:
        """
        Create a test user and project.
        For E2E tests, we need to either:
        1. Use a pre-existing test account
        2. Create one via the auth flow
        
        For now, we'll create the project directly in the database.
        """
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.core.config import settings
        from app.models.user import User
        from app.models.project import Project
        
        # Override database URL for host access to docker container
        # Use credentials and port from docker-compose
        db_url = "postgresql+asyncpg://codi:codi_password@localhost:5433/codi_db"
        engine = create_async_engine(db_url)
        AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with AsyncSessionLocal() as session:
            # Clear legacy operation logs that might cause enum errors
            from app.models.operation_log import OperationLog
            from sqlalchemy import delete
            await session.execute(delete(OperationLog))
            await session.commit()
            
            # Create or get test user
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.github_username == "e2e_test_user")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    github_id=999999,
                    github_username="e2e_test_user",
                    email="e2e@test.com",
                    name="E2E Test User",
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            # Generate a unique project slug
            slug = f"{project_name.lower().replace(' ', '-')}-{datetime.now().strftime('%H%M%S')}"
            
            # Create project
            project = Project(
                name=project_name,
                description="E2E Test Project",
                owner_id=user.id,
                framework="custom",
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            
            # Create project folder
            project_path = TEST_REPOS_ROOT / str(user.id) / slug
            project_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize with a basic file
            (project_path / "README.md").write_text(f"# {project_name}\n\nTest project for E2E testing.\n")
            
            # Update project with local path (from container perspective)
            # Both API and Celery Worker see the project root as /app
            project.local_path = f"/app/test_repos/{user.id}/{slug}"
            await session.commit()
            
            self.project_id = project.id
            
            # Generate a test token
            from app.utils.security import create_access_token
            self.token = create_access_token(data={"sub": str(user.id), "user_id": user.id})
            
            return {
                "user_id": user.id,
                "project_id": project.id,
                "project_path": str(project_path),
                "token": self.token,
            }
        
    async def send_message_via_websocket(self, message: str) -> list[dict]:
        """
        Send a message via WebSocket and collect all responses.
        This mimics exactly what the frontend does.
        """
        ws_url = f"{WS_BASE_URL}/api/v1/agents/{self.project_id}/ws?token={self.token}"
        
        responses = []
        
        async with ws_connect(ws_url) as websocket:
            # Send the user message
            await websocket.send(json.dumps({
                "type": "user_message",
                "message": message,
            }))
            
            # Collect responses until completion or timeout
            start_time = asyncio.get_event_loop().time()
            completed = False
            has_content_response = False
            
            while not (completed and has_content_response):
                try:
                    # Wait for message with timeout
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=TEST_TIMEOUT
                    )
                    data = json.loads(response)
                    responses.append(data)
                    
                    # Debug log
                    msg_type = data.get("type", "")
                    status = data.get("status", "")
                    print(f"  [WS] Received: {msg_type} (status: {status})")
                    
                    # Check for completion signals
                    if msg_type == "agent_error":
                        completed = True
                        has_content_response = True # Errors are content
                    elif msg_type == "conversational_response":
                        completed = True
                        has_content_response = True
                    elif msg_type == "agent_response":
                        has_content_response = True
                    elif msg_type == "agent_status" and status in ["completed", "failed"]:
                        completed = True
                    elif msg_type == "deployment_complete":
                        completed = True
                        has_content_response = True
                    
                    # Safety break: If we got a status 'completed' but no response for 5 seconds, give up
                    if completed and not has_content_response:
                        try:
                            # Short poll for any trailing message
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            data = json.loads(response)
                            responses.append(data)
                            if data.get("type") in ["agent_response", "conversational_response"]:
                                has_content_response = True
                        except asyncio.TimeoutError:
                            print("  [WS] Timeout waiting for content after completion status")
                            break
                    
                    # Safety timeout for the whole loop
                    if asyncio.get_event_loop().time() - start_time > TEST_TIMEOUT:
                        print("  [WS] Overall timeout reached")
                        break
                        
                except asyncio.TimeoutError:
                    print("  [WS] Timeout waiting for message")
                    break
        
        self.messages = responses
        return responses


@pytest.fixture
async def test_client():
    """Fixture to create and cleanup test client."""
    client = E2ETestClient()
    await client.setup()
    yield client
    await client.teardown()


@pytest.fixture
def llm_validator():
    """Fixture for LLM validator."""
    return LLMValidator()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_conversational_message(test_client: E2ETestClient, llm_validator: LLMValidator):
    """
    Test: Send a conversational message and get a response.
    
    This tests the basic chat functionality without file operations.
    """
    # Setup
    setup = await test_client.create_test_user_and_project("E2E Chat Test")
    
    # Send a simple conversational message
    task = "What is the capital of France?"
    responses = await test_client.send_message_via_websocket(task)
    
    # Find the response message
    response_text = ""
    for msg in responses:
        if msg.get("type") in ["conversational_response", "agent_response"]:
            response_text = msg.get("message", "")
            break
    
    # Use LLM to validate
    passed, explanation = await llm_validator.validate(
        task=task,
        result=response_text,
        criteria="The response should mention 'Paris' as the capital of France"
    )
    
    assert passed, f"LLM Validation failed: {explanation}"
    print(f"✅ Test passed: {explanation}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_create_file(test_client: E2ETestClient, llm_validator: LLMValidator):
    """
    Test: Ask the agent to create a Python file.
    
    This tests the file creation capability.
    """
    setup = await test_client.create_test_user_and_project("E2E File Creation")
    project_path = Path(setup["project_path"])
    
    # Ask agent to create a file
    task = "Create a Python file called hello.py that prints 'Hello, World!'"
    responses = await test_client.send_message_via_websocket(task)
    
    # Check if file was created
    hello_file = project_path / "hello.py"
    file_exists = hello_file.exists()
    file_content = hello_file.read_text() if file_exists else ""
    
    # Collect all message types received
    message_types = [msg.get("type") for msg in responses]
    
    result = f"""
File exists: {file_exists}
File content: {file_content}
Messages received: {message_types}
"""
    
    # Use LLM to validate
    passed, explanation = await llm_validator.validate(
        task=task,
        result=result,
        criteria="A file called hello.py should exist and contain code that prints 'Hello, World!'"
    )
    
    assert passed, f"LLM Validation failed: {explanation}"
    print(f"✅ Test passed: {explanation}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_edit_file(test_client: E2ETestClient, llm_validator: LLMValidator):
    """
    Test: Ask the agent to edit an existing file.
    
    This tests the file editing capability.
    """
    setup = await test_client.create_test_user_and_project("E2E File Edit")
    project_path = Path(setup["project_path"])
    
    # Create a file to edit
    test_file = project_path / "greeting.py"
    test_file.write_text('message = "Hello"\nprint(message)\n')
    
    # Ask agent to edit the file
    task = 'In greeting.py, change the message from "Hello" to "Goodbye"'
    responses = await test_client.send_message_via_websocket(task)
    
    # Check the result
    file_content = test_file.read_text()
    
    result = f"""
File content after edit:
{file_content}
"""
    
    # Use LLM to validate
    passed, explanation = await llm_validator.validate(
        task=task,
        result=result,
        criteria='The file should now contain "Goodbye" instead of "Hello"'
    )
    
    assert passed, f"LLM Validation failed: {explanation}"
    print(f"✅ Test passed: {explanation}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_list_files(test_client: E2ETestClient, llm_validator: LLMValidator):
    """
    Test: Ask the agent what files exist in the project.
    
    This tests the file listing and understanding capability.
    """
    setup = await test_client.create_test_user_and_project("E2E List Files")
    project_path = Path(setup["project_path"])
    
    # Create some files
    (project_path / "app.py").write_text("# Main app\n")
    (project_path / "utils.py").write_text("# Utilities\n")
    (project_path / "config.json").write_text('{"debug": true}\n')
    
    # Ask agent about the files
    task = "What files are in this project? List them for me."
    responses = await test_client.send_message_via_websocket(task)
    
    # Get the response
    response_text = ""
    for msg in responses:
        if msg.get("type") in ["conversational_response", "agent_response"]:
            response_text = msg.get("message", "")
            break
    
    result = f"Agent response: {response_text}"
    
    # Use LLM to validate
    passed, explanation = await llm_validator.validate(
        task=task,
        result=result,
        criteria="The response should mention app.py, utils.py, config.json, and README.md"
    )
    
    assert passed, f"LLM Validation failed: {explanation}"
    print(f"✅ Test passed: {explanation}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multi_step_task(test_client: E2ETestClient, llm_validator: LLMValidator):
    """
    Test: Ask the agent to perform a multi-step task.
    
    This tests the agent's ability to plan and execute multiple operations.
    """
    setup = await test_client.create_test_user_and_project("E2E Multi Step")
    project_path = Path(setup["project_path"])
    
    # Ask for a multi-step task
    task = """Create a simple Python calculator module with:
1. A file called calculator.py with add, subtract, multiply, divide functions
2. A file called test_calculator.py with basic tests for each function"""
    
    responses = await test_client.send_message_via_websocket(task)
    
    # Check results
    calc_file = project_path / "calculator.py"
    test_file = project_path / "test_calculator.py"
    
    calc_exists = calc_file.exists()
    test_exists = test_file.exists()
    calc_content = calc_file.read_text() if calc_exists else ""
    test_content = test_file.read_text() if test_exists else ""
    
    result = f"""
calculator.py exists: {calc_exists}
calculator.py content:
{calc_content}

test_calculator.py exists: {test_exists}
test_calculator.py content:
{test_content}
"""
    
    # Use LLM to validate
    passed, explanation = await llm_validator.validate(
        task=task,
        result=result,
        criteria="""
Both files should exist:
- calculator.py should have add, subtract, multiply, and divide functions
- test_calculator.py should have tests for these functions
"""
    )
    
    assert passed, f"LLM Validation failed: {explanation}"
    print(f"✅ Test passed: {explanation}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
