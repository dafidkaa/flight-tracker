import os
import sys
import logging
import signal
import time
from flask import Flask
import threading

# Set up path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import our modules
from app import app as flask_app
from scheduler import FlightScheduler
from logging_config import configure_logging

# Set up logging
configure_logging()
logger = logging.getLogger('main')

# Global variables
scheduler = None
stop_event = threading.Event()

def setup_signal_handlers():
    """
    Set up signal handlers for graceful shutdown
    """
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        stop_event.set()

        if scheduler:
            logger.info("Stopping scheduler...")
            scheduler.stop()

        logger.info("Shutdown complete")
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Signal handlers registered")

def initialize_directories():
    """
    Initialize required directories
    """
    directories = [
        'logs',
        'data'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    logger.info("Directories initialized")

def start_scheduler():
    """
    Initialize and start the flight scheduler
    """
    global scheduler

    try:
        # Create scheduler instance
        scheduler = FlightScheduler()

        # Start scheduler
        scheduler.start()

        logger.info("Scheduler started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}", exc_info=True)
        return False

def start_flask_app():
    """
    Start the Flask application
    """
    try:
        # Get port from environment variable or use default
        port = int(os.environ.get('PORT', 8080))

        # Start Flask app in a separate thread
        flask_thread = threading.Thread(
            target=flask_app.run,
            kwargs={
                'debug': False,  # Disable debug mode when running in a thread
                'host': '0.0.0.0',
                'port': port
            }
        )
        flask_thread.daemon = True
        flask_thread.start()

        logger.info(f"Flask application started successfully on port {port}")
        return True
    except Exception as e:
        logger.error(f"Error starting Flask application: {str(e)}", exc_info=True)
        return False

def main():
    """
    Main entry point for the application
    """
    logger.info("Starting Zagreb Airport Flight Tracker")

    # Set up signal handlers
    setup_signal_handlers()

    # Initialize directories
    initialize_directories()

    # Start scheduler
    if not start_scheduler():
        logger.error("Failed to start scheduler, exiting")
        return 1

    # Start Flask app
    if not start_flask_app():
        logger.error("Failed to start Flask application, exiting")
        scheduler.stop()
        return 1

    logger.info("Zagreb Airport Flight Tracker started successfully")

    # Keep the main thread alive
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        if scheduler:
            scheduler.stop()

    return 0

if __name__ == "__main__":
    sys.exit(main())