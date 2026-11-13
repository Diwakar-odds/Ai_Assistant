import json
import random
import os
from pathlib import Path

# ==========================================
# 🧠 ENTERPRISE MULTI-LANGUAGE INTENT MATRIX
# ==========================================

# We map 3 languages: english, hindi, hinglish
# Target categories: dev, student, pro, general, vision, web

INTENT_MATRIX = {
    # ---------------- DEVELOPER PERSONA ---------------- #
    "dev_start_server": {
        "tool_name": "developer_tools", "action": "run_command",
        "verbs": {
            "en": ["start the local server", "run localhost", "boot up the dev server", "start npm run dev"],
            "hi": ["local server chalu karo", "localhost shuru kijiye", "npm run dev chalaiye"],
            "hinglish": ["bhai server start kar de", "localhost on kar", "npm chala de fatak se"]
        },
        "targets": ["port 3000", "port 8080", "react app", "flask backend", "vite"]
    },
    "dev_docker": {
        "tool_name": "developer_tools", "action": "docker_manage",
        "verbs": {
            "en": ["restart docker container", "spin up docker compose", "kill docker container"],
            "hi": ["docker container band karke chalu karo", "docker compose shuru kijiye"],
            "hinglish": ["docker restart maar", "container uda de bhai", "docker compose up kar"]
        },
        "targets": ["database", "redis", "postgres", "frontend", "all containers"]
    },
    "dev_git": {
        "tool_name": "developer_tools", "action": "git_action",
        "verbs": {
            "en": ["push the code", "pull latest changes", "commit this", "check git status"],
            "hi": ["code push kardo", "latest changes pull kijiye", "git status check karo"],
            "hinglish": ["bhai code push maar de", "pull lele master se", "commit kar de yaar"]
        },
        "targets": ["origin main", "master branch", "feature branch", "upstream"]
    },
    "dev_open_ide": {
        "tool_name": "system_automation", "action": "open_app",
        "verbs": {
            "en": ["open my IDE", "launch visual studio code", "start pycharm"],
            "hi": ["code editor kholiye", "IDE shuru karein"],
            "hinglish": ["vscode khol de bhai", "pycharm chala", "editor khol"]
        },
        "targets": ["vscode", "pycharm", "intellij", "sublime text", "vim"]
    },

    # ---------------- PROFESSIONAL PERSONA ---------------- #
    "pro_schedule": {
        "tool_name": "productivity_tools", "action": "schedule_meeting",
        "verbs": {
            "en": ["schedule a meeting", "book a calendar slot", "set up a call"],
            "hi": ["ek meeting schedule kijiye", "calendar me time block karein"],
            "hinglish": ["meeting fix kar de", "calendar me slot daal de", "call set kar"]
        },
        "targets": ["for tomorrow", "with the team", "at 5 PM", "with client"]
    },
    "pro_email": {
        "tool_name": "productivity_tools", "action": "send_email",
        "verbs": {
            "en": ["send an email", "draft an email", "reply to this thread"],
            "hi": ["ek email bhejiye", "email likhiye"],
            "hinglish": ["mail bhej de", "is mail ka reply likh", "draft bana de bhai"]
        },
        "targets": ["to boss", "to client", "to marketing team", "about the project"]
    },
    "pro_apps": {
        "tool_name": "system_automation", "action": "open_app",
        "verbs": {
            "en": ["open the spreadsheet", "launch teams", "start outlook", "open word document"],
            "hi": ["excel sheet kholiye", "teams shuru karein", "word file kholiye"],
            "hinglish": ["excel khol de", "teams on kar", "outlook chala yaar", "ppt khol"]
        },
        "targets": ["excel", "teams", "outlook", "powerpoint", "zoom", "slack"]
    },

    # ---------------- STUDENT PERSONA ---------------- #
    "student_research": {
        "tool_name": "web_navigation", "action": "search_wiki",
        "verbs": {
            "en": ["look up on wikipedia", "find information about", "search for the topic"],
            "hi": ["wikipedia par dhundhiye", "iske baare me jankari nikaliye"],
            "hinglish": ["wiki pe search kar", "topic ke baare me bata", "jaldi se research kar"]
        },
        "targets": ["quantum physics", "world war 2", "machine learning", "black holes"]
    },
    "student_focus": {
        "tool_name": "system_settings", "action": "toggle_focus_mode",
        "verbs": {
            "en": ["turn on focus mode", "enable do not disturb", "block notifications"],
            "hi": ["focus mode chalu karein", "notifications band kijiye"],
            "hinglish": ["dnd laga de", "focus mode on kar bhai", "notification mute kar sab"]
        },
        "targets": ["for 2 hours", "until evening", "now"]
    },
    "student_notes": {
        "tool_name": "system_automation", "action": "open_app",
        "verbs": {
            "en": ["open my notes", "launch notion", "start evernote"],
            "hi": ["notes app kholiye", "notion shuru karein"],
            "hinglish": ["notion khol de", "notes nikal", "evernote chala"]
        },
        "targets": ["notion", "evernote", "onenote", "obsidian"]
    },

    # ---------------- GENERAL OS & INTEGRATIONS ---------------- #
    "system_toggle_wifi": {
        "tool_name": "system_settings", "action": "toggle_wifi",
        "verbs": {
            "en": ["turn on the wifi", "disconnect internet", "disable wifi"],
            "hi": ["wifi on kijiye", "internet band kardo", "wifi chalu karo"],
            "hinglish": ["net band kar de", "wifi uda de", "net on kar bhai"]
        },
        "targets": ["on", "off", "connect", "disconnect"]
    },
    "system_volume": {
        "tool_name": "system_automation", "action": "set_volume",
        "verbs": {
            "en": ["increase volume", "decrease sound", "mute the pc", "set volume to max"],
            "hi": ["awaaz badhaiye", "awaaz kam kijiye", "chup kijiye"],
            "hinglish": ["volume bada de", "awaaz kam kar", "mute maar isko", "full sound kar"]
        },
        "targets": ["100", "50", "0", "max", "mute"]
    },
    "vision_ocr": {
        "tool_name": "vision_agent", "action": "extract_text",
        "verbs": {
            "en": ["extract text from this image", "read what's on the screen", "run OCR"],
            "hi": ["is chitra se text nikaliye", "screen par kya likha hai padiye"],
            "hinglish": ["is photo se text nikal", "screen padh ke bata", "ocr chala is pe"]
        },
        "targets": ["from image", "from screenshot", "from current window"]
    },
    "web_scrape": {
        "tool_name": "web_agent", "action": "scrape_content",
        "verbs": {
            "en": ["summarize this article", "scrape the page", "extract data from this link"],
            "hi": ["is lekh ka saar banaiye", "is page se data nikaliye"],
            "hinglish": ["article short me bata", "page scrape maar de", "link se data nikal"]
        },
        "targets": ["news article", "blog post", "wikipedia page", "research paper"]
    }
}

