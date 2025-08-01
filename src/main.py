#!/usr/bin/env python3
"""
A basic CLI tool with file system access using Ollama with streaming responses.
"""

import os
import sys
import json
import click
import requests
from rich.console import Console
from rich.panel import Panel
from typing import Dict, List, Optional, Any
from .config import Config

console = Console()

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        
    def stream_chat(self, model: str, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None, verbose: bool = False):
        """Stream chat completion from Ollama"""
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
            response = requests.post(url, json=payload, stream=True, timeout=30)
            response.raise_for_status()
            
            if verbose:
                console.print(f"[dim]Response status: {response.status_code}[/dim]")
                console.print(f"[dim]Response headers: {dict(response.headers)}[/dim]")
            
            line_count = 0
            for line in response.iter_lines():
                if line:
                    line_count += 1
                    if verbose:
                        console.print(f"[dim]Line {line_count}: {line.decode('utf-8')[:100]}...[/dim]")
                    try:
                        data = json.loads(line.decode('utf-8'))
                        yield data
                    except json.JSONDecodeError as e:
                        if verbose:
                            console.print(f"[dim]JSON decode error: {e}[/dim]")
                        continue
            
            if verbose:
                console.print(f"[dim]Total lines received: {line_count}[/dim]")
                        
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error connecting to Ollama: {e}[/red]")
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

class ChatSession:
    def __init__(self, config: Config, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.messages: List[Dict[str, str]] = config.load_session()
        self.tools = self._define_tools()
        self.fs_tools = FileSystemTools()
        
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
            else:
                return {"success": False, "error": f"Unknown tool: {function_name}"}
        except (IOError, OSError) as e:
            return {"success": False, "error": str(e)}
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation"""
        self.messages.append({"role": role, "content": content})
        self.config.save_session(self.messages)
    
    def chat_with_streaming(self, client: OllamaClient, model: str, user_input: str):
        """Handle a chat interaction with streaming"""
        
        # Add system message if this is the first user message
        if len(self.messages) == 0:
            self.messages.append({
                "role": "system", 
                "content": "You are FounderAI, a helpful assistant. You have access to file operations (read_file, write_file, list_directory). Only use these tools when the user explicitly asks for file operations like 'read file.txt', 'write to file', or 'list directory'. For normal conversation, greetings, or questions about content you've already read, respond directly without using tools."
            })
        
        self.add_message("user", user_input)
        
        # Decide whether to use tools based on user input and recent context
        tools_to_use = self.tools if len(self.tools) > 0 else None
        
        if self.verbose:
            console.print(f"[dim]Messages to send: {len(self.messages)}[/dim]")
            console.print(f"[dim]Last message: {self.messages[-1]}[/dim]")
        
        assistant_content = ""
        tool_calls = []
        
        console.print("\n[bold blue]Assistant:[/bold blue]")
        
        if self.verbose:
            console.print(f"[dim]Using tools: {tools_to_use is not None}[/dim]")
        
        chunk_count = 0
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
                    console.print(content, end="")
                
                if "tool_calls" in message:
                    tool_calls.extend(message["tool_calls"])
            
            # Check for done after processing the message
            if chunk.get("done"):
                if self.verbose:
                    console.print(f"[dim]Stream completed with 'done' flag[/dim]")
                break
        
        if self.verbose:
            console.print(f"\n[dim]Total chunks processed: {chunk_count}[/dim]")
            console.print(f"[dim]Assistant content length: {len(assistant_content)}[/dim]")
        
        console.print()
        
        if assistant_content:
            self.add_message("assistant", assistant_content)
        
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
                    else:
                        console.print(f"[green]{result.get('message', 'Tool executed successfully')}[/green]")
                        tool_results.append(result.get('message', 'Tool executed successfully'))
                else:
                    console.print(f"[red]Tool error: {result.get('error', 'Unknown error')}[/red]")
                    tool_results.append(f"Error: {result.get('error', 'Unknown error')}")
            
            # Add tool results to conversation history so the model can reference them
            if tool_results:
                combined_results = "\n\n".join(tool_results)
                self.add_message("assistant", f"I executed the requested tools. Here are the results:\n\n{combined_results}")

@click.command()
@click.option('--model', '-m', help='Ollama model to use')
@click.option('--host', '-h', help='Ollama host:port')
@click.option('--config', '-c', is_flag=True, help='Show configuration')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose debug output')
@click.option('--no-tools', is_flag=True, help='Disable file system tools for conversation only')
@click.option('--stateless', is_flag=True, help='Disable session persistence')
@click.argument('message', required=False)
def main(model: Optional[str], host: Optional[str], config: bool, verbose: bool, no_tools: bool, stateless: bool, message: Optional[str]):
    """A CLI tool with file system access using Ollama"""
    
    cfg = Config()
    
    if stateless:
        cfg.set("save_sessions", False)
    
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
        return
    
    try:
        while True:
            try:
                user_input = console.input("\n[bold cyan]You:[/bold cyan] ")
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                
                if not user_input.strip():
                    continue
                
                session.chat_with_streaming(client, model, user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit properly[/yellow]")
                continue
                
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
