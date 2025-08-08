import json
from pathlib import Path
from typing import Dict, Any

class Config:
    def __init__(self):
        self.config_dir = Path.home() / ".cli_tool"
        self.config_file = self.config_dir / "config.json"
        self.session_file = self.config_dir / "session.json"
        self.config_dir.mkdir(exist_ok=True)
        
        self.default_config = {
            # Function calling capable models: qwen3:30b-a3b-instruct-2507-q4_K_M, qwen2.5:0.5b, mistral:7b-instruct (text-based)
            # Non-function calling models: qwen3-coder:latest, codestral:latest, gemma3:27b
            "default_model": "qwen3:30b-a3b-instruct-2507-q4_K_M",  # Supports true OpenAI-style function calling
            "default_host": "localhost:11434",
            "max_history": 50,
            "save_sessions": True,
            "max_context_tokens": 8000,
            "auto_summarize": True
        }
        
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return {**self.default_config, **json.load(f)}
            except (json.JSONDecodeError, IOError):
                pass
        return self.default_config.copy()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError:
            pass
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()
    
    def save_session(self, messages: list):
        """Save session messages"""
        if not self.get("save_sessions"):
            return
            
        try:
            with open(self.session_file, 'w') as f:
                json.dump(messages[-self.get("max_history"):], f, indent=2)
        except IOError:
            pass
    
    def load_session(self) -> list:
        """Load previous session messages"""
        if not self.get("save_sessions") or not self.session_file.exists():
            return []
            
        try:
            with open(self.session_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def clear_session(self):
        """Clear/reset the current session"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
        except IOError:
            pass