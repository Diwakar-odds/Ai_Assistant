import json
import gzip
import random
import itertools
from pathlib import Path

# Templates covering OS automation, Docker, Web, Git, etc.
actions = {
    # System & App Commands
    "open_app": {
        "targets": ["notepad", "chrome", "whatsapp", "calculator", "vscode", "spotify", "discord", "settings"],
        "verbs": ["khol do", "open karo", "chalu karo", "start karo", "launch karo", "kholo", "chalu kar de", "khol de"],
        "tool_call": lambda t: {"name": "system_tools", "arguments": json.dumps({"action": "open_app", "app": t})}
    },
    "close_app": {
        "targets": ["notepad", "chrome", "whatsapp", "calculator", "vscode", "spotify", "discord"],
        "verbs": ["band kar do", "close karo", "kill karo", "hatao", "band kro", "band kar de"],
        "tool_call": lambda t: {"name": "system_tools", "arguments": json.dumps({"action": "close_app", "app": t})}
    },
    "volume_control": {
        "targets": ["volume", "awaaz", "sound", "awaz"],
        "verbs": ["full kar do", "tej karo", "badha do", "max karo", "kam karo", "slow karo", "mute kar do", "band kar do"],
        "tool_call": lambda t: {"name": "system_tools", "arguments": json.dumps({"action": "volume_adjust", "level": "auto"})}
    },
    "search_web": {
        "targets": ["youtube", "google", "wikipedia", "internet"],
        "verbs": ["pe search karo", "kholo aur dhoondo", "pe dhoondna", "pe kuch search mar do"],
        "tool_call": lambda t: {"name": "web_tools", "arguments": json.dumps({"action": "search", "engine": t})}
    },
    "docker_manage": {
        "targets": ["redis", "postgres", "mysql", "mongodb", "nginx", "frontend", "backend"],
        "verbs": ["spin up kar do", "start kar do", "chala do", "up karo", "docker compose up mar do", "restart maar do", "band kar do"],
        "tool_call": lambda t: {"name": "developer_tools", "arguments": json.dumps({"action": "docker_manage", "target": t})}
    },
    "git_action": {
        "targets": ["origin main", "master branch", "dev branch", "repo", "changes", "code"],
        "verbs": ["me push maar de", "pull kar lo", "commit kar do", "pe push karo", "sync kar do", "ka status dikhao"],
        "tool_call": lambda t: {"name": "developer_tools", "arguments": json.dumps({"action": "git_action", "target": t})}
    },
    "screenshot": {
        "targets": ["screenshot", "screen ka photo", "snip"],
        "verbs": ["le lo", "kheench lo", "capture karo", "nikalo", "le le"],
        "tool_call": lambda t: {"name": "system_tools", "arguments": json.dumps({"action": "take_screenshot"})}
    }
}

prefixes = ["Yaar", "Bhai", "Suno,", "Oye,", "Ek kaam karo,", "Jaldi se", "Fatafat", "Abhi ke abhi", "Bro", ""]
mid_fillers = ["zara", "please", "thoda", "abhi", "ekdam se", "bhai", ""]
suffixes = ["jaldi", "fast", "samjhe?", "theek hai?", "abhi!", "yaar", ""]

system_prompt = "You are YourDaddy, the Ultimate Enterprise Windows OS Assistant. You have deep OS access, agentic reasoning, and multi-modal vision. Execute user commands purely via JSON tool calls across English, Hindi, and Hinglish."

def generate_combinations(target_count):
    dataset = []
    
    print(f"Generating {target_count} synthetic Hinglish commands...")
    
    action_keys = list(actions.keys())
    
    while len(dataset) < target_count:
        action_key = random.choice(action_keys)
        action_data = actions[action_key]
        
        target = random.choice(action_data["targets"])
        verb = random.choice(action_data["verbs"])
        
        prefix = random.choice(prefixes)
        mid = random.choice(mid_fillers)
        suffix = random.choice(suffixes)
        
        parts = [prefix, target, mid, verb, suffix]
        sentence = " ".join([p for p in parts if p]).strip()
        sentence = " ".join(sentence.split())
        
        row = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": sentence},
                {"role": "assistant", "tool_calls": [
                    {
                        "type": "function",
                        "function": action_data["tool_call"](target)
                    }
                ]}
            ]
        }
        
        dataset.append(row)
        
        if len(dataset) % 50000 == 0:
            print(f"Generated {len(dataset)} / {target_count}...")
            
    return dataset

def main():
    target_count = 250000  # 2.5 Lakh rows
    
    output_path = Path("d:/Projects/Ai_Assistant/data/training/hinglish_commands_v4.jsonl.gz")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    dataset = generate_combinations(target_count)
    
    print(f"Saving dataset to {output_path}...")
    with gzip.open(output_path, 'wt', encoding='utf-8') as f:
        for row in dataset:
            f.write(json.dumps(row) + "\\n")
            
    print("Done! Dataset is ready for 12-hour training run.")

if __name__ == "__main__":
    main()
