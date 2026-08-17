import json
import random
import os
from pathlib import Path

# Exhaustive OS Intents, Settings, AI Integrations, and File Management
INTENTS = {
    # ---------------- APP MANAGEMENT ---------------- #
    "open_app": {
        "tool_name": "system_automation", "action": "open_app",
        "hinglish_verbs": ["khol do", "open kar", "start kar de", "chala de", "khol de bhai", "on kar de", "launch kar"],
        "targets": ["chrome", "notepad", "spotify", "vscode", "settings", "calculator", "discord", "whatsapp", "telegram", "word", "excel", "powerpoint", "steam", "epic games", "task manager", "control panel", "terminal", "powershell", "registry editor"]
    },
    "close_app": {
        "tool_name": "system_automation", "action": "close_app",
        "hinglish_verbs": ["band kar", "close kar de", "hata de", "kill kar", "band kro", "off kar de", "bhai hata isko", "exit kar"],
        "targets": ["chrome", "notepad", "spotify", "vscode", "discord", "whatsapp", "word", "excel", "active window", "sab kuch", "all apps"]
    },
    "minimize_window": {
        "tool_name": "system_automation", "action": "minimize_window",
        "hinglish_verbs": ["minimize kar", "niche kar de", "chhupa de", "hide kar", "chota kar de"],
        "targets": ["chrome", "spotify", "current window", "active app", "is window ko"]
    },
    "maximize_window": {
        "tool_name": "system_automation", "action": "maximize_window",
        "hinglish_verbs": ["maximize kar", "bada kar de", "full screen kar", "zoom kar de"],
        "targets": ["current window", "active app", "chrome", "video"]
    },

    # ---------------- POWER & SYSTEM TOGGLES ---------------- #
    "shutdown": {
        "tool_name": "system_automation", "action": "shutdown_pc",
        "hinglish_verbs": ["pc band kar de", "shutdown kar", "system off kar", "laptop band kar do", "shut down kar de"],
        "targets": ["now", "immediately", "bhai", "fast"]
    },
    "restart": {
        "tool_name": "system_automation", "action": "restart_pc",
        "hinglish_verbs": ["restart kar", "reboot kar de", "phir se chalu kar", "laptop restart maar"],
        "targets": ["now", "immediately", "jaldi"]
    },
    "sleep_lock": {
        "tool_name": "system_automation", "action": "sleep_pc",
        "hinglish_verbs": ["sleep me daal", "lock kar de", "screen lock kar", "pc lock kar de"],
        "targets": ["now", "immediately"]
    },
    "toggle_wifi": {
        "tool_name": "system_settings", "action": "toggle_wifi",
        "hinglish_verbs": ["wifi on kar", "wifi band kar", "internet connect kar", "net chala de", "wifi disable kar"],
        "targets": ["on", "off", "connect", "disconnect"]
    },
    "toggle_bluetooth": {
        "tool_name": "system_settings", "action": "toggle_bluetooth",
        "hinglish_verbs": ["bluetooth on kar", "bluetooth band kar de", "bt connect kar", "earpods connect kar"],
        "targets": ["on", "off"]
    },
    "toggle_dark_mode": {
        "tool_name": "system_settings", "action": "set_theme",
        "hinglish_verbs": ["dark mode laga", "light mode kar de", "theme change kar", "aankh me lag raha hai dark kar"],
        "targets": ["dark", "light", "toggle"]
    },

    # ---------------- MEDIA & DISPLAY ---------------- #
    "set_volume": {
        "tool_name": "system_automation", "action": "set_volume",
        "hinglish_verbs": ["volume badha", "awaaz tez kar", "volume full kar", "awaaz kam kar", "sound adjust kar"],
        "targets": ["100", "50", "80", "20", "up", "down", "max", "full"]
    },
    "mute": {
        "tool_name": "system_automation", "action": "set_volume",
        "hinglish_verbs": ["mute kar de", "awaaz band kar", "silent kar de", "chup kar de", "shant kar isko"],
        "targets": ["0", "mute"]
    },
    "set_brightness": {
        "tool_name": "system_settings", "action": "set_brightness",
        "hinglish_verbs": ["brightness badha", "roshni kam kar", "screen dim kar", "brightness full kar de"],
        "targets": ["100", "50", "20", "up", "down", "max"]
    },
    "play_music": {
        "tool_name": "media_control", "action": "play_pause",
        "hinglish_verbs": ["gaana chala", "music baja", "play kar", "song chala de", "music on kar"],
        "targets": ["spotify", "gaana", "music", "kuch bhi"]
    },
    "pause_music": {
        "tool_name": "media_control", "action": "play_pause",
        "hinglish_verbs": ["gaana rok de", "music band kar", "pause kar", "gaana stop kar", "chup kar de music"],
        "targets": ["spotify", "song", "music"]
    },
    "next_track": {
        "tool_name": "media_control", "action": "next_track",
        "hinglish_verbs": ["agla gaana chala", "next kar", "gaana change kar", "skip kar de"],
        "targets": ["song", "music", "track"]
    },
    "change_wallpaper": {
        "tool_name": "system_automation", "action": "change_wallpaper",
        "hinglish_verbs": ["wallpaper change kar", "naya wallpaper laga de", "background badal de", "screen mast kar de"],
        "targets": ["nature", "dark", "cyberpunk", "cars", "space", "anime", "minimalist"]
    },

    # ---------------- WEB & SCRAPING (Integrations) ---------------- #
    "open_website": {
        "tool_name": "web_navigation", "action": "open_url",
        "hinglish_verbs": ["khol do", "open kar", "search kar", "jaa", "website laga", "browser me khol"],
        "targets": ["youtube.com", "google.com", "github.com", "chatgpt.com", "reddit.com", "twitter.com", "amazon.in"]
    },
    "search_web": {
        "tool_name": "web_navigation", "action": "search",
        "hinglish_verbs": ["search kar", "dhundh", "kya hota hai", "google kar", "bata", "find kar"],
        "targets": ["weather in delhi", "latest news", "stock market price", "python tutorial", "nifty 50 today", "bitcoin price"]
    },
    "scrape_page": {
        "tool_name": "web_agent", "action": "scrape_content",
        "hinglish_verbs": ["article padh ke bata", "summarize kar de", "is page ka data nikal", "scrape kar"],
        "targets": ["current page", "this article", "wikipedia link", "news site"]
    },

    # ---------------- FILE SYSTEM & DATA ---------------- #
    "organize_files": {
        "tool_name": "file_manager", "action": "organize_folder",
        "hinglish_verbs": ["files arrange kar de", "folder saaf kar", "organize kar", "sab ek jagah kar"],
        "targets": ["downloads", "desktop", "documents", "my files"]
    },
    "delete_duplicates": {
        "tool_name": "file_manager", "action": "remove_duplicates",
        "hinglish_verbs": ["duplicate delete kar", "faltu files hata", "storage clean kar", "kachra saaf kar"],
        "targets": ["downloads", "c drive", "pictures"]
    },
    
    # ---------------- VISION & OCR (Learning Systems) ---------------- #
    "read_screen": {
        "tool_name": "vision_agent", "action": "analyze_screen",
        "hinglish_verbs": ["screen pe kya hai", "dekh ke bata", "ye error kya hai", "kya chal raha hai"],
        "targets": ["screen", "display", "monitor"]
    },
    "extract_text": {
        "tool_name": "vision_agent", "action": "extract_ocr",
        "hinglish_verbs": ["text copy kar", "image se text nikal", "ocr run kar", "padh ke bata"],
        "targets": ["screenshot", "this image", "photo"]
    }
}

PREFIXES = ["bhai ", "jaldi se ", "yaar ", "hey ", "chalo ", "zara ", "ek kaam kar ", "sun ", "ai ", "daddy ", ""]
SUFFIXES = [" jaldi", " yaar", " fast", " please", " bhai", " turant", " abhi ke abhi", ""]

def generate_dataset(num_samples=1000):
    dataset = []
    
    for _ in range(num_samples):
        intent_key = random.choice(list(INTENTS.keys()))
        intent = INTENTS[intent_key]
        
        verb = random.choice(intent["hinglish_verbs"])
        target = random.choice(intent["targets"])
        prefix = random.choice(PREFIXES)
        suffix = random.choice(SUFFIXES)
        
        if intent_key in ["shutdown", "restart", "sleep_lock", "mute"]:
            user_prompt = f"{prefix}{verb}{suffix}".strip()
        else:
            user_prompt = f"{prefix}{target} {verb}{suffix}".strip()
            
        user_prompt = " ".join(user_prompt.split())
        
        arguments = {"action": intent["action"]}
        if intent_key not in ["shutdown", "restart", "sleep_lock", "mute"]:
            arguments["target"] = target
            
        message = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are YourDaddy, a snarky but extremely capable Windows OS Assistant. You have deep OS access, web integration, and multi-modal vision. You execute user intents purely via JSON tool calls."
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
        
        dataset.append(message)
        
    return dataset

if __name__ == "__main__":
    out_dir = Path("d:/Projects/Ai_Assistant/data/training")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_file = out_dir / "automation_finetune_v2.jsonl"
    
    # Massive Scale Output: 200,000 permutations
    data = generate_dataset(200000)
    
    with open(out_file, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    try:
        print(f"Generated {len(data)} EXHAUSTIVE training examples at {out_file}")
    except UnicodeEncodeError:
        print(f"Generated {len(data)} examples (unicode error suppressed).")
