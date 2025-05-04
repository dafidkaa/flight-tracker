import os
import logging
import datetime
import resend
from jinja2 import Template
from typing import Dict, List, Any, Optional

# Set up logging - only use stream handler for serverless environments
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('email_service')

class EmailService:
    """
    Service for sending email notifications about flight status changes
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email service with configuration

        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.email_settings = config['notification_settings']['email_settings']
        self.email_recipients = config['email_recipients']

        # Load flight-email mappings
        self.flight_email_mappings = config.get('flight_email_mappings', {})

        # Log flight-email mappings for debugging
        if self.flight_email_mappings:
            logger.info(f"Loaded {len(self.flight_email_mappings)} flight-email mappings")
            for flight_number, emails in self.flight_email_mappings.items():
                logger.info(f"Flight {flight_number} is mapped to emails: {emails}")
        else:
            logger.info("No flight-email mappings found in configuration")

        # Fix the template path to use OS-specific path separator and absolute path
        # For Vercel, we need to use an absolute path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.email_template_path = os.path.join(current_dir, 'templates', 'email_notification.html')

        # Fallback path if the first one doesn't work
        if not os.path.exists(self.email_template_path):
            parent_dir = os.path.dirname(current_dir)
            self.email_template_path = os.path.join(parent_dir, 'templates', 'email_notification.html')

        logger.info(f"Email template path: {self.email_template_path}")

        # Initialize Resend API key
        resend.api_key = "re_Xo8QezxL_M7ZCgLcpztLngNJ5J2XhMHx2"

        # Log initialization
        logger.info(f"Email service initialized with {len(self.email_recipients)} recipients")

    def _load_email_template(self) -> Optional[str]:
        """
        Load email template from file

        Returns:
            Email template content or None if loading failed
        """
        try:
            # Try to load from the configured path
            if os.path.exists(self.email_template_path):
                with open(self.email_template_path, 'r', encoding='utf-8') as f:
                    logger.info(f"Successfully loaded email template from {self.email_template_path}")
                    return f.read()

            # If that fails, try some alternative paths
            alternative_paths = [
                os.path.join('templates', 'email_notification.html'),
                os.path.join('app', 'templates', 'email_notification.html'),
                os.path.join('app', 'api', 'templates', 'email_notification.html')
            ]

            for path in alternative_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        logger.info(f"Successfully loaded email template from alternative path: {path}")
                        return f.read()

            # If all else fails, return a simple default template
            logger.warning("Could not load email template from any path, using default template")
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Flight Status Update</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 5px; }
                    .header { text-align: center; padding-bottom: 20px; border-bottom: 1px solid #ddd; }
                    .flight-info { margin: 20px 0; }
                    .flight-info table { width: 100%; border-collapse: collapse; }
                    .flight-info th, .flight-info td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
                    .status-ontime { color: green; font-weight: bold; }
                    .status-delayed { color: orange; font-weight: bold; }
                    .status-cancelled { color: red; font-weight: bold; }
                    .status-landed { color: blue; font-weight: bold; }
                    .footer { margin-top: 20px; text-align: center; font-size: 12px; color: #777; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Flight Status Update</h1>
                        <p>{{ notification_message }}</p>
                    </div>
                    <div class="flight-info">
                        <table>
                            <tr>
                                <th>Flight Number:</th>
                                <td>{{ flight_number }}</td>
                            </tr>
                            <tr>
                                <th>Airline:</th>
                                <td>{{ airline }}</td>
                            </tr>
                            <tr>
                                <th>Origin:</th>
                                <td>{{ origin }}</td>
                            </tr>
                            <tr>
                                <th>Scheduled Time:</th>
                                <td>{{ scheduled_time }}</td>
                            </tr>
                            <tr>
                                <th>Expected Time:</th>
                                <td>{{ expected_time }}</td>
                            </tr>
                            <tr>
                                <th>Gate:</th>
                                <td>{{ gate }}</td>
                            </tr>
                            <tr>
                                <th>Baggage:</th>
                                <td>{{ baggage }}</td>
                            </tr>
                            <tr>
                                <th>Previous Status:</th>
                                <td>{{ previous_status }}</td>
                            </tr>
                            <tr>
                                <th>Current Status:</th>
                                <td class="{{ status_class }}">{{ status }}</td>
                            </tr>
                        </table>
                    </div>
                    <div class="footer">
                        <p>&copy; {{ current_year }} Flight Tracker. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        except Exception as e:
            logger.error(f"Error loading email template: {str(e)}")
            return None

    def _determine_status_class(self, status: str) -> str:
        """
        Determine CSS class for styling based on flight status

        Args:
            status: Flight status string

        Returns:
            CSS class name for styling
        """
        status_lower = status.lower()

        if 'kasni' in status_lower or 'delay' in status_lower or 'odgođen' in status_lower:
            return 'status-delayed'
        elif 'sletio' in status_lower or 'arrived' in status_lower or 'stigao' in status_lower or 'pristigao' in status_lower:
            return 'status-landed'
        elif 'otkazan' in status_lower or 'cancel' in status_lower:
            return 'status-cancelled'
        else:
            return 'status-ontime'

    def _translate_status_to_croatian(self, status: str) -> str:
        """
        Translate flight status from English to Croatian or ensure Croatian status is used

        Args:
            status: Flight status string (could be in English or Croatian)

        Returns:
            Flight status string in Croatian
        """
        status_lower = status.lower()

        # Check if status is already in Croatian
        croatian_statuses = {
            'kasni': 'Kasni',
            'na vrijeme': 'Na vrijeme',
            'sletio': 'Sletio',
            'otkazan': 'Otkazan',
            'ukrcavanje': 'Ukrcavanje',
            'poletio': 'Poletio',
            'planiran': 'Planiran',
            'preusmjeren': 'Preusmjeren',
            'odgođen': 'Odgođen',
            'stigao': 'Stigao',
            'pristigao': 'Pristigao',
            'po rasporedu': 'Po rasporedu',
            'očekivan': 'Očekivan',
            'u letu': 'U letu',
            'taksiranje': 'Taksiranje',
            'izlaz zatvoren': 'Izlaz zatvoren',
            'zadnji poziv': 'Zadnji poziv',
            'ukrcavanje u tijeku': 'Ukrcavanje u tijeku',
            'slijeće': 'Slijeće'
        }

        # Check if status is already in Croatian
        for croatian_status_lower, croatian_status in croatian_statuses.items():
            if croatian_status_lower in status_lower:
                return croatian_status

        # Define English to Croatian translation mapping
        translations = {
            'arrived': 'Sletio',
            'landing': 'Slijeće',
            'landed': 'Sletio',
            'delayed': 'Kasni',
            'on time': 'Na vrijeme',
            'cancelled': 'Otkazan',
            'boarding': 'Ukrcavanje',
            'scheduled': 'Po rasporedu',
            'departed': 'Poletio',
            'diverted': 'Preusmjeren',
            'expected': 'Očekivan',
            'in flight': 'U letu',
            'taxiing': 'Taksiranje',
            'gate closed': 'Izlaz zatvoren',
            'final call': 'Zadnji poziv',
            'now boarding': 'Ukrcavanje u tijeku'
        }

        # Check for exact matches first
        if status_lower in translations:
            return translations[status_lower]

        # Check for partial matches
        for eng, cro in translations.items():
            if eng in status_lower:
                return cro

        # If no match found, return original status
        return status

    def _get_subject_for_event(self, event_type: str, flight_number: str, status: str, flight: Dict[str, Any] = None) -> str:
        """
        Get email subject based on event type with detailed flight information

        Args:
            event_type: Type of event (status_change, delay, gate_change, arrival)
            flight_number: Flight number
            status: Current flight status
            flight: Full flight data dictionary (optional)

        Returns:
            Email subject in Croatian with detailed flight information
        """
        # Translate status to Croatian
        status_croatian = self._translate_status_to_croatian(status)

        # Create a base subject with flight number
        base_subject = f"Let {flight_number}"

        # Add airline name if available
        if flight and flight.get('airline') and flight['airline'].get('name'):
            base_subject += f" ({flight['airline']['name']})"

        # Add origin if available
        if flight and flight.get('origin'):
            base_subject += f" iz {flight['origin']}"

        # Add scheduled time if available
        scheduled_time = ""
        if flight and flight.get('scheduled_time'):
            scheduled_time = f" - {flight['scheduled_time']}"

        # Add event-specific information with status in UPPERCASE for emphasis
        if event_type == 'status_change':
            status_info = f" - {status_croatian.upper()}"
            time_info = ""
            if flight and flight.get('expected_time'):
                time_info = f" ({flight['expected_time']})"
            return f"{base_subject}{scheduled_time}{status_info}{time_info}"
        elif event_type == 'delay':
            delay_info = " - KASNI"
            time_info = ""
            if flight and flight.get('expected_time'):
                time_info = f" ({flight['expected_time']})"
            return f"{base_subject}{scheduled_time}{delay_info}{time_info}"
        elif event_type == 'gate_change':
            gate_info = ""
            if flight and flight.get('gate'):
                gate_info = f" - NOVI IZLAZ: {flight['gate']}"
            return f"{base_subject}{scheduled_time}{gate_info}"
        elif event_type == 'arrival':
            return f"{base_subject}{scheduled_time} - SLETIO"
        else:
            return f"{base_subject}{scheduled_time} - {status_croatian.upper()}"

    def _get_notification_message(self, event_type: str) -> str:
        """
        Get notification message based on event type

        Args:
            event_type: Type of event (status_change, delay, gate_change, arrival)

        Returns:
            Notification message in Croatian
        """
        if event_type == 'status_change':
            return "Obavještavamo Vas o promjeni statusa leta kojeg pratite:"
        elif event_type == 'delay':
            return "Obavještavamo Vas da let kojeg pratite kasni:"
        elif event_type == 'gate_change':
            return "Obavještavamo Vas o promjeni izlaza za let kojeg pratite:"
        elif event_type == 'arrival':
            return "Obavještavamo Vas da je let kojeg pratite sletio:"
        else:
            return "Obavještavamo Vas o promjeni informacija za let kojeg pratite:"

    def send_notification(self, flight: Dict[str, Any], prev_flight: Dict[str, Any], event_type: str) -> bool:
        """
        Send notification email about flight changes using Resend API

        Args:
            flight: Current flight data
            prev_flight: Previous flight data
            event_type: Type of event (status_change, delay, gate_change, arrival)

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Load email template
            template_content = self._load_email_template()
            if not template_content:
                logger.error("Failed to load email template")
                return False

            # Create template
            template = Template(template_content)

            # Determine status class for styling
            status_class = self._determine_status_class(flight['status'])

            # Get notification message
            notification_message = self._get_notification_message(event_type)

            # Translate statuses to Croatian
            current_status_croatian = self._translate_status_to_croatian(flight['status'])
            previous_status_croatian = self._translate_status_to_croatian(prev_flight['status'])

            # Render email content
            email_content = template.render(
                flight_number=flight['flight_number'],
                airline=flight['airline']['name'] if flight.get('airline') and flight['airline'].get('name') else '',
                origin=flight['origin'],
                scheduled_time=flight['scheduled_time'],
                expected_time=flight['expected_time'],
                gate=flight['gate'],
                baggage=flight['baggage'],
                status=current_status_croatian,
                previous_status=previous_status_croatian,
                status_class=status_class,
                notification_message=notification_message,
                current_year=datetime.datetime.now().year
            )

            # Set subject based on event type with detailed flight information
            subject = self._get_subject_for_event(event_type, flight['flight_number'], flight['status'], flight)

            # Determine recipients for this flight
            flight_number = flight['flight_number']

            # Check if this flight has specific email recipients assigned
            flight_specific_recipients = self.flight_email_mappings.get(flight_number, [])

            # If flight has specific recipients, use ONLY those specific recipients
            # If no specific recipients are assigned, use ALL email recipients
            if flight_specific_recipients:
                recipients = flight_specific_recipients
                logger.info(f"Using flight-specific email recipients for flight {flight_number}: {recipients}")
            else:
                recipients = self.email_recipients
                logger.info(f"No specific recipients for flight {flight_number}, using all email recipients: {recipients}")

            if not recipients:
                logger.warning(f"No email recipients configured for flight {flight_number}, skipping email notification")
                return False

            # Log the recipients for debugging
            logger.info(f"Final email recipients for flight {flight_number}: {recipients}")

            # For Resend API, if there's only one recipient, use a string instead of a list
            to_field = recipients[0] if len(recipients) == 1 else recipients

            params = {
                "from": "Zagreb Airport <notifications@fuji.lemonmedia.hr>",
                "to": to_field,
                "subject": subject,
                "html": email_content,
            }

            logger.info(f"Sending email to {recipients} with subject: {subject}")

            # Send email using Resend API
            try:
                # Log the API key (first few characters only for security)
                api_key = resend.api_key
                masked_key = api_key[:5] + "..." if api_key else "None"
                logger.info(f"Using Resend API key: {masked_key}")

                # Log the params without sensitive information
                safe_params = params.copy()
                logger.info(f"Calling Resend API with params: {safe_params}")

                # Send the email
                response = resend.Emails.send(params)
                logger.info(f"Resend API response type: {type(response)}")

                # The Resend API returns a dictionary with an 'id' key when successful
                if response and isinstance(response, dict) and 'id' in response:
                    logger.info(f"Notification email sent for flight {flight['flight_number']} ({event_type}) with Resend API. Email ID: {response['id']}")
                    return True
                else:
                    logger.error(f"Failed to send email with Resend API: {response}")
                    return False
            except Exception as inner_e:
                logger.error(f"Error in Resend API call: {str(inner_e)}")
                logger.error(f"Error type: {type(inner_e)}")
                # Don't raise the exception, just log it and return False
                return False

        except Exception as e:
            logger.error(f"Error sending notification email with Resend API: {str(e)}")
            return False