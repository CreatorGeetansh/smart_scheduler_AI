# state_manager.py
import json
import os
from models import MeetingRequestState
from logger_config import logger

STATE_FILE = "conversation_state.json"

class StateManager:
    """Handles loading and saving the conversation state."""
    def __init__(self, state_file=STATE_FILE):
        self.state_file = state_file

    def save_state(self, state: MeetingRequestState):
        """Saves the current state to a JSON file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=4)
            logger.info(f"State saved successfully to {self.state_file}")
        except IOError as e:
            logger.error(f"Error saving state to {self.state_file}: {e}")

    def load_state(self) -> MeetingRequestState:
        """Loads the state from a JSON file, or creates a new one."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"State loaded successfully from {self.state_file}")
                    return MeetingRequestState.from_dict(data)
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Error loading state from {self.state_file}, creating new state. Error: {e}")
                return MeetingRequestState()
        else:
            logger.info("No state file found, creating a new state.")
            return MeetingRequestState()