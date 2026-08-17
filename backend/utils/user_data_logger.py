
import os
import json
from datetime import datetime

USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_data')

def get_timestamp():
    return datetime.now().strftime('%Y%m%d_%H%M%S')

def save_data(data_type, data):
    """
    Saves data to the appropriate folder with a timestamp.

    Args:
        data_type (str): The type of data (e.g., 'actions', 'queries', 'replies', 'modules').
        data (dict): The data to save as a JSON file.
    """
    timestamp = get_timestamp()
    folder_path = os.path.join(USER_DATA_DIR, data_type)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    file_path = os.path.join(folder_path, f'{timestamp}.json')
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def log_action(action_name, params):
    """Logs a user action."""
    save_data('actions', {'action': action_name, 'parameters': params})

def log_query(query_text):
    """Logs a user query."""
    save_data('queries', {'query': query_text})

def log_reply(reply_text):
    """Logs an assistant reply."""
    save_data('replies', {'reply': reply_text})

def log_module_usage(module_name, function_name):
    """Logs the usage of a module and function."""
    save_data('modules', {'module': module_name, 'function': function_name})

if __name__ == '__main__':
    # Example Usage
    log_action('play_music', {'song_name': 'Bohemian Rhapsody'})
    log_query('What is the weather today?')
    log_reply('The weather is sunny.')
    log_module_usage('music', 'play')
    print(f"User data logging setup in: {USER_DATA_DIR}")