# Add general App Open/Close intents dynamically to inflate combinations
COMMON_APPS = ["chrome", "notepad", "spotify", "calculator", "settings", "discord", "whatsapp", "telegram", "terminal", "powershell", "task manager", "control panel", "event viewer", "registry editor", "paint", "photos", "camera", "weather", "calendar", "mail"]

INTENT_MATRIX["general_open_app"] = {
    "tool_name": "system_automation", "action": "open_app",
    "verbs": {
        "en": ["open", "launch", "start", "boot up"],
        "hi": ["kholiye", "shuru karein", "chalaiye"],
        "hinglish": ["khol de bhai", "on kar de", "chala de yaar"]
    },
    "targets": COMMON_APPS
}

INTENT_MATRIX["general_close_app"] = {
    "tool_name": "system_automation", "action": "close_app",
    "verbs": {
        "en": ["close", "exit", "kill", "shut down"],
        "hi": ["band kijiye", "hataiye"],
        "hinglish": ["band kar de", "uda de bhai", "hata isko", "kill maar"]
    },
    "targets": COMMON_APPS
}

PREFIXES = {
    "en": ["Please ", "Hey AI, ", "Can you ", "Just ", ""],
    "hi": ["Kripya ", "Suniye, ", "Zara ", ""],
    "hinglish": ["Bhai ", "Yaar ", "Fatak se ", "Jaldi ", "Dekh bhai ", "Sun ", ""]
}
SUFFIXES = {
    "en": [" immediately.", " for me.", " right now.", " please.", ""],
    "hi": [" jaldi se.", " kripya.", " abhi.", ""],
    "hinglish": [" jaldi.", " yaar.", " bhai.", " fatak se.", " abhi ke abhi.", ""]
}

def generate_enterprise_dataset(total_samples=2500000, batch_size=50000):
    """
    Generates a massive dataset in streaming batches to prevent memory overflow.
    2,500,000 samples will take roughly 2-5 minutes to generate and write to disk.
    """
    out_dir = Path("d:/Projects/Ai_Assistant/data/training")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "ultimate_windows_dataset_v3.jsonl"
    
    # We open in write mode first to clear any old file
    with open(out_file, "w", encoding="utf-8") as f:
        pass
        
    generated_count = 0
    intent_keys = list(INTENT_MATRIX.keys())
    langs = ["en", "hi", "hinglish"]
    
    print(f"Starting Massive Dataset Generation: Target {total_samples} lines...")
    
    # Open in append mode for streaming
    with open(out_file, "a", encoding="utf-8") as f:
        while generated_count < total_samples:
            batch = []
            
            # Generate a batch of size batch_size
            for _ in range(min(batch_size, total_samples - generated_count)):
                intent_key = random.choice(intent_keys)
                intent = INTENT_MATRIX[intent_key]
                
                lang = random.choice(langs)
                
                verb = random.choice(intent["verbs"][lang])
                target = random.choice(intent["targets"])
                prefix = random.choice(PREFIXES[lang])
                suffix = random.choice(SUFFIXES[lang])
                
                # Construct the prompt based on language structure
                if lang == "hi" or lang == "hinglish":
                    # Hindi/Hinglish often puts verb at the end: "Chrome khol de"
                    user_prompt = f"{prefix}{target} {verb}{suffix}".strip()
                else:
                    # English often puts verb first: "Open Chrome"
                    user_prompt = f"{prefix}{verb} {target}{suffix}".strip()
                    
                user_prompt = " ".join(user_prompt.split())
                
                arguments = {"action": intent["action"], "target": target}
                
                message = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are Pulsar, the Ultimate Enterprise Windows OS Assistant. You have deep OS access, agentic reasoning, and multi-modal vision. Execute user commands purely via JSON tool calls across English, Hindi, and Hinglish."
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        },
                        {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "function": {
                                        "name": intent["tool_name"],
                                        "arguments": json.dumps(arguments)
                                    }
                                }
                            ]
                        }
                    ]
                }
                
                batch.append(message)
                
            # Write the batch to disk to clear memory
            for item in batch:
                f.write(json.dumps(item, ensure_ascii=False) + "\n\n# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

")
                
            generated_count += len(batch)
            print(f"Progress: {generated_count:,} / {total_samples:,} lines generated...", flush=True)

    print(f"EXHAUSTIVE DATASET COMPLETE! Saved to: {out_file}")

if __name__ == "__main__":
    generate_enterprise_dataset(total_samples=2500000, batch_size=100000)
