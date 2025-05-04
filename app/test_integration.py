"""
Integration test for Zagreb Airport Flight Tracker
This script tests the integration of all components:
- Scraper
- Email Service
- Scheduler
- Flask App
"""

import os
import sys
import unittest
import json
import time
import threading
from unittest.mock import patch, MagicMock

# Ensure we're in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Create necessary directories
os.makedirs('../logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Import application modules
from app.scraper import ZagrebAirportScraper
from app.email_service import EmailService
import app.app as flask_app

# Mock the scheduler to avoid actual scheduling during tests
class MockScheduler:
    def __init__(self, config_path='../config.json'):
        self.config_path = config_path
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
    def start(self):
        pass
        
    def stop(self):
        pass

class IntegrationTest(unittest.TestCase):
    """Integration test for the flight tracker system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Create test config
        cls.test_config = {
            "app_settings": {
                "language": "hr",
                "check_interval_minutes": 1,
                "max_flights": 20,
                "timezone": "Europe/Zagreb"
            },
            "notification_settings": {
                "send_email": False,  # Disable actual email sending for tests
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
            "tracked_flights": [
                "OU 491",
                "LH 1726"
            ],
            "email_recipients": [
                "test@example.com"
            ]
        }
        
        # Save test config
        with open('test_config.json', 'w', encoding='utf-8') as f:
            json.dump(cls.test_config, f, ensure_ascii=False, indent=2)
        
        # Configure Flask app for testing
        flask_app.app.config['TESTING'] = True
        cls.client = flask_app.app.test_client()
        
        print("Test environment set up")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        # Remove test config
        if os.path.exists('test_config.json'):
            os.remove('test_config.json')
        
        print("Test environment cleaned up")
    
    def test_1_scraper_functionality(self):
        """Test that the scraper can fetch flight data"""
        scraper = ZagrebAirportScraper()
        flight_data = scraper.scrape_arrivals()
        
        # Check that we got valid data
        self.assertIsNotNone(flight_data)
        self.assertIn('flights', flight_data)
        self.assertIsInstance(flight_data['flights'], list)
        self.assertGreater(len(flight_data['flights']), 0)
        
        # Check that the first flight has all required fields
        first_flight = flight_data['flights'][0]
        self.assertIn('airline', first_flight)
        self.assertIn('flight_number', first_flight)
        self.assertIn('origin', first_flight)
        self.assertIn('scheduled_time', first_flight)
        self.assertIn('status', first_flight)
        
        print("Scraper test passed")
    
    def test_2_email_service_initialization(self):
        """Test that the email service initializes correctly"""
        email_service = EmailService(self.test_config)
        
        # Check that the email service has the correct configuration
        self.assertEqual(email_service.email_settings, self.test_config['notification_settings']['email_settings'])
        self.assertEqual(email_service.email_recipients, self.test_config['email_recipients'])
        
        print("Email service initialization test passed")
    
    @patch('app.email_service.smtplib.SMTP')
    def test_3_email_notification(self, mock_smtp):
        """Test that email notifications can be sent"""
        # Configure mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        # Enable email sending for this test
        test_config = self.test_config.copy()
        test_config['notification_settings']['send_email'] = True
        
        # Create email service
        email_service = EmailService(test_config)
        
        # Create test flight data
        current_flight = {
            'airline': {'name': 'Test Airline', 'logo': None},
            'flight_number': 'TS 123',
            'origin': 'TEST CITY',
            'scheduled_time': '12:00',
            'expected_time': '12:30',
            'gate': 'A1',
            'baggage': '01',
            'status': 'Kasni'
        }
        
        previous_flight = {
            'airline': {'name': 'Test Airline', 'logo': None},
            'flight_number': 'TS 123',
            'origin': 'TEST CITY',
            'scheduled_time': '12:00',
            'expected_time': '12:00',
            'gate': 'A1',
            'baggage': '01',
            'status': 'On time'
        }
        
        # Send notification
        result = email_service.send_notification(current_flight, previous_flight, 'delay')
        
        # Check that the email was "sent"
        self.assertTrue(result)
        mock_smtp_instance.send_message.assert_called_once()
        
        print("Email notification test passed")
    
    @patch('app.app.ZagrebAirportScraper')
    def test_5_flask_api_endpoints(self, mock_scraper):
        """Test that the Flask API endpoints work correctly"""
        # Configure mock
        mock_scraper_instance = MagicMock()
        mock_scraper.return_value = mock_scraper_instance
        mock_scraper_instance.scrape_arrivals.return_value = {
            'timestamp': '2025-05-03T12:00:00',
            'source': 'test',
            'flights': [
                {
                    'airline': {'name': 'Test Airline', 'logo': None},
                    'flight_number': 'TS 123',
                    'origin': 'TEST CITY',
                    'scheduled_time': '12:00',
                    'expected_time': '12:30',
                    'gate': 'A1',
                    'baggage': '01',
                    'status': 'Kasni'
                }
            ]
        }
        
        # Test GET /api/flights
        response = self.client.get('/api/flights')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('flights', data)
        
        # Test GET /api/config
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('app_settings', data)
        self.assertIn('notification_settings', data)
        self.assertIn('tracked_flights', data)
        
        print("Flask API endpoints test passed")
    
    def test_6_track_flight_api(self):
        """Test the flight tracking API endpoints"""
        # Test POST /api/flights/track
        response = self.client.post(
            '/api/flights/track',
            json={'flight_number': 'FR 5867'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify the flight was added
        response = self.client.get('/api/config')
        data = json.loads(response.data)
        self.assertIn('FR 5867', data['tracked_flights'])
        
        # Test POST /api/flights/untrack
        response = self.client.post(
            '/api/flights/untrack',
            json={'flight_number': 'FR 5867'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify the flight was removed
        response = self.client.get('/api/config')
        data = json.loads(response.data)
        self.assertNotIn('FR 5867', data['tracked_flights'])
        
        print("Flight tracking API test passed")
    
    def test_7_email_management_api(self):
        """Test the email management API endpoints"""
        # Test POST /api/email/add
        response = self.client.post(
            '/api/email/add',
            json={'email': 'new@example.com'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify the email was added
        response = self.client.get('/api/config')
        data = json.loads(response.data)
        self.assertIn('new@example.com', data['email_recipients'])
        
        # Test POST /api/email/remove
        response = self.client.post(
            '/api/email/remove',
            json={'email': 'new@example.com'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify the email was removed
        response = self.client.get('/api/config')
        data = json.loads(response.data)
        self.assertNotIn('new@example.com', data['email_recipients'])
        
        print("Email management API test passed")
    
    def test_8_notification_settings_api(self):
        """Test the notification settings API endpoint"""
        # Test POST /api/settings/notifications
        new_settings = {
            'notification_events': {
                'status_change': False,
                'delay': True,
                'gate_change': False,
                'arrival': True
            }
        }
        
        response = self.client.post(
            '/api/settings/notifications',
            json=new_settings
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify the settings were updated
        response = self.client.get('/api/config')
        data = json.loads(response.data)
        self.assertEqual(
            data['notification_settings']['notification_events'],
            new_settings['notification_events']
        )
        
        print("Notification settings API test passed")
    
    @patch('app.app.update_flight_data')
    def test_9_manual_refresh_api(self, mock_update):
        """Test the manual refresh API endpoint"""
        # Configure mock
        mock_update.return_value = None
        
        # Test POST /api/refresh
        response = self.client.post('/api/refresh')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        print("Manual refresh API test passed")

if __name__ == '__main__':
    unittest.main()