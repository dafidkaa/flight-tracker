# Zagreb Airport Flight Tracker - Scheduler and Monitoring System

## Overview

This document describes the implementation of the scheduler and monitoring system for the Zagreb Airport Flight Tracker application. The system periodically checks for flight status updates and sends email notifications when changes are detected.

## Components

### 1. Scheduler Module (`scheduler.py`)

The scheduler module is responsible for:
- Periodically checking flight status updates every 5 minutes
- Comparing new flight data with previously stored data
- Triggering notifications when changes are detected
- Implementing error handling and retry mechanisms

Key features:
- Uses APScheduler for reliable task scheduling
- Implements backoff strategy for handling failures
- Maintains state between application restarts
- Provides comprehensive logging

### 2. Main Application Entry Point (`main.py`)

The main application entry point:
- Initializes the Flask application
- Sets up the scheduler
- Configures logging
- Provides a clean startup process
- Handles graceful shutdown

### 3. Logging Configuration (`logging_config.py`)

The logging configuration:
- Sets up comprehensive logging for all components
- Configures log rotation to manage log file sizes
- Provides different log levels for different components
- Formats log messages for easy reading and analysis

## Functionality

### Flight Status Monitoring

The system monitors the following types of changes:
- Status changes (e.g., "On Time" to "Delayed")
- Delays (when a flight status changes to indicate a delay)
- Gate changes
- Arrivals (when a flight status changes to indicate it has landed)

### Error Handling and Recovery

The system includes robust error handling:
- Graceful handling of network interruptions
- Automatic retry with exponential backoff
- State persistence between application restarts
- Comprehensive logging of errors and recovery attempts

### Notification System

When changes are detected, the system:
- Determines the type of change
- Prepares appropriate notification content in Croatian
- Sends email notifications to configured recipients
- Logs notification attempts and results

## Configuration

The system uses the central configuration file (`config.json`) for:
- Check interval settings (default: 5 minutes)
- Notification preferences
- Email settings
- Tracked flights

## Usage

To start the application:

```bash
python app/main.py
```

This will start both the Flask web application and the scheduler.

## Resilience Features

- **Network Interruptions**: The system handles network interruptions gracefully and implements retry mechanisms.
- **Failure Recovery**: If the system encounters consecutive failures, it implements a backoff strategy to reduce load.
- **State Persistence**: The system maintains state between restarts, ensuring no notifications are missed.
- **Comprehensive Logging**: All operations are logged for monitoring and debugging purposes.