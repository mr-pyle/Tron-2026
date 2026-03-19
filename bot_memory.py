'''
# HOW TO USE WITHIN BOTS:

import bot_memory

# 1. Load previous learning (Returns an empty dict {} the first time)
ai_data = bot_memory.load_memory()

def get_move(x, y, board):
    # ... student's machine learning algorithm ...
    
    # 2. Update their AI dictionary
    ai_data["matches_played"] = ai_data.get("matches_played", 0) + 1
    
    # 3. Save it securely back to their JSON file!
    bot_memory.save_memory(ai_data)
    
    return "UP"

'''



import os
import json

# The engine will securely pass the bot's name through the environment
BOT_NAME = os.environ.get("TRON_BOT_NAME")
MEMORY_DIR = "bot_memory"

def _get_memory_path():
    if not BOT_NAME:
        # If someone tries to run this outside the engine, block it
        raise RuntimeError("bot_memory can only be used inside the Tron Engine.")
    
    # Create the bot_memory folder if it doesn't exist
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        
    # Strip any weird characters just in case, locking them to their specific file
    safe_name = "".join(c for c in BOT_NAME if c.isalnum() or c in ('_', '-'))
    return os.path.join(MEMORY_DIR, f"{safe_name}_data.json")

def save_memory(data_dict):
    """Saves a Python dictionary to your bot's personal JSON file."""
    if not isinstance(data_dict, dict):
        print("Error: save_memory only accepts Python dictionaries.")
        return False
        
    try:
        filepath = _get_memory_path()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=4)
        return True
    except Exception as e:
        print(f"Failed to save memory: {e}")
        return False

def load_memory():
    """Loads your bot's personal JSON file as a Python dictionary."""
    filepath = _get_memory_path()
    if not os.path.exists(filepath):
        return {} # Return an empty dictionary if no memory exists yet
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load memory: {e}")
        return {}