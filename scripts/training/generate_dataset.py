import csv
import os

def create_dataset():
    dataset = []
    
    def add(text, intent, lang):
        dataset.append({"text": text, "intent": intent, "lang": lang})

    # OPEN_APP
    apps = ["chrome", "spotify", "notepad", "calculator", "vscode", "word"]
    for app in apps:
        intent = "OPEN_BROWSER" if app == "chrome" else "OPEN_APP"
        add(f"open {app}", intent, "English")
        add(f"launch {app}", intent, "English")
        add(f"start {app}", intent, "English")
        add(f"{app} kholo", intent, "Hindi")
        add(f"{app} chalu karo", intent, "Hindi")
        add(f"{app} start karo", intent, "Hindi")
        add(f"{app} khol da", intent, "Bhojpuri")
        add(f"{app}wa chalu kara", intent, "Bhojpuri")

    # CLOSE_APP
    for app in apps:
        add(f"close {app}", "CLOSE_APP", "English")
        add(f"quit {app}", "CLOSE_APP", "English")
        add(f"exit {app}", "CLOSE_APP", "English")
        add(f"{app} band karo", "CLOSE_APP", "Hindi")
        add(f"{app} hatao", "CLOSE_APP", "Hindi")
        add(f"{app} band kar da", "CLOSE_APP", "Bhojpuri")

    # SYSTEM_SHUTDOWN
    add("shut down the computer", "SYSTEM_SHUTDOWN", "English")
    add("turn off the pc", "SYSTEM_SHUTDOWN", "English")
    add("power off the system", "SYSTEM_SHUTDOWN", "English")
    add("computer band kar do", "SYSTEM_SHUTDOWN", "Hindi")
    add("pc off kar do", "SYSTEM_SHUTDOWN", "Hindi")
    add("system band kardo", "SYSTEM_SHUTDOWN", "Hindi")
    add("computerwa band kar da", "SYSTEM_SHUTDOWN", "Bhojpuri")
    add("systemwa off kar da", "SYSTEM_SHUTDOWN", "Bhojpuri")
    add("pc band kara", "SYSTEM_SHUTDOWN", "Bhojpuri")

    # VOLUME_UP
    add("increase the volume", "VOLUME_UP", "English")
    add("volume up", "VOLUME_UP", "English")
    add("make it louder", "VOLUME_UP", "English")
    add("awaaz badha do", "VOLUME_UP", "Hindi")
    add("volume tez karo", "VOLUME_UP", "Hindi")
    add("sound badhao", "VOLUME_UP", "Hindi")
    add("awaaz tej kara", "VOLUME_UP", "Bhojpuri")
    add("volume badha da", "VOLUME_UP", "Bhojpuri")
    add("josh me aawaz kara", "VOLUME_UP", "Bhojpuri")

    # VOLUME_DOWN
    add("decrease the volume", "VOLUME_DOWN", "English")
    add("volume down", "VOLUME_DOWN", "English")
    add("make it quieter", "VOLUME_DOWN", "English")
    add("awaaz kam karo", "VOLUME_DOWN", "Hindi")
    add("volume dheere karo", "VOLUME_DOWN", "Hindi")
    add("sound kam kar do", "VOLUME_DOWN", "Hindi")
    add("awaaz kam kara", "VOLUME_DOWN", "Bhojpuri")
    add("volume dheere kara", "VOLUME_DOWN", "Bhojpuri")
    add("soundwa kam kar da", "VOLUME_DOWN", "Bhojpuri")
    
    # GET_WEATHER
    add("what is the weather like", "GET_WEATHER", "English")
    add("check the weather", "GET_WEATHER", "English")
    add("is it raining outside", "GET_WEATHER", "English")
    add("mausam kaisa hai", "GET_WEATHER", "Hindi")
    add("bahar ka mausam batao", "GET_WEATHER", "Hindi")
    add("kya barish ho rahi hai", "GET_WEATHER", "Hindi")
    add("mausam kaisan ba", "GET_WEATHER", "Bhojpuri")
    add("baharwa ke mausam batawa", "GET_WEATHER", "Bhojpuri")
    add("ka paani barsat ba", "GET_WEATHER", "Bhojpuri")

    # web_search
    add("search for AI news", "web_search", "English")
    add("google who is the president", "web_search", "English")
    add("find a recipe for pasta", "web_search", "English")
    add("AI news dhund ke batao", "web_search", "Hindi")
    add("internet pe search karo machine learning", "web_search", "Hindi")
    add("pasta recipe khoj karo", "web_search", "Bhojpuri")

    # play
    add("play some music", "play", "English")
    add("put on a song", "play", "English")
    add("search for techburner on youtube", "play", "English")
    add("gana bajao", "play", "Hindi")
    add("kuch chalao", "play", "Hindi")
    add("baja do kuch", "play", "Bhojpuri")

    # vision
    add("look at this", "vision", "English")
    add("what is on my screen", "vision", "English")
    add("screen dekho", "vision", "Hindi")
    add("kya hai ye screen par", "vision", "Hindi")
    add("ankhein khol ke dekho", "vision", "Bhojpuri")

    # file_ops
    add("create a file named report.txt with content hello", "create_file", "English")
    add("create file script.py", "create_file", "English")
    add("save this document", "create_file", "English")
    add("report.txt naam ka file banao", "create_file", "Hindi")
    add("ek naya file bana da", "create_file", "Bhojpuri")

    # research
    add("research AI agents and give me a summary", "research_summarize", "English")
    add("research quantum computing", "research", "English")
    add("AI agents ke bare mein research karo", "research", "Hindi")
    
    return dataset

def main():
    dataset = create_dataset()
    output_file = os.path.join(os.path.dirname(__file__), "commands_dataset.csv")
    
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["text", "intent", "lang"])
        writer.writeheader()
        writer.writerows(dataset)
        
    print(f"Dataset successfully generated at: {output_file}")
    print(f"Total commands generated: {len(dataset)}")

if __name__ == "__main__":
    main()