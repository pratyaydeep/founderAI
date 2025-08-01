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
- `--stateless`: Force stateless mode (no conversation history)
- `--persistent`: Enable conversation history (overrides default stateless mode)

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

# Interactive mode with conversation history
founderai --persistent

# Force stateless mode (default anyway)
founderai --stateless "Hello"
```

## Available Tools

The AI assistant has access to these file system tools:

1. **read_file**: Read contents of a file
2. **write_file**: Write content to a file
3. **list_directory**: List directory contents

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

- `default_model`: Default Ollama model (qwen3:30b-a3b-instruct-2507-q4_K_M)
- `default_host`: Default Ollama host:port
- `max_history`: Maximum conversation history to keep
- `save_sessions`: Whether to save chat sessions

## Session Management

- Conversations are automatically saved to `~/.cli_tool/session.json`
- Previous sessions are restored when starting the tool
- History is limited by `max_history` setting

## Example Interactions

```
You: Read the contents of requirements.txt
Assistant: [Tool executes and shows file contents]

You: Create a new Python file called hello.py with a simple hello world program
Assistant: [Tool creates the file with Python code]

You: What files are in the current directory?
Assistant: [Tool lists directory contents with file types and sizes]
```

## Troubleshooting

1. **Ollama not responding**: Ensure Ollama is running on the specified host/port
2. **Model not found**: Make sure the model is installed in Ollama (`ollama pull model-name`)
3. **Permission errors**: Check file permissions for read/write operations
4. **Config issues**: Delete `~/.cli_tool/` directory to reset configuration