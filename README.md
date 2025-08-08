# FounderAI

A command-line AI assistant that uses Ollama for AI interactions with file system access capabilities and streaming responses.

## Features

- **Streaming responses** from Ollama models
- **File system access** tools (read, write, list directories)
- **Interactive chat sessions** with conversation history
- **Configuration management** with persistent settings
- **Rich terminal output** with syntax highlighting

## Requirements

- Python 3.8+
- Ollama running locally (default: localhost:11434)
- An Ollama model (default: llama3.2)

## Installation

### Using uv (Recommended)

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the project and dependencies:
```bash
uv pip install -e .
```

4. Run the tool:
```bash
founderai  # After activating the virtual environment
# OR
python3 -m src.main  # Direct module execution
# OR
.venv/bin/founderai  # Direct script execution without activation
```

### Using pip

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable:
```bash
chmod +x cli_tool.py
```

4. (Optional) Install as a package:
```bash
pip install -e .
```

## Usage

### Interactive Mode
```bash
founderai
# OR if running directly
python3 -m src.main
```

### Single Message
```bash
founderai "List the files in the current directory"
# OR
python3 -m src.main "List the files in the current directory"
```

### Options
- `--model, -m`: Specify Ollama model (default: qwen3:30b-a3b-instruct-2507-q4_K_M)
- `--host, -h`: Specify Ollama host:port (default: localhost:11434)
- `--config, -c`: Show current configuration
- `--verbose, -v`: Enable verbose debug output
- `--no-tools`: Disable file system tools (conversation only mode)

### Examples

```bash
# Use a different model
founderai --model codellama "Explain this Python code"

# Connect to remote Ollama instance
founderai --host remote-server:11434

# Show configuration
founderai --config

# Debug mode for troubleshooting
founderai --verbose "Hello"

# Conversation only (no file tools)
founderai --no-tools "Hello"
```

## Available Tools

The AI assistant has access to these powerful tools:

### File Operations
1. **read_file**: Read contents of a file
2. **write_file**: Write content to a file  
3. **list_directory**: List directory contents

### Command Execution
4. **run_shell_command**: Execute any shell command
5. **git_command**: Execute git operations (status, add, commit, push, pull, diff, log, branch, checkout)

### Task Management
6. **todo_add**: Add new TODO items for task tracking
7. **todo_list**: List TODO items (can filter by status)
8. **todo_update**: Update TODO status (pending, in_progress, completed)
9. **todo_remove**: Remove TODO items

### Web Search
10. **search_web**: Search the web for information
11. **search_documentation**: Search for documentation on specific sites
12. **search_code_examples**: Search for code examples and implementations

### Advanced Features
- **Multi-turn context management**: Maintains conversation history across interactions
- **Auto-context compression**: Automatically summarizes older conversation when approaching token limits
- **Function calling fallback**: Works with models that don't support function calling
- **Rich terminal output**: Beautiful formatted output with syntax highlighting

## Development

### With uv

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .

# Lint code
flake8

# Type check
mypy .
```

## Configuration

Configuration is stored in `~/.cli_tool/config.json`. You can modify:

- `default_model`: Default Ollama model (qwen3-coder:latest)
- `default_host`: Default Ollama host:port (localhost:11434)
- `max_history`: Maximum conversation history to keep (50)
- `save_sessions`: Whether to save chat sessions (true)
- `max_context_tokens`: Maximum tokens before auto-compression (8000)
- `auto_summarize`: Enable automatic context compression (true)

## Session Management

- Conversations persist only during the current session
- Session history is automatically cleared when you exit the tool
- Each new session starts fresh with no previous conversation history

## Example Interactions

### File Operations
```
You: Read the contents of requirements.txt
Assistant: [Tool executes and shows file contents]

You: Create a new Python file called hello.py with a simple hello world program
Assistant: [Tool creates the file with Python code]

You: What files are in the current directory?
Assistant: [Tool lists directory contents with file types and sizes]
```

### Command Execution
```
You: Check the git status
Assistant: [Executes git status and shows output]

You: Run the tests using pytest
Assistant: [Executes pytest command and shows results]
```

### Task Management
```
You: Add a TODO to implement user authentication
Assistant: [Creates new TODO item with ID]

You: Show me all my pending tasks
Assistant: [Lists TODO items with status and priority]

You: Mark task abc123 as completed
Assistant: [Updates TODO status]
```

### Web Search
```
You: Search for Python best practices
Assistant: [Searches web and shows relevant results]

You: Find documentation for FastAPI
Assistant: [Searches documentation sites for FastAPI info]
```

## Troubleshooting

1. **Ollama not responding**: Ensure Ollama is running on the specified host/port
2. **Model not found**: Make sure the model is installed in Ollama (`ollama pull model-name`)
3. **Function calling errors**: Some models don't support function calling - the app will automatically fall back to text-based responses
4. **Permission errors**: Check file permissions for read/write operations
5. **Config issues**: Delete `~/.cli_tool/` directory to reset configuration
6. **TODOs not persisting**: Check write permissions for `~/.cli_tool/` or project directory (`.founder_todo.json`)

### Function Calling Support

Not all Ollama models support OpenAI-style function calling. When function calling fails, FounderAI automatically falls back to conversation-only mode. 

**✅ Tested Models with Function Calling Support:**
- `qwen3:30b-a3b-instruct-2507-q4_K_M` - Full OpenAI-style function calling support (recommended, default)
- `qwen2.5:0.5b` - Full OpenAI-style function calling support
- `mistral:7b-instruct` - Text-based tool mentions (partial support)

**❌ Models without Function Calling Support:**
- `qwen3-coder:latest` - No function calling (falls back to conversation)
- `codestral:latest` - No function calling
- `gemma3:27b` - No function calling
- `deepseek-coder-v2:latest` - No function calling
- `llama3-gradient:instruct` - No function calling

The fallback ensures the application works with any model, providing helpful guidance even without direct tool execution. For the best experience with file operations and tools, use `qwen3:30b-a3b-instruct-2507-q4_K_M` or `qwen2.5:0.5b` as they both support full function calling.