import time
import logging
import datetime
import json
import os
from typing import Dict, List, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
import threading

# Import our modules
# Use relative imports to avoid path issues
from scraper import ZagrebAirportScraper
from email_service import EmailService

# Get logger
logger = logging.getLogger('scheduler')

class FlightScheduler:
    """
    Scheduler for periodically checking flight status updates and sending notifications
    """

    def __init__(self, config_path: str = 'config.json', data_path: str = 'data'):
        """
        Initialize the flight scheduler

        Args:
            config_path: Path to the configuration file
            data_path: Path to the data directory
        """
        self.config_path = config_path
        self.data_path = data_path
        self.current_data_path = os.path.join(data_path, 'current_data.json')
        self.previous_data_path = os.path.join(data_path, 'previous_data.json')
        self.state_path = os.path.join(data_path, 'scheduler_state.json')

        # Create data directory if it doesn't exist
        os.makedirs(data_path, exist_ok=True)

        # Load configuration
        self.config = self._load_config()

        # Initialize email service
        self.email_service = EmailService(self.config)

        # Initialize scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

        # Load state or initialize defaults
        self._load_state()

        # Lock for thread safety
        self.lock = threading.Lock()

        logger.info("Flight scheduler initialized")

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file

        Returns:
            Configuration dictionary
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info("Configuration loaded successfully")
                return config
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            # Return default configuration
            return {
                "app_settings": {
                    "language": "hr",
                    "check_interval_minutes": 5,
                    "max_flights": 20,
                    "timezone": "Europe/Zagreb"
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
                "email_recipients": []
            }

    def _save_state(self) -> None:
        """
        Save scheduler state to file
        """
        try:
            state = {
                "consecutive_failures": self.consecutive_failures,
                "last_check_time": datetime.datetime.now().isoformat(),
                "current_interval": self.config['app_settings']['check_interval_minutes'],
                "backoff_active": self.consecutive_failures >= self.max_consecutive_failures
            }

            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            logger.debug("Scheduler state saved")
        except Exception as e:
            logger.error(f"Error saving scheduler state: {str(e)}")

    def _load_state(self) -> None:
        """
        Load scheduler state from file or initialize defaults
        """
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                self.consecutive_failures = state.get('consecutive_failures', 0)
                self.max_consecutive_failures = 3

                # If we were in backoff mode, restore that state
                if state.get('backoff_active', False):
                    logger.info("Restoring backoff state from previous run")
                else:
                    logger.info("Restoring normal state from previous run")
            else:
                # Initialize defaults
                self.consecutive_failures = 0
                self.max_consecutive_failures = 3
                logger.info("No previous state found, initializing defaults")
        except Exception as e:
            logger.error(f"Error loading scheduler state: {str(e)}")
            # Initialize defaults
            self.consecutive_failures = 0
            self.max_consecutive_failures = 3

    def _save_flight_data(self, data: Dict[str, Any], filepath: str) -> bool:
        """
        Save flight data to file

        Args:
            data: Flight data dictionary
            filepath: Path to save the data

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving flight data to {filepath}: {str(e)}")
            return False

    def _load_flight_data(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Load flight data from file

        Args:
            filepath: Path to the flight data file

        Returns:
            Flight data dictionary or None if loading failed
        """
        try:
            if not os.path.exists(filepath):
                return None

            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading flight data from {filepath}: {str(e)}")
            return None

    def _job_listener(self, event):
        """
        Listener for scheduler job events

        Args:
            event: Scheduler event
        """
        if event.exception:
            logger.error(f"Job {event.job_id} failed with exception: {str(event.exception)}")

            with self.lock:
                self.consecutive_failures += 1

                if self.consecutive_failures >= self.max_consecutive_failures:
                    logger.warning(f"Maximum consecutive failures ({self.max_consecutive_failures}) reached. Implementing backoff strategy.")

                    # Implement backoff strategy - increase interval temporarily
                    current_interval = self.config['app_settings']['check_interval_minutes']
                    backoff_interval = min(current_interval * 2, 30)  # Max 30 minutes

                    logger.info(f"Temporarily increasing check interval from {current_interval} to {backoff_interval} minutes")

                    # Update job with new interval
                    self.scheduler.reschedule_job(
                        'check_flight_updates',
                        trigger=IntervalTrigger(minutes=backoff_interval)
                    )

                # Save state after failure
                self._save_state()
        else:
            # Reset consecutive failures counter on success
            with self.lock:
                if self.consecutive_failures > 0:
                    logger.info(f"Job {event.job_id} executed successfully after {self.consecutive_failures} failures")
                    self.consecutive_failures = 0

                    # If we were in backoff mode, restore normal interval
                    normal_interval = self.config['app_settings']['check_interval_minutes']

                    # Check if current interval is different from normal
                    current_job = self.scheduler.get_job('check_flight_updates')
                    if current_job and current_job.trigger.interval.total_seconds() != normal_interval * 60:
                        logger.info(f"Restoring normal check interval of {normal_interval} minutes")

                        # Update job with normal interval
                        self.scheduler.reschedule_job(
                            'check_flight_updates',
                            trigger=IntervalTrigger(minutes=normal_interval)
                        )

                # Save state after success
                self._save_state()

    def check_flight_updates(self) -> None:
        """
        Check for flight updates and send notifications if needed
        """
        try:
            logger.info("Checking for flight updates")

            # Reload configuration to get latest settings
            self.config = self._load_config()

            # Create scraper instance
            scraper = ZagrebAirportScraper()

            # Scrape arrivals data
            new_data = scraper.scrape_arrivals()

            if not new_data:
                logger.error("Failed to scrape flight data")
                raise Exception("Failed to scrape flight data")

            # Load previous data for comparison
            previous_data = self._load_flight_data(self.current_data_path)

            # Save current data as previous data
            if previous_data:
                self._save_flight_data(previous_data, self.previous_data_path)

            # Save new data as current data
            self._save_flight_data(new_data, self.current_data_path)

            # Check for changes and send notifications
            if previous_data:
                self._check_for_changes_and_notify(new_data, previous_data)

            logger.info(f"Flight data updated successfully. {len(new_data['flights'])} flights found.")

        except Exception as e:
            logger.error(f"Error checking flight updates: {str(e)}", exc_info=True)
            raise  # Re-raise to trigger job listener

    def _check_for_changes_and_notify(self, new_data: Dict[str, Any], previous_data: Dict[str, Any]) -> None:
        """
        Check for changes in flight data and send notifications

        Args:
            new_data: New flight data
            previous_data: Previous flight data
        """
        tracked_flights = self.config['tracked_flights']

        if not tracked_flights:
            logger.info("No tracked flights configured, skipping notifications")
            return

        notification_events = self.config['notification_settings']['notification_events']

        # Create a dictionary of previous flights for easy lookup
        prev_flights_dict = {flight['flight_number']: flight for flight in previous_data['flights']}

        # Check each current flight for changes
        for flight in new_data['flights']:
            flight_number = flight['flight_number']

            # Skip if not a tracked flight
            if flight_number not in tracked_flights:
                continue

            # Skip if flight wasn't in previous data
            if flight_number not in prev_flights_dict:
                logger.info(f"New tracked flight detected: {flight_number}")
                continue

            prev_flight = prev_flights_dict[flight_number]

            changes_detected = []

            # Check for status change
            if notification_events['status_change'] and flight['status'] != prev_flight['status']:
                logger.info(f"Status change detected for flight {flight_number}: {prev_flight['status']} -> {flight['status']}")
                changes_detected.append('status_change')
                self._send_notification(flight, prev_flight, 'status_change')

            # Check for delay
            if notification_events['delay'] and ('kasni' in flight['status'].lower() or 'delay' in flight['status'].lower() or 'odgođen' in flight['status'].lower()) and \
               not ('kasni' in prev_flight['status'].lower() or 'delay' in prev_flight['status'].lower() or 'odgođen' in prev_flight['status'].lower()):
                logger.info(f"Delay detected for flight {flight_number}")
                changes_detected.append('delay')
                self._send_notification(flight, prev_flight, 'delay')

            # Check for gate change
            if notification_events['gate_change'] and flight['gate'] != prev_flight['gate']:
                logger.info(f"Gate change detected for flight {flight_number}: {prev_flight['gate']} -> {flight['gate']}")
                changes_detected.append('gate_change')
                self._send_notification(flight, prev_flight, 'gate_change')

            # Check for arrival
            if notification_events['arrival'] and \
               ('sletio' in flight['status'].lower() or 'arrived' in flight['status'].lower() or 'stigao' in flight['status'].lower() or 'pristigao' in flight['status'].lower()) and \
               not ('sletio' in prev_flight['status'].lower() or 'arrived' in prev_flight['status'].lower() or 'stigao' in prev_flight['status'].lower() or 'pristigao' in prev_flight['status'].lower()):
                logger.info(f"Arrival detected for flight {flight_number}")
                changes_detected.append('arrival')
                self._send_notification(flight, prev_flight, 'arrival')

            if changes_detected:
                logger.info(f"Changes detected for flight {flight_number}: {', '.join(changes_detected)}")
            else:
                logger.debug(f"No changes detected for flight {flight_number}")

    def _send_notification(self, flight: Dict[str, Any], prev_flight: Dict[str, Any], event_type: str) -> None:
        """
        Send notification email about flight changes

        Args:
            flight: Current flight data
            prev_flight: Previous flight data
            event_type: Type of event (status_change, delay, gate_change, arrival)
        """
        try:
            # Ensure email service is initialized with latest config
            self.email_service = EmailService(self.config)

            # Send notification
            result = self.email_service.send_notification(flight, prev_flight, event_type)

            if result:
                logger.info(f"Notification sent successfully for flight {flight['flight_number']} ({event_type})")
            else:
                logger.warning(f"Failed to send notification for flight {flight['flight_number']} ({event_type})")
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}", exc_info=True)

    def start(self) -> None:
        """
        Start the scheduler
        """
        try:
            # Get check interval from configuration
            check_interval = self.config['app_settings']['check_interval_minutes']

            # If we were in backoff mode, use backoff interval
            if self.consecutive_failures >= self.max_consecutive_failures:
                backoff_interval = min(check_interval * 2, 30)  # Max 30 minutes
                logger.info(f"Starting with backoff interval of {backoff_interval} minutes due to previous failures")
                check_interval = backoff_interval

            # Add job to check for flight updates
            self.scheduler.add_job(
                self.check_flight_updates,
                trigger=IntervalTrigger(minutes=check_interval),
                id='check_flight_updates',
                replace_existing=True,
                max_instances=1
            )

            # Start the scheduler
            self.scheduler.start()

            logger.info(f"Scheduler started with check interval of {check_interval} minutes")

            # Run initial check
            self.check_flight_updates()

        except Exception as e:
            logger.error(f"Error starting scheduler: {str(e)}", exc_info=True)
            raise

    def stop(self) -> None:
        """
        Stop the scheduler
        """
        try:
            # Save state before stopping
            self._save_state()

            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}", exc_info=True)