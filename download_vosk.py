import urllib.request
import zipfile
import os

model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
model_dir = r"d:\Projects\Ai_Assistant\core_ai\src\ai_assistant\models"
zip_path = os.path.join(model_dir, "vosk-model.zip")

os.makedirs(model_dir, exist_ok=True)

print("Downloading Vosk model...")
urllib.request.urlretrieve(model_url, zip_path)

print("Extracting Vosk model...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(model_dir)

# Rename the extracted folder for easier access
extracted_folder = os.path.join(model_dir, "vosk-model-small-en-us-0.15")
final_folder = os.path.join(model_dir, "vosk-model")

if os.path.exists(extracted_folder):
    if os.path.exists(final_folder):
        import shutil
        shutil.rmtree(final_folder)
    os.rename(extracted_folder, final_folder)

os.remove(zip_path)
print("Vosk model successfully downloaded and extracted to:", final_folder)
