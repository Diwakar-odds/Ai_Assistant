"""
Forensic Audit Script: Search Entire Codebase for Hardcoded Personal Data, Names, Paths, and Camera/Face Artifacts
"""

import os
import re
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IGNORE_DIRS = {
    "node_modules", ".git", "venv", "__pycache__", ".pytest_cache",
    "dist", "build", ".vscode", ".idea", "dist_package", "models", "docs",
    "target", "logs", ".gemini", "src-tauri"
}

IGNORE_EXTENSIONS = {
    ".exe", ".dll", ".bin", ".gguf", ".onnx", ".tflite", ".png", ".jpg",
    ".jpeg", ".ico", ".npy", ".npz", ".pyc", ".pyd", ".woff", ".woff2",
    ".ttf", ".eot", ".mp3", ".wav", ".tar", ".gz", ".zip"
}

PATTERNS = {
    "personal_name_diwakar": re.compile(r"\b(diwakar|divyakar|bdiwa)\b", re.IGNORECASE),
    "hardcoded_user_c_drive": re.compile(r"[a-zA-Z]:[\\/][uU]sers[\\/][a-zA-Z0-9_-]+"),
    "hardcoded_d_drive_path": re.compile(r"d:[\\/](?:Projects|Ai_Assistant|resume|data|models)", re.IGNORECASE),
    "phone_numbers": re.compile(r"(?:\+91[\-\s]?[6-9]\d{9}\b|\b[6-9]\d{9}\b)"),
    "email_addresses": re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"),
    "friend_greeting_vlm": re.compile(r"\b(friend|dost|pehchan|greet.*friend|greet.*person|known_face)\b", re.IGNORECASE),
}

results = {k: [] for k in PATTERNS}

for root, dirs, files in os.walk(PROJECT_ROOT):
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in IGNORE_EXTENSIONS:
            continue
        file_path = os.path.join(root, file)
        rel_path = os.path.relpath(file_path, PROJECT_ROOT)

        # Skip our own audit script
        if rel_path.endswith("audit_hardcoded_data.py") or "audit_hardcoded_results" in rel_path or "clean_personal_data" in rel_path:
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_no, line in enumerate(f, 1):
                    for name, pat in PATTERNS.items():
                        matches = pat.findall(line)
                        if matches:
                            clean_line = line.strip()
                            # Filter obvious false positives like example@email.com or docs
                            results[name].append({
                                "file": rel_path,
                                "line": line_no,
                                "match": matches[0] if isinstance(matches[0], str) else matches[0][0],
                                "content": clean_line[:140]
                            })
        except Exception:
            pass

output_report = os.path.join(PROJECT_ROOT, "audit_hardcoded_results.json")
with open(output_report, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("AUDIT SUMMARY:")
for k, items in results.items():
    print(f"  - {k}: {len(items)} instances found")

print(f"\nFull detailed results saved to {output_report}")
