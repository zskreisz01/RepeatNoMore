"""Document search and manipulation tools for LLM function calling.

These tools allow the LLM to explore and edit documentation files
without requiring embeddings or vector databases.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Any, List, Dict

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def grep_files(pattern: str, directory: str = "", case_sensitive: bool = False) -> str:
    """
    Search for a pattern in documentation files using grep.

    Args:
        pattern: Regular expression pattern to search for
        directory: Subdirectory to search in (relative to docs root). Empty string searches all docs.
        case_sensitive: Whether the search should be case-sensitive

    Returns:
        String containing search results with file paths and matching lines
    """
    settings = get_settings()
    docs_path = Path(settings.docs_repo_path)

    search_path = docs_path / directory if directory else docs_path

    if not search_path.exists():
        return f"Error: Directory '{directory}' not found"

    try:
        # Build grep command
        cmd = ["grep", "-r", "-n"]  # recursive, with line numbers
        if not case_sensitive:
            cmd.append("-i")  # case-insensitive
        cmd.extend([pattern, str(search_path)])

        # Execute grep
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # Format results to be more readable
            lines = result.stdout.strip().split('\n')
            formatted = []
            for line in lines[:50]:  # Limit to 50 results
                # Make paths relative to docs root
                if str(docs_path) in line:
                    line = line.replace(str(docs_path) + '/', '')
                formatted.append(line)

            if len(lines) > 50:
                formatted.append(f"\n... and {len(lines) - 50} more results")

            return '\n'.join(formatted) if formatted else "No matches found"
        elif result.returncode == 1:
            return "No matches found"
        else:
            return f"Error: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "Error: Search timed out (pattern too broad?)"
    except Exception as e:
        logger.error("grep_files_failed", error=str(e))
        return f"Error: {str(e)}"


def find_files(pattern: str, directory: str = "") -> str:
    """
    Find files by name pattern in documentation.

    Args:
        pattern: File name pattern (supports wildcards like *.md)
        directory: Subdirectory to search in (relative to docs root)

    Returns:
        String containing list of matching file paths
    """
    settings = get_settings()
    docs_path = Path(settings.docs_repo_path)

    search_path = docs_path / directory if directory else docs_path

    if not search_path.exists():
        return f"Error: Directory '{directory}' not found"

    try:
        # Use glob to find matching files
        if '*' in pattern or '?' in pattern:
            matches = list(search_path.rglob(pattern))
        else:
            # Exact name match
            matches = list(search_path.rglob(f"*{pattern}*"))

        if not matches:
            return "No matching files found"

        # Format results as relative paths
        results = []
        for match in sorted(matches)[:100]:  # Limit to 100 results
            rel_path = match.relative_to(docs_path)
            results.append(str(rel_path))

        if len(matches) > 100:
            results.append(f"\n... and {len(matches) - 100} more files")

        return '\n'.join(results)

    except Exception as e:
        logger.error("find_files_failed", error=str(e))
        return f"Error: {str(e)}"


def read_file(file_path: str) -> str:
    """
    Read the contents of a documentation file.

    Args:
        file_path: Path to file relative to docs root

    Returns:
        String containing file contents
    """
    settings = get_settings()
    docs_path = Path(settings.docs_repo_path)

    full_path = docs_path / file_path

    if not full_path.exists():
        return f"Error: File '{file_path}' not found"

    if not full_path.is_file():
        return f"Error: '{file_path}' is not a file"

    # Security: ensure the path is within docs directory
    try:
        full_path.resolve().relative_to(docs_path.resolve())
    except ValueError:
        return f"Error: Access denied - path outside documentation directory"

    try:
        content = full_path.read_text(encoding='utf-8')

        # Add line numbers for easier reference
        lines = content.split('\n')
        numbered_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]

        return '\n'.join(numbered_lines)

    except UnicodeDecodeError:
        return f"Error: File '{file_path}' is not a text file"
    except Exception as e:
        logger.error("read_file_failed", file_path=file_path, error=str(e))
        return f"Error: {str(e)}"


def list_files(directory: str = "", include_subdirs: bool = True) -> str:
    """
    List files and directories in documentation.

    Args:
        directory: Directory to list (relative to docs root). Empty string lists root.
        include_subdirs: Whether to include subdirectories in the listing

    Returns:
        String containing directory listing
    """
    settings = get_settings()
    docs_path = Path(settings.docs_repo_path)

    target_path = docs_path / directory if directory else docs_path

    if not target_path.exists():
        return f"Error: Directory '{directory}' not found"

    if not target_path.is_dir():
        return f"Error: '{directory}' is not a directory"

    try:
        items = []

        # List immediate children
        for item in sorted(target_path.iterdir()):
            rel_path = item.relative_to(docs_path)
            if item.is_dir():
                items.append(f"[DIR]  {rel_path}/")
            else:
                size = item.stat().st_size
                items.append(f"[FILE] {rel_path} ({size} bytes)")

        if not items:
            return f"Directory '{directory or 'root'}' is empty"

        header = f"Contents of '{directory or 'root'}':\n" + "=" * 60 + "\n"
        return header + '\n'.join(items)

    except Exception as e:
        logger.error("list_files_failed", directory=directory, error=str(e))
        return f"Error: {str(e)}"


def edit_file(file_path: str, old_content: str, new_content: str) -> str:
    """
    Edit a documentation file by replacing old content with new content.

    Args:
        file_path: Path to file relative to docs root
        old_content: Exact content to replace (must match exactly)
        new_content: New content to insert

    Returns:
        String indicating success or error message
    """
    settings = get_settings()
    docs_path = Path(settings.docs_repo_path)

    full_path = docs_path / file_path

    if not full_path.exists():
        return f"Error: File '{file_path}' not found"

    if not full_path.is_file():
        return f"Error: '{file_path}' is not a file"

    # Security: ensure the path is within docs directory
    try:
        full_path.resolve().relative_to(docs_path.resolve())
    except ValueError:
        return f"Error: Access denied - path outside documentation directory"

    try:
        # Read current content
        current_content = full_path.read_text(encoding='utf-8')

        # Check if old_content exists in file
        if old_content not in current_content:
            return f"Error: old_content not found in file. Make sure it matches exactly."

        # Count occurrences
        count = current_content.count(old_content)
        if count > 1:
            return f"Error: old_content appears {count} times in the file. Please be more specific to ensure a unique match."

        # Perform replacement
        new_file_content = current_content.replace(old_content, new_content, 1)

        # Write back
        full_path.write_text(new_file_content, encoding='utf-8')

        logger.info("file_edited", file_path=file_path, bytes_changed=len(new_file_content) - len(current_content))

        return f"Success: File '{file_path}' edited successfully. Changed {len(old_content)} bytes to {len(new_content)} bytes."

    except Exception as e:
        logger.error("edit_file_failed", file_path=file_path, error=str(e))
        return f"Error: {str(e)}"


# Tool definitions for OpenAI function calling
DOCUMENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "grep_files",
            "description": "Search for a text pattern in documentation files. Use this to find mentions of specific topics, functions, or concepts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern or regular expression to search for"
                    },
                    "directory": {
                        "type": "string",
                        "description": "Subdirectory to search in (relative to docs root). Leave empty to search all docs."
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether the search should be case-sensitive",
                        "default": False
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files by name pattern. Use this to locate specific documentation files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "File name pattern (supports wildcards like *.md)"
                    },
                    "directory": {
                        "type": "string",
                        "description": "Subdirectory to search in. Leave empty to search all docs."
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a documentation file. Use this after finding relevant files with grep or find.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file relative to docs root (e.g., 'getting-started.md' or 'api/authentication.md')"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in documentation. Use this to explore the documentation structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to list. Leave empty to list root directory."
                    },
                    "include_subdirs": {
                        "type": "boolean",
                        "description": "Whether to include subdirectories",
                        "default": True
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a documentation file by replacing specific content. Use this to update or fix documentation based on user requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file relative to docs root"
                    },
                    "old_content": {
                        "type": "string",
                        "description": "Exact content to replace (must match exactly, including whitespace)"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "New content to insert in place of old_content"
                    }
                },
                "required": ["file_path", "old_content", "new_content"]
            }
        }
    }
]


# Tool executor mapping
TOOL_FUNCTIONS = {
    "grep_files": grep_files,
    "find_files": find_files,
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
}


def execute_tool(tool_name: str, **kwargs) -> str:
    """
    Execute a tool by name with provided arguments.

    Args:
        tool_name: Name of the tool to execute
        **kwargs: Tool arguments

    Returns:
        String result from tool execution
    """
    if tool_name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool '{tool_name}'"

    try:
        tool_func = TOOL_FUNCTIONS[tool_name]
        result = tool_func(**kwargs)
        return result
    except TypeError as e:
        return f"Error: Invalid arguments for {tool_name}: {str(e)}"
    except Exception as e:
        logger.error("tool_execution_failed", tool=tool_name, error=str(e))
        return f"Error executing {tool_name}: {str(e)}"
