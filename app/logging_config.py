import os
import logging
from logging.handlers import RotatingFileHandler
import sys

def configure_logging():
    """
    Configure comprehensive logging for the application
    
    Sets up logging with:
    - Console output
    - File output with rotation
    - Different log levels for different components
    - Formatted log messages
    """
    # Create logs directory if it doesn't exist
    log_dir = '../logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Define log files
    main_log = os.path.join(log_dir, 'main.log')
    scheduler_log = os.path.join(log_dir, 'scheduler.log')
    scraper_log = os.path.join(log_dir, 'scraper.log')
    email_log = os.path.join(log_dir, 'email.log')
    flask_log = os.path.join(log_dir, 'flask.log')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler (for all logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Main log file handler
    main_handler = RotatingFileHandler(
        main_log,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(main_handler)
    
    # Configure component-specific loggers
    configure_component_logger('scheduler', scheduler_log, logging.INFO, detailed_formatter)
    configure_component_logger('scraper', scraper_log, logging.INFO, detailed_formatter)
    configure_component_logger('email_service', email_log, logging.INFO, detailed_formatter)
    configure_component_logger('flask', flask_log, logging.INFO, detailed_formatter)
    
    # Log startup message
    logging.info("Logging configured successfully")

def configure_component_logger(name, log_file, level, formatter):
    """
    Configure a logger for a specific component
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level
        formatter: Log formatter
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Don't propagate to root logger to avoid duplicate console logs
    logger.propagate = False
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=3
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)