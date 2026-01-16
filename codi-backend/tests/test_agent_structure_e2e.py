"""E2E Tests for the simplified coding agent."""
import pytest
from pathlib import Path

from app.agent.agent import CodingAgent
from app.agent.tools import AgentContext, read_file, write_file, edit_file, list_files, search_files


@pytest.mark.asyncio
async def test_agent_context(tmp_path: Path):
    """Test AgentContext creation."""
    project_path = tmp_path / "test-project"
    project_path.mkdir(parents=True, exist_ok=True)
    
    context = AgentContext(
        project_id=1,
        user_id=1,
        project_folder=str(project_path),
    )
    
    assert context.project_id == 1
    assert context.project_folder == str(project_path)


@pytest.mark.asyncio
async def test_read_file_tool(tmp_path: Path):
    """Test read_file tool."""
    project_path = tmp_path / "test-project"
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Create a test file
    test_file = project_path / "test.py"
    test_file.write_text("print('Hello World')\n")
    
    context = AgentContext(
        project_id=1,
        user_id=1,
        project_folder=str(project_path),
    )
    
    result = read_file("test.py", context)
    assert "Hello World" in result
    assert "1 |" in result  # Line numbers


@pytest.mark.asyncio
async def test_write_file_tool(tmp_path: Path):
    """Test write_file tool."""
    project_path = tmp_path / "test-project"
    project_path.mkdir(parents=True, exist_ok=True)
    
    context = AgentContext(
        project_id=1,
        user_id=1,
        project_folder=str(project_path),
    )
    
    result = write_file("new_file.py", "print('Created')\n", context)
    assert "Successfully wrote" in result
    
    # Verify file exists
    assert (project_path / "new_file.py").exists()


@pytest.mark.asyncio
async def test_edit_file_tool(tmp_path: Path):
    """Test edit_file tool."""
    project_path = tmp_path / "test-project"
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Create file to edit
    test_file = project_path / "edit_me.py"
    test_file.write_text("old_value = 1\n")
    
    context = AgentContext(
        project_id=1,
        user_id=1,
        project_folder=str(project_path),
    )
    
    result = edit_file("edit_me.py", "old_value = 1", "new_value = 2", context)
    assert "Successfully edited" in result
    
    # Verify edit
    content = test_file.read_text()
    assert "new_value = 2" in content


@pytest.mark.asyncio
async def test_list_files_tool(tmp_path: Path):
    """Test list_files tool."""
    project_path = tmp_path / "test-project"
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Create some files
    (project_path / "file1.py").write_text("# file 1\n")
    (project_path / "file2.py").write_text("# file 2\n")
    
    context = AgentContext(
        project_id=1,
        user_id=1,
        project_folder=str(project_path),
    )
    
    result = list_files(context, ".")
    assert "file1.py" in result
    assert "file2.py" in result


@pytest.mark.asyncio
async def test_search_files_tool(tmp_path: Path):
    """Test search_files tool."""
    project_path = tmp_path / "test-project"
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Create files with searchable content
    (project_path / "a.py").write_text("def hello_world():\n    pass\n")
    (project_path / "b.py").write_text("def goodbye():\n    pass\n")
    
    context = AgentContext(
        project_id=1,
        user_id=1,
        project_folder=str(project_path),
    )
    
    result = search_files("hello_world", context)
    assert "a.py" in result
    assert "hello_world" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
