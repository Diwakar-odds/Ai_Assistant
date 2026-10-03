# ==============================================================================
# 🚀 KAGGLE CONTINUOUS MULTI-SESSION TRAINING SCRIPT (Llama-3 8B Abliterated)
# Multilingual Windows Assistant: Hinglish + Hindi (हिंदी) + Bhojpuri (भोजपुरी) + English
# Auto-detects highest checkpoint (e.g., checkpoint-21000) and continues training!
# ==============================================================================

import os
import sys

# 1. Force single GPU & disable xformers to prevent T4 backward pass crashes
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
sys.modules['xformers'] = None

# --- STEP 1: INSTALL DEPENDENCIES ---
print("📦 [1/5] Installing Unsloth & Dependencies...")
import subprocess
subprocess.run("pip install -q unsloth unsloth_zoo", shell=True)
subprocess.run("pip install -q --no-deps trl peft accelerate bitsandbytes", shell=True)

# --- STEP 2: SCAN FOR HIGHEST CHECKPOINT ---
print("🔍 [2/5] Scanning for the Highest Trained Checkpoint...")
import re

search_dirs = ["/kaggle/input", "/kaggle/working"]
max_step = -1
best_path = None

for s_dir in search_dirs:
    if not os.path.exists(s_dir):
        continue
    for root, dirs, files in os.walk(s_dir):
        for d in dirs:
            match = re.match(r"^checkpoint-(\d+)$", d)
            if match:
                step = int(match.group(1))
                cand_path = os.path.join(root, d)
                try:
                    f_list = os.listdir(cand_path)
                    if any(f.endswith(".safetensors") or f.endswith(".bin") for f in f_list):
                        if step > max_step:
                            max_step = step
                            best_path = cand_path
                except Exception:
                    pass

if best_path:
    print(f"🔥 FOUND HIGHEST CHECKPOINT: Step {max_step} at: {best_path}")
else:
    print("ℹ️ No previous checkpoint found. Starting fresh from base model.")

# --- STEP 3: LOAD UNCENSORED BASE MODEL & MOUNT LATEST CHECKPOINT ---
print("🧠 [3/5] Loading Uncensored Base Model & Mounting Latest Checkpoint...")
from unsloth import FastLanguageModel
from peft import PeftModel
import torch

max_seq_length = 2048
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="failspy/Meta-Llama-3-8B-Instruct-abliterated-v3",
    max_seq_length=max_seq_length,
    dtype=None,
    load_in_4bit=True,
)

if best_path:
    print(f"⚡ Resuming directly on checkpoint: {best_path}")
    model = PeftModel.from_pretrained(model, best_path, is_trainable=True)
    print(f"✅ SUCCESS: Checkpoint {max_step} Weights Mounted on Uncensored Base!")
else:
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )
    print("✅ Initialized fresh LoRA adapters.")

# --- STEP 4: GENERATE 3.5 LAKH HINGLISH + HINDI + BHOJPURI DATASET ---
print("📝 [4/5] Generating 3.5 Lakh Diverse Commands (Hinglish + Hindi + Bhojpuri)...")
import json
import random
from datasets import Dataset

apps = ['chrome', 'vscode', 'notepad', 'whatsapp', 'calculator', 'spotify', 'discord', 'telegram', 'excel', 'word', 'powerpoint', 'vlc', 'steam', 'postman', 'docker', 'terminal', 'powershell', 'obsidian', 'figma', 'slack', 'settings', 'paint', 'task manager', 'file explorer', 'edge', 'brave', 'blender', 'photoshop', 'zoom', 'teams', 'pycharm', 'cmd']
docker_targets = ['redis', 'postgres', 'mongodb', 'mysql', 'nginx', 'frontend', 'backend', 'rabbitmq', 'celery', 'kafka', 'elasticsearch', 'docker compose']
git_branches = ['main', 'dev', 'master', 'feature/auth', 'fix/bug-404', 'staging', 'release-v1', 'hotfix', 'patch-2']
git_commits = ['fixed bug', 'updated ui', 'refactored backend', 'added tests', 'initial commit', 'perf improvement', 'docs updated', 'wip changes']
search_topics = ['python tutorial', 'ipl live score', 'weather today', 'react hooks guide', 'best gaming laptop', 'how to install docker', 'machine learning course', 'hindi songs playlist', 'latest tech news', 'fastapi tutorial', 'github trending repos', 'dal makhani recipe', 'stock market live', 'chatgpt 5 release date', 'bhojpuri video song', 'nirahua song']
search_engines = ['google', 'youtube', 'github', 'stackoverflow', 'wikipedia', 'reddit', 'amazon']

