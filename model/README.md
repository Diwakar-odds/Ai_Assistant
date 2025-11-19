# Voice Recognition Model Directory

This directory contains voice recognition model files for YourDaddy Assistant.

## Vosk Model Setup

To use voice recognition, download a Vosk model:

1. Visit: https://alphacephei.com/vosk/models
2. Download: vosk-model-small-en-us-0.15.zip (or similar)
3. Extract to: `model/vosk-model-small-en-us-0.15/`

## Directory Structure

```
model/
├── README.md (this file)
└── vosk-model-small-en-us-0.15/  (download required)
    ├── README
    ├── am/
    │   └── final.mdl
    ├── conf/
    │   ├── mfcc.conf
    │   └── model.conf
    ├── graph/
    │   ├── disambig_tid.int
    │   ├── Gr.fst
    │   └── ...
    └── ivector/
        └── ...
```

## Model Download Script

You can download the model automatically using:

```bash
# For Windows:
curl -L -o vosk-model.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model.zip

# For Linux/macOS:
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

## Alternative Models

- `vosk-model-en-us-0.22` - Large English model (1.8GB)
- `vosk-model-small-en-us-0.15` - Small English model (40MB) - Recommended
- Other languages available on the Vosk website

## Configuration

The model path is configured in `multimodal_config.json`:

```json
{
  "voice": {
    "recognition": {
      "model_path": "model/vosk-model-small-en-us-0.15"
    }
  }
}
```