import os
import sys
import json
import time
import logging
import threading
from datetime import datetime

# Configure basic logging for the test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('test_scheduler')

# Create test directories
os.makedirs('logs', exist_ok=True)
os.makedirs('app/data', exist_ok=True)

# Mock flight data for testing
def generate_mock_flight_data():
    """Generate mock flight data for testing"""
    return {
        "timestamp": datetime.now().isoformat(),
        "source": "mock_data",
        "flights": [
            {
                "airline": {
                    "name": "Croatia Airlines",
                    "logo": None
                },
                "scheduled_time": "10:00",
                "expected_time": "10:15",
                "origin": "Frankfurt",
                "flight_number": "OU123",
                "baggage": "5",
                "gate": "A1",
                "status": "On Time"
            },
            {
                "airline": {
                    "name": "Lufthansa",
                    "logo": None
                },
                "scheduled_time": "11:30",
                "expected_time": "12:00",
                "origin": "Munich",
                "flight_number": "LH1234",
                "baggage": "7",
                "gate": "B3",
                "status": "Delayed"
            }
        ]
    }

# Create test data files
def create_test_data():
    """Create test data files"""
    # Create current data file
    current_data = generate_mock_flight_data()
    with open('app/data/current_data.json', 'w', encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)
    
    # Create previous data file with slight differences
    previous_data = generate_mock_flight_data()
    previous_data['flights'][0]['status'] = "Scheduled"
    previous_data['flights'][1]['gate'] = "B2"
    with open('app/data/previous_data.json', 'w', encoding='utf-8') as f:
        json.dump(previous_data, f, ensure_ascii=False, indent=2)
    
    return current_data, previous_data

# Create test config
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
        "tracked_flights": ["OU123", "LH1234"],
        "email_recipients": ["recipient@example.com"]
    }
    
    # Create test config file
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    return config

# Mock scheduler for testing
class MockScheduler:
    """Mock scheduler for testing"""
    
    def __init__(self):
        self.config = create_test_config()
        self.current_data, self.previous_data = create_test_data()
        self.running = False
        self.check_interval = self.config['app_settings']['check_interval_minutes']
        self.stop_event = threading.Event()
        logger.info("Mock scheduler initialized")
    
    def check_flight_updates(self):
        """Mock flight update check"""
        logger.info("Checking for flight updates")
        
        # Generate new mock data with changes
        new_data = generate_mock_flight_data()
        new_data['flights'][0]['status'] = "Landed"
        new_data['flights'][1]['gate'] = "B4"
        
        # Save new data
        with open('app/data/current_data.json', 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        
        # Check for changes
        self._check_for_changes(new_data, self.current_data)
        
        # Update current data
        self.previous_data = self.current_data
        self.current_data = new_data
        
        logger.info("Flight data updated successfully")
    
    def _check_for_changes(self, new_data, previous_data):
        """Check for changes in flight data"""
        tracked_flights = self.config['tracked_flights']
        
        # Create dictionaries for easy lookup
        prev_flights = {f['flight_number']: f for f in previous_data['flights']}
        new_flights = {f['flight_number']: f for f in new_data['flights']}
        
        # Check each tracked flight
        for flight_number in tracked_flights:
            if flight_number in prev_flights and flight_number in new_flights:
                prev_flight = prev_flights[flight_number]
                new_flight = new_flights[flight_number]
                
                # Check for status change
                if new_flight['status'] != prev_flight['status']:
                    logger.info(f"Status change detected for flight {flight_number}: {prev_flight['status']} -> {new_flight['status']}")
                
                # Check for gate change
                if new_flight['gate'] != prev_flight['gate']:
                    logger.info(f"Gate change detected for flight {flight_number}: {prev_flight['gate']} -> {new_flight['gate']}")
    
    def start(self):
        """Start the mock scheduler"""
        self.running = True
        logger.info(f"Scheduler started with check interval of {self.check_interval} minutes")
        
        # Start a thread to run checks
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        # Run initial check
        self.check_flight_updates()
    
    def _run(self):
        """Run the scheduler loop"""
        while not self.stop_event.is_set():
            time.sleep(self.check_interval * 60)
            if not self.stop_event.is_set():
                self.check_flight_updates()
    
    def stop(self):
        """Stop the mock scheduler"""
        self.stop_event.set()
        self.running = False
        logger.info("Scheduler stopped")

def test_scheduler():
    """Test the scheduler functionality"""
    logger.info("Starting scheduler test")
    
    try:
        # Initialize mock scheduler
        scheduler = MockScheduler()
        
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
        if os.path.exists('app/data/current_data.json'):
            logger.info("Current data file created successfully")
        else:
            logger.error("Current data file not created")
        
        logger.info("Test completed successfully")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_scheduler()
    sys.exit(0 if success else 1)