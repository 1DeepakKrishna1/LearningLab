# telemetry_setup.py

import logging
import os
from dotenv import load_dotenv 
from azure.monitor.opentelemetry import configure_azure_monitor
import uuid
from contextvars import ContextVar

load_dotenv()

LOG_ENV = os.environ.get("LOG_ENV")

# Connection string for Azure Application Insights
CONNECTION_STRING = os.environ.get("AZURE_INSIGHT_CONNECTION_STRING")
LOCAL_LOG_FILE = os.environ.get("LOG_FILE", "app_activity.log")

# Context variable for trace_id
trace_id_var = ContextVar("trace_id", default=None)

class TraceIDFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = trace_id_var.get()
        return True

def setup_telemetry():

    if LOG_ENV == "store_log_azureinsight":
        configure_azure_monitor(
            connection_string=CONNECTION_STRING,
            logger_name="app_logger" 
        )
        print("INFO: Azure Monitor telemetry enabled.")
    elif LOG_ENV is None or LOG_ENV not in ["store_log_local", "store_log_azureinsight"]:
        print(f"WARNING: LOG_ENV not set or invalid ('{LOG_ENV}'). Logging only to console.")
    else:
         print(f"INFO: LOG_ENV set to '{LOG_ENV}'. Azure Monitor skipped.")


def get_logger():
    """
    logger based on the LOG_ENV variable.
    """
    logger = logging.getLogger("app_logger")
    logger.setLevel(logging.DEBUG)  # Set overall logger level
    logger.addFilter(TraceIDFilter()) # Add trace_id filter

    # Stream Handler for Console Output (Default fallback)
    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(trace_id)s - %(message)s")
    stream_handler.setFormatter(stream_formatter)

    # Conditional File Handler for Local Storage
    if LOG_ENV == "store_log_local":
        try:
            
            file_handler = logging.FileHandler(LOCAL_LOG_FILE, encoding='utf-8')
            
            # log format for the local file
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(trace_id)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.INFO) # Set a specific level for the file
            
            # Add the file handler, preventing duplicates
            is_file_handler_present = any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(LOCAL_LOG_FILE) for h in logger.handlers)
            if not is_file_handler_present:
                 logger.addHandler(file_handler)
            
            logger.info(f"Local logging initialized. Logs being written to {os.path.abspath(LOCAL_LOG_FILE)}")

        except Exception as e:
            # Log a warning to the console if local logging setup fails
            print(f"WARNING: Failed to set up local file logging to {LOCAL_LOG_FILE}: {e}")
            logger.warning(f"Failed to set up local file logging: {e}") 

    # Add the Stream Handler if the logger is currently empty (default to console output)
    # This ensures that even if no specific environment is set, logs still appear in the console.
    if not logger.handlers:
        logger.addHandler(stream_handler)
        logger.info("Logger configured with only StreamHandler (console).")
    
    return logger

setup_telemetry()

app_logger = get_logger()