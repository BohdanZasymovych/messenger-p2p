"""Function to set up logging"""
import os
import logging
from datetime import datetime


def setup_logging():
    """Sets up logging for the application"""
    # Ensure folder for logs exists
    FOLDER_PATH = "./logs"
    if not os.path.exists(FOLDER_PATH):
        os.makedirs(FOLDER_PATH)

    # Set up logging
    TIMESTAMP = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]
    LOG_FILENAME = f"./logs/log_{TIMESTAMP}.log"
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
