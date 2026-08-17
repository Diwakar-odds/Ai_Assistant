import sqlite3
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    from ai_assistant.database_config import get_db_path
except ImportError:
    pass

def update_manual():
    print("Manually enriching profile based on workspace inspection...")
    db_path = "data/personal_knowledge.db"
    
    # Inferred from file structure
    inferred_skills = [
        "Python Development", 
        "React", 
        "AI Architecture", 
        "Data Science",
        "Windows Desktop Development",
        "Mobile Development"
    ]
    
    inferred_interests = [
        "Artificial Intelligence",
        "Voice Assistants",
        "Automation",
        "Cross-platform Development"
    ]
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get User
    cursor.execute("SELECT node_id, content, metadata FROM knowledge_nodes WHERE node_type='person'")
    rows = cursor.fetchall()
    
    user_node_id = None
    user_name = None
    
    for nid, content, meta_json in rows:
        meta = json.loads(meta_json) if meta_json else {}
        if meta.get('is_primary_user'):
            user_node_id = nid
            user_name = content
            break
            
    if not user_node_id and rows:
        user_node_id = rows[0][0]
        user_name = rows[0][1]
        
    if user_node_id:
        print(f"Updating user: {user_name}")
        
        # Add Skills
        for skill in inferred_skills:
            skill_id = f"skill_{hash(skill) % 10000:04d}"
            cursor.execute("INSERT OR IGNORE INTO knowledge_nodes (node_id, content, node_type, importance_score) VALUES (?, ?, 'skill', 0.8)", (skill_id, skill))
            
            edge_id = f"edge_{hash(user_node_id + skill_id) % 10000:04d}"
            cursor.execute("INSERT OR IGNORE INTO knowledge_edges (edge_id, source_node, target_node, relationship_type, strength) VALUES (?, ?, ?, 'has_skill', 0.8)", 
                          (edge_id, user_node_id, skill_id))
            print(f"  + Added Skill: {skill}")

        # Add Interests
        for interest in inferred_interests:
            topic_id = f"topic_{hash(interest) % 10000:04d}"
            cursor.execute("INSERT OR IGNORE INTO knowledge_nodes (node_id, content, node_type, importance_score) VALUES (?, ?, 'topic', 0.7)", (topic_id, interest))
            
            edge_id = f"edge_{hash(user_node_id + topic_id) % 10000:04d}"
            cursor.execute("INSERT OR IGNORE INTO knowledge_edges (edge_id, source_node, target_node, relationship_type, strength) VALUES (?, ?, ?, 'interested_in', 0.8)", 
                          (edge_id, user_node_id, topic_id))
            print(f"  + Added Interest: {interest}")
            
        print("✅ Data successfully saved to personal_knowledge.db")
    else:
        print("❌ No user profile found to update.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_manual()