system_prompt = "You are YourDaddy, the Ultimate Enterprise Windows OS Assistant. You have deep OS access, agentic reasoning, and multi-modal vision. Execute user commands purely via JSON tool calls across English, Hindi, Hinglish, and Bhojpuri."

dataset_list = []
target_count = 350000

while len(dataset_list) < target_count:
    lang = random.choice(['hinglish', 'hindi', 'bhojpuri', 'english'])
    cat = random.choice(['app_open', 'app_close', 'vol', 'bright', 'settings', 'telemetry', 'docker', 'git', 'web', 'power', 'files', 'vision'])
    
    # 1. BHOJPURI (देहाती & बिहारी लहज़ा)
    if lang == 'bhojpuri':
        p = random.choice(['भैया, ', 'तनी ', 'ए भाई, ', 'अरे, ', 'सुन न, ', 'ए भैया, ', 'Bhaiya, ', 'Tani ', 'E bhai, ', 'Sun na, ', ''])
        s = random.choice([' न', ' तनी', ' जल्दी से', ' देखा', ' na', ' tani', ' jaldi se', ''])
        if cat == 'app_open':
            a = random.choice(apps)
            v = random.choice([f'{a} खोल द', f'{a} चालू कर द', f'{a} चला द', f'{a}वा चालू कर द', f'{a} khol da', f'{a} chalu kar da'])
            text = f'{p}{v}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps({'action': 'open_app', 'target': a})}
        elif cat == 'app_close':
            a = random.choice(apps)
            v = random.choice([f'{a} बंद कर द', f'{a} हटा द', f'{a} काट द', f'{a}वा बंद क द', f'{a} band kar da', f'{a} hata da'])
            text = f'{p}{v}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps({'action': 'close_app', 'target': a})}
        elif cat == 'vol':
            lvl = random.randint(0, 100)
            v = random.choice([f'अवाज़िया {lvl}% कर द', f'तनी अवाज़ बढ़ा द {lvl}%', f'अवाज़ कम क द {lvl} प', f'soundva band kar da', f'awaj {lvl}% pe set kar da'])
            text = f'{p}{v}{s}'.strip()
            tc = {'name': 'system_settings', 'arguments': json.dumps({'action': 'set_volume', 'level': lvl})}
        elif cat == 'bright':
            lvl = random.randint(10, 100)
            v = random.choice([f'लाईटवा {lvl}% कर द', f'स्क्रीन के रौशनी बढ़ा द {lvl}%', f'brightness kam kar da {lvl}%'])
            text = f'{p}{v}{s}'.strip()
            tc = {'name': 'system_settings', 'arguments': json.dumps({'action': 'set_brightness', 'level': lvl})}
        elif cat == 'settings':
            opt = random.choice([
                ('डार्क मोड चालू कर द', {'action': 'set_theme', 'theme': 'dark'}),
                ('वाईफाई बंद कर द', {'action': 'toggle_wifi', 'state': 'off'}),
                ('वाईफाई चालू कर द', {'action': 'toggle_wifi', 'state': 'on'}),
                ('ब्लूटूथवा चालू कर द', {'action': 'toggle_bluetooth', 'state': 'on'}),
                ('bluetooth band kar da', {'action': 'toggle_bluetooth', 'state': 'off'}),
            ])
            text = f'{p}{opt[0]}{s}'.strip()
            tc = {'name': 'system_settings', 'arguments': json.dumps(opt[1])}
        elif cat == 'telemetry':
            q = random.choice([
                ('कतना रैम बाचल बा?', {'action': 'get_system_info', 'query': 'ram'}),
                ('बैटरिया कतना पर्सेंट बा?', {'action': 'get_battery_status'}),
                ('सी ड्राइववा में कतना जगह बा?', {'action': 'get_disk_space', 'drive': 'C:'}),
                ('Ram kitna bachal ba?', {'action': 'get_system_info', 'query': 'ram'}),
                ('Batteriya kethane charge ba?', {'action': 'get_battery_status'}),
            ])
            text = f'{p}{q[0]}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps(q[1])}
        elif cat == 'power':
            pw = random.choice([
                ('लैपटॉपवा सुता द', 'sleep_pc'),
                ('कंप्यूटर बंद कर द', 'shutdown_pc'),
                ('रीस्टार्ट मार द', 'restart_pc'),
                ('स्क्रीन लॉक कर द', 'lock_pc'),
                ('Laptopva suta da', 'sleep_pc'),
                ('Computer band kar da', 'shutdown_pc'),
            ])
            text = f'{p}{pw[0]}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps({'action': pw[1]})}
        elif cat == 'vision':
            v_act = random.choice([
                ('एगो स्क्रीनशॉटवा खींच ल', 'take_screenshot'),
                ('स्क्रीन प का गड़बड़ बा देख त', 'analyze_screen'),
                ('Ego screenshot le la tani', 'take_screenshot'),
                ('Dekha ta screen pa ka error ba', 'analyze_screen'),
            ])
            text = f'{p}{v_act[0]}{s}'.strip()
            tc = {'name': 'vision_agent', 'arguments': json.dumps({'action': v_act[1]})}
        elif cat == 'web':
            eng = random.choice(['youtube', 'google'])
            top = random.choice(['bhojpuri gana', 'pawansingh song', 'weather live', 'match score'])
            text = f'{p}{eng} प {top} खोज द{s}'.strip()
            tc = {'name': 'web_navigation', 'arguments': json.dumps({'action': 'search', 'engine': eng, 'query': top})}
        else:
            d = random.choice(docker_targets)
            text = f'{p}{d} चालू कर द{s}'.strip()
            tc = {'name': 'developer_tools', 'arguments': json.dumps({'action': 'docker_manage', 'target': d})}

    # 2. SHUDDH HINDI (हिंदी - देवनागरी & रोमन)
    elif lang == 'hindi':
        p = random.choice(['कृपया, ', 'जरा ', 'भाई, ', 'अरे सुनो, ', 'जल्दी से ', 'फटाफट ', 'Kripya ', 'Jara ', 'Bhai ', ''])
        s = random.choice([' करो', ' करिए', ' कर दीजिए', ' तुरंत', ' kijiye', ' karo', ''])
        if cat == 'app_open':
            a = random.choice(apps)
            text = f'{p}{a} खोल दो{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps({'action': 'open_app', 'target': a})}
        elif cat == 'app_close':
            a = random.choice(apps)
            text = f'{p}{a} को बंद करो{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps({'action': 'close_app', 'target': a})}
        elif cat == 'vol':
            lvl = random.randint(0, 100)
            text = f'{p}ध्वनि {lvl}% पर सेट{s}'.strip()
            tc = {'name': 'system_settings', 'arguments': json.dumps({'action': 'set_volume', 'level': lvl})}
        elif cat == 'bright':
            lvl = random.randint(10, 100)
            text = f'{p}स्क्रीन की चमक {lvl}%{s}'.strip()
            tc = {'name': 'system_settings', 'arguments': json.dumps({'action': 'set_brightness', 'level': lvl})}
        elif cat == 'telemetry':
            q = random.choice([
                ('रैम की स्थिति बताओ', {'action': 'get_system_info', 'query': 'ram'}),
                ('सीपीयू का उपयोग कितना है?', {'action': 'get_system_info', 'query': 'cpu'}),
                ('बैटरी कितने प्रतिशत है?', {'action': 'get_battery_status'}),
                ('डिस्क में कितना स्थान शेष है?', {'action': 'get_disk_space', 'drive': 'C:'}),
            ])
            text = f'{p}{q[0]}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps(q[1])}
        elif cat == 'power':
            pw = random.choice([
                ('कंप्यूटर को स्लीप मोड में डालें', 'sleep_pc'),
                ('सिस्टम को शटडाउन करें', 'shutdown_pc'),
                ('कंप्यूटर पुनः प्रारंभ करें', 'restart_pc'),
                ('स्क्रीन को लॉक करें', 'lock_pc'),
            ])
            text = f'{p}{pw[0]}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps({'action': pw[1]})}
        elif cat == 'vision':
            text = f'{p}स्क्रीनशॉट ले लीजिए{s}'.strip()
            tc = {'name': 'vision_agent', 'arguments': json.dumps({'action': 'take_screenshot'})}
        elif cat == 'web':
            eng = random.choice(search_engines)
            top = random.choice(search_topics)
            text = f'{p}{eng} पर {top} खोजें{s}'.strip()
            tc = {'name': 'web_navigation', 'arguments': json.dumps({'action': 'search', 'engine': eng, 'query': top})}
        else:
            text = f'{p}डार्क मोड सक्रिय करो{s}'.strip()
            tc = {'name': 'system_settings', 'arguments': json.dumps({'action': 'set_theme', 'theme': 'dark'})}

    # 3. HINGLISH & ENGLISH (रोजमर्रा की बोलचाल)
    else:
        p = random.choice(['Yaar ', 'Bhai ', 'Suno, ', 'Oye, ', 'Jaldi se ', 'Fatafat ', 'Abhi ke abhi ', 'Bro ', 'Ek kaam karo, ', 'Zara ', 'Please ', 'Hey, ', ''])
        s = random.choice([' jaldi', ' fast', ' samjhe?', ' theek hai?', ' abhi!', ' yaar', ' please', ' turant', ''])
        if cat == 'app_open':
            a = random.choice(apps)
            v = random.choice(['khol do', 'open karo', 'chalu karo', 'start karo', 'launch karo', 'kholo', 'chala de'])
            text = f'{p}{a} {v}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps({'action': 'open_app', 'target': a})}
        elif cat == 'app_close':
            a = random.choice(apps)
            v = random.choice(['band karo', 'close kar do', 'kill kar de', 'hata do', 'screen se hatao', 'exit karo'])
            text = f'{p}{a} {v}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps({'action': 'close_app', 'target': a})}
        elif cat == 'vol':
            lvl = random.randint(0, 100)
            v = random.choice([f'volume {lvl}% kar do', f'awaaz {lvl} pe set karo', f'sound {lvl} karo', f'volume badhao {lvl}%', f'sound kam karke {lvl} karo'])
            text = f'{p}{v}{s}'.strip()
            tc = {'name': 'system_settings', 'arguments': json.dumps({'action': 'set_volume', 'level': lvl})}
        elif cat == 'bright':
            lvl = random.randint(10, 100)
            v = random.choice([f'brightness {lvl}% karo', f'screen light {lvl}% pe set karo', f'display dim karke {lvl}% kar do'])
            text = f'{p}{v}{s}'.strip()
            tc = {'name': 'system_settings', 'arguments': json.dumps({'action': 'set_brightness', 'level': lvl})}
        elif cat == 'settings':
            opt = random.choice([
                ('dark mode chalu karo', {'action': 'set_theme', 'theme': 'dark'}),
                ('light mode on karo', {'action': 'set_theme', 'theme': 'light'}),
                ('wifi on kar do', {'action': 'toggle_wifi', 'state': 'on'}),
                ('wifi band karo', {'action': 'toggle_wifi', 'state': 'off'}),
                ('bluetooth chalu karo', {'action': 'toggle_bluetooth', 'state': 'on'}),
                ('bluetooth band kar do', {'action': 'toggle_bluetooth', 'state': 'off'}),
                ('night light on karo', {'action': 'toggle_night_light', 'state': 'on'}),
            ])
            text = f'{p}{opt[0]}{s}'.strip()
            tc = {'name': 'system_settings', 'arguments': json.dumps(opt[1])}
        elif cat == 'telemetry':
            q = random.choice([
                ('RAM kitna bacha hai?', {'action': 'get_system_info', 'query': 'ram'}),
                ('CPU usage kitna chal raha hai?', {'action': 'get_system_info', 'query': 'cpu'}),
                ('Battery kitne percent hai?', {'action': 'get_battery_status'}),
                ('Disk C me kitna space khali hai?', {'action': 'get_disk_space', 'drive': 'C:'}),
            ])
            text = f'{p}{q[0]}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps(q[1])}
        elif cat == 'docker':
            d = random.choice(docker_targets)
            act = random.choice(['spin up kar do', 'start karo', 'chala do', 'up karo', 'restart maar do', 'down karo', 'logs dikhao'])
            text = f'{p}{d} {act}{s}'.strip()
            tc = {'name': 'developer_tools', 'arguments': json.dumps({'action': 'docker_manage', 'target': d})}
        elif cat == 'git':
            b = random.choice(git_branches)
            act = random.choice([
                (f'{b} me push maar de', {'action': 'git_push', 'target': b}),
                (f'{b} pull kar lo', {'action': 'git_pull', 'target': b}),
                (f'{b} branch pe checkout karo', {'action': 'git_checkout', 'target': b}),
                ('git status dikhao', {'action': 'git_status'}),
                ('changes commit kar do', {'action': 'git_commit', 'message': random.choice(git_commits)}),
            ])
            text = f'{p}{act[0]}{s}'.strip()
            tc = {'name': 'developer_tools', 'arguments': json.dumps(act[1])}
        elif cat == 'web':
            eng = random.choice(search_engines)
            top = random.choice(search_topics)
            text = f'{p}{eng} pe {top} search karo{s}'.strip()
            tc = {'name': 'web_navigation', 'arguments': json.dumps({'action': 'search', 'engine': eng, 'query': top})}
        elif cat == 'power':
            pw = random.choice([
                ('PC lock kar do', 'lock_pc'),
                ('laptop sleep mode me daal do', 'sleep_pc'),
                ('computer restart kar do', 'restart_pc'),
                ('system shutdown karo', 'shutdown_pc'),
            ])
            text = f'{p}{pw[0]}{s}'.strip()
            tc = {'name': 'system_automation', 'arguments': json.dumps({'action': pw[1]})}
        elif cat == 'files':
            fl = random.choice([
                ('Downloads folder kholo', {'action': 'open_folder', 'path': 'Downloads'}),
                ('Recycle bin khali kar do', {'action': 'empty_recycle_bin'}),
                ('temp files delete karo', {'action': 'clean_temp_files'}),
                ('Desktop dikhao', {'action': 'show_desktop'}),
            ])
            text = f'{p}{fl[0]}{s}'.strip()
            tc = {'name': 'productivity_tools', 'arguments': json.dumps(fl[1])}
        else: # vision
            v_act = random.choice([
                ('screenshot le lo', 'take_screenshot'),
                ('screen ka photo kheecho', 'take_screenshot'),
                ('active window capture karo', 'capture_active_window'),
                ('ye screen pe kya error hai dekho', 'analyze_screen'),
            ])
            text = f'{p}{v_act[0]}{s}'.strip()
            tc = {'name': 'vision_agent', 'arguments': json.dumps({'action': v_act[1]})}

    row = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
            {"role": "assistant", "tool_calls": [{"type": "function", "function": tc}]}
        ]
    }
    dataset_list.append(row)

hf_dataset = Dataset.from_list(dataset_list)
print(f"✅ Multilingual Dataset Ready: {len(hf_dataset)} unique Hinglish + Hindi + Bhojpuri commands!")

# --- STEP 5: CONTINUOUS TRAINING ---
base_step = max(max_step, 0)
print(f"🔥 [5/5] Starting Continuous Training from Step {base_step}...")
from trl import SFTTrainer
from transformers import TrainingArguments, TrainerCallback
from unsloth.chat_templates import get_chat_template

tokenizer = get_chat_template(tokenizer, chat_template="llama-3")

def formatting_prompts_func(examples):
    texts = [tokenizer.apply_chat_template(msg, tokenize=False, add_generation_prompt=False) for msg in examples["messages"]]
    return {"text": texts}

formatted_dataset = hf_dataset.map(formatting_prompts_func, batched=True)

# Callback to preserve true cumulative step numbering (e.g. checkpoint-21500)
class StepOffsetCallback(TrainerCallback):
    def __init__(self, offset):
        self.offset = offset
    def on_train_begin(self, args, state, control, **kwargs):
        if self.offset > 0 and state.global_step == 0:
            print(f"⏩ Offsetting training step counter to start at: {self.offset}")
            state.global_step = self.offset

callbacks = []
if base_step > 0:
    callbacks.append(StepOffsetCallback(base_step))

total_session_max_steps = base_step + 12000

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=formatted_dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    dataset_num_proc=2,
    callbacks=callbacks,
    args=TrainingArguments(
        per_device_train_batch_size=4,
        gradient_accumulation_steps=2,
        warmup_steps=10,
        max_steps=total_session_max_steps,
        learning_rate=1.5e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        save_steps=500,
        save_total_limit=4,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="/kaggle/working/outputs",
    ),
)

trainer.train()
print(f"🎉 Session Complete! Latest checkpoints saved in /kaggle/working/outputs/")
