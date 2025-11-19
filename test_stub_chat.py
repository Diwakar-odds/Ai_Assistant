from modules import conversational_ai
from modules.conversational_ai import AdvancedConversationalAI


def fake_callback(action, param):
    return f"[stub] {action} -> {param}"


def main():
    # Patch side-effectful functions for safe testing
    conversational_ai.webbrowser.open = lambda url: print(f"[webbrowser] {url}")

    def fake_popen(cmd, *_, **__):
        print(f"[Popen] {cmd}")
        class Dummy:
            def poll(self):
                return 0
        return Dummy()

    def fake_run(cmd, *_, **__):
        print(f"[run] {cmd}")
        class Result:
            returncode = 0
        return Result()

    conversational_ai.subprocess.Popen = fake_popen
    conversational_ai.subprocess.run = fake_run

    ai = AdvancedConversationalAI(automation_callback=fake_callback)
    commands = [
        "open chrome",
        "open youtube.com",
        "close chrome",
        "google best laptops",
        "play imagine dragons",
        "create a powerpoint",
        "volume 40",
        "open wifi settings",
        "lock the system",
    ]
    for cmd in commands:
        print(cmd, '=>', ai.process_message(cmd))


if __name__ == "__main__":
    main()
