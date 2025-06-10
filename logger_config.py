# logger_config.py
import logging
import sys

def setup_logger():
    """Sets up a structured logger for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s",
        handlers=[
            logging.FileHandler("agent.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()