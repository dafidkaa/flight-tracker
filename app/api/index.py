import os
import sys
import json
import logging
from flask import Flask, render_template, jsonify, request

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
from scraper import ZagrebAirportScraper
from email_service import EmailService

# Set up logging for Vercel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('flight_tracker')

# Initialize Flask app
app = Flask(__name__, 
            static_folder='../static',
            template_folder='../templates')

# Global variables
CONFIG_PATH = '/tmp/config.json'  # Use /tmp for Vercel
SAMPLE_DATA_PATH = '/tmp/sample_data.json'  # Use /tmp for Vercel

# Flight data cache
flight_data = {}
previous_flight_data = {}

# Email service instance
email_service = None

# Load configuration
def load_config():
    """Load configuration from config.json file or create default if not exists"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Return default configuration if file not found
            default_config = {
                "app_settings": {
                    "language": "hr",
                    "check_interval_minutes": 5,
                    "max_flights": 20,
                    "timezone": "Europe/Zagreb",
                    "scraping_enabled": True
                },
                "notification_settings": {
                    "send_email": True,
                    "email_settings": {
                        "smtp_server": "",
                        "smtp_port": 587,
                        "smtp_username": "",
                        "smtp_password": "",
                        "sender_email": "",
                        "use_tls": True
                    },
                    "notification_events": {
                        "status_change": True,
                        "delay": True,
                        "gate_change": True,
                        "arrival": True
                    }
                },
                "tracked_flights": [],
                "email_recipients": [],
                "flight_email_mappings": {}
            }
            # Save the default config
            save_config(default_config)
            return default_config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        # Return default configuration if error
        return {
            "app_settings": {
                "language": "hr",
                "check_interval_minutes": 5,
                "max_flights": 20,
                "timezone": "Europe/Zagreb",
                "scraping_enabled": True
            },
            "notification_settings": {
                "send_email": True,
                "email_settings": {
                    "smtp_server": "",
                    "smtp_port": 587,
                    "smtp_username": "",
                    "smtp_password": "",
                    "sender_email": "",
                    "use_tls": True
                },
                "notification_events": {
                    "status_change": True,
                    "delay": True,
                    "gate_change": True,
                    "arrival": True
                }
            },
            "tracked_flights": [],
            "email_recipients": [],
            "flight_email_mappings": {}
        }

# Save configuration
def save_config(config):
    """Save configuration to config.json file"""
    try:
        logger.info("Saving configuration to file")
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # Update email service with new configuration
        global email_service
        if email_service:
            logger.info("Reinitializing email service with updated configuration")
            email_service = EmailService(config)
            logger.info(f"Email service reinitialized with {len(config['email_recipients'])} recipients")
        else:
            logger.info("Initializing email service for the first time")
            email_service = EmailService(config)
            logger.info(f"Email service initialized with {len(config['email_recipients'])} recipients")

        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        return False

# Load flight data
def load_flight_data():
    """Load flight data from cache or sample data"""
    global flight_data

    if flight_data:
        return flight_data

    try:
        if os.path.exists(SAMPLE_DATA_PATH):
            with open(SAMPLE_DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # If no sample data exists, create it by scraping
            update_flight_data()
            return flight_data
    except Exception as e:
        logger.error(f"Error loading flight data: {str(e)}")
        return {"timestamp": "", "source": "", "flights": []}

# Update flight data
def update_flight_data():
    """Update flight data by scraping Zagreb Airport website"""
    global flight_data, previous_flight_data

    try:
        # Store previous flight data for comparison
        if flight_data and 'flights' in flight_data:
            previous_flight_data = flight_data.copy()

        # Create scraper instance
        scraper = ZagrebAirportScraper()

        # Scrape arrivals data
        new_data = scraper.scrape_arrivals()

        if new_data:
            flight_data = new_data

            # Save to sample data file for development/testing
            os.makedirs(os.path.dirname(SAMPLE_DATA_PATH), exist_ok=True)
            scraper.save_to_json(new_data, SAMPLE_DATA_PATH)

            logger.info(f"Flight data updated successfully. {len(new_data['flights'])} flights found.")
        else:
            logger.error("Failed to update flight data")
    except Exception as e:
        logger.error(f"Error updating flight data: {str(e)}")

# Initialize email service
def initialize_email_service():
    """Initialize email service with configuration"""
    global email_service
    config = load_config()

    # Ensure flight_email_mappings exists in config
    if 'flight_email_mappings' not in config:
        config['flight_email_mappings'] = {}
        save_config(config)
        logger.info("Created empty flight_email_mappings in configuration")

    # Log flight-email mappings for debugging
    if config['flight_email_mappings']:
        logger.info(f"Found {len(config['flight_email_mappings'])} flight-email mappings in configuration")
        for flight_number, emails in config['flight_email_mappings'].items():
            logger.info(f"Flight {flight_number} is mapped to emails: {emails}")
    else:
        logger.info("No flight-email mappings found in configuration")

    # Initialize email service with the config
    email_service = EmailService(config)
    logger.info("Email service initialized with flight-email mappings")

# Flask routes
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/flights')
def get_flights():
    """API endpoint to get flight data"""
    return jsonify(load_flight_data())

@app.route('/api/flights/tracked')
def get_tracked_flights():
    """API endpoint to get tracked flights"""
    config = load_config()
    tracked_flights = config['tracked_flights']

    # Get current flight data
    current_flights = load_flight_data()

    # Filter flights to only include tracked flights
    tracked_flight_data = []
    for flight in current_flights.get('flights', []):
        if flight['flight_number'] in tracked_flights:
            tracked_flight_data.append(flight)

    return jsonify({
        "timestamp": current_flights.get('timestamp', ''),
        "source": current_flights.get('source', ''),
        "flights": tracked_flight_data
    })

@app.route('/api/config')
def get_config_api():
    """API endpoint to get configuration"""
    config = load_config()

    # Remove sensitive information
    if 'notification_settings' in config and 'email_settings' in config['notification_settings']:
        email_settings = config['notification_settings']['email_settings']
        if 'smtp_password' in email_settings:
            email_settings['smtp_password'] = ''

    return jsonify(config)

@app.route('/api/flights/track', methods=['POST'])
def track_flight():
    """API endpoint to track a flight"""
    data = request.json

    if not data or 'flight_number' not in data:
        return jsonify({'error': 'Missing flight number'}), 400

    flight_number = data['flight_number']

    config = load_config()

    # Check if maximum number of tracked flights reached (default max is 20)
    max_flights = config.get('app_settings', {}).get('max_flights', 20)
    if len(config['tracked_flights']) >= max_flights:
        return jsonify({'error': 'Maximum number of tracked flights reached (20)'}), 400

    # Check if flight is already tracked
    if flight_number in config['tracked_flights']:
        return jsonify({'error': 'Flight is already tracked'}), 400

    # Add flight to tracked flights
    config['tracked_flights'].append(flight_number)

    # Save configuration
    if save_config(config):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to save configuration'}), 500

@app.route('/api/flights/untrack', methods=['POST'])
def untrack_flight():
    """API endpoint to untrack a flight"""
    data = request.json

    if not data or 'flight_number' not in data:
        return jsonify({'error': 'Missing flight number'}), 400

    flight_number = data['flight_number']

    config = load_config()

    # Check if flight is tracked
    if flight_number not in config['tracked_flights']:
        return jsonify({'error': 'Flight is not tracked'}), 400

    # Remove flight from tracked flights
    config['tracked_flights'].remove(flight_number)

    # Save configuration
    if save_config(config):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to save configuration'}), 500

@app.route('/api/email/add', methods=['POST'])
def add_email():
    """API endpoint to add email recipient"""
    try:
        data = request.json

        if not data or 'email' not in data:
            return jsonify({'error': 'Missing email address'}), 400

        email = data['email']
        logger.info(f"Attempting to add email: {email}")

        config = load_config()

        # Check if email is already added
        if email in config['email_recipients']:
            logger.info(f"Email {email} is already in recipients list")
            return jsonify({'error': 'Email is already added'}), 400

        # Add email to recipients
        config['email_recipients'].append(email)
        logger.info(f"Added email {email} to recipients list")

        # Save configuration
        if save_config(config):
            logger.info(f"Successfully saved configuration with new email {email}")
            return jsonify({'success': True})
        else:
            logger.error(f"Failed to save configuration when adding email {email}")
            return jsonify({'error': 'Failed to save configuration'}), 500
    except Exception as e:
        logger.error(f"Error in add_email endpoint: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/email/remove', methods=['POST'])
def remove_email():
    """API endpoint to remove email recipient"""
    try:
        data = request.json

        if not data or 'email' not in data:
            return jsonify({'error': 'Missing email address'}), 400

        email = data['email']
        logger.info(f"Attempting to remove email: {email}")

        config = load_config()

        # Check if email is in recipients
        if email not in config['email_recipients']:
            logger.info(f"Email {email} is not in recipients list")
            return jsonify({'error': 'Email is not in recipients'}), 400

        # Remove email from recipients
        config['email_recipients'].remove(email)
        logger.info(f"Removed email {email} from recipients list")

        # Save configuration
        if save_config(config):
            logger.info(f"Successfully saved configuration after removing email {email}")
            return jsonify({'success': True})
        else:
            logger.error(f"Failed to save configuration when removing email {email}")
            return jsonify({'error': 'Failed to save configuration'}), 500
    except Exception as e:
        logger.error(f"Error in remove_email endpoint: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/flights/assign_email', methods=['POST'])
def assign_email_to_flight():
    """API endpoint to assign an email to a specific flight"""
    global email_service
    
    try:
        data = request.json

        if not data or 'flight_number' not in data or 'email' not in data:
            return jsonify({'error': 'Missing flight number or email'}), 400

        flight_number = data['flight_number']
        email = data['email']

        config = load_config()

        # Check if flight is tracked
        if flight_number not in config['tracked_flights']:
            return jsonify({'error': 'Flight is not tracked'}), 400

        # Check if email is in recipients
        if email not in config['email_recipients']:
            return jsonify({'error': 'Email is not in recipients list'}), 400

        # Initialize flight_email_mappings if it doesn't exist
        if 'flight_email_mappings' not in config:
            config['flight_email_mappings'] = {}

        # Assign email to flight
        if flight_number not in config['flight_email_mappings']:
            config['flight_email_mappings'][flight_number] = []

        # Check if email is already assigned to this flight
        if email in config['flight_email_mappings'][flight_number]:
            return jsonify({'error': 'Email is already assigned to this flight'}), 400

        # Add email to flight's email list
        config['flight_email_mappings'][flight_number].append(email)

        logger.info(f"Assigning email {email} to flight {flight_number}")

        # Save configuration
        if save_config(config):
            # Update the email service with the new mappings
            if email_service:
                email_service.flight_email_mappings = config['flight_email_mappings']
                logger.info(f"Updated email service with new flight-email mappings")
            
            return jsonify({
                'success': True,
                'message': f'Email {email} assigned to flight {flight_number}',
                'flight_email_mappings': config['flight_email_mappings']
            })
        else:
            return jsonify({'error': 'Failed to save configuration'}), 500
    except Exception as e:
        logger.error(f"Error assigning email to flight: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/flights/unassign_email', methods=['POST'])
def unassign_email_from_flight():
    """API endpoint to unassign an email from a specific flight"""
    global email_service
    
    try:
        data = request.json

        if not data or 'flight_number' not in data or 'email' not in data:
            return jsonify({'error': 'Missing flight number or email'}), 400

        flight_number = data['flight_number']
        email = data['email']

        config = load_config()

        # Check if flight_email_mappings exists
        if 'flight_email_mappings' not in config or flight_number not in config['flight_email_mappings']:
            return jsonify({'error': 'No email mappings found for this flight'}), 400

        # Check if email is assigned to this flight
        if email not in config['flight_email_mappings'][flight_number]:
            return jsonify({'error': 'Email is not assigned to this flight'}), 400

        # Remove email from flight's email list
        config['flight_email_mappings'][flight_number].remove(email)

        # If no emails left for this flight, remove the flight entry
        if not config['flight_email_mappings'][flight_number]:
            del config['flight_email_mappings'][flight_number]

        logger.info(f"Unassigning email {email} from flight {flight_number}")

        # Save configuration
        if save_config(config):
            # Update the email service with the new mappings
            if email_service:
                email_service.flight_email_mappings = config['flight_email_mappings']
                logger.info(f"Updated email service with new flight-email mappings after unassigning")
                
            return jsonify({
                'success': True,
                'message': f'Email {email} unassigned from flight {flight_number}',
                'flight_email_mappings': config['flight_email_mappings']
            })
        else:
            return jsonify({'error': 'Failed to save configuration'}), 500
    except Exception as e:
        logger.error(f"Error unassigning email from flight: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/flights/email_mappings', methods=['GET'])
def get_flight_email_mappings():
    """API endpoint to get all flight-email mappings"""
    try:
        config = load_config()

        # Initialize flight_email_mappings if it doesn't exist
        if 'flight_email_mappings' not in config:
            config['flight_email_mappings'] = {}
            save_config(config)

        return jsonify({
            'success': True,
            'flight_email_mappings': config['flight_email_mappings']
        })
    except Exception as e:
        logger.error(f"Error getting flight-email mappings: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """API endpoint to manually refresh flight data"""
    try:
        # Update flight data
        update_flight_data()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error refreshing data: {str(e)}")
        return jsonify({'error': 'Failed to refresh data'}), 500

@app.route('/api/settings/toggle_scraping', methods=['POST'])
def toggle_scraping():
    """API endpoint to toggle scraping on/off with confirmation"""
    try:
        data = request.json or {}  # Default to empty dict if no JSON data

        # Get the current scraping status
        config = load_config()
        current_status = config['app_settings'].get('scraping_enabled', True)
        
        # If turning off scraping, require confirmation
        if current_status and ('confirmation' not in data or data['confirmation'] != 'STOP'):
            return jsonify({
                'success': False, 
                'requires_confirmation': True,
                'current_status': current_status,
                'message': 'To turn off scraping, please type STOP in the confirmation field'
            })

        # Toggle the scraping status
        new_status = not current_status
        config['app_settings']['scraping_enabled'] = new_status
        
        logger.info(f"Toggling scraping status from {current_status} to {new_status}")

        # Save configuration
        if save_config(config):
            status_text = "enabled" if new_status else "disabled"
            return jsonify({
                'success': True, 
                'scraping_enabled': new_status,
                'message': f'Scraping has been {status_text}'
            })
        else:
            return jsonify({'error': 'Failed to save configuration'}), 500
    except Exception as e:
        logger.error(f"Error toggling scraping status: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/test_email', methods=['POST'])
def test_email():
    """API endpoint to test email sending"""
    global email_service
    
    try:
        # Check if email service is initialized
        if not email_service:
            initialize_email_service()
            
        # Get request data
        data = request.get_json() or {}
        specific_email = data.get('email')
        
        if specific_email:
            # Send test email to specific recipient
            result = email_service.send_test_email(specific_email)
            if result:
                return jsonify({'success': True, 'message': f'Test email sent to {specific_email}'})
            else:
                return jsonify({'error': 'Failed to send test email'}), 500
        else:
            # Send test email to all recipients
            config = load_config()
            if not config['email_recipients']:
                return jsonify({'error': 'No email recipients configured'}), 400
                
            result = email_service.send_test_email()
            if result:
                return jsonify({'success': True, 'message': 'Test email sent to all recipients'})
            else:
                return jsonify({'error': 'Failed to send test email'}), 500
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        return jsonify({'error': f'Failed to send test email: {str(e)}'}), 500

# Initialize email service
initialize_email_service()

# Initial data update
update_flight_data()

# For Vercel serverless function
def handler(event, context):
    return app(event, context)

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
