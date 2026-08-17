# 🧠 PULSAR - No-Code Fine-Tuning Guide (LLaMA-Factory)

Hi there! If you're reading this, you are the friend tasked with taking our massive 2.5 million line dataset and turning it into a hyper-intelligent, OS-controlling AI model for PULSAR. 

We have prepared everything for you. The raw dataset was 1.3 GB, but we compressed it into highly efficient `.jsonl.gz` files located in `data/training/`.

**Good News:** You do NOT need to write any Python code! We will be using **LLaMA-Factory**, a beautiful Web UI that automates the entire fine-tuning process.

---

## 🛠️ Step 1: Launch Google Colab (Free GPU)
Training a model on 2.5 million lines requires a powerful GPU (like NVIDIA T4). Do **not** try to train this on your local laptop (Intel Graphics won't work).
1. Go to **[Google Colab](https://colab.research.google.com/)**.
2. Create a New Notebook.
3. Go to **Runtime -> Change runtime type** -> Select **T4 GPU** (or A100 if you have Colab Pro).

## 📥 Step 2: The "All-in-One" Setup & Launch
Colab mein ek naya Code cell banao aur ye poora code ek sath copy-paste karke run karo. Ye khud download karega, dataset register karega, aur Web UI start kar dega:

```python
# 1. Download & Install LLaMA-Factory
!git clone https://github.com/hiyouga/LLaMA-Factory.git
%cd /content/LLaMA-Factory
!pip install -e .[metrics] bitsandbytes

# 2. Extract and Convert Dataset to Alpaca Format
import json
import os
import shutil

!rm -rf /root/.cache/huggingface/datasets/

root_file = '/content/ultimate_windows_dataset_v3.jsonl.gz'
data_file_gz = '/content/LLaMA-Factory/data/ultimate_windows_dataset_v3.jsonl.gz'
data_file_in = '/content/LLaMA-Factory/data/ultimate_windows_dataset_v3.jsonl'
data_file_out = '/content/LLaMA-Factory/data/alpaca_windows_dataset.jsonl'

if os.path.exists(root_file):
    shutil.move(root_file, data_file_gz)
if os.path.exists(data_file_gz):
    os.system(f'gunzip -f {data_file_gz}')

print("Converting dataset to Alpaca format for LLaMA-Factory...")
with open(data_file_in, 'r', encoding='utf-8') as fin, open(data_file_out, 'w', encoding='utf-8') as fout:
    for line in fin:
        data = json.loads(line)
        system, instruction, output = "", "", ""
        for msg in data.get("messages", []):
            if msg["role"] == "system":
                system = msg.get("content", "")
            elif msg["role"] == "user":
                instruction = msg.get("content", "")
            elif msg["role"] == "assistant":
                if "tool_calls" in msg and len(msg["tool_calls"]) > 0:
                    output = json.dumps(msg["tool_calls"][0]["function"])
                else:
                    output = msg.get("content", "")
        
        alpaca_item = {
            "instruction": instruction,
            "input": "",
            "output": output,
            "system": system
        }
        fout.write(json.dumps(alpaca_item) + "\n")

filepath = '/content/LLaMA-Factory/data/dataset_info.json'
info = {}
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        info = json.load(f)

# Register as standard Alpaca format
info['pulsar_windows_data'] = {
    "file_name": "alpaca_windows_dataset.jsonl"
}

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(info, f, indent=2)

print("\n✅ Setup Complete! Starting Web UI...\n")

# 3. Launch Web UI
%cd /content/LLaMA-Factory
%env GRADIO_SHARE=1
!llamafactory-cli webui
```
*Wait for a few minutes. At the end of the output, you will see a public URL (like `https://xxxx.gradio.live`). Click on it to open the Web UI!*

## 🖱️ Step 3: Configure Training in the Web UI
Before clicking start, upload your dataset:
1. **Upload File:** In Colab's left sidebar (📁), open `LLaMA-Factory` -> `data` folder, and upload `ultimate_windows_dataset_v3.jsonl.gz` inside it.
2. **Model Name:** Select `Llama-3.1-8B-Instruct` (or `Llama-3-8B-Instruct`) from the drop-down.
3. **Advanced -> Quantization:** Set to `4-bit` (This saves VRAM so it fits on the T4 GPU).
4. **Dataset:** Select `pulsar_windows_data` in the Dataset dropdown.
5. **Learning Rate:** Set to `2e-4`.
5. **Epochs:** Start with `1` epoch.
6. **Output Directory:** Name it `pulsar-lora-model`.
7. Scroll down and click the big orange **"Start"** button!

*(Grab a coffee, this will take a few hours depending on the dataset size).*

## 📦 Step 4: Export to GGUF (For Local PC)
Once the training hits 100% and says "Completed", we need to export it so it can run offline on Windows.
1. In the same Web UI, go to the **Export** tab at the top.
2. Select **Export to GGUF**.
3. Choose the quantization method (e.g., `q4_k_m`).
4. Click **Export**. It will generate a `.gguf` file.
5. Download this `.gguf` file to your local Windows PC.

## 🚀 Step 5: Run PULSAR on Your Windows PC!
Now that you have the `.gguf` file, you can run it completely offline natively on Windows!

1. Download and install [Ollama](https://ollama.com/) on your Windows PC.
2. Create a file named `Modelfile` on your desktop:
```dockerfile
# Point this to where you downloaded the GGUF file
FROM ./pulsar-model-q4_k_m.gguf

TEMPLATE """{{ if .System }}<|start_header_id|>system<|end_header_id|>
{{ .System }}<|eot_id|>{{ end }}{{ if .Prompt }}<|start_header_id|>user<|end_header_id|>
{{ .Prompt }}<|eot_id|>{{ end }}<|start_header_id|>assistant<|end_header_id|>
"""
```
3. Open Terminal/PowerShell and run: `ollama create pulsar -f Modelfile`
4. Finally, start the AI: `ollama run pulsar`

**Congratulations! The PULSAR AI is now ready to control your OS!**

> Note: If you ever want to see how this works under the hood with raw Python (Unsloth), check out the `ADVANCED_TRAINING_GUIDE.md` file.
