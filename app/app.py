import os
import json
import time
import logging
import threading
import datetime
from flask import Flask, render_template, jsonify, request
from typing import Dict, List, Any, Optional

# Import our modules
from scraper import ZagrebAirportScraper
from email_service import EmailService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('flight_tracker')

# Initialize Flask app
app = Flask(__name__)

# Global variables
CONFIG_PATH = 'config.json'
SAMPLE_DATA_PATH = 'app/data/sample_data.json'

# Flight data cache
flight_data = {}
previous_flight_data = {}

# Scraping control flag
scraping_enabled = True

# Email service instance
email_service = None

# Load configuration
def load_config() -> Dict[str, Any]:
    """Load configuration from config.json file"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        # Return default configuration if file not found or invalid
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
def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to config.json file"""
    try:
        logger.info("Saving configuration to file")
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
def load_flight_data() -> Dict[str, Any]:
    """Load flight data from cache or sample data"""
    global flight_data

    if flight_data:
        return flight_data

    try:
        with open(SAMPLE_DATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading flight data: {str(e)}")
        return {"timestamp": "", "source": "", "flights": []}

# Update flight data
def update_flight_data() -> None:
    """Update flight data by scraping Zagreb Airport website"""
    global flight_data, previous_flight_data, scraping_enabled

    # Double-check if scraping is enabled before proceeding
    config = load_config()
    scraping_enabled = config['app_settings'].get('scraping_enabled', True)

    if not scraping_enabled:
        logger.info("Scraping is disabled in update_flight_data. Skipping flight data update.")
        return

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
            scraper.save_to_json(new_data, SAMPLE_DATA_PATH)

            # Check for changes and send notifications
            if previous_flight_data and 'flights' in previous_flight_data:
                check_for_changes_and_notify()

            logger.info(f"Flight data updated successfully. {len(new_data['flights'])} flights found.")
        else:
            logger.error("Failed to update flight data")
    except Exception as e:
        logger.error(f"Error updating flight data: {str(e)}")

# Global variable to track when the next update should occur
next_update_time = None

# Background task to update flight data periodically
def background_update_task() -> None:
    """Background task to update flight data periodically"""
    global next_update_time, scraping_enabled

    while True:
        # Reload config each time to get the latest check interval and scraping status
        config = load_config()
        check_interval = config['app_settings']['check_interval_minutes'] * 60

        # Update global scraping_enabled flag from config
        scraping_enabled = config['app_settings'].get('scraping_enabled', True)

        # Check if it's time to update and if scraping is enabled
        current_time = time.time()

        if scraping_enabled and (next_update_time is None or current_time >= next_update_time):
            logger.info(f"Updating flight data (check interval: {config['app_settings']['check_interval_minutes']} minutes)")
            update_flight_data()

            # Set the next update time
            next_update_time = time.time() + check_interval
            logger.info(f"Next update scheduled at: {time.strftime('%H:%M:%S', time.localtime(next_update_time))}")
        elif not scraping_enabled and (next_update_time is None or current_time >= next_update_time):
            # If scraping is disabled but it's time for an update, just log it and update the next time
            logger.info("Scraping is disabled. Skipping flight data update.")
            next_update_time = time.time() + check_interval
            logger.info(f"Next check scheduled at: {time.strftime('%H:%M:%S', time.localtime(next_update_time))}")

        # Sleep for a short interval and check again
        time.sleep(5)

# Check for changes in flight data and send notifications
def check_for_changes_and_notify() -> None:
    """Check for changes in flight data and send notifications"""
    config = load_config()
    tracked_flights = config['tracked_flights']

    if not tracked_flights:
        return

    notification_events = config['notification_settings']['notification_events']

    # Create a dictionary of previous flights for easy lookup
    prev_flights_dict = {flight['flight_number']: flight for flight in previous_flight_data['flights']}

    # Check each current flight for changes
    for flight in flight_data['flights']:
        flight_number = flight['flight_number']

        # Skip if not a tracked flight
        if flight_number not in tracked_flights:
            continue

        # Skip if flight wasn't in previous data
        if flight_number not in prev_flights_dict:
            continue

        prev_flight = prev_flights_dict[flight_number]

        # Check for status change
        if notification_events['status_change'] and flight['status'] != prev_flight['status']:
            send_notification(flight, prev_flight, 'status_change')

        # Check for delay (only using Croatian terms)
        if notification_events['delay'] and ('kasni' in flight['status'].lower() or 'odgođen' in flight['status'].lower()) and \
           not ('kasni' in prev_flight['status'].lower() or 'odgođen' in prev_flight['status'].lower()):
            send_notification(flight, prev_flight, 'delay')

        # Check for gate change
        if notification_events['gate_change'] and flight['gate'] != prev_flight['gate']:
            send_notification(flight, prev_flight, 'gate_change')

        # Check for arrival (only using Croatian terms)
        if notification_events['arrival'] and \
           ('sletio' in flight['status'].lower() or 'stigao' in flight['status'].lower() or 'pristigao' in flight['status'].lower()) and \
           not ('sletio' in prev_flight['status'].lower() or 'stigao' in prev_flight['status'].lower() or 'pristigao' in prev_flight['status'].lower()):
            send_notification(flight, prev_flight, 'arrival')

# Send notification email
def send_notification(flight: Dict[str, Any], prev_flight: Dict[str, Any], event_type: str) -> None:
    """Send notification email about flight changes"""
    global email_service

    if email_service:
        email_service.send_notification(flight, prev_flight, event_type)
    else:
        logger.error("Email service not initialized")

# Initialize email service
def initialize_email_service() -> None:
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

@app.route('/api/settings/notifications', methods=['POST'])
def update_notification_settings():
    """API endpoint to update notification settings"""
    data = request.json

    if not data or 'notification_events' not in data:
        return jsonify({'error': 'Missing notification events'}), 400

    notification_events = data['notification_events']

    config = load_config()

    # Update notification events
    config['notification_settings']['notification_events'] = notification_events

    # Save configuration
    if save_config(config):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to save configuration'}), 500

@app.route('/api/settings/email', methods=['POST'])
def update_email_settings():
    """API endpoint to update email settings"""
    data = request.json

    if not data or 'email_settings' not in data:
        return jsonify({'error': 'Missing email settings'}), 400

    email_settings = data['email_settings']

    config = load_config()

    # Update email settings
    config['notification_settings']['email_settings'] = email_settings

    # Save configuration
    if save_config(config):
        # Reinitialize email service with new settings
        initialize_email_service()
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to save configuration'}), 500

@app.route('/api/settings/app', methods=['POST'])
def update_app_settings():
    """API endpoint to update app settings"""
    data = request.json

    if not data or 'app_settings' not in data:
        return jsonify({'error': 'Missing app settings'}), 400

    app_settings = data['app_settings']

    config = load_config()

    # Ensure max_flights doesn't exceed 20
    if 'max_flights' in app_settings and app_settings['max_flights'] > 20:
        app_settings['max_flights'] = 20

    # Update app settings
    config['app_settings'] = app_settings

    # Save configuration
    if save_config(config):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to save configuration'}), 500

@app.route('/api/settings/check_interval', methods=['POST'])
def update_check_interval():
    """API endpoint to update the check interval for flight data updates"""
    global next_update_time

    try:
        data = request.json

        if not data or 'check_interval_minutes' not in data:
            return jsonify({'error': 'Missing check interval minutes'}), 400

        check_interval_minutes = data['check_interval_minutes']

        # Validate the check interval (minimum 1 minute, maximum 60 minutes)
        if not isinstance(check_interval_minutes, (int, float)) or check_interval_minutes < 1 or check_interval_minutes > 60:
            return jsonify({'error': 'Check interval must be between 1 and 60 minutes'}), 400

        config = load_config()

        # Update check interval
        config['app_settings']['check_interval_minutes'] = check_interval_minutes

        logger.info(f"Updating check interval to {check_interval_minutes} minutes")

        # Save configuration
        if save_config(config):
            # Reset the timer for the next automatic update
            check_interval = check_interval_minutes * 60
            next_update_time = time.time() + check_interval

            logger.info(f"Check interval updated. Next update scheduled at: {time.strftime('%H:%M:%S', time.localtime(next_update_time))}")

            return jsonify({'success': True, 'message': f'Check interval updated to {check_interval_minutes} minutes'})
        else:
            return jsonify({'error': 'Failed to save configuration'}), 500
    except Exception as e:
        logger.error(f"Error updating check interval: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/settings/toggle_scraping', methods=['POST'])
def toggle_scraping():
    """API endpoint to toggle scraping on/off with confirmation"""
    global scraping_enabled

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

        # Update global variable
        scraping_enabled = new_status

        logger.info(f"Toggling scraping status from {current_status} to {new_status}")

        # Save configuration
        if save_config(config):
            # If turning off scraping, send notification email
            if not new_status:
                try:
                    # Send email notification to dafidkaa@gmail.com
                    send_scraping_disabled_notification()
                    logger.info("Sent email notification about scraping being disabled")
                except Exception as email_error:
                    logger.error(f"Failed to send scraping disabled notification: {str(email_error)}")
                    # Continue even if email fails

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

def send_scraping_disabled_notification():
    """Send email notification when scraping is disabled"""
    global email_service

    if not email_service:
        initialize_email_service()

    # Create a simple message for the notification in Croatian
    subject = "Praćenje letova - Prikupljanje podataka isključeno"
    html_content = """
    <html>
    <body>
        <h2>Prikupljanje podataka o letovima isključeno</h2>
        <p>Ovo je automatska obavijest da je prikupljanje podataka o letovima isključeno.</p>
        <p>Novi podaci o letovima neće biti prikupljani dok se prikupljanje ponovno ne uključi.</p>
        <p>Vrijeme promjene: {time}</p>
        <hr>
        <p>Za ponovno uključivanje prikupljanja podataka, posjetite postavke aplikacije.</p>
    </body>
    </html>
    """.format(time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Use the email service to send the notification
    try:
        # Create a simple flight object for the notification
        dummy_flight = {
            'flight_number': 'SYSTEM',
            'airline': {'name': 'System Notification'},
            'origin': 'System',
            'scheduled_time': datetime.datetime.now().strftime("%H:%M"),
            'expected_time': '',
            'gate': '',
            'baggage': '',
            'status': 'Prikupljanje podataka isključeno'
        }

        # Create a simple previous flight object
        dummy_prev_flight = dummy_flight.copy()
        dummy_prev_flight['status'] = 'Prikupljanje podataka uključeno'

        # Send the notification using the email service
        if email_service:
            # Use a custom method to send this specific notification
            recipients = ["dafidkaa@gmail.com"]  # Admin email

            # Prepare email parameters
            params = {
                "from": "Zagreb Airport <notifications@fuji.lemonmedia.hr>",
                "to": recipients[0] if len(recipients) == 1 else recipients,
                "subject": subject,
                "html": html_content,
            }

            # Import resend here to avoid the global import issue
            import resend

            # Set the API key
            resend.api_key = "re_Xo8QezxL_M7ZCgLcpztLngNJ5J2XhMHx2"

            # Send the email
            response = resend.Emails.send(params)

            if response and isinstance(response, dict) and 'id' in response:
                logger.info(f"Scraping disabled notification email sent successfully. Email ID: {response['id']}")
                return True
            else:
                logger.error(f"Failed to send scraping disabled notification email: {response}")
                return False
        else:
            logger.error("Email service not initialized, cannot send scraping disabled notification")
            return False
    except Exception as e:
        logger.error(f"Error sending scraping disabled notification email: {str(e)}")
        return False

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
    global next_update_time

    try:
        # Check if scraping is enabled
        config = load_config()
        if not config['app_settings'].get('scraping_enabled', True):
            return jsonify({
                'success': False,
                'message': 'Cannot refresh data because scraping is disabled. Please enable scraping first.'
            }), 400

        # Update flight data
        update_flight_data()

        # Reset the timer for the next automatic update
        check_interval = config['app_settings']['check_interval_minutes'] * 60
        next_update_time = time.time() + check_interval

        logger.info(f"Manual refresh triggered. Next update scheduled at: {time.strftime('%H:%M:%S', time.localtime(next_update_time))}")

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error refreshing data: {str(e)}")
        return jsonify({'error': 'Failed to refresh data'}), 500

@app.route('/api/settings/scraping_status', methods=['GET'])
def get_scraping_status():
    """API endpoint to get the current scraping status"""
    try:
        config = load_config()
        scraping_enabled = config['app_settings'].get('scraping_enabled', True)

        return jsonify({
            'success': True,
            'scraping_enabled': scraping_enabled
        })
    except Exception as e:
        logger.error(f"Error getting scraping status: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/email/test', methods=['POST'])
def test_email():
    """API endpoint to test email sending using Resend API"""
    global email_service

    try:
        # Check if email service is initialized
        if not email_service:
            initialize_email_service()

        # Load config
        config = load_config()

        # Get request data
        data = request.get_json() or {}
        specific_email = data.get('email')

        # If a specific email is provided, use it directly
        if specific_email:
            logger.info(f"Sending test email to specific recipient: {specific_email}")
            recipients = [specific_email]
        else:
            # Check if there are any recipients
            if not config['email_recipients']:
                # Add a test recipient if none exists
                config['email_recipients'] = ['dafidkaa@gmail.com']
                save_config(config)
                logger.info("Added test recipient: dafidkaa@gmail.com")

                # Reinitialize email service with updated config
                initialize_email_service()

            recipients = config['email_recipients']

        # Create a sample flight data for testing
        test_flight = {
            'flight_number': 'TEST123',
            'airline': {'name': 'Test Airline', 'logo': ''},
            'origin': 'Test Origin',
            'scheduled_time': '12:00',
            'expected_time': '12:00',
            'gate': 'A1',
            'baggage': 'B1',
            'status': 'Na vrijeme'  # Croatian status
        }

        # Prepare email parameters for Resend API
        template_content = None
        template_path = os.path.join('templates', 'email_notification.html')
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except Exception as e:
            logger.error(f"Error loading email template: {str(e)}")
            return jsonify({'error': f'Failed to load email template: {str(e)}'}), 500

        if not template_content:
            return jsonify({'error': 'Failed to load email template'}), 500

        # Create template
        from jinja2 import Template
        template = Template(template_content)

        # Render email content
        email_content = template.render(
            flight_number=test_flight['flight_number'],
            airline=test_flight['airline']['name'],
            origin=test_flight['origin'],
            scheduled_time=test_flight['scheduled_time'],
            expected_time=test_flight['expected_time'],
            gate=test_flight['gate'],
            baggage=test_flight['baggage'],
            status=test_flight['status'],
            previous_status=test_flight['status'],
            status_class='status-ontime',
            notification_message='Ovo je testna poruka za provjeru slanja e-maila:',
            current_year=datetime.datetime.now().year
        )

        # Set subject with detailed flight information
        subject = f"Let {test_flight['flight_number']} ({test_flight['airline']['name']}) iz {test_flight['origin']} - {test_flight['expected_time']} - TEST"

        # Prepare email parameters for Resend API
        # Log the recipients for debugging
        logger.info(f"Test email recipients: {recipients}")

        # For Resend API, if there's only one recipient, use a string instead of a list
        to_field = recipients[0] if len(recipients) == 1 else recipients

        params = {
            "from": "Zagreb Airport <notifications@fuji.lemonmedia.hr>",
            "to": to_field,
            "subject": subject,
            "html": email_content,
        }

        logger.info(f"Sending test email to {recipients}")

        # Send email using Resend API
        import resend
        from resend.exceptions import ResendError

        try:
            # Log the API key (first few characters only for security)
            resend.api_key = "re_Xo8QezxL_M7ZCgLcpztLngNJ5J2XhMHx2"
            masked_key = resend.api_key[:5] + "..." if resend.api_key else "None"
            logger.info(f"Using Resend API key: {masked_key}")

            # Log the params without sensitive information
            safe_params = params.copy()
            logger.info(f"Calling Resend API with params: {safe_params}")

            # Send the email
            response = resend.Emails.send(params)
            logger.info(f"Resend API response type: {type(response)}")

            if response and isinstance(response, dict) and 'id' in response:
                logger.info(f"Test email sent successfully. Email ID: {response['id']}")
                return jsonify({'success': True, 'message': 'Test email sent successfully using Resend API'})
            else:
                logger.error(f"Failed to send email with Resend API: {response}")
                return jsonify({'error': 'Failed to send test email. Check logs for details.'}), 500
        except Exception as e:
            logger.error(f"Error in Resend API call: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            return jsonify({'error': f'Failed to send test email: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        return jsonify({'error': f'Failed to send test email: {str(e)}'}), 500

# Start background task
def start_background_task():
    """Start background task to update flight data periodically"""
    thread = threading.Thread(target=background_update_task)
    thread.daemon = True
    thread.start()

# Main entry point
if __name__ == '__main__':
    # Initialize email service
    initialize_email_service()

    # Initial data update
    update_flight_data()

    # Start background task
    start_background_task()

    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)