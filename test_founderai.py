#!/usr/bin/env python3
"""
Test script for FounderAI functionality
"""

import subprocess
import sys
import os

def test_basic_functionality():
    """Test basic FounderAI functionality"""
    print("🧪 Testing FounderAI Basic Functionality")
    print("=" * 50)
    
    # Test help
    print("\n1. Testing --help:")
    result = subprocess.run([sys.executable, "-m", "src.main", "--help"], 
                          capture_output=True, text=True)
    print(f"✅ Help command works: {result.returncode == 0}")
    
    # Test config
    print("\n2. Testing --config:")
    result = subprocess.run([sys.executable, "-m", "src.main", "--config"], 
                          capture_output=True, text=True)
    print(f"✅ Config command works: {result.returncode == 0}")
    if result.returncode == 0:
        print("Config output:", result.stdout[:200] + "...")
    
    # Test no-tools mode
    print("\n3. Testing --no-tools mode:")
    result = subprocess.run([sys.executable, "-m", "src.main", "--no-tools", "Hello"], 
                          capture_output=True, text=True, timeout=30)
    print(f"✅ No-tools mode works: {result.returncode == 0}")
    
    # Test with tools (may fallback to no tools)
    print("\n4. Testing with tools:")
    result = subprocess.run([sys.executable, "-m", "src.main", "What files are in this directory?"], 
                          capture_output=True, text=True, timeout=30)
    print(f"✅ Tools mode works: {result.returncode == 0}")
    if result.returncode == 0:
        print("Response snippet:", result.stdout[-200:])

def test_todo_manager():
    """Test TODO manager functionality"""
    print("\n🧪 Testing TODO Manager")
    print("=" * 50)
    
    try:
        from src.todo_manager import TodoManager
        
        # Test creating a todo manager
        todo_mgr = TodoManager()
        print("✅ TodoManager created successfully")
        
        # Test adding todos
        todo_id1 = todo_mgr.add_todo("Test task 1", "high")
        todo_id2 = todo_mgr.add_todo("Test task 2", "medium")
        print(f"✅ Added todos: {todo_id1}, {todo_id2}")
        
        # Test listing todos
        todos = todo_mgr.list_todos()
        print(f"✅ Listed {len(todos)} todos")
        
        # Test updating todo
        success = todo_mgr.update_todo_status(todo_id1, "completed")
        print(f"✅ Updated todo status: {success}")
        
        # Test summary
        summary = todo_mgr.get_summary()
        print(f"✅ Summary: {summary}")
        
        # Clean up
        todo_mgr.remove_todo(todo_id1)
        todo_mgr.remove_todo(todo_id2)
        print("✅ Cleaned up test todos")
        
    except Exception as e:
        print(f"❌ TODO manager test failed: {e}")

def test_file_tools():
    """Test file system tools"""
    print("\n🧪 Testing File System Tools")
    print("=" * 50)
    
    try:
        from src.main import FileSystemTools
        
        fs_tools = FileSystemTools()
        
        # Test listing directory
        items = fs_tools.list_directory(".")
        print(f"✅ Listed directory: found {len(items)} items")
        
        # Test writing and reading a file
        test_file = "test_founder.txt"
        test_content = "Hello from FounderAI test!"
        
        write_result = fs_tools.write_file(test_file, test_content)
        print(f"✅ Wrote file: {write_result}")
        
        read_content = fs_tools.read_file(test_file)
        print(f"✅ Read file: content matches = {read_content == test_content}")
        
        # Test shell command
        shell_result = fs_tools.run_shell_command("echo 'Hello from shell'")
        print(f"✅ Shell command: {shell_result['success']}")
        if shell_result['success']:
            print(f"   Output: {shell_result['stdout'].strip()}")
        
        # Test git command
        git_result = fs_tools.git_command("status")
        print(f"✅ Git command: {git_result['success']}")
        
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
            print("✅ Cleaned up test file")
            
    except Exception as e:
        print(f"❌ File tools test failed: {e}")

def main():
    """Run all tests"""
    print("🚀 FounderAI Test Suite")
    print("=" * 50)
    
    test_basic_functionality()
    test_todo_manager()
    test_file_tools()
    
    print("\n🎉 Test suite completed!")
    print("\nℹ️  Note: If some tests show function calling errors, that's expected")
    print("   as many Ollama models don't support OpenAI-style function calling.")
    print("   The application will fall back to text-based responses.")

if __name__ == "__main__":
    main()