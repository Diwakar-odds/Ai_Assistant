import os
import json
import uuid
import random

def create_dataset():
    dataset = []
    
    # Helper to create entries
    def add(text, intent, entities, action_type, lang, category, is_multi=False, steps=1, diff="easy", tags=None):
        dataset.append({
            "id": f"CMD_{len(dataset):03d}",
            "text": text,
            "expected_intent": intent,
            "expected_entities": entities,
            "expected_action_type": action_type,
            "expected_chain_steps": steps,
            "language": lang,
            "category": category,
            "is_multi_step": is_multi,
            "difficulty": diff,
            "tags": tags or []
        })

    # OPEN_APP
    apps = [("chrome", "browser"), ("spotify", "music"), ("notepad", "text editor"), ("calculator", "calc")]
    for app, category in apps:
        add(f"open {app}", "OPEN_BROWSER" if app=="chrome" else "OPEN_APP", {"app": app} if app!="chrome" else {"url": None}, "APP" if app!="chrome" else "BROWSER", "English", "app_control", tags=["app", "open"])
        add(f"launch {app}", "OPEN_BROWSER" if app=="chrome" else "OPEN_APP", {"app": app} if app!="chrome" else {"url": None}, "APP" if app!="chrome" else "BROWSER", "English", "app_control", tags=["app", "launch"])
        add(f"{app} kholo", "OPEN_BROWSER" if app=="chrome" else "OPEN_APP", {"app": app} if app!="chrome" else {"url": None}, "APP" if app!="chrome" else "BROWSER", "Hindi", "app_control", tags=["app", "open"])
        add(f"{app} chalu karo", "OPEN_BROWSER" if app=="chrome" else "OPEN_APP", {"app": app} if app!="chrome" else {"url": None}, "APP" if app!="chrome" else "BROWSER", "Hindi", "app_control", tags=["app", "launch"])
        add(f"{app} khol da", "OPEN_BROWSER" if app=="chrome" else "OPEN_APP", {"app": app} if app!="chrome" else {"url": None}, "APP" if app!="chrome" else "BROWSER", "Bhojpuri", "app_control", tags=["app", "open"])

    # CLOSE_APP
    for app, category in apps:
        add(f"close {app}", "CLOSE_APP", {"app": app}, "APP", "English", "app_control", tags=["app", "close"])
        add(f"quit {app}", "CLOSE_APP", {"app": app}, "APP", "English", "app_control", tags=["app", "quit"])
        add(f"{app} band karo", "CLOSE_APP", {"app": app}, "APP", "Hindi", "app_control", tags=["app", "close"])
        add(f"{app} band kar da", "CLOSE_APP", {"app": app}, "APP", "Bhojpuri", "app_control", tags=["app", "close"])

    # SYSTEM_SHUTDOWN
    add("shut down the computer", "SYSTEM_SHUTDOWN", {}, "SYSTEM", "English", "system", tags=["shutdown"])
    add("turn off the pc", "SYSTEM_SHUTDOWN", {}, "SYSTEM", "English", "system", tags=["shutdown"])
    add("power off the system", "SYSTEM_SHUTDOWN", {}, "SYSTEM", "English", "system", tags=["shutdown"])
    add("computer band kar do", "SYSTEM_SHUTDOWN", {}, "SYSTEM", "Hindi", "system", tags=["shutdown"])
    add("pc off kar do", "SYSTEM_SHUTDOWN", {}, "SYSTEM", "Hindi", "system", tags=["shutdown"])
    add("system band kardo", "SYSTEM_SHUTDOWN", {}, "SYSTEM", "Hindi", "system", tags=["shutdown"])
    add("computerwa band kar da", "SYSTEM_SHUTDOWN", {}, "SYSTEM", "Bhojpuri", "system", tags=["shutdown"])
    add("systemwa off kar da", "SYSTEM_SHUTDOWN", {}, "SYSTEM", "Bhojpuri", "system", tags=["shutdown"])
    add("pc band kara", "SYSTEM_SHUTDOWN", {}, "SYSTEM", "Bhojpuri", "system", tags=["shutdown"])

    # VOLUME_UP
    add("increase the volume", "VOLUME_UP", {}, "SYSTEM", "English", "system", tags=["volume", "up"])
    add("volume up", "VOLUME_UP", {}, "SYSTEM", "English", "system", tags=["volume", "up"])
    add("make it louder", "VOLUME_UP", {}, "SYSTEM", "English", "system", tags=["volume", "up"])
    add("awaaz badha do", "VOLUME_UP", {}, "SYSTEM", "Hindi", "system", tags=["volume", "up"])
    add("volume tez karo", "VOLUME_UP", {}, "SYSTEM", "Hindi", "system", tags=["volume", "up"])
    add("awaaz tej kara", "VOLUME_UP", {}, "SYSTEM", "Bhojpuri", "system", tags=["volume", "up"])
    
    # VOLUME_DOWN
    add("decrease the volume", "VOLUME_DOWN", {}, "SYSTEM", "English", "system", tags=["volume", "down"])
    add("volume down", "VOLUME_DOWN", {}, "SYSTEM", "English", "system", tags=["volume", "down"])
    add("make it quieter", "VOLUME_DOWN", {}, "SYSTEM", "English", "system", tags=["volume", "down"])
    add("awaaz kam karo", "VOLUME_DOWN", {}, "SYSTEM", "Hindi", "system", tags=["volume", "down"])
    add("volume dheere karo", "VOLUME_DOWN", {}, "SYSTEM", "Hindi", "system", tags=["volume", "down"])
    add("awaaz kam kara", "VOLUME_DOWN", {}, "SYSTEM", "Bhojpuri", "system", tags=["volume", "down"])

    # SEARCH_WEB
    add("search for AI news", "web_search", {"query": "AI news"}, "BROWSER", "English", "web", tags=["search"])
    add("google who is the president", "web_search", {"query": "who is the president"}, "BROWSER", "English", "web", tags=["search", "google"])
    add("find a recipe for pasta", "web_search", {"query": "a recipe for pasta"}, "BROWSER", "English", "web", tags=["search"])
    add("AI news dhund ke batao", "web_search", {"query": "AI news"}, "BROWSER", "Hindi", "web", tags=["search"])
    add("internet pe search karo machine learning", "web_search", {"query": "machine learning"}, "BROWSER", "Hindi", "web", tags=["search"])
    add("pasta recipe khoj karo", "web_search", {"query": "pasta recipe"}, "BROWSER", "Bhojpuri", "web", tags=["search"])

    # PLAY_MEDIA
    add("play some music", "play", {}, "APP", "English", "media", tags=["play", "music"])
    add("put on a song", "play", {}, "APP", "English", "media", tags=["play", "music"])
    add("search for techburner on youtube", "play", {"query": "techburner"}, "APP", "English", "media", tags=["play", "youtube"])
    add("gana bajao", "play", {}, "APP", "Hindi", "media", tags=["play", "music"])
    add("kuch chalao", "play", {}, "APP", "Hindi", "media", tags=["play", "video"])
    add("baja do kuch", "play", {}, "APP", "Bhojpuri", "media", tags=["play"])

    # VISION
    add("look at this", "vision", {}, "CUSTOM", "English", "vision", tags=["vision", "look"])
    add("what is on my screen", "vision", {}, "CUSTOM", "English", "vision", tags=["vision", "screen"])
    add("screen dekho", "vision", {}, "CUSTOM", "Hindi", "vision", tags=["vision", "screen"])
    add("kya hai ye screen par", "vision", {}, "CUSTOM", "Hindi", "vision", tags=["vision", "screen"])
    add("ankhein khol ke dekho", "vision", {}, "CUSTOM", "Bhojpuri", "vision", tags=["vision"])

    # FILE_OPS
    add("create a file named report.txt with content hello", "create_file", {"filename": "report.txt", "content": "hello"}, "FILE", "English", "file", tags=["file", "create"])
    add("create file script.py", "create_file", {"filename": "script.py"}, "FILE", "English", "file", tags=["file", "create"])
    add("save this document", "create_file", {}, "FILE", "English", "file", tags=["file", "save"])
    add("report.txt naam ka file banao", "create_file", {"filename": "report.txt"}, "FILE", "Hindi", "file", tags=["file", "create"])
    add("ek naya file bana da", "create_file", {}, "FILE", "Bhojpuri", "file", tags=["file", "create"])

    # WEATHER
    add("what is the weather like", "GET_WEATHER", {}, "CUSTOM", "English", "weather", tags=["weather"])
    add("check the weather", "GET_WEATHER", {}, "CUSTOM", "English", "weather", tags=["weather"])
    add("is it raining outside", "GET_WEATHER", {}, "CUSTOM", "English", "weather", tags=["weather"])
    add("mausam kaisa hai", "GET_WEATHER", {}, "CUSTOM", "Hindi", "weather", tags=["weather"])
    add("bahar ka mausam batao", "GET_WEATHER", {}, "CUSTOM", "Hindi", "weather", tags=["weather"])
    add("mausam kaisan ba", "GET_WEATHER", {}, "CUSTOM", "Bhojpuri", "weather", tags=["weather"])

    # RESEARCH
    add("research AI agents and give me a summary", "research_summarize", {"topic": "AI agents"}, "CUSTOM", "English", "research", tags=["research", "summarize"])
    add("research quantum computing", "research", {"topic": "quantum computing"}, "CUSTOM", "English", "research", tags=["research"])
    add("scrape http://example.com and give me a summary", "scrape_summarize", {"url": "http://example.com"}, "CUSTOM", "English", "research", tags=["scrape", "summarize"])
    add("AI agents ke bare mein research karo", "research", {"topic": "AI agents"}, "CUSTOM", "Hindi", "research", tags=["research"])
    
    # MULTI_STEP
    add("open chrome and search for AI", "MULTI_STEP", {}, "CHAIN", "English", "multi_step", is_multi=True, steps=2, diff="medium", tags=["chain", "browser"])
    add("WhatsApp kholo aur message karo hi", "MULTI_STEP", {}, "CHAIN", "Hindi", "multi_step", is_multi=True, steps=2, diff="medium", tags=["chain", "app"])
    add("create a file named test.txt, write hello, and close notepad", "MULTI_STEP", {}, "CHAIN", "English", "multi_step", is_multi=True, steps=3, diff="hard", tags=["chain", "file", "app"])
    add("volume tez karo aur spotify pe gana bajao", "MULTI_STEP", {}, "CHAIN", "Hindi", "multi_step", is_multi=True, steps=2, diff="medium", tags=["chain", "system", "media"])
    add("research quantum mechanics and create a file summary.txt with the results", "MULTI_STEP", {}, "CHAIN", "English", "multi_step", is_multi=True, steps=2, diff="hard", tags=["chain", "research", "file"])

    # AMBIGUOUS / FALLBACK
    add("do something cool", "unknown", {}, "CUSTOM", "English", "ambiguous", tags=["unknown"])
    add("kuch karo", "unknown", {}, "CUSTOM", "Hindi", "ambiguous", tags=["unknown"])
    add("I need help", "unknown", {}, "CUSTOM", "English", "ambiguous", tags=["unknown"])
    
    # EDGE_CASES
    add("", "unknown", {}, "CUSTOM", "English", "edge_cases", diff="hard", tags=["empty"])
    add(" " * 50, "unknown", {}, "CUSTOM", "English", "edge_cases", diff="hard", tags=["spaces"])
    add("shut" * 100, "unknown", {}, "CUSTOM", "English", "edge_cases", diff="hard", tags=["long"])
    add("DROP TABLE users; --", "unknown", {}, "CUSTOM", "English", "edge_cases", diff="hard", tags=["injection"])
    
    return dataset

if __name__ == "__main__":
    import os
    data = create_dataset()
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    with open("test_commands_dataset.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(data)} test commands.")
