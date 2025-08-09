"""
__all__ = ['TodoManager', 'add_todo', 'list_todos', 'update_todo_status', 'remove_todo', 'get_todo', 'clear_completed', 'get_summary']

TODO Management Tool for FounderAI
Allows tracking tasks across sessions and projects.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class TodoManager:
    def __init__(self, project_root: str = None):
        """Initialize TODO manager with project-specific or global storage"""
        if project_root:
            self.todo_file = Path(project_root) / ".founder_todo.json"
        else:
            # Global todos in user config directory
            config_dir = Path.home() / ".cli_tool"
            config_dir.mkdir(exist_ok=True)
            self.todo_file = config_dir / "global_todos.json"
        
        self.todos = self._load_todos()
    
    def _load_todos(self) -> List[Dict[str, Any]]:
        """Load todos from file"""
        if not self.todo_file.exists():
            return []
        
        try:
            with open(self.todo_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_todos(self):
        """Save todos to file"""
        try:
            with open(self.todo_file, 'w') as f:
                json.dump(self.todos, f, indent=2)
        except IOError:
            pass
    
    def add_todo(self, description: str, priority: str = "medium") -> str:
        """Add a new todo item"""
        todo_id = str(uuid.uuid4())[:8]
        todo = {
            "id": todo_id,
            "description": description,
            "priority": priority,  # high, medium, low
            "status": "pending",   # pending, in_progress, completed
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.todos.append(todo)
        self._save_todos()
        return todo_id
    
    def list_todos(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List todos, optionally filtered by status"""
        if status:
            return [todo for todo in self.todos if todo["status"] == status]
        return self.todos.copy()
    
    def update_todo_status(self, todo_id: str, status: str) -> bool:
        """Update todo status (pending, in_progress, completed)"""
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["status"] = status
                todo["updated_at"] = datetime.now().isoformat()
                self._save_todos()
                return True
        return False
    
    def remove_todo(self, todo_id: str) -> bool:
        """Remove a todo item"""
        for i, todo in enumerate(self.todos):
            if todo["id"] == todo_id:
                del self.todos[i]
                self._save_todos()
                return True
        return False
    
    def get_todo(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific todo by ID"""
        for todo in self.todos:
            if todo["id"] == todo_id:
                return todo.copy()
        return None
    
    def clear_completed(self) -> int:
        """Remove all completed todos and return count removed"""
        initial_count = len(self.todos)
        self.todos = [todo for todo in self.todos if todo["status"] != "completed"]
        removed_count = initial_count - len(self.todos)
        
        if removed_count > 0:
            self._save_todos()
        
        return removed_count
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary of todos by status"""
        summary = {"pending": 0, "in_progress": 0, "completed": 0}
        for todo in self.todos:
            status = todo.get("status", "pending")
            if status in summary:
                summary[status] += 1
        return summary