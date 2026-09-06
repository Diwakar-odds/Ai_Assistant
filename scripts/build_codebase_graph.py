import os
import ast
import json
from pathlib import Path

# Configuration
PROJECT_ROOT = r"d:\Projects\Ai_Assistant"
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "shared", "data", "codebase_graph.json")

# Directories to ignore
IGNORE_DIRS = {
    "venv", "node_modules", "__pycache__", ".git", ".vscode", ".gemini", 
    "frontend", "dist", "build", "outputs", "logs", "test_download", ".pytest_cache"
}

def determine_module_tags(relative_path: Path):
    """
    Applies the '2nd Method' Optimization: 
    Automatically generate tags based on directory structure.
    """
    tags = []
    parts = relative_path.parts
    
    if len(parts) > 0:
        main_dir = parts[0]
        if main_dir == "core_ai":
            tags.append("module:core_ai")
            # Deeper inspection for core_ai
            if "agents" in parts:
                tags.append("module:agents")
            elif "ai" in parts:
                tags.append("module:learning_systems")
            elif "voice" in parts:
                tags.append("module:voice")
            elif "vision" in parts:
                tags.append("module:vision")
            elif "automation" in parts:
                tags.append("module:automation")
        elif main_dir == "backend":
            tags.append("module:backend")
            if "routes" in parts:
                tags.append("module:api_routes")
        elif main_dir == "scripts":
            tags.append("module:scripts")
        elif main_dir == "shared":
            tags.append("module:shared_data")
        elif main_dir == "desktop":
            tags.append("module:desktop_integration")
            
    if not tags:
        tags.append("module:root")
        
    return tags

def parse_python_file(filepath):
    """Parses a Python file and extracts its classes and functions."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        classes = []
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "line": node.lineno
                })
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append({
                    "name": node.name,
                    "line": node.lineno
                })
                
        return {"classes": classes, "functions": functions, "error": None}
    except Exception as e:
        return {"classes": [], "functions": [], "error": str(e)}

def build_knowledge_graph():
    print("Starting AST parsing of the monorepo...")
    graph = {
        "metadata": {
            "project": "PULSAR Ai_Assistant",
            "description": "Codebase Knowledge Graph with Module Tags",
            "total_files": 0,
            "total_classes": 0,
            "total_functions": 0
        },
        "nodes": []
    }
    
    root_path = Path(PROJECT_ROOT)
    
    total_files = 0
    total_classes = 0
    total_functions = 0
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Remove ignored directories in place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        
        for filename in filenames:
            if filename.endswith(".py"):
                full_path = Path(dirpath) / filename
                relative_path = full_path.relative_to(root_path)
                
                # Apply the 2nd Method Optimization (Tags)
                tags = determine_module_tags(relative_path)
                
                # Parse AST
                parsed_data = parse_python_file(str(full_path))
                
                node = {
                    "id": str(relative_path),
                    "type": "file",
                    "filename": filename,
                    "path": str(relative_path),
                    "tags": tags,
                    "classes": parsed_data["classes"],
                    "functions": parsed_data["functions"],
                    "parse_error": parsed_data["error"]
                }
                
                graph["nodes"].append(node)
                
                total_files += 1
                total_classes += len(parsed_data["classes"])
                total_functions += len(parsed_data["functions"])

    graph["metadata"]["total_files"] = total_files
    graph["metadata"]["total_classes"] = total_classes
    graph["metadata"]["total_functions"] = total_functions
    
    print(f"Scanning complete! Found {total_files} files, {total_classes} classes, and {total_functions} functions.")
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(graph, f, indent=4)
        
    print(f"Knowledge Graph saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_knowledge_graph()
