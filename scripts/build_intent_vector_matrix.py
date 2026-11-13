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
                
    # Add domain-specific Hinglish variations for critical desktop commands
    hinglish_supplements = [
        # open_app
        ("open_app", "kholo notepad"),
        ("open_app", "chrome open karo"),
        ("open_app", "calculator chalao"),
        ("open_app", "launch visual studio code"),
        ("open_app", "whatsapp khol do"),
        ("open_app", "spotify start karo"),
        # close_app
        ("close_app", "band karo chrome"),
        ("close_app", "notepad close kar do"),
        ("close_app", "quit visual studio code"),
        ("close_app", "whatsapp band kar do"),
        # volume_control
        ("volume_control", "awaaz kam karo"),
        ("volume_control", "awaaz badhao"),
        ("volume_control", "sound badha do"),
        ("volume_control", "volume dheema karo"),
        ("volume_control", "volume tez kar do"),
        ("volume_control", "mute karo"),
        ("volume_control", "unmute karo sound"),
        # media_control / play_media
        ("media_control", "agla gaana chalao"),
        ("media_control", "pichla gaana lagao"),
        ("media_control", "gaana pause karo"),
        ("media_control", "music stop kar do"),
        ("media_control", "gaana resume karo"),
        ("media_control", "next track play karo"),
        # wifi_toggle
        ("wifi_toggle", "wifi chalu karo"),
        ("wifi_toggle", "wifi band kar do"),
        ("wifi_toggle", "turn on wifi"),
        ("wifi_toggle", "turn off wi-fi"),
        # bluetooth_toggle
        ("bluetooth_toggle", "bluetooth chalu karo"),
        ("bluetooth_toggle", "bluetooth band kar do"),
        ("bluetooth_toggle", "turn on bluetooth"),
        ("bluetooth_toggle", "turn off bluetooth"),
        # set_brightness
        ("set_brightness", "screen ki brightness badhao"),
        ("set_brightness", "brightness kam karo"),
        ("set_brightness", "brightness full kar do"),
        # battery_status
        ("battery_status", "battery kitni bachi hai"),
        ("battery_status", "battery percentage batao"),
        ("battery_status", "check laptop battery"),
        # analyze_screen
        ("analyze_screen", "screenshot le lo"),
        ("analyze_screen", "screen ki photo kheencho"),
        ("analyze_screen", "take a screenshot"),
        ("analyze_screen", "screen capture karo"),
        # send_message
        ("send_message", "whatsapp par message bhejo"),
        ("send_message", "mom ko message likh kar bhejo"),
        ("send_message", "bhai ko whatsapp par msg karo"),
        # search_web
        ("search_web", "google par search karo"),
        ("search_web", "web par check karo"),
        ("search_web", "internet par dhoondo"),
        # system_control
        ("system_control", "laptop shutdown kar do"),
        ("system_control", "computer restart karo"),
        ("system_control", "screen lock kar do"),
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
