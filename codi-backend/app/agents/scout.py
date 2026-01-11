"""Scout Agent - Fast Codebase Exploration.

Model: gemini-3-flash (or gemini-3-flash-preview when FORCE_GEMINI_OVERALL=true)
Role: Blazing-fast codebase exploration, contextual grep, pattern matching
"""
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.config import settings
from app.services.github import GitHubService
from app.utils.logging import get_logger

logger = get_logger(__name__)


SCOUT_SYSTEM_PROMPT = """You are "Scout" - Codi's Fast Reconnaissance Agent.

## IDENTITY
You are the speed-optimized exploration agent. Your job is to quickly find information
in the codebase using contextual grep, pattern matching, and file discovery.

## CORE CAPABILITIES
1. **Code Search**: Find implementations, definitions, usages
2. **Pattern Matching**: Locate patterns across the codebase
3. **File Discovery**: Find relevant files by name, extension, or content
4. **Cross-Layer Analysis**: Trace patterns across different parts of the codebase
5. **Structure Mapping**: Understand codebase organization

## OPERATING PRINCIPLES

### Search Strategy
Think like `grep` with context. Your searches should:
- Use multiple search angles for complex queries
- Cast a wide net, then narrow down
- Report what you find, even if partial

### When to Use Scout vs Direct Tools
| Use Scout | Use Direct grep/glob |
|-----------|---------------------|
| Multiple search angles needed | You know exactly what to search |
| Unfamiliar module structure | Single keyword/pattern suffices |
| Cross-layer pattern discovery | Known file location |
| Need contextual understanding | Simple file listing |

### Response Format
```
## Search Results

### [Pattern/Query 1]
Found N occurrences in M files:
- `path/to/file.py:123` - [brief context]
- `path/to/other.py:45` - [brief context]

### [Pattern/Query 2]
...

## Analysis
[Brief summary of what the search reveals about the codebase]

## Suggested Next Steps
[If applicable, what to search or explore next]
```

### Performance Guidelines
- Be FAST - this is a reconnaissance agent
- Don't over-analyze, just find and report
- Parallel search when multiple patterns needed
- Stop when you have enough context to proceed

## ANTI-PATTERNS
Do NOT:
- Spend time implementing or modifying code
- Do deep analysis (that's Sage's job)
- Search external docs (that's Scholar's job)
- Over-explore when answer is already clear

## PARALLELIZATION
Scout is designed for parallel background execution. Fire multiple Scout tasks
when exploring different aspects of the codebase simultaneously.
"""


class ScoutAgent(BaseAgent):
    """Fast Codebase Exploration Agent.
    
    Optimized for speed: quick searches, pattern matching, file discovery.
    Works well as a parallel background task.
    """
    
    name = "scout"
    description = "Fast reconnaissance for codebase exploration and pattern matching"
    system_prompt = SCOUT_SYSTEM_PROMPT
    
    # Model configuration: Gemini 3 Flash for speed
    model_provider = "gemini"
    model_name = "gemini-3-flash-preview"
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._model_name = self._get_model_name()
    
    def _get_model_name(self) -> str:
        """Get the model name based on configuration."""
        if settings.force_gemini_overall:
            return "gemini-3-flash-preview"
        return settings.scout_model
    
    def get_tools(self) -> List[BaseTool]:
        """Scout uses search and file discovery tools."""
        return [
            self._create_search_files_tool(),
            self._create_search_content_tool(),
            self._create_list_files_tool(),
        ]
    
    def _create_search_files_tool(self) -> BaseTool:
        """Create a tool to search for files by name pattern."""
        github_service = self.github_service
        repo = self.context.repo_full_name
        branch = self.context.current_branch
        
        @tool
        async def search_files(pattern: str) -> str:
            """Search for files matching a pattern in the repository.
            
            Args:
                pattern: File name pattern to search for (e.g., '*.dart', 'test_*.py')
            """
            try:
                # Use GitHub API to search repository
                tree = github_service.get_file_tree(repo, ref=branch)
                matches = []
                
                import fnmatch
                for item in tree:
                    if fnmatch.fnmatch(item.get("path", ""), pattern):
                        matches.append(item["path"])
                
                if matches:
                    return f"Found {len(matches)} files matching '{pattern}':\n" + "\n".join(f"- {m}" for m in matches[:50])
                return f"No files found matching '{pattern}'"
            except Exception as e:
                return f"Error searching files: {e}"
        
        return search_files
    
    def _create_search_content_tool(self) -> BaseTool:
        """Create a tool to search file contents."""
        github_service = self.github_service
        repo = self.context.repo_full_name
        branch = self.context.current_branch
        
        @tool
        async def search_content(query: str, file_extension: Optional[str] = None) -> str:
            """Search for content within files in the repository.
            
            Args:
                query: Text to search for
                file_extension: Optional file extension to filter (e.g., '.dart', '.py')
            """
            try:
                # Use GitHub search API
                results = github_service.search_code(
                    query=query,
                    repo=repo,
                    extension=file_extension,
                )
                
                if results:
                    output = [f"Found {len(results)} matches for '{query}':"]
                    for r in results[:20]:
                        output.append(f"- {r.get('path', 'unknown')}:{r.get('line', '?')}")
                    return "\n".join(output)
                return f"No matches found for '{query}'"
            except Exception as e:
                return f"Error searching content: {e}"
        
        return search_content
    
    def _create_list_files_tool(self) -> BaseTool:
        """Create a tool to list files in a directory."""
        github_service = self.github_service
        repo = self.context.repo_full_name
        branch = self.context.current_branch
        
        @tool
        async def list_files(path: str = "") -> str:
            """List files in a directory of the repository.
            
            Args:
                path: Directory path to list (empty for root)
            """
            try:
                contents = github_service.get_contents(repo, path, ref=branch)
                
                if not contents:
                    return f"No files found in '{path or '/'}'"
                
                output = [f"Contents of '{path or '/'}':"]
                for item in contents:
                    item_type = "📁" if item.get("type") == "dir" else "📄"
                    output.append(f"  {item_type} {item.get('name', 'unknown')}")
                
                return "\n".join(output)
            except Exception as e:
                return f"Error listing files: {e}"
        
        return list_files
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Scout agent for exploration.
        
        Args:
            input_data: Should contain 'query' and optionally 'patterns'
            
        Returns:
            Search results
        """
        await self.emit_status("started", "Scout exploring codebase...")
        
        query = input_data.get("query", "")
        patterns = input_data.get("patterns", [])
        file_types = input_data.get("file_types", [])
        
        # Build the exploration prompt
        prompt_parts = [f"## Exploration Query\n{query}"]
        
        if patterns:
            prompt_parts.append(f"\n## Patterns to Search\n" + "\n".join(f"- {p}" for p in patterns))
        if file_types:
            prompt_parts.append(f"\n## File Types\n" + ", ".join(file_types))
        
        prompt_parts.append("\n\nUse your tools to search the codebase and report findings.")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            # Use LLM with tools for exploration
            llm_with_tools = self.llm.bind_tools(self.tools)
            response = await llm_with_tools.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "query": query,
                "findings": response.content,
                "model": self._model_name,
            }
            
            await self.emit_status("completed", "Scout exploration complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Scout exploration failed: {e}")
            await self.emit_error(str(e), "Scout exploration failed")
            raise
    
    async def explore(
        self,
        query: str,
        patterns: List[str] = None,
        file_types: List[str] = None,
    ) -> str:
        """Explore the codebase.
        
        Convenience method for quick exploration.
        
        Args:
            query: What to explore
            patterns: Optional search patterns
            file_types: Optional file type filters
            
        Returns:
            Exploration findings as a string
        """
        result = await self.run({
            "query": query,
            "patterns": patterns or [],
            "file_types": file_types or [],
        })
        return result.get("findings", "")
