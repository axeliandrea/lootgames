import os
import json
import logging

HISTORY_FILE = "storage/topup_history.json"
logger = logging.getLogger(__name__)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_history_entry(uid, entry):
    data = load_history()
    if uid not in data:
        data[uid] = []
    data[uid].append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"🧾 History top-up disimpan untuk {uid}")
