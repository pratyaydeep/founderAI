#!/usr/bin/env python3
"""
A basic CLI tool with file system access using Ollama with streaming responses.
"""

import os
import sys
import json
import click
import requests
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from typing import Dict, List, Optional, Any
from .config import Config
from .todo_manager import TodoManager
from .web_search import WebSearchTool

console = Console()

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        
    def stream_chat(self, model: str, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None, verbose: bool = False):
        """Stream chat completion from Ollama with proper timeout handling"""
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        
        if tools:
            payload["tools"] = tools
            
        if verbose:
            console.print(f"[dim]Sending request to: {url}[/dim]")
            console.print(f"[dim]Payload: {json.dumps(payload, indent=2)}[/dim]")
            
        try:
            # Initial connection timeout of 30 seconds, but no read timeout for streaming
            response = requests.post(url, json=payload, stream=True, timeout=(30, None))
            if response.status_code == 400:
                # Model likely doesn't support tools, raise specific exception
                raise ValueError("Model doesn't support tools")
            response.raise_for_status()
            
            if verbose:
                console.print(f"[dim]Response status: {response.status_code}[/dim]")
                console.print(f"[dim]Response headers: {dict(response.headers)}[/dim]")
            
            line_count = 0
            import time
            last_data_time = time.time()
            
            # Stream with dynamic timeout - if we're getting data, keep waiting
            for line in response.iter_lines(chunk_size=1, decode_unicode=False):
                current_time = time.time()
                
                if line:
                    line_count += 1
                    last_data_time = current_time
                    
                    if verbose and line_count % 10 == 0:  # Less verbose logging
                        console.print(f"[dim]Processed {line_count} lines...[/dim]")
                    
                    try:
                        decoded_line = line.decode('utf-8')
                        data = json.loads(decoded_line)
                        yield data
                    except json.JSONDecodeError as e:
                        if verbose:
                            console.print(f"[dim]JSON decode error: {e}[/dim]")
                        continue
                    except UnicodeDecodeError as e:
                        if verbose:
                            console.print(f"[dim]Unicode decode error: {e}[/dim]")
                        continue
                else:
                    # No data in this chunk, check if we've been waiting too long without any data
                    if current_time - last_data_time > 60:  # 60 seconds without any data
                        if verbose:
                            console.print(f"[dim]No data received for 60 seconds, assuming stream ended[/dim]")
                        break
                    
                    # Short sleep to prevent busy waiting
                    time.sleep(0.1)
            
            if verbose:
                console.print(f"[dim]Total lines received: {line_count}[/dim]")
                        
        except requests.exceptions.ConnectTimeout:
            console.print(f"[red]Connection timeout: Could not connect to Ollama at {self.base_url}[/red]")
            console.print(f"[yellow]Make sure Ollama is running: `ollama serve`[/yellow]")
            return
        except requests.exceptions.ReadTimeout:
            console.print(f"[red]Read timeout: Ollama took too long to respond[/red]")
            console.print(f"[yellow]This might happen with complex requests. Try a simpler query first.[/yellow]")
            return
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error connecting to Ollama: {e}[/red]")
            return
        except Exception as e:
            console.print(f"[red]Unexpected error during streaming: {e}[/red]")
            return

class FileSystemTools:
    @staticmethod
    def read_file(path: str) -> str:
        """Read file contents, raising an exception on failure."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Failed to read file at {path}: {e}") from e
    
    @staticmethod
    def write_file(path: str, content: str) -> str:
        """Write content to file, raising an exception on failure."""
        try:
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            raise IOError(f"Failed to write to file at {path}: {e}") from e
    
    @staticmethod
    def list_directory(path: str = ".") -> List[Dict[str, Any]]:
        """List directory contents, raising an exception on failure."""
        try:
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                is_dir = os.path.isdir(item_path)
                size = os.path.getsize(item_path) if not is_dir else 0
                items.append({
                    "name": item,
                    "type": "directory" if is_dir else "file",
                    "size": size,
                    "path": item_path
                })
            return items
        except Exception as e:
            raise IOError(f"Failed to list directory at {path}: {e}") from e
    
    @staticmethod
    def run_shell_command(command: str, cwd: str = None) -> Dict[str, Any]:
        """Execute a shell command and return the result."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "command": command
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after 30 seconds: {command}",
                "command": command
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute command '{command}': {e}",
                "command": command
            }
    
    @staticmethod
    def git_command(action: str, *args) -> Dict[str, Any]:
        """Execute git commands with common actions."""
        git_commands = {
            "status": "git status",
            "add": f"git add {' '.join(args) if args else '.'}",
            "commit": f"git commit -m \"{args[0] if args else 'Auto commit from FounderAI'}\"",
            "push": "git push",
            "pull": "git pull",
            "diff": "git diff",
            "log": f"git log --oneline -n {args[0] if args and args[0].isdigit() else '10'}",
            "branch": "git branch",
            "checkout": f"git checkout {args[0] if args else 'main'}"
        }
        
        if action not in git_commands:
            return {
                "success": False,
                "error": f"Unknown git action: {action}. Available: {', '.join(git_commands.keys())}",
                "command": f"git {action}"
            }
        
        return FileSystemTools.run_shell_command(git_commands[action])

class ChatSession:
    def __init__(self, config: Config, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.messages: List[Dict[str, str]] = config.load_session()
        self.tools = self._define_tools()
        self.fs_tools = FileSystemTools()
        self.max_context_tokens = config.get("max_context_tokens", 8000)
        self.summary_threshold = int(self.max_context_tokens * 0.8)
        self.todo_manager = TodoManager()
        self.web_search = WebSearchTool()
        
    def _define_tools(self) -> List[Dict]:
        """Define available tools for the model"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a specific file when the user explicitly asks to read, open, or view a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file to read"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file when the user explicitly asks to create, write, or save content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file to write"},
                            "content": {"type": "string", "description": "Content to write to the file"}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory", 
                    "description": "List contents of a directory when the user explicitly asks to list, show directory contents, or see what files are in a folder",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to directory (default: current directory)"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_shell_command",
                    "description": "Execute a shell command when the user explicitly asks to run a command, execute a script, or perform system operations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "The shell command to execute"},
                            "cwd": {"type": "string", "description": "Working directory to run the command in (optional)"}
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_command",
                    "description": "Execute git commands when the user explicitly asks for git operations like status, commit, push, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "description": "Git action (status, add, commit, push, pull, diff, log, branch, checkout)"},
                            "args": {"type": "array", "items": {"type": "string"}, "description": "Additional arguments for the git command"}
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "todo_add",
                    "description": "Add a new TODO item when user asks to create tasks, track work, or manage todos",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string", "description": "Description of the task to add"},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"], "description": "Priority level (default: medium)"}
                        },
                        "required": ["description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "todo_list",
                    "description": "List TODO items when user asks to see tasks, show todos, or check progress",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "Filter by status (optional)"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "todo_update",
                    "description": "Update TODO status when user marks tasks as done, in progress, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "todo_id": {"type": "string", "description": "ID of the todo to update"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "New status"}
                        },
                        "required": ["todo_id", "status"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "todo_remove",
                    "description": "Remove a TODO item when user asks to delete or remove a task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "todo_id": {"type": "string", "description": "ID of the todo to remove"}
                        },
                        "required": ["todo_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web when user asks to look up information, find documentation, or search online",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "max_results": {"type": "integer", "description": "Maximum number of results (default: 5)"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_documentation",
                    "description": "Search for documentation on specific sites when user asks for docs or help with technologies",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "What to search for"},
                            "site": {"type": "string", "description": "Specific site to search (e.g., 'python.org', 'stackoverflow.com')"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_code_examples",
                    "description": "Search for code examples when user asks for coding examples or implementations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "What kind of code to search for"},
                            "language": {"type": "string", "description": "Programming language (optional)"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def execute_tool(self, tool_call: Dict) -> Dict[str, Any]:
        """Execute a tool call and handle potential exceptions."""
        function_name = tool_call.get("function", {}).get("name")
        arguments = tool_call.get("function", {}).get("arguments", {})
        
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return {"success": False, "error": "Invalid JSON in tool arguments"}

        try:
            if function_name == "read_file":
                content = self.fs_tools.read_file(arguments.get("path", ""))
                return {"success": True, "content": content}
            elif function_name == "write_file":
                message = self.fs_tools.write_file(arguments.get("path", ""), arguments.get("content", ""))
                return {"success": True, "message": message}
            elif function_name == "list_directory":
                items = self.fs_tools.list_directory(arguments.get("path", "."))
                return {"success": True, "items": items}
            elif function_name == "run_shell_command":
                result = self.fs_tools.run_shell_command(
                    arguments.get("command", ""), 
                    arguments.get("cwd")
                )
                return result
            elif function_name == "git_command":
                result = self.fs_tools.git_command(
                    arguments.get("action", ""), 
                    *arguments.get("args", [])
                )
                return result
            elif function_name == "todo_add":
                todo_id = self.todo_manager.add_todo(
                    arguments.get("description", ""),
                    arguments.get("priority", "medium")
                )
                return {"success": True, "message": f"Added TODO with ID: {todo_id}", "todo_id": todo_id}
            elif function_name == "todo_list":
                todos = self.todo_manager.list_todos(arguments.get("status"))
                return {"success": True, "todos": todos}
            elif function_name == "todo_update":
                success = self.todo_manager.update_todo_status(
                    arguments.get("todo_id", ""),
                    arguments.get("status", "")
                )
                if success:
                    return {"success": True, "message": f"Updated TODO {arguments.get('todo_id')} to {arguments.get('status')}"}
                else:
                    return {"success": False, "error": f"TODO with ID {arguments.get('todo_id')} not found"}
            elif function_name == "todo_remove":
                success = self.todo_manager.remove_todo(arguments.get("todo_id", ""))
                if success:
                    return {"success": True, "message": f"Removed TODO {arguments.get('todo_id')}"}
                else:
                    return {"success": False, "error": f"TODO with ID {arguments.get('todo_id')} not found"}
            elif function_name == "search_web":
                result = self.web_search.search_web(
                    arguments.get("query", ""),
                    arguments.get("max_results", 5)
                )
                return result
            elif function_name == "search_documentation":
                result = self.web_search.search_documentation(
                    arguments.get("query", ""),
                    arguments.get("site")
                )
                return result
            elif function_name == "search_code_examples":
                result = self.web_search.search_code_examples(
                    arguments.get("query", ""),
                    arguments.get("language")
                )
                return result
            else:
                return {"success": False, "error": f"Unknown tool: {function_name}"}
        except (IOError, OSError) as e:
            return {"success": False, "error": str(e)}
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4
    
    def _get_total_tokens(self) -> int:
        """Calculate total tokens in current conversation"""
        return sum(self._estimate_tokens(msg["content"]) for msg in self.messages)
    
    def _summarize_conversation(self) -> str:
        """Create a summary of older messages to compress context"""
        if len(self.messages) <= 3:
            return ""
        
        # Keep system message and last 2 exchanges
        system_msg = next((msg for msg in self.messages if msg["role"] == "system"), None)
        recent_messages = self.messages[-4:]  # Last 2 user-assistant pairs
        
        # Messages to summarize (everything except system and recent)
        to_summarize = [msg for msg in self.messages if msg not in recent_messages and msg != system_msg]
        
        if not to_summarize:
            return ""
        
        # Create summary prompt
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in to_summarize])
        summary_prompt = f"""Please create a concise summary of this conversation, preserving all important details, code snippets, file paths, and key facts:

{conversation_text}

Summary:"""
        
        return summary_prompt
    
    def _manage_context_size(self):
        """Auto-compress conversation if it's getting too long"""
        current_tokens = self._get_total_tokens()
        
        if current_tokens > self.summary_threshold and len(self.messages) > 5:
            if self.verbose:
                console.print(f"[dim]Context size ({current_tokens} tokens) approaching limit. Compressing...[/dim]")
            
            system_msg = next((msg for msg in self.messages if msg["role"] == "system"), None)
            recent_messages = self.messages[-4:]  # Keep last 2 exchanges
            
            # Create summary of older messages
            summary = self._summarize_conversation()
            
            # Rebuild message list
            new_messages = []
            if system_msg:
                new_messages.append(system_msg)
            
            if summary:
                new_messages.append({
                    "role": "assistant", 
                    "content": f"[Previous conversation summary: {summary}]"
                })
            
            new_messages.extend(recent_messages)
            
            self.messages = new_messages
            
            if self.verbose:
                new_tokens = self._get_total_tokens()
                console.print(f"[dim]Context compressed from {current_tokens} to {new_tokens} tokens[/dim]")
    
    def _parse_manual_tool_calls(self, user_input: str, assistant_response: str) -> List[Dict]:
        """Parse user input to determine if tools should be executed manually"""
        tool_calls = []
        user_lower = user_input.lower()
        
        # File operations
        if any(keyword in user_lower for keyword in ["read", "open", "show", "display", "contents of"]):
            # Extract file path from user input
            import re
            file_patterns = [
                r"read (?:the )?(?:contents of )?(?:file )?['\"]?([^\s'\"]+)['\"]?",
                r"open ['\"]?([^\s'\"]+)['\"]?",
                r"show (?:me )?(?:the )?(?:contents of )?['\"]?([^\s'\"]+)['\"]?",
                r"display ['\"]?([^\s'\"]+)['\"]?"
            ]
            
            for pattern in file_patterns:
                match = re.search(pattern, user_lower)
                if match:
                    file_path = match.group(1)
                    tool_calls.append({
                        "function": {
                            "name": "read_file",
                            "arguments": {"path": file_path}
                        }
                    })
                    break
        
        elif any(keyword in user_lower for keyword in ["list", "show directory", "what files", "ls", "dir"]):
            # Directory listing
            path = "."  # Default to current directory
            
            # Try to extract directory path from various patterns
            import re
            dir_patterns = [
                r"(?:in|from) (?:the )?['\"]?([^\s'\"]+)['\"]?",
                r"(?:files? (?:in|from) )?(?:the )?([a-zA-Z0-9_\-./]+)/?(?:\s|$)",
                r"(?:directory|folder) ([a-zA-Z0-9_\-./]+)"
            ]
            
            for pattern in dir_patterns:
                match = re.search(pattern, user_lower)
                if match:
                    potential_path = match.group(1)
                    # Check if it's actually a directory name, not just common words
                    if potential_path not in ["what", "are", "the", "files", "directory", "folder"]:
                        path = potential_path
                        break
            
            tool_calls.append({
                "function": {
                    "name": "list_directory", 
                    "arguments": {"path": path}
                }
            })
            
        elif any(keyword in user_lower for keyword in ["create", "write", "make file", "save to"]):
            # This would need more complex parsing to extract filename and content
            # For now, we'll skip auto-execution of write operations for safety
            pass
            
        elif any(keyword in user_lower for keyword in ["git status", "check git", "repository status"]):
            tool_calls.append({
                "function": {
                    "name": "git_command",
                    "arguments": {"action": "status"}
                }
            })
            
        elif any(keyword in user_lower for keyword in ["run", "execute", "command"]) and not any(skip in user_lower for skip in ["don't", "do not", "avoid"]):
            # Extract command from user input (be careful with this)
            import re
            command_patterns = [
                r"run ['\"]([^'\"]+)['\"]",
                r"execute ['\"]([^'\"]+)['\"]",
                r"command ['\"]([^'\"]+)['\"]"
            ]
            
            for pattern in command_patterns:
                match = re.search(pattern, user_input)  # Use original case
                if match:
                    command = match.group(1)
                    # Only allow safe commands
                    safe_commands = ["ls", "pwd", "whoami", "date", "echo", "cat", "head", "tail"]
                    if any(command.startswith(safe_cmd) for safe_cmd in safe_commands):
                        tool_calls.append({
                            "function": {
                                "name": "run_shell_command",
                                "arguments": {"command": command}
                            }
                        })
                    break
        
        return tool_calls
    
    def _get_tools_description(self) -> str:
        """Generate a description of available tools for the LLM"""
        return """**File Operations (CRITICAL for deep repository analysis):**
- read_file(path): Read ANY file - source code, configs, docs, tests. Use extensively!
- write_file(path, content): Write content to a file  
- list_directory(path='.'): Explore directories - use on src/, tests/, docs/, etc.

**Command Execution (For project insights):**
- run_shell_command(command, cwd=None): Find files, check dependencies, analyze structure
- git_command(action, args=[]): Git operations - status, log, diff, branch info

**Task Management:**
- todo_add(description, priority='medium'): Add new TODO items
- todo_list(status=None): List TODO items (filter by status)
- todo_update(todo_id, status): Update TODO status (pending, in_progress, completed)
- todo_remove(todo_id): Remove TODO items

**Web Search:**
- search_web(query, max_results=5): Search the web for information
- search_documentation(query, site=None): Search for documentation
- search_code_examples(query, language=None): Search for code examples

**COMPREHENSIVE Repository Analysis Pattern:**
1. list_directory() - see structure
2. list_directory('src/') - explore source
3. read_file() for EACH major source file
4. list_directory('tests/') if exists
5. read_file() for test files
6. git_command('status') and git_command('log')
7. Continue reading until you understand the COMPLETE codebase

**REMEMBER: Read 5-10+ files minimum for proper analysis!**"""
    
    def _parse_llm_tool_calls(self, assistant_response: str) -> List[Dict]:
        """Parse TOOL_CALL directives from LLM response"""
        tool_calls = []
        lines = assistant_response.split('\n')
        
        import re
        for line in lines:
            line = line.strip()
            if line.startswith('TOOL_CALL:'):
                # Parse tool call: TOOL_CALL: tool_name(arg1='value1', arg2='value2')
                tool_call_text = line[10:].strip()  # Remove 'TOOL_CALL:'
                
                # Extract function name and arguments
                match = re.match(r'(\w+)\((.*)\)', tool_call_text)
                if match:
                    function_name = match.group(1)
                    args_text = match.group(2)
                    
                    # Parse arguments
                    arguments = {}
                    if args_text.strip():
                        # Simple parsing for key='value' format
                        arg_matches = re.findall(r"(\w+)=(['\"]?)([^'\"]*)\2", args_text)
                        for arg_name, quote, arg_value in arg_matches:
                            arguments[arg_name] = arg_value
                    
                    tool_calls.append({
                        "function": {
                            "name": function_name,
                            "arguments": arguments
                        }
                    })
        
        return tool_calls
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation"""
        self.messages.append({"role": role, "content": content})
        self._manage_context_size()
        self.config.save_session(self.messages)
    
    def chat_with_streaming(self, client: OllamaClient, model: str, user_input: str):
        """Handle a chat interaction with streaming"""
        
        # Add system message if this is the first user message
        if len(self.messages) == 0:
            # Create system message with tool information
            tools_description = self._get_tools_description()
            self.messages.append({
                "role": "system", 
                "content": f"You are FounderAI, a comprehensive CLI coding assistant with access to these tools:\n\n{tools_description}\n\nWhen analyzing repositories or codebases, be EXTREMELY THOROUGH like Claude Code:\n\n**MANDATORY EXPLORATION STEPS:**\n1. Start with list_directory() to see overall structure\n2. Read ALL configuration files (pyproject.toml, package.json, requirements.txt, Cargo.toml, etc.)\n3. Explore ALL source directories (src/, lib/, app/, components/, etc.)\n4. Read ALL main source files (.py, .js, .ts, .go, .rs, .java, etc.)\n5. Read test files to understand testing approach\n6. Read documentation files (README.md, docs/, etc.)\n7. Check git status and recent commits\n8. Read any configuration or environment files (.env, config/, etc.)\n\n**YOU MUST READ MULTIPLE FILES** - don't stop after just README and config files! A proper analysis requires reading:\n- At least 5-10 source files to understand the codebase\n- All major modules/components\n- Key implementation files\n- Test files and examples\n\nProvide detailed insights about:\n- Complete project architecture and file organization\n- All major features and functionality \n- Technology stack and dependencies\n- Code patterns and design decisions\n- Development workflow and tools\n\nFormat tool calls as: TOOL_CALL: tool_name(arg1='value1', arg2='value2')\nFor normal conversation, respond directly without TOOL_CALL."
            })
        
        self.add_message("user", user_input)
        
        # Decide whether to use tools based on user input and recent context
        # Try tools first, fallback to text-based tool simulation if model doesn't support them
        tools_to_use = self.tools if len(self.tools) > 0 else None
        
        if self.verbose:
            console.print(f"[dim]Messages to send: {len(self.messages)}[/dim]")
            console.print(f"[dim]Last message: {self.messages[-1]}[/dim]")
        
        assistant_content = ""
        tool_calls = []
        
        console.print("\n[bold blue]AI:[/bold blue]")
        
        if self.verbose:
            console.print(f"[dim]Using tools: {tools_to_use is not None}[/dim]")
        
        # Show streaming indicator for user feedback
        streaming_indicator_shown = True
        console.print("[dim]🔄 Streaming response...[/dim]")
        
        chunk_count = 0
        try:
            for chunk in client.stream_chat(model, self.messages, tools_to_use, self.verbose):
                chunk_count += 1
                if self.verbose:
                    console.print(f"[dim]Chunk {chunk_count}: {chunk}[/dim]")
                    
                # Process message content first, then check for done
                if "message" in chunk:
                    message = chunk["message"]
                    
                    if "content" in message and message["content"]:
                        content = message["content"]
                        assistant_content += content
                        
                        # Clear streaming indicator on first content
                        if streaming_indicator_shown:
                            # Simply print a carriage return to overwrite the streaming line
                            console.print("\r", end="")
                            streaming_indicator_shown = False
                        
                        console.print(content, end="")
                    
                    if "tool_calls" in message:
                        tool_calls.extend(message["tool_calls"])
                
                # Check for done after processing the message
                if chunk.get("done"):
                    if self.verbose:
                        console.print(f"[dim]Stream completed with 'done' flag[/dim]")
                    break
        except Exception as e:
            if ("400" in str(e) or "doesn't support tools" in str(e)) and tools_to_use:
                # Model doesn't support tools, try again without them
                console.print(f"[yellow]Model doesn't support function calling. Continuing without tools...[/yellow]")
                    
                try:
                    for chunk in client.stream_chat(model, self.messages, None, self.verbose):
                        chunk_count += 1
                        if self.verbose:
                            console.print(f"[dim]Fallback chunk {chunk_count}: {chunk}[/dim]")
                            
                        if "message" in chunk:
                            message = chunk["message"]
                            
                            if "content" in message and message["content"]:
                                content = message["content"]
                                assistant_content += content
                                console.print(content, end="")
                        
                        if chunk.get("done"):
                            if self.verbose:
                                console.print(f"[dim]Fallback stream completed[/dim]")
                            break
                except Exception as fallback_error:
                    console.print(f"[red]Error even without tools: {fallback_error}[/red]")
                    return
            else:
                console.print(f"[red]Error during streaming: {e}[/red]")
                return
        
        if self.verbose:
            console.print(f"\n[dim]Total chunks processed: {chunk_count}[/dim]")
            console.print(f"[dim]Assistant content length: {len(assistant_content)}[/dim]")
        
        console.print()
        
        if assistant_content:
            self.add_message("assistant", assistant_content)
            
            # If no tool calls were made but the request seems to be asking for tool usage,
            # parse LLM's tool call directives from the response
            if not tool_calls and tools_to_use:
                tool_calls = self._parse_llm_tool_calls(assistant_content)
                if tool_calls:
                    console.print(f"\n[yellow]🔧 Executing tools as requested by the LLM...[/yellow]")
                else:
                    # Fallback to manual parsing if LLM didn't use TOOL_CALL format
                    tool_calls = self._parse_manual_tool_calls(user_input, assistant_content)
                    if tool_calls:
                        console.print(f"\n[yellow]🔧 Executing tools automatically since model doesn't support function calling...[/yellow]")
        
        if tool_calls:
            tool_results = []
            for tool_call in tool_calls:
                console.print(f"\n[yellow]Executing tool: {tool_call.get('function', {}).get('name')}[/yellow]")
                result = self.execute_tool(tool_call)
                
                if result.get("success"):
                    if "content" in result:
                        console.print(Panel(result["content"][:500] + "..." if len(result.get("content", "")) > 500 else result["content"], 
                                           title=f"File: {tool_call.get('function', {}).get('arguments', {}).get('path', 'unknown')}"))
                        tool_results.append(f"File content from {tool_call.get('function', {}).get('arguments', {}).get('path', 'unknown')}:\n{result['content']}")
                    elif "items" in result:
                        items_display = "\n".join([f"{'📁' if item['type'] == 'directory' else '📄'} {item['name']}" for item in result["items"][:20]])
                        if len(result["items"]) > 20:
                            items_display += f"\n... and {len(result['items']) - 20} more items"
                        console.print(Panel(items_display, title=f"Directory: {tool_call.get('function', {}).get('arguments', {}).get('path', '.')}"))
                        tool_results.append(f"Directory listing for {tool_call.get('function', {}).get('arguments', {}).get('path', '.')}:\n{items_display}")
                    elif "stdout" in result or "stderr" in result:
                        # Handle shell/git command output
                        command = result.get("command", "unknown command")
                        output = ""
                        if result.get("stdout"):
                            output += f"[green]STDOUT:[/green]\n{result['stdout']}"
                        if result.get("stderr"):
                            if output:
                                output += "\n\n"
                            output += f"[yellow]STDERR:[/yellow]\n{result['stderr']}"
                        if result.get("return_code", 0) != 0:
                            output += f"\n\n[red]Exit code: {result['return_code']}[/red]"
                        
                        console.print(Panel(output or "[dim]No output[/dim]", title=f"Command: {command}"))
                        tool_results.append(f"Command '{command}' executed:\n{result.get('stdout', '')}{result.get('stderr', '')}")
                    elif "todos" in result:
                        # Handle TODO list display
                        todos = result["todos"]
                        if not todos:
                            display = "[dim]No TODOs found[/dim]"
                        else:
                            priority_icons = {"high": "🔥", "medium": "⚡", "low": "📝"}
                            status_icons = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}
                            
                            todo_lines = []
                            for todo in todos:
                                priority_icon = priority_icons.get(todo.get("priority", "medium"), "📝")
                                status_icon = status_icons.get(todo.get("status", "pending"), "⏳")
                                todo_lines.append(f"{status_icon} {priority_icon} [{todo.get('id', 'unknown')}] {todo.get('description', 'No description')}")
                            
                            display = "\n".join(todo_lines)
                        
                        console.print(Panel(display, title="TODO List"))
                        tool_results.append(f"TODO list:\n{display}")
                    elif "query" in result and ("answer" in result or "results" in result):
                        # Handle web search results
                        query = result.get("query", "")
                        if result.get("type") == "instant_answer" and result.get("answer"):
                            display = f"[bold]Answer:[/bold]\n{result['answer']}"
                            console.print(Panel(display, title=f"Search: {query}"))
                            tool_results.append(f"Search result for '{query}':\n{result['answer']}")
                        elif result.get("results"):
                            results_text = []
                            for i, res in enumerate(result["results"][:3], 1):
                                if "error" not in res:
                                    results_text.append(f"{i}. {res.get('title', 'No title')}\n   {res.get('snippet', 'No snippet')}")
                            
                            display = "\n\n".join(results_text) if results_text else "[dim]No results found[/dim]"
                            console.print(Panel(display, title=f"Search Results: {query}"))
                            tool_results.append(f"Search results for '{query}':\n{display}")
                        else:
                            console.print(f"[yellow]No results found for: {query}[/yellow]")
                            tool_results.append(f"No results found for: {query}")
                    else:
                        console.print(f"[green]{result.get('message', 'Tool executed successfully')}[/green]")
                        tool_results.append(result.get('message', 'Tool executed successfully'))
                else:
                    console.print(f"[red]Tool error: {result.get('error', 'Unknown error')}[/red]")
                    tool_results.append(f"Error: {result.get('error', 'Unknown error')}")
            
            # Add tool results to conversation history so the model can continue analysis
            if tool_results:
                combined_results = "\n\n".join(tool_results)
                tool_results_message = f"Tool execution results:\n\n{combined_results}"
                self.add_message("user", tool_results_message)
                
                # Continue the conversation with the LLM to analyze the results
                console.print(f"\n[blue]📊 Analyzing results...[/blue]")
                console.print("[dim]🔄 Streaming analysis...[/dim]")
                
                # Continue the conversation - the LLM may want to make more tool calls
                max_iterations = 25  # Allow comprehensive repository analysis
                iteration = 0
                
                while iteration < max_iterations:
                    iteration += 1
                    additional_tool_calls = []
                    analysis_content = ""
                    analysis_streaming_shown = True
                    
                    # Safety check - if conversation is getting too long, summarize
                    if len(self.messages) > 100:
                        if self.verbose:
                            console.print(f"[dim]Long conversation detected ({len(self.messages)} messages), will summarize if needed[/dim]")
                        self._manage_context_size()
                    
                    try:
                        for chunk in client.stream_chat(model, self.messages, tools_to_use, self.verbose):
                            if "message" in chunk:
                                message = chunk["message"]
                                if "content" in message and message["content"]:
                                    content = message["content"]
                                    analysis_content += content
                                    
                                    # Clear streaming indicator on first content
                                    if analysis_streaming_shown:
                                        # Simply print a carriage return to overwrite the streaming line
                                        console.print("\r", end="")
                                        analysis_streaming_shown = False
                                    
                                    console.print(content, end="")
                                
                                # Check for additional tool calls
                                if "tool_calls" in message:
                                    additional_tool_calls.extend(message["tool_calls"])
                            
                            if chunk.get("done"):
                                break
                    except Exception as e:
                        if ("400" in str(e) or "doesn't support tools" in str(e)) and tools_to_use:
                            # Parse tool calls from text response for non-function calling models
                            additional_tool_calls = self._parse_llm_tool_calls(analysis_content)
                            if additional_tool_calls:
                                console.print(f"\n[yellow]🔧 Executing additional tools requested by LLM...[/yellow]")
                        else:
                            console.print(f"[red]Error during analysis: {e}[/red]")
                            break
                    
                    console.print()
                    if analysis_content:
                        self.add_message("assistant", analysis_content)
                    
                    # If no more tool calls, we're done
                    if not additional_tool_calls:
                        break
                    
                    # Execute additional tools and add results back to conversation
                    additional_results = []
                    for tool_call in additional_tool_calls:
                        console.print(f"\n[yellow]Executing tool: {tool_call.get('function', {}).get('name')}[/yellow]")
                        result = self.execute_tool(tool_call)
                        
                        # Display the result (simplified)
                        if result.get("success"):
                            if "content" in result:
                                console.print(Panel(result["content"][:500] + "..." if len(result.get("content", "")) > 500 else result["content"], 
                                               title=f"File: {tool_call.get('function', {}).get('arguments', {}).get('path', 'unknown')}"))
                                additional_results.append(f"File content from {tool_call.get('function', {}).get('arguments', {}).get('path', 'unknown')}:\n{result['content']}")
                            elif "items" in result:
                                items_display = "\n".join([f"{'📁' if item['type'] == 'directory' else '📄'} {item['name']}" for item in result["items"][:20]])
                                console.print(Panel(items_display, title=f"Directory: {tool_call.get('function', {}).get('arguments', {}).get('path', '.')}"))
                                additional_results.append(f"Directory listing:\n{items_display}")
                            else:
                                console.print(f"[green]{result.get('message', 'Tool executed successfully')}[/green]")
                                additional_results.append(result.get('message', 'Tool executed successfully'))
                        else:
                            console.print(f"[red]Tool error: {result.get('error', 'Unknown error')}[/red]")
                            additional_results.append(f"Error: {result.get('error', 'Unknown error')}")
                    
                    # Add results back to conversation for next iteration
                    if additional_results:
                        combined_results = "\n\n".join(additional_results)
                        self.add_message("user", f"Additional tool results:\n\n{combined_results}")
                        console.print(f"\n[blue]📊 Continuing analysis with iteration {iteration}...[/blue]")
                        console.print("[dim]🔄 Streaming analysis...[/dim]")

@click.command()
@click.option('--model', '-m', help='Ollama model to use')
@click.option('--host', '-h', help='Ollama host:port')
@click.option('--config', '-c', is_flag=True, help='Show configuration')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose debug output')
@click.option('--no-tools', is_flag=True, help='Disable file system tools for conversation only')
@click.argument('message', required=False)
def main(model: Optional[str], host: Optional[str], config: bool, verbose: bool, no_tools: bool, message: Optional[str]):
    """A CLI tool with file system access using Ollama"""
    
    cfg = Config()
    
    if config:
        console.print(Panel(json.dumps(cfg.config, indent=2), title="Configuration"))
        return
    
    model = model or cfg.get("default_model")
    host = host or cfg.get("default_host")
    
    client = OllamaClient(f"http://{host}")
    session = ChatSession(cfg, verbose=verbose)
    
    # Disable tools if requested
    if no_tools:
        session.tools = []
    
    console.print(Panel.fit(
        "[bold green]FounderAI[/bold green]\n"
        f"Model: {model}\n"
        f"Host: {host}\n"
        "Type 'exit' or 'quit' to end the session",
        border_style="green"
    ))
    
    if message:
        session.chat_with_streaming(client, model, message)
        cfg.clear_session()
        return
    
    try:
        while True:
            try:
                user_input = console.input("\n[bold cyan]Founder:[/bold cyan] ")
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    console.print("[yellow]Goodbye![/yellow]")
                    cfg.clear_session()
                    break
                
                if not user_input.strip():
                    continue
                
                session.chat_with_streaming(client, model, user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit properly[/yellow]")
                continue
                
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        cfg.clear_session()
        sys.exit(1)
    finally:
        cfg.clear_session()

if __name__ == "__main__":
    main()
