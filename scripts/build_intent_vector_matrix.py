"""
Offline Precomputation Script: Builds data/core/intent_embeddings.npz
Extracts examples from all 47 IntentRouter intents + high-frequency Hindi/Hinglish variants,
encodes them with SentenceTransformer ('all-MiniLM-L6-v2'), L2-normalizes them,
and saves a compressed .npz archive for <1ms runtime vector matching.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Set root paths
project_root = Path(__file__).resolve().parents[1]
sys.path.extend([str(project_root), str(project_root / "core_ai" / "src"), str(project_root / "backend")])

import numpy as np

# Ensure no TF clutter
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from ai_assistant.ai.intent_router import IntentRouter
from ai_assistant.ai.shared_embedder import encode_batch, is_embedder_available


def generate_intent_matrix():
    print("🚀 Initializing IntentRouter to extract intent definitions...")
    router = IntentRouter()
    
    phrases = []
    intent_names = []
    
    for iname, idef in router.intents.items():
        # Add registered examples
        for ex in idef.examples:
            cleaned = ex.strip().lower()
            if cleaned and cleaned not in phrases:
                phrases.append(cleaned)
                intent_names.append(iname)
                
    # Add comprehensive Hindi (Devanagari), Hinglish, and Whisper ASR phonetic variations
    hinglish_supplements = [
        # open_app - English, Hinglish, Devanagari & Whisper Phonetics
        ("open_app", "open whatsapp"),
        ("open_app", "launch whatsapp"),
        ("open_app", "start whatsapp"),
        ("open_app", "whatsapp open"),
        ("open_app", "whatsapp open karo"),
        ("open_app", "whatsapp open kar do"),
        ("open_app", "open chrome"),
        ("open_app", "launch chrome"),
        ("open_app", "chrome open karo"),
        ("open_app", "open spotify"),
        ("open_app", "launch spotify"),
        ("open_app", "open notepad"),
        ("open_app", "launch visual studio code"),
        ("open_app", "kholo notepad"),
        ("open_app", "calculator chalao"),
        ("open_app", "whatsapp khol do"),
        ("open_app", "whatsapp kholo"),
        ("open_app", "kholo whatsapp"),
        ("open_app", "whatsapp chalu karo"),
        ("open_app", "spotify start karo"),
        ("open_app", "youtube khol do"),
        ("open_app", "browser open karo"),
        ("open_app", "file explorer kholo"),
        ("open_app", "terminal chalu karo"),
        ("open_app", "settings open karo"),
        ("open_app", "task manager kholo"),
        # Devanagari open_app
        ("open_app", "व्हाट्सएप खोलो"),
        ("open_app", "व्हाट्सएप खोल दो"),
        ("open_app", "व्हाट्सएप चालू करो"),
        ("open_app", "खोलो व्हाट्सएप"),
        ("open_app", "खोल दो व्हाट्सएप"),
        ("open_app", "क्रोम खोलो"),
        ("open_app", "क्रोम खोल दो"),
        ("open_app", "नोटपैड खोलो"),
        ("open_app", "नोटपैड चालू करो"),
        ("open_app", "कैलकुलेटर खोलो"),
        ("open_app", "स्पॉटिफ़ाई चलाओ"),
        ("open_app", "यूट्यूब खोलो"),
        ("open_app", "ब्राउज़र खोलो"),
        ("open_app", "सेटिंग्स खोलो"),
        # Whisper ASR Mishearings for open_app
        ("open_app", "वाट्सब खोलो"),
        ("open_app", "वाटसब खोलो"),
        ("open_app", "वाट्सब प्वलो"),
        ("open_app", "वाटसब प्वलो"),
        ("open_app", "वाट्सप प्वलो"),
        ("open_app", "व्हाट्सएप प्वलो"),
        ("open_app", "वाट्सब पोलो"),
        ("open_app", "वाटसब पोलो"),
        ("open_app", "युटुब खोलो"),
        ("open_app", "युट्यूब खोलो"),
        ("open_app", "वाटसप खोलो"),

        # close_app
        ("close_app", "band karo chrome"),
        ("close_app", "notepad close kar do"),
        ("close_app", "quit visual studio code"),
        ("close_app", "whatsapp band kar do"),
        ("close_app", "chrome band karo"),
        ("close_app", "spotify hata do"),
        ("close_app", "band karo notepad"),
        ("close_app", "close all windows"),
        # Devanagari close_app
        ("close_app", "क्रोम बंद करो"),
        ("close_app", "व्हाट्सएप बंद करो"),
        ("close_app", "व्हाट्सएप बंद कर दो"),
        ("close_app", "नोटपैड बंद करो"),
        ("close_app", "बंद करो क्रोम"),
        ("close_app", "विंडो बंद करो"),
        ("close_app", "ऐप बंद कर दो"),
        ("close_app", "वाट्सब बंद करो"),

        # play_media
        ("play_media", "gaana chalao"),
        ("play_media", "music bajao"),
        ("play_media", "koi gaana sunao"),
        ("play_media", "saiyaara gaana chalao"),
        ("play_media", "saiyaara play karo"),
        ("play_media", "arijit singh ke gaane lagao"),
        ("play_media", "lofi beats play karo"),
        ("play_media", "hindi song chalao"),
        ("play_media", "punjabi song bajao"),
        ("play_media", "gaana play karo"),
        # Devanagari play_media
        ("play_media", "गाना चलाओ"),
        ("play_media", "म्यूजिक बजाओ"),
        ("play_media", "गाना बजाओ"),
        ("play_media", "सैयारा गाना चलाओ"),
        ("play_media", "सैयारा बजाओ"),
        ("play_media", "कोई अच्छा गाना सुनाओ"),
        ("play_media", "अरिजित सिंह के गाने चलाओ"),
        ("play_media", "गाना लगाओ"),
        ("play_media", "म्यूजिक चलाओ"),
        ("play_media", "सॉन्ग प्ले करो"),

        # media_control
        ("media_control", "agla gaana chalao"),
        ("media_control", "pichla gaana lagao"),
        ("media_control", "gaana pause karo"),
        ("media_control", "music stop kar do"),
        ("media_control", "gaana resume karo"),
        ("media_control", "next track play karo"),
        ("media_control", "next song please"),
        ("media_control", "previous song"),
        ("media_control", "pause song"),
        ("media_control", "resume playback"),
        # Devanagari media_control
        ("media_control", "अगला गाना चलाओ"),
        ("media_control", "अगला गाना"),
        ("media_control", "पिछला गाना लगाओ"),
        ("media_control", "गाना रोको"),
        ("media_control", "गाना पॉज़ करो"),
        ("media_control", "गाना चालू करो"),
        ("media_control", "गाना रिज्यूमे करो"),

        # volume_control
        ("volume_control", "awaaz kam karo"),
        ("volume_control", "awaaz badhao"),
        ("volume_control", "sound badha do"),
        ("volume_control", "volume dheema karo"),
        ("volume_control", "volume tez kar do"),
        ("volume_control", "mute karo"),
        ("volume_control", "unmute karo sound"),
        ("volume_control", "awaaz band karo"),
        ("volume_control", "awaaz thodi badhao"),
        ("volume_control", "thoda dheema karo"),
        ("volume_control", "volume full kar do"),
        ("volume_control", "sound 50 percent karo"),
        # Devanagari volume_control
        ("volume_control", "आवाज़ बढ़ाओ"),
        ("volume_control", "आवाज़ बढ़ा दो"),
        ("volume_control", "आवाज कम करो"),
        ("volume_control", "आवाज़ धीमी करो"),
        ("volume_control", "आवाज़ तेज़ करो"),
        ("volume_control", "म्यूट करो"),
        ("volume_control", "आवाज़ बंद करो"),
        ("volume_control", "आवाज़ चालू करो"),
        ("volume_control", "वॉल्यूम कम करो"),
        ("volume_control", "वॉल्यूम बढ़ाओ"),
        ("volume_control", "वॉल्यूम पचास करो"),

        # wifi_toggle
        ("wifi_toggle", "wifi chalu karo"),
        ("wifi_toggle", "wifi band kar do"),
        ("wifi_toggle", "turn on wifi"),
        ("wifi_toggle", "turn off wi-fi"),
        ("wifi_toggle", "wifi on karo"),
        ("wifi_toggle", "wifi off karo"),
        # Devanagari wifi_toggle
        ("wifi_toggle", "वाईफाई चालू करो"),
        ("wifi_toggle", "वाईफाई बंद करो"),
        ("wifi_toggle", "वाईफाई ऑन करो"),
        ("wifi_toggle", "वाईफाई ऑफ करो"),

        # bluetooth_toggle
        ("bluetooth_toggle", "bluetooth chalu karo"),
        ("bluetooth_toggle", "bluetooth band kar do"),
        ("bluetooth_toggle", "turn on bluetooth"),
        ("bluetooth_toggle", "turn off bluetooth"),
        ("bluetooth_toggle", "bluetooth on karo"),
        ("bluetooth_toggle", "bluetooth off karo"),
        # Devanagari bluetooth_toggle
        ("bluetooth_toggle", "ब्लूटूथ चालू करो"),
        ("bluetooth_toggle", "ब्लूटूथ बंद करो"),
        ("bluetooth_toggle", "ब्लूटूथ ऑन करो"),
        ("bluetooth_toggle", "ब्लूटूथ ऑफ करो"),

        # set_brightness
        ("set_brightness", "screen ki brightness badhao"),
        ("set_brightness", "brightness kam karo"),
        ("set_brightness", "brightness full kar do"),
        ("set_brightness", "screen thodi bright karo"),
        ("set_brightness", "brightness dheemi karo"),
        # Devanagari set_brightness
        ("set_brightness", "ब्राइटनेस बढ़ाओ"),
        ("set_brightness", "ब्राइटनेस कम करो"),
        ("set_brightness", "स्क्रीन की ब्राइटनेस बढ़ा दो"),
        ("set_brightness", "ब्राइटनेस धीमी करो"),

        # battery_status
        ("battery_status", "battery kitni bachi hai"),
        ("battery_status", "battery percentage batao"),
        ("battery_status", "check laptop battery"),
        ("battery_status", "laptop charge kitna hai"),
        ("battery_status", "battery check karo"),
        # Devanagari battery_status
        ("battery_status", "बैटरी कितनी बची है"),
        ("battery_status", "लैपटॉप चार्ज कितना है"),
        ("battery_status", "बैटरी प्रतिशत बताओ"),
        ("battery_status", "बैटरी चेक करो"),

        # analyze_screen
        ("analyze_screen", "screenshot le lo"),
        ("analyze_screen", "screen ki photo kheencho"),
        ("analyze_screen", "take a screenshot"),
        ("analyze_screen", "screen capture karo"),
        ("analyze_screen", "screen par kya dikh raha hai"),
        ("analyze_screen", "screen dekho"),
        ("analyze_screen", "screen dekh kar batao"),
        # Devanagari analyze_screen
        ("analyze_screen", "स्क्रीनशॉट लो"),
        ("analyze_screen", "स्क्रीन देखो"),
        ("analyze_screen", "स्क्रीन पर क्या है"),
        ("analyze_screen", "स्क्रीन पर क्या दिख रहा है"),
        ("analyze_screen", "स्क्रीन की फोटो खींचो"),

        # send_message
        ("send_message", "whatsapp par message bhejo"),
        ("send_message", "mom ko message likh kar bhejo"),
        ("send_message", "bhai ko whatsapp par msg karo"),
        ("send_message", "whatsapp msg karo"),
        # Devanagari send_message
        ("send_message", "व्हाट्सएप पर मैसेज भेजो"),
        ("send_message", "मैसेज भेजो"),
        ("send_message", "व्हाट्सएप मैसेज करो"),

        # search_web
        ("search_web", "google par search karo"),
        ("search_web", "web par check karo"),
        ("search_web", "internet par dhoondo"),
        ("search_web", "online pata karo"),
        ("search_web", "google search karo"),
        # Devanagari search_web
        ("search_web", "गूगल पर सर्च करो"),
        ("search_web", "इंटरनेट पर खोजो"),
        ("search_web", "ऑनलाइन पता करो"),

        # list_running_apps
        ("list_running_apps", "kaunse apps khule hain"),
        ("list_running_apps", "running apps dikhao"),
        ("list_running_apps", "open programs batao"),
        ("list_running_apps", "taskbar check karo"),
        # Devanagari list_running_apps
        ("list_running_apps", "कौन से ऐप खुले हैं"),
        ("list_running_apps", "रनिंग ऐप्स दिखाओ"),
        ("list_running_apps", "टास्कबार चेक करो"),

        # system_control
        ("system_control", "laptop shutdown kar do"),
        ("system_control", "computer restart karo"),
        ("system_control", "screen lock kar do"),
        ("system_control", "pc sleep mode me dalo"),
        ("system_control", "laptop band karo"),
        # Devanagari system_control
        ("system_control", "लैपटॉप बंद करो"),
        ("system_control", "कंप्यूटर रीस्टार्ट करो"),
        ("system_control", "स्क्रीन लॉक करो"),
        ("system_control", "सिस्टम शटडाउन करो"),
    ]
    
    for iname, phr in hinglish_supplements:
        cleaned = phr.strip().lower()
        if cleaned not in phrases:
            phrases.append(cleaned)
            intent_names.append(iname)
            
    print(f"📦 Total corpus: {len(phrases)} phrases across {len(set(intent_names))} unique intents.")
    print("⚡ Encoding batch with shared SentenceTransformer...")
    
    matrix = encode_batch(phrases, normalize=True)
    if matrix is None:
        print("❌ Encoding failed. Check sentence_transformers installation.")
        sys.exit(1)
        
    out_dir = project_root / "data" / "core"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "intent_embeddings.npz"
    
    np.savez_compressed(
        out_file,
        matrix=matrix,
        intent_names=np.array(intent_names),
        phrases=np.array(phrases),
        created_at=datetime.utcnow().isoformat()
    )
    
    print(f"✅ Precomputed vector matrix saved successfully to: {out_file}")
    print(f"📊 Matrix shape: {matrix.shape}, Size on disk: {out_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    generate_intent_matrix()
