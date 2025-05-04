import os
import sys
import json
import time
import logging
from scheduler import FlightScheduler

# Configure basic logging for the test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('test_scheduler')

def create_test_config():
    """Create a test configuration file"""
    config = {
        "app_settings": {
            "language": "hr",
            "check_interval_minutes": 1,  # Short interval for testing
            "max_flights": 20,
            "timezone": "Europe/Zagreb"
        },
        "notification_settings": {
            "send_email": False,  # Disable email for testing
            "email_settings": {
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "smtp_username": "test@example.com",
                "smtp_password": "password",
                "sender_email": "test@example.com",
                "use_tls": True
            },
            "notification_events": {
                "status_change": True,
                "delay": True,
                "gate_change": True,
                "arrival": True
            }
        },
        "tracked_flights": ["OU123", "LH1234"],  # Example flight numbers
        "email_recipients": ["recipient@example.com"]
    }
    
    # Create test config file
    with open('test_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    return 'test_config.json'

def test_scheduler():
    """Test the scheduler functionality"""
    logger.info("Starting scheduler test")
    
    # Create test directories
    os.makedirs('test_data', exist_ok=True)
    
    # Create test config
    config_path = create_test_config()
    
    try:
        # Initialize scheduler with test config
        scheduler = FlightScheduler(config_path=config_path, data_path='test_data')
        
        # Start scheduler
        logger.info("Starting scheduler")
        scheduler.start()
        
        # Let it run for a short time
        logger.info("Scheduler running, waiting for 10 seconds...")
        time.sleep(10)
        
        # Stop scheduler
        logger.info("Stopping scheduler")
        scheduler.stop()
        
        # Check if data files were created
        current_data_path = os.path.join('test_data', 'current_data.json')
        state_path = os.path.join('test_data', 'scheduler_state.json')
        
        if os.path.exists(current_data_path):
            logger.info(f"Current data file created: {current_data_path}")
        else:
            logger.error(f"Current data file not created: {current_data_path}")
        
        if os.path.exists(state_path):
            logger.info(f"State file created: {state_path}")
        else:
            logger.error(f"State file not created: {state_path}")
        
        logger.info("Test completed successfully")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False
    finally:
        # Clean up test files
        if os.path.exists(config_path):
            os.remove(config_path)
            logger.info(f"Removed test config: {config_path}")

if __name__ == "__main__":
    success = test_scheduler()
    sys.exit(0 if success else 1)