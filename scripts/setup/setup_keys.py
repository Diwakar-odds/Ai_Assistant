import os
import shutil

def setup_keys():
    print("="*60)
    print("YourDaddy Assistant - API Key Setup")
    print("="*60)
    print("To enable advanced AI features (like Gemini or ChatGPT),")
    print("you need to provide your API keys.")
    print("="*60)

    # Check if .env exists
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            print("Creating .env file from .env.example...")
            shutil.copy('.env.example', '.env')
        else:
            print("Error: .env.example not found. Creating a new .env file.")
            with open('.env', 'w') as f:
                f.write("# YourDaddy Assistant Environment Variables\n")

    # Read existing .env
    env_content = {}
    with open('.env', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                env_content[key.strip()] = value.strip()

    # Ask for Gemini Key
    print("\n[1] Google Gemini API Key (Recommended for free usage)")
    print("    Get it here: https://aistudio.google.com/app/apikey")
    current_gemini = env_content.get('GEMINI_API_KEY', '')
    if current_gemini and current_gemini != 'your_gemini_api_key_here':
        print(f"    Current: {current_gemini[:5]}...{current_gemini[-5:]}")
        change = input("    Change? (y/N): ").lower()
        if change == 'y':
            gemini_key = input("    Enter new Gemini API Key: ").strip()
            if gemini_key:
                env_content['GEMINI_API_KEY'] = gemini_key
    else:
        gemini_key = input("    Enter Gemini API Key (or press Enter to skip): ").strip()
        if gemini_key:
            env_content['GEMINI_API_KEY'] = gemini_key

    # Ask for OpenAI Key
    print("\n[2] OpenAI API Key (Optional, paid)")
    print("    Get it here: https://platform.openai.com/api-keys")
    current_openai = env_content.get('OPENAI_API_KEY', '')
    if current_openai and current_openai != 'your_openai_api_key_here':
        print(f"    Current: {current_openai[:5]}...{current_openai[-5:]}")
        change = input("    Change? (y/N): ").lower()
        if change == 'y':
            openai_key = input("    Enter new OpenAI API Key: ").strip()
            if openai_key:
                env_content['OPENAI_API_KEY'] = openai_key
    else:
        openai_key = input("    Enter OpenAI API Key (or press Enter to skip): ").strip()
        if openai_key:
            env_content['OPENAI_API_KEY'] = openai_key

    # Write back to .env
    with open('.env', 'w') as f:
        for key, value in env_content.items():
            f.write(f"{key}={value}\n")
        
        # Ensure keys exist if they weren't in the file originally
        if 'GEMINI_API_KEY' not in env_content and 'GEMINI_API_KEY' in locals() and gemini_key:
             f.write(f"GEMINI_API_KEY={gemini_key}\n")
        if 'OPENAI_API_KEY' not in env_content and 'OPENAI_API_KEY' in locals() and openai_key:
             f.write(f"OPENAI_API_KEY={openai_key}\n")

    print("\n" + "="*60)
    print("Setup Complete!")
    print("Please restart the application for changes to take effect.")
    print("="*60)

if __name__ == "__main__":
    setup_keys()
