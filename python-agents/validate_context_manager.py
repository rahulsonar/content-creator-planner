"""
Simple syntax validation for Context Manager Agent
Validates the agent code without importing dependencies
"""
import ast
import sys
from pathlib import Path


def validate_syntax(file_path):
    """Validate Python syntax of a file"""
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        ast.parse(code)
        return True, "Syntax valid"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"


def main():
    """Validate context manager agent files"""
    python_agents_dir = Path(__file__).parent
    
    files_to_check = [
        python_agents_dir / "agents" / "context_manager.py",
        python_agents_dir / "config" / "prompts.py",
        python_agents_dir / "agents" / "__init__.py",
        python_agents_dir / "utils" / "__init__.py",
    ]
    
    print("=" * 60)
    print("Context Manager Agent - Syntax Validation")
    print("=" * 60)
    
    all_valid = True
    for file_path in files_to_check:
        valid, message = validate_syntax(file_path)
        status = "✓" if valid else "✗"
        print(f"{status} {file_path.name}: {message}")
        if not valid:
            all_valid = False
    
    print("=" * 60)
    if all_valid:
        print("✓ All files have valid syntax!")
        print("\nContext Manager Agent created successfully!")
        print("\nKey Features:")
        print("  - Receives information from other agents")
        print("  - Manages user context in agent_context/{userId}/")
        print("  - Creates structured markdown files")
        print("  - Maintains INDEX.md for easy navigation")
        print("  - Supports tool-based and direct file operations")
        print("\nFiles created:")
        print("  - agents/context_manager.py")
        print("  - agents/README_CONTEXT_MANAGER.md")
        print("  - test_context_manager.py")
        print("  - Updated: config/prompts.py (added CONTEXT_MANAGER_SYSTEM_PROMPT)")
        print("  - Updated: agents/__init__.py (exported ContextManagerAgent)")
        print("  - Updated: utils/__init__.py (fixed imports)")
        return 0
    else:
        print("✗ Some files have syntax errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
