import unittest
import json
import os
from app import app, load_config, save_config, initialize_email_service
from email_service import EmailService

class FlightTrackerTestCase(unittest.TestCase):
    """Test case for the Flight Tracker application"""
    
    def setUp(self):
        """Set up test client and test data"""
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Create a test config
        self.test_config = {
            "app_settings": {
                "language": "hr",
                "check_interval_minutes": 5,
                "max_flights": 20,
                "timezone": "Europe/Zagreb"
            },
            "notification_settings": {
                "send_email": True,
                "email_settings": {
                    "smtp_server": "smtp.gmail.com",
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
            "tracked_flights": ["OU 491"],
            "email_recipients": ["recipient@example.com"]
        }
        
        # Sample flight data
        self.sample_flight = {
            "airline": {
                "name": "Croatia Airlines",
                "logo": "https://www.zagreb-airport.hr/img/airlines/Croatia_Airlines.svg"
            },
            "scheduled_time": "23:05",
            "expected_time": "00:34",
            "origin": "LONDON",
            "flight_number": "OU 491",
            "baggage": "05",
            "gate": "A16",
            "status": "Sletio"
        }
        
        self.previous_flight = {
            "airline": {
                "name": "Croatia Airlines",
                "logo": "https://www.zagreb-airport.hr/img/airlines/Croatia_Airlines.svg"
            },
            "scheduled_time": "23:05",
            "expected_time": "00:34",
            "origin": "LONDON",
            "flight_number": "OU 491",
            "baggage": "05",
            "gate": "A16",
            "status": "Na vrijeme"
        }
    
    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()
    
    def test_email_service_initialization(self):
        """Test email service initialization"""
        email_service = EmailService(self.test_config)
        self.assertIsNotNone(email_service)
        self.assertEqual(email_service.email_settings['smtp_server'], 'smtp.gmail.com')
    
    def test_email_service_status_class(self):
        """Test status class determination"""
        email_service = EmailService(self.test_config)
        
        self.assertEqual(email_service._determine_status_class("Sletio"), "status-landed")
        self.assertEqual(email_service._determine_status_class("Kasni"), "status-delayed")
        self.assertEqual(email_service._determine_status_class("Otkazan"), "status-cancelled")
        self.assertEqual(email_service._determine_status_class("Na vrijeme"), "status-ontime")
    
    def test_email_subject(self):
        """Test email subject generation"""
        email_service = EmailService(self.test_config)
        
        self.assertEqual(
            email_service._get_subject_for_event("status_change", "OU 491", "Sletio"),
            "Promjena statusa leta OU 491 - Sletio"
        )
        
        self.assertEqual(
            email_service._get_subject_for_event("delay", "OU 491", "Kasni"),
            "Let OU 491 kasni"
        )
    
    def test_api_get_flights(self):
        """Test API endpoint for getting flights"""
        response = self.app.get('/api/flights')
        self.assertEqual(response.status_code, 200)
    
    def test_api_get_config(self):
        """Test API endpoint for getting configuration"""
        response = self.app.get('/api/config')
        self.assertEqual(response.status_code, 200)
        
        # Ensure password is not returned
        data = json.loads(response.data)
        self.assertIn('notification_settings', data)
        self.assertIn('email_settings', data['notification_settings'])
        self.assertEqual(data['notification_settings']['email_settings'].get('smtp_password', ''), '')
    
    def test_api_track_flight(self):
        """Test API endpoint for tracking a flight"""
        # First, ensure the flight is not already tracked
        config = load_config()
        if "OU 123" in config['tracked_flights']:
            config['tracked_flights'].remove("OU 123")
            save_config(config)
        
        response = self.app.post(
            '/api/flights/track',
            data=json.dumps({"flight_number": "OU 123"}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify the flight was added
        config = load_config()
        self.assertIn("OU 123", config['tracked_flights'])
    
    def test_api_add_email(self):
        """Test API endpoint for adding an email recipient"""
        # First, ensure the email is not already added
        config = load_config()
        if "test@example.com" in config['email_recipients']:
            config['email_recipients'].remove("test@example.com")
            save_config(config)
        
        response = self.app.post(
            '/api/email/add',
            data=json.dumps({"email": "test@example.com"}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify the email was added
        config = load_config()
        self.assertIn("test@example.com", config['email_recipients'])

if __name__ == '__main__':
    unittest.main()