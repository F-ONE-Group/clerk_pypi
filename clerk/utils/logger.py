import inspect
import os
import logging
import sys

if sys.platform == "win32":
    base_path = os.path.join(os.getcwd(), "data", "artifacts")
else:
    base_path = "/app/data/artifacts"

os.makedirs(base_path, exist_ok=True)


def debug(message: str):
    """
    Logs a debug message.

    This function logs a debug message by calling the _log function with "DEBUG" as the level.

    Args:
        module (str): The name of the module or component that generated the log message.
        message (str): The log message to be logged.
    """
    _log("DEBUG", message)


def info(message: str):
    """
    Logs an info message.

    This function logs an info message by calling the _log function with "INFO" as the level.

    Args:
        module (str): The name of the module or component that generated the log message.
        message (str): The log message to be logged.
    """
    _log("INFO", message)


def warning(message: str):
    """
    Logs a warning message.

    This function logs a warning message by calling the _log function with "WARNING" as the level.

    Args:
        module (str): The name of the module or component that generated the log message.
        message (str): The log message to be logged.
    """
    _log("WARNING", message)


def error(message: str):
    """
    Logs an error message.

    This function logs an error message by calling the _log function with "ERROR" as the level.

    Args:
        module (str): The name of the module or component that generated the log message.
        message (str): The log message to be logged.
    """
    _log("ERROR", message)


def _log(level: str, message: str):
    """
    Log a message to a file in the artifacts folder using the Python logging module.

    Args:
        level (str): The log level of the message (e.g., "INFO", "DEBUG", "WARNING", "ERROR", "AUDIT").
        module (str): The name of the module or component that generated the log message.
        message (str): The log message to be logged.

    Returns:
        None

    Example Usage:
        _log_to_console("INFO", "module_name", "This is an info message")

    """
    # Get run_id from environment variable or default to "unknown"
    run_id = os.getenv("_RUN_ID", "unknown")

    # Create the base path for artifacts
    logs_path = os.path.join(base_path, run_id)
    os.makedirs(logs_path, exist_ok=True)
    # Define the log file path
    log_file_path = os.path.join(logs_path, "logs.txt")

    # Get the calling file (two levels up the stack)
    frame = inspect.stack()[2]
    module = os.path.basename(frame.filename)

    # Configure the logger
    logger = logging.getLogger(module)
    if not logger.handlers:
        fh = logging.FileHandler(log_file_path)
        format = "%(asctime)s - %(name)s - %(levelname)s: - %(message)s"
        formatter = logging.Formatter(format)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        # → console handler  (same formatter)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # keep root logger from printing duplicates

    # Log the message based on the level
    if level.lower() == "info":
        logger.info(message)
    elif level.lower() == "audit":
        logger.info("AUDIT: " + message)
    elif level.lower() == "debug":
        logger.debug(message)
    elif level.lower() == "warning":
        logger.warning(message)
    elif level.lower() == "error":
        logger.error(message)

    # Remove handlers to avoid duplicate logs
    logger.handlers.clear()
