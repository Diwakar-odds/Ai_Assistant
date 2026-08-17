import pyautogui
import time
import sys

# Usage: python win_start_menu_launcher.py "App Name"
def open_app_via_start_menu(app_name: str):
    # Minimize all windows (Win+D)
    pyautogui.hotkey('win', 'd')
    time.sleep(0.5)
    # Open Start menu
    pyautogui.press('win')
    time.sleep(0.5)
    # Type app name
    pyautogui.write(app_name, interval=0.05)
    time.sleep(1)
    # Press Enter to launch
    pyautogui.press('enter')
    print(f"Tried to open '{app_name}' via Start menu.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python win_start_menu_launcher.py 'App Name'")
    else:
        open_app_via_start_menu(sys.argv[1])
