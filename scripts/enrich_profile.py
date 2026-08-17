import sqlite3
import json
import os
import sys
from pathlib import Path
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    from ai_assistant.database_config import get_db_path
except ImportError:
    # Fallback if imports fail
    pass

LOG_FILE = "enrichment_log.txt"

def log(msg):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def analyze_workspace():
    """Analyze current workspace to deduce skills"""
    skills = []
    interests = []
    
    # Check for specific files/dirs
    if os.path.exists("pyproject.toml") or os.path.exists("requirements.txt"):
        skills.append("Python")
        skills.append("Dependency Management")
        
    if os.path.exists("package.json"):
        skills.append("JavaScript")
        skills.append("Node.js")
        
        # Check for React
        try:
            with open("package.json") as f:
                content = f.read()
                if "react" in content:
                    skills.append("React")
                    skills.append("Frontend Development")
        except:
            pass

    # Check AI specific files
    ai_files = [f for f in os.listdir(".") if "ai" in f.lower() or "llm" in f.lower()]
    if ai_files or os.path.exists("ai_assistant"):
        skills.append("AI Development")
        skills.append("Machine Learning")
        interests.append("Artificial Intelligence")
        interests.append("Automation")

    return list(set(skills)), list(set(interests))

def analyze_app_usage(db_path):
    """Analyze app usage database for patterns"""
    if not os.path.exists(db_path):
        return [], []
        
    skills = []
    interests = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_usage'")
        if cursor.fetchone():
            cursor.execute("SELECT app_name, duration_seconds FROM app_usage ORDER BY duration_seconds DESC LIMIT 20")
            rows = cursor.fetchall()
            
            for app, _ in rows:
                app_lower = app.lower()
                if "code" in app_lower or "visual studio" in app_lower:
                    skills.append("Software Engineering")
                    interests.append("Coding")
                elif "chrome" in app_lower or "edge" in app_lower:
                    pass
                elif "python" in app_lower:
                    skills.append("Python")
                elif "spotify" in app_lower:
                    interests.append("Music")
    except Exception as e:
        log(f"Error analyzing app usage: {e}")
        
    return list(set(skills)), list(set(interests))

def update_profile():
    log("Starting Profile Analysis & Enrichment...")
    
    # 1. Workspace Analysis
    ws_skills, ws_interests = analyze_workspace()
    log(f"Analyzed Workspace - Skills: {ws_skills}, Interests: {ws_interests}")
    
    # 2. App Usage Analysis
    app_db = "data/app_usage.db"
    app_skills, app_interests = analyze_app_usage(app_db)
    log(f"Analyzed App Usage - Skills: {app_skills}, Interests: {app_interests}")
    
    # Merge findings
    new_skills = list(set(ws_skills + app_skills))
    new_interests = list(set(ws_interests + app_interests))
    
    # 3. Update Knowledge Graph
    try:
        kg_db = "data/personal_knowledge.db"
        if not os.path.exists(kg_db):
            log("Personal knowledge DB not found. Run setup first.")
            return

        kg = PersonalKnowledgeGraph(kg_db)
        
        # Find user node
        conn = sqlite3.connect(kg_db)
        cursor = conn.cursor()
        cursor.execute("SELECT node_id, content, metadata FROM knowledge_nodes WHERE node_type='person'")
        rows = cursor.fetchall()
        
        user_node_id = None
        user_name = None
        current_metadata = {}
        
        for nid, content, meta_json in rows:
            meta = json.loads(meta_json) if meta_json else {}
            if meta.get('is_primary_user'):
                user_node_id = nid
                user_name = content
                current_metadata = meta
                break
        
        # Fallback
        if not user_node_id and rows:
            user_node_id = rows[0][0]
            user_name = rows[0][1]
            current_metadata = json.loads(rows[0][2]) if rows[0][2] else {}

        if user_node_id:
            log(f"Updating profile for: {user_name}")
            
            # Merge Metadata Lists
            current_skills = set(current_metadata.get('skills', []))
            current_interests = set(current_metadata.get('interests', []))
            
            updated_skills = list(current_skills.union(new_skills))
            updated_interests = list(current_interests.union(new_interests))
            
            # Update Metadata in DB
            current_metadata['skills'] = updated_skills
            current_metadata['interests'] = updated_interests
            
            cursor.execute("UPDATE knowledge_nodes SET metadata = ? WHERE node_id = ?", 
                          (json.dumps(current_metadata), user_node_id))
            conn.commit()
            
            # Add Graph Nodes/Edges
            for skill in new_skills:
                if skill not in current_skills:
                    s_id = kg.add_knowledge_node(skill, "skill", {"inferred": True})
                    kg.add_relationship(user_node_id, s_id, "has_skill", 0.7)
                    log(f"  + Added Skill: {skill}")
            
            for interest in new_interests:
                if interest not in current_interests:
                    i_id = kg.add_knowledge_node(interest, "topic", {"inferred": True})
                    kg.add_relationship(user_node_id, i_id, "interested_in", 0.6)
                    log(f"  + Added Interest: {interest}")
                    
            log("\n✅ Profile successfully enriched with analysis data!")
        else:
            log("❌ User profile not found. Please run setup_user_profile.py first.")
            
        conn.close()
        
    except Exception as e:
        log(f"Error updating profile: {e}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    update_profile()
