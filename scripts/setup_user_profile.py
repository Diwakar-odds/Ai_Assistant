#!/usr/bin/env python3
"""
Setup User Profile
Introduces the user to the AI by adding them to the personal knowledge graph.
"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    from ai_assistant.core.database_config import get_db_path
    print("✅ Successfully imported AI modules")
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

def init_knowledge_db(db_path):
    """Initialize the knowledge graph tables if they don't exist"""
    print(f"Checking database at: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Knowledge graph nodes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            node_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            node_type TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            importance_score REAL DEFAULT 0.5
        )
    ''')
    
    # Knowledge graph edges
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_edges (
            edge_id TEXT PRIMARY KEY,
            source_node TEXT NOT NULL,
            target_node TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            strength REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_node) REFERENCES knowledge_nodes (node_id),
            FOREIGN KEY (target_node) REFERENCES knowledge_nodes (node_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database tables verified")

def main():
    print("\n" + "="*50)
    print("AI ASSISTANT - USER INTRODUCTION")
    print("="*50)
    
    try:
        db_path = get_db_path('personal_knowledge')
        init_knowledge_db(db_path)
        
        kg = PersonalKnowledgeGraph(str(db_path))
        
        print("\nI'd like to get to know you better so I can serve you better.")
        print("Please answer the following questions to build your detailed profile.")
        
        # 1. Basic Identity
        name = input("\n1. What is your name? (Required): ").strip()
        while not name:
            name = input("Please enter your name: ").strip()
            
        role_input = input(f"2. What is your role regarding this AI? (e.g., Creator, Developer, User) [Default: Creator]: ").strip()
        role = role_input if role_input else "Creator"
        
        location = input("3. Where are you based? (City/Timezone) [Optional]: ").strip()

        # 2. Preferences
        print("\n--- Communication Preferences ---")
        style = input("4. How do you prefer I communicate? (e.g., Concise & Direct, Detailed & Explanatory, Casual & Fun, Technical) [Default: Concise]: ").strip()
        if not style:
            style = "Concise"
            
        print("\n--- Expertise & Interests ---")
        interests_input = input("5. What are your main interests/hobbies? (comma separated): ").strip()
        interests = [i.strip() for i in interests_input.split(',')] if interests_input else []
        
        skills_input = input("6. What are your technical skills or areas of expertise? (comma separated): ").strip()
        skills = [s.strip() for s in skills_input.split(',')] if skills_input else []

        print("\n--- Goals & Workflow ---")
        goals_input = input("7. What are your main goals for using this AI? (comma separated): ").strip()
        goals = [g.strip() for g in goals_input.split(',')] if goals_input else []

        work_pattern = input("8. When are you typically most active? (e.g., Early Morning, Late Night, 9-5) [Optional]: ").strip()
        
        print(f"\nBuilding detailed profile for {name}...")
        
        # Add User Node with RICH metadata
        user_metadata = {
            "role": role,
            "is_primary_user": True,
            "interests": interests,
            "location": location,
            "communication_style": style,
            "skills": skills,
            "goals": goals,
            "work_pattern": work_pattern,
            "full_profile_complete": True
        }
        user_node_id = kg.add_knowledge_node(name, "person", user_metadata)
        
        # Add Role Node
        role_node_id = kg.add_knowledge_node(role, "role", {})
        kg.add_relationship(user_node_id, role_node_id, "has_role", strength=1.0)
        
        # Add Interests
        for interest in interests:
            if interest:
                interest_node_id = kg.add_knowledge_node(interest, "topic", {})
                kg.add_relationship(user_node_id, interest_node_id, "interested_in", strength=0.8)

        # Add Skills
        for skill in skills:
            if skill:
                skill_node_id = kg.add_knowledge_node(skill, "skill", {})
                kg.add_relationship(user_node_id, skill_node_id, "has_skill", strength=0.9)

        # Add Goals
        for goal in goals:
            if goal:
                goal_node_id = kg.add_knowledge_node(goal, "goal", {})
                kg.add_relationship(user_node_id, goal_node_id, "aims_for", strength=1.0)
        
        # Add "Creator" relationship if applicable
        if role.lower() in ["creator", "maker", "author", "developer", "architect"]:
            ai_node_id = kg.add_knowledge_node("AI Assistant", "system", {})
            kg.add_relationship(user_node_id, ai_node_id, "created", strength=1.0)
        
        print(f"\n✅ Profile Updated Successfully!")
        print(f"I currently know about your:")
        print(f"- Role: {role}")
        print(f"- Interests: {len(interests)} items")
        print(f"- Skills: {len(skills)} items")
        print(f"- Goals: {len(goals)} items")
        print(f"- Communication Style: {style}")
        print("\nNext time we talk, I'll tailor my responses to this profile.")
        
    except Exception as e:
        print(f"\n❌ Error updating profile: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
