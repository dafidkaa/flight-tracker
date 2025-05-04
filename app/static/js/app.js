/**
 * Zagreb Airport Flight Tracker
 * Frontend JavaScript functionality
 */

// DOM Elements
const flightDataTable = document.getElementById('flight-data');
const trackedFlightsTable = document.getElementById('tracked-flights-data');
const emailRecipientsList = document.getElementById('email-recipients');
const lastUpdateElement = document.getElementById('last-update');
const refreshButton = document.getElementById('refresh-btn');
const addFlightForm = document.getElementById('add-flight-form');
const addEmailForm = document.getElementById('add-email-form');
const notificationSettingsForm = document.getElementById('notification-settings-form');
const checkIntervalForm = document.getElementById('check-interval-form');
const currentCheckIntervalElement = document.getElementById('current-check-interval');
const nextRefreshTimeElement = document.getElementById('next-refresh-time');
const notificationsContainer = document.getElementById('notifications-container');

// Configuration and state
let config = null;
let flightData = null;
let trackedFlights = [];
let emailRecipients = [];
let flightEmailMappings = {};

// Initialize the application
async function initApp() {
    try {
        console.log('Initializing application...');

        // Load configuration
        await loadConfig();

        // Set check interval value in the form
        if (config && config.app_settings && config.app_settings.check_interval_minutes) {
            document.getElementById('check-interval').value = config.app_settings.check_interval_minutes;
            currentCheckIntervalElement.textContent = config.app_settings.check_interval_minutes;
        }

        // Set scraping toggle state
        if (config && config.app_settings && 'scraping_enabled' in config.app_settings) {
            updateScrapingToggleUI(config.app_settings.scraping_enabled);
        }

        // Load flight-email mappings explicitly
        console.log('Loading flight-email mappings during initialization');
        await loadFlightEmailMappings();

        // Load flight data
        await loadFlightData();

        // Set up event listeners
        setupEventListeners();

        // Update last refresh time and next refresh time
        updateLastRefreshTime();
        updateNextRefreshTime();

        // Switch to tracked flights tab by default
        switchTab('tracked');

        console.log('Aplikacija uspješno inicijalizirana');
    } catch (error) {
        console.error('Greška prilikom inicijalizacije aplikacije:', error);
        showNotification('Greška', 'Došlo je do greške prilikom učitavanja aplikacije. Molimo osvježite stranicu.', 'error');
    }
}

// Load configuration from server
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error(`HTTP greška! status: ${response.status}`);
        }

        config = await response.json();
        trackedFlights = config.tracked_flights || [];
        emailRecipients = config.email_recipients || [];
        flightEmailMappings = config.flight_email_mappings || {};

        // Render tracked flights and email recipients
        renderTrackedFlights();
        renderEmailRecipients();

        // Set notification settings form values
        setNotificationSettings(config.notification_settings);

        // Load flight-email mappings
        await loadFlightEmailMappings();

        console.log('Konfiguracija uspješno učitana');
    } catch (error) {
        console.error('Greška prilikom učitavanja konfiguracije:', error);
        throw error;
    }
}

// Load flight data from server
async function loadFlightData(forceRefresh = false) {
    try {
        // Show loading state
        flightDataTable.innerHTML = `
            <tr>
                <td colspan="9" class="text-center">
                    <div class="spinner"></div>
                    <p>Učitavanje podataka o letovima...</p>
                </td>
            </tr>
        `;

        let response;

        // If forceRefresh is true, call the refresh endpoint to trigger a new scrape
        if (forceRefresh) {
            console.log('Osvježavanje podataka sa servera...');
            const refreshResponse = await fetch('/api/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            if (!refreshResponse.ok) {
                throw new Error(`HTTP greška prilikom osvježavanja! status: ${refreshResponse.status}`);
            }

            // After successful refresh, get the updated data
            response = await fetch('/api/flights');
        } else {
            // Just get the current data without refreshing
            response = await fetch('/api/flights');
        }

        if (!response.ok) {
            throw new Error(`HTTP greška! status: ${response.status}`);
        }

        flightData = await response.json();
        renderFlightData();
        renderTrackedFlights(); // Update tracked flights with current status

        console.log('Podaci o letovima uspješno učitani');
    } catch (error) {
        console.error('Greška prilikom učitavanja podataka o letovima:', error);
        flightDataTable.innerHTML = `
            <tr>
                <td colspan="9" class="text-center">
                    <p><i class="fas fa-exclamation-triangle"></i> Greška prilikom učitavanja podataka.</p>
                    <button id="retry-load" class="btn btn-primary mt-2">Pokušaj ponovno</button>
                </td>
            </tr>
        `;

        document.getElementById('retry-load')?.addEventListener('click', () => loadFlightData(forceRefresh));
        throw error;
    }
}

// Set up event listeners
function setupEventListeners() {
    // Tab switching
    const tabTracked = document.getElementById('tab-tracked');
    const tabAll = document.getElementById('tab-all');

    if (tabTracked && tabAll) {
        tabTracked.addEventListener('click', () => switchTab('tracked'));
        tabAll.addEventListener('click', () => switchTab('all'));
    }

    // Refresh button
    refreshButton.addEventListener('click', async () => {
        refreshButton.disabled = true;
        refreshButton.innerHTML = '<div class="spinner"></div> Učitavanje...';

        try {
            // Pass true to force a refresh from the server
            await loadFlightData(true);
            updateLastRefreshTime();
            updateNextRefreshTime();
            showNotification('Uspjeh', 'Podaci o letovima uspješno osvježeni.', 'success');
        } catch (error) {
            console.error('Greška prilikom osvježavanja podataka:', error);
            showNotification('Greška', error.message || 'Došlo je do greške prilikom osvježavanja podataka.', 'error');
        } finally {
            refreshButton.disabled = false;
            refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i> Osvježi podatke';
        }
    });

    // Scraping toggle button
    const toggleScrapingBtn = document.getElementById('toggle-scraping-btn');
    if (toggleScrapingBtn) {
        toggleScrapingBtn.addEventListener('click', () => {
            // Check current state based on button class
            const isCurrentlyEnabled = toggleScrapingBtn.classList.contains('btn-danger');

            if (isCurrentlyEnabled) {
                // If currently enabled, show confirmation dialog to disable
                showScrapingConfirmationDialog();
            } else {
                // If currently disabled, enable without confirmation
                toggleScraping(true);
            }
        });
    }

    // Enable scraping button in the banner
    const enableScrapingBtn = document.getElementById('enable-scraping-btn');
    if (enableScrapingBtn) {
        enableScrapingBtn.addEventListener('click', () => {
            toggleScraping(true);
        });
    }

    // Test email button
    const testEmailBtn = document.getElementById('test-email-btn');
    if (testEmailBtn) {
        testEmailBtn.addEventListener('click', async () => {
            testEmailBtn.disabled = true;
            testEmailBtn.innerHTML = '<div class="spinner"></div> Slanje...';

            try {
                const response = await fetch('/api/email/test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();

                if (response.ok) {
                    showNotification('Uspjeh', 'Testni e-mail uspješno poslan. Provjerite svoju e-mail adresu.', 'success');
                } else {
                    showNotification('Greška', data.error || 'Došlo je do greške prilikom slanja testnog e-maila.', 'error');
                }
            } catch (error) {
                console.error('Greška prilikom slanja testnog e-maila:', error);
                showNotification('Greška', 'Došlo je do greške prilikom slanja testnog e-maila.', 'error');
            } finally {
                testEmailBtn.disabled = false;
                testEmailBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Testiraj slanje';
            }
        });
    }

    // Add flight form
    addFlightForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const flightNumberInput = document.getElementById('flight-number');
        const flightNumber = flightNumberInput.value.trim();

        if (!flightNumber) {
            showNotification('Upozorenje', 'Molimo unesite broj leta.', 'error');
            return;
        }

        if (trackedFlights.length >= 20) {
            showNotification('Upozorenje', 'Dostigli ste maksimalan broj praćenih letova (20).', 'error');
            return;
        }

        if (trackedFlights.includes(flightNumber)) {
            showNotification('Upozorenje', 'Ovaj let već pratite.', 'error');
            return;
        }

        try {
            await addTrackedFlight(flightNumber);
            flightNumberInput.value = '';
            showNotification('Uspjeh', `Let ${flightNumber} dodan u praćene letove.`, 'success');
        } catch (error) {
            console.error('Greška prilikom dodavanja leta:', error);
            showNotification('Greška', 'Došlo je do greške prilikom dodavanja leta.', 'error');
        }
    });

    // Add email form
    addEmailForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const emailInput = document.getElementById('email');
        const email = emailInput.value.trim();

        if (!email) {
            showNotification('Upozorenje', 'Molimo unesite e-mail adresu.', 'error');
            return;
        }

        if (!isValidEmail(email)) {
            showNotification('Upozorenje', 'Molimo unesite ispravnu e-mail adresu.', 'error');
            return;
        }

        if (emailRecipients.includes(email)) {
            showNotification('Upozorenje', 'Ova e-mail adresa već je dodana.', 'error');
            return;
        }

        try {
            await addEmailRecipient(email);
            emailInput.value = '';
            showNotification('Uspjeh', `E-mail adresa ${email} dodana.`, 'success');
        } catch (error) {
            console.error('Greška prilikom dodavanja e-mail adrese:', error);
            showNotification('Greška', 'Došlo je do greške prilikom dodavanja e-mail adrese.', 'error');
        }
    });

    // Notification settings form
    notificationSettingsForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const settings = {
            status_change: document.getElementById('notify-status-change').checked,
            delay: document.getElementById('notify-delay').checked,
            gate_change: document.getElementById('notify-gate-change').checked,
            arrival: document.getElementById('notify-arrival').checked
        };

        try {
            await saveNotificationSettings(settings);
            showNotification('Uspjeh', 'Postavke obavijesti uspješno spremljene.', 'success');
        } catch (error) {
            console.error('Greška prilikom spremanja postavki:', error);
            showNotification('Greška', 'Došlo je do greške prilikom spremanja postavki.', 'error');
        }
    });

    // Check interval form
    checkIntervalForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const checkIntervalInput = document.getElementById('check-interval');
        const checkInterval = parseInt(checkIntervalInput.value.trim(), 10);

        if (isNaN(checkInterval) || checkInterval < 1 || checkInterval > 60) {
            showNotification('Upozorenje', 'Molimo unesite ispravnu vrijednost intervala (1-60 minuta).', 'error');
            return;
        }

        try {
            await updateCheckInterval(checkInterval);
            showNotification('Uspjeh', `Interval provjere postavljen na ${checkInterval} minuta.`, 'success');
            updateNextRefreshTime();
        } catch (error) {
            console.error('Greška prilikom ažuriranja intervala provjere:', error);
            showNotification('Greška', 'Došlo je do greške prilikom ažuriranja intervala provjere.', 'error');
        }
    });
}

// Render flight data table
function renderFlightData() {
    if (!flightData || !flightData.flights || !flightData.flights.length) {
        flightDataTable.innerHTML = `
            <tr>
                <td colspan="9" class="text-center">
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <i class="fas fa-plane-slash"></i>
                        </div>
                        <p>Nema dostupnih podataka o letovima.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    // Clear the table first
    flightDataTable.innerHTML = '';

    // Create table rows for each flight
    flightData.flights.forEach(flight => {
        // Create a table row
        const row = document.createElement('tr');

        // Get status class for row styling
        const statusClass = getStatusClass(flight.status);

        // Create all cells at once with proper structure
        const cells = createFlightTableCells(flight, statusClass);

        // Add track/untrack button to the action cell
        const isTracked = trackedFlights.includes(flight.flight_number);
        const actionButton = createActionButton(
            isTracked ? 'btn-danger' : 'btn-primary',
            isTracked ? '<i class="fas fa-times"></i> Ukloni' : '<i class="fas fa-bell"></i> Prati',
            async () => {
                try {
                    if (isTracked) {
                        await removeTrackedFlight(flight.flight_number);
                        showNotification('Uspjeh', `Let ${flight.flight_number} uklonjen iz praćenih letova.`, 'success');
                    } else {
                        if (trackedFlights.length >= 20) {
                            showNotification('Upozorenje', 'Dostigli ste maksimalan broj praćenih letova (20).', 'error');
                            return;
                        }
                        await addTrackedFlight(flight.flight_number);
                        showNotification('Uspjeh', `Let ${flight.flight_number} dodan u praćene letove.`, 'success');
                    }
                } catch (error) {
                    console.error('Greška prilikom ažuriranja praćenih letova:', error);
                    showNotification('Greška', 'Došlo je do greške prilikom ažuriranja praćenih letova.', 'error');
                }
            }
        );

        // Add the action button to the action cell
        const actionButtonsContainer = cells.actionCell.querySelector('.action-buttons');
        actionButtonsContainer.appendChild(actionButton);

        // Add all cells to the row
        Object.values(cells).forEach(cell => row.appendChild(cell));

        // Add the row to the table
        flightDataTable.appendChild(row);
    });
}

// Helper function to create a standardized set of cells for a flight
function createFlightTableCells(flight, statusClass) {
    // Create all cells
    const airlineCell = document.createElement('td');
    const flightNumberCell = document.createElement('td');
    const originCell = document.createElement('td');
    const scheduledTimeCell = document.createElement('td');
    const expectedTimeCell = document.createElement('td');
    const gateCell = document.createElement('td');
    const baggageCell = document.createElement('td');
    const statusCell = document.createElement('td');
    const actionCell = document.createElement('td');

    // Set classes and attributes
    airlineCell.className = 'airline-cell';
    flightNumberCell.className = 'flight-number';
    gateCell.className = 'hide-sm';
    baggageCell.className = 'hide-sm';
    statusCell.className = 'status-cell';
    actionCell.className = 'action-cell';

    // Create airline container with logo and name
    const airlineContainer = document.createElement('div');
    airlineContainer.className = 'airline-container';

    // Add airline logo if available
    if (flight.airline && flight.airline.logo) {
        const airlineLogo = document.createElement('img');
        airlineLogo.src = flight.airline.logo;
        airlineLogo.alt = flight.airline.name || 'Airline logo';
        airlineLogo.className = 'airline-logo';
        airlineContainer.appendChild(airlineLogo);
    }

    // Add airline name
    const airlineName = document.createElement('span');
    airlineName.className = 'airline-name';
    airlineName.textContent = flight.airline && flight.airline.name ? flight.airline.name : '-';
    airlineContainer.appendChild(airlineName);
    airlineCell.appendChild(airlineContainer);

    // Set content for other cells
    flightNumberCell.textContent = flight.flight_number;
    originCell.textContent = flight.origin || '-';
    scheduledTimeCell.textContent = flight.scheduled_time || '-';
    expectedTimeCell.textContent = flight.expected_time || '-';
    gateCell.textContent = flight.gate || '-';
    baggageCell.textContent = flight.baggage || '-';

    // Create status indicator
    const statusSpan = document.createElement('span');
    statusSpan.className = `status-${statusClass}`;
    statusSpan.textContent = translateStatus(flight.status);
    statusCell.appendChild(statusSpan);

    // Create action buttons container
    const actionButtonsContainer = document.createElement('div');
    actionButtonsContainer.className = 'action-buttons';
    actionCell.appendChild(actionButtonsContainer);

    // Return all cells as an object for easy access
    return {
        airlineCell,
        flightNumberCell,
        originCell,
        scheduledTimeCell,
        expectedTimeCell,
        gateCell,
        baggageCell,
        statusCell,
        actionCell
    };
}

// Helper function to create action buttons
function createActionButton(className, innerHTML, clickHandler) {
    const button = document.createElement('button');
    button.className = `btn btn-sm ${className}`;
    button.innerHTML = innerHTML;
    button.addEventListener('click', clickHandler);
    return button;
}

// Render tracked flights table
function renderTrackedFlights() {
    if (!trackedFlights || !trackedFlights.length) {
        trackedFlightsTable.innerHTML = `
            <tr>
                <td colspan="9" class="text-center">
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <i class="fas fa-plane"></i>
                        </div>
                        <p>Trenutno ne pratite nijedan let.</p>
                        <p>Dodajte let za praćenje putem obrasca ispod ili iz tablice svih letova.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    // Clear the table first
    trackedFlightsTable.innerHTML = '';

    // Create table rows for each tracked flight
    trackedFlights.forEach(flightNumber => {
        // Find flight data if available
        const flightInfo = flightData && flightData.flights ?
            flightData.flights.find(f => f.flight_number === flightNumber) : null;

        // Create a table row
        const row = document.createElement('tr');

        // Get status class for row styling
        const statusClass = flightInfo ? getStatusClass(flightInfo.status) : '';

        // Create a flight object to pass to the cell creation function
        const flight = flightInfo || {
            flight_number: flightNumber,
            airline: null,
            origin: null,
            scheduled_time: null,
            expected_time: null,
            gate: null,
            baggage: null,
            status: null
        };

        // Create all cells at once with proper structure
        const cells = createFlightTableCells(flight, statusClass);

        // Create email assignment dropdown
        const emailDropdown = document.createElement('select');
        emailDropdown.className = 'email-assignment-dropdown';
        emailDropdown.setAttribute('data-flight', flightNumber);

        // Check if this flight has any assigned emails
        const assignedEmails = flightEmailMappings[flightNumber] || [];

        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';

        if (assignedEmails.length > 0) {
            // If there are assigned emails, show them in the dropdown text
            defaultOption.textContent = `${assignedEmails.length} dodijeljeno`;
            defaultOption.disabled = true; // Disable the default option when emails are assigned
        } else {
            // If no emails are assigned, show the default text
            defaultOption.textContent = emailRecipients.length > 0 ? 'Dodijeli' : 'Nema e-mailova';
        }

        emailDropdown.appendChild(defaultOption);

        // Add options for each email recipient
        if (emailRecipients.length > 0) {
            emailRecipients.forEach(email => {
                const option = document.createElement('option');
                option.value = email;
                option.textContent = email;

                // Check if this email is assigned to this flight
                if (assignedEmails.includes(email)) {
                    option.selected = true;
                    option.textContent = `✓ ${email}`; // Add a checkmark to show it's assigned
                }

                emailDropdown.appendChild(option);
            });

            // Add change event listener
            emailDropdown.addEventListener('change', async (event) => {
                const selectedEmail = event.target.value;
                if (selectedEmail) {
                    try {
                        // Check if this email is already assigned to this flight
                        if (assignedEmails.includes(selectedEmail)) {
                            // If already assigned, unassign it
                            await unassignEmailFromFlight(flightNumber, selectedEmail);
                            showNotification('Uspjeh', `E-mail ${selectedEmail} uklonjen s leta ${flightNumber}.`, 'success');
                        } else {
                            // If not assigned, assign it
                            await assignEmailToFlight(flightNumber, selectedEmail);
                            showNotification('Uspjeh', `E-mail ${selectedEmail} dodijeljen letu ${flightNumber}.`, 'success');
                        }

                        // Re-render the tracked flights to update the UI
                        renderTrackedFlights();
                    } catch (error) {
                        showNotification('Greška', error.message || 'Došlo je do greške prilikom upravljanja e-mailom.', 'error');
                        // Reset dropdown to default option
                        renderTrackedFlights();
                    }
                }
            });
        } else {
            emailDropdown.disabled = true;
        }

        // Create remove button
        const removeButton = createActionButton(
            'btn-danger',
            '<i class="fas fa-times"></i> Ukloni',
            async () => {
                try {
                    await removeTrackedFlight(flightNumber);
                    showNotification('Uspjeh', `Let ${flightNumber} uklonjen iz praćenih letova.`, 'success');
                } catch (error) {
                    console.error('Greška prilikom uklanjanja leta:', error);
                    showNotification('Greška', 'Došlo je do greške prilikom uklanjanja leta.', 'error');
                }
            }
        );
        removeButton.setAttribute('data-flight', flightNumber);

        // Add dropdown and button to action cell
        const actionButtonsContainer = cells.actionCell.querySelector('.action-buttons');
        actionButtonsContainer.appendChild(emailDropdown);
        actionButtonsContainer.appendChild(removeButton);

        // Add all cells to the row
        Object.values(cells).forEach(cell => row.appendChild(cell));

        // Add the row to the table
        trackedFlightsTable.appendChild(row);
    });
}

// Render email recipients list
function renderEmailRecipients() {
    if (!emailRecipients || !emailRecipients.length) {
        emailRecipientsList.innerHTML = `
            <li class="text-center">
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <i class="fas fa-envelope-open"></i>
                    </div>
                    <p>Nema dodanih e-mail adresa.</p>
                    <p>Dodajte e-mail adresu putem obrasca ispod.</p>
                </div>
            </li>
        `;
        return;
    }

    emailRecipientsList.innerHTML = '';

    // Get the template
    const template = document.getElementById('email-item-template');

    emailRecipients.forEach(email => {
        // Clone the template
        const clone = template.content.cloneNode(true);

        // Set the email address
        clone.querySelector('.email-address').textContent = email;

        // Set data attributes for the buttons
        const testButton = clone.querySelector('.test-email-btn');
        testButton.setAttribute('data-email', email);

        const removeButton = clone.querySelector('.remove-email-btn');
        removeButton.setAttribute('data-email', email);

        // Add the item to the list
        emailRecipientsList.appendChild(clone);
    });

    // Add event listeners to remove buttons
    document.querySelectorAll('.remove-email-btn').forEach(button => {
        button.addEventListener('click', async () => {
            const email = button.getAttribute('data-email');
            try {
                await removeEmailRecipient(email);
                showNotification('Uspjeh', `E-mail adresa ${email} uklonjena.`, 'success');
            } catch (error) {
                console.error('Greška prilikom uklanjanja e-mail adrese:', error);
                showNotification('Greška', 'Došlo je do greške prilikom uklanjanja e-mail adrese.', 'error');
            }
        });
    });

    // Add event listeners to test email buttons
    document.querySelectorAll('.test-email-btn').forEach(button => {
        button.addEventListener('click', async () => {
            const email = button.getAttribute('data-email');
            const originalContent = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '<div class="spinner"></div>';

            try {
                const response = await fetch('/api/email/test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email: email })
                });

                const data = await response.json();

                if (response.ok) {
                    showNotification('Uspjeh', `Testni e-mail poslan na adresu ${email}.`, 'success');
                } else {
                    showNotification('Greška', data.error || 'Došlo je do greške prilikom slanja testnog e-maila.', 'error');
                }
            } catch (error) {
                console.error('Greška prilikom slanja testnog e-maila:', error);
                showNotification('Greška', 'Došlo je do greške prilikom slanja testnog e-maila.', 'error');
            } finally {
                button.disabled = false;
                button.innerHTML = originalContent;
            }
        });
    });
}

// Set notification settings form values
function setNotificationSettings(settings) {
    if (!settings || !settings.notification_events) return;

    const events = settings.notification_events;
    document.getElementById('notify-status-change').checked = events.status_change;
    document.getElementById('notify-delay').checked = events.delay;
    document.getElementById('notify-gate-change').checked = events.gate_change;
    document.getElementById('notify-arrival').checked = events.arrival;
}

// Add tracked flight
async function addTrackedFlight(flightNumber) {
    try {
        const response = await fetch('/api/flights/track', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ flight_number: flightNumber })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP greška! status: ${response.status}`);
        }

        // Update local state
        trackedFlights.push(flightNumber);
        renderTrackedFlights();
        renderFlightData(); // Re-render to update action buttons

        return true;
    } catch (error) {
        console.error('Greška prilikom dodavanja leta:', error);
        throw error;
    }
}

// Remove tracked flight
async function removeTrackedFlight(flightNumber) {
    try {
        const response = await fetch('/api/flights/untrack', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ flight_number: flightNumber })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP greška! status: ${response.status}`);
        }

        // Update local state
        trackedFlights = trackedFlights.filter(f => f !== flightNumber);
        renderTrackedFlights();
        renderFlightData(); // Re-render to update action buttons

        return true;
    } catch (error) {
        console.error('Greška prilikom uklanjanja leta:', error);
        throw error;
    }
}

// Add email recipient
async function addEmailRecipient(email) {
    try {
        const response = await fetch('/api/email/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP greška! status: ${response.status}`);
        }

        // Update local state
        emailRecipients.push(email);

        // Render both email recipients list and tracked flights to update dropdowns
        renderEmailRecipients();
        renderTrackedFlights(); // Re-render to update email dropdowns with the new email

        return true;
    } catch (error) {
        console.error('Greška prilikom dodavanja e-mail adrese:', error);
        throw error;
    }
}

// Remove email recipient
async function removeEmailRecipient(email) {
    try {
        const response = await fetch('/api/email/remove', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP greška! status: ${response.status}`);
        }

        // Update local state
        emailRecipients = emailRecipients.filter(e => e !== email);

        // Also update flight-email mappings to remove this email from all flights
        Object.keys(flightEmailMappings).forEach(flightNumber => {
            if (flightEmailMappings[flightNumber].includes(email)) {
                flightEmailMappings[flightNumber] = flightEmailMappings[flightNumber].filter(e => e !== email);

                // If no emails left for this flight, remove the flight entry
                if (flightEmailMappings[flightNumber].length === 0) {
                    delete flightEmailMappings[flightNumber];
                }
            }
        });

        // Render both email recipients list and tracked flights
        renderEmailRecipients();
        renderTrackedFlights(); // Re-render to update email dropdowns

        return true;
    } catch (error) {
        console.error('Greška prilikom uklanjanja e-mail adrese:', error);
        throw error;
    }
}

// Save notification settings
async function saveNotificationSettings(settings) {
    try {
        const response = await fetch('/api/settings/notifications', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ notification_events: settings })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP greška! status: ${response.status}`);
        }

        // Update local state
        if (config && config.notification_settings) {
            config.notification_settings.notification_events = settings;
        }

        return true;
    } catch (error) {
        console.error('Greška prilikom spremanja postavki:', error);
        throw error;
    }
}

// Update last refresh time
function updateLastRefreshTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('hr-HR');
    lastUpdateElement.textContent = timeString;
}

// Update next refresh time
function updateNextRefreshTime(isScrapingEnabled = null) {
    if (!config || !config.app_settings || !config.app_settings.check_interval_minutes) {
        nextRefreshTimeElement.textContent = '-';
        return;
    }

    // If isScrapingEnabled is not provided, use the value from config
    if (isScrapingEnabled === null) {
        isScrapingEnabled = config.app_settings.scraping_enabled !== false;
    }

    // If scraping is disabled, show a message instead of the next refresh time
    if (!isScrapingEnabled) {
        nextRefreshTimeElement.innerHTML = '<span class="status-inactive">Prikupljanje podataka isključeno</span>';
        return;
    }

    // Calculate and display the next refresh time
    const now = new Date();
    const nextRefresh = new Date(now.getTime() + (config.app_settings.check_interval_minutes * 60 * 1000));
    const timeString = nextRefresh.toLocaleTimeString('hr-HR');
    nextRefreshTimeElement.textContent = timeString;
}

// Update check interval
async function updateCheckInterval(minutes) {
    try {
        const response = await fetch('/api/settings/check_interval', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ check_interval_minutes: minutes })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP greška! status: ${response.status}`);
        }

        // Update local state
        if (config && config.app_settings) {
            config.app_settings.check_interval_minutes = minutes;
            currentCheckIntervalElement.textContent = minutes;
        }

        return true;
    } catch (error) {
        console.error('Greška prilikom ažuriranja intervala provjere:', error);
        throw error;
    }
}

// Load flight-email mappings
async function loadFlightEmailMappings() {
    try {
        console.log('Loading flight-email mappings from server');
        const response = await fetch('/api/flights/email_mappings');

        if (!response.ok) {
            throw new Error(`HTTP greška! status: ${response.status}`);
        }

        const data = await response.json();

        if (data && data.success) {
            flightEmailMappings = data.flight_email_mappings || {};
            console.log('Flight-email mappings loaded successfully:', flightEmailMappings);
        } else {
            console.warn('Failed to load flight-email mappings:', data);
            flightEmailMappings = {};
        }

        return flightEmailMappings;
    } catch (error) {
        console.error('Greška prilikom učitavanja flight-email mappings:', error);
        flightEmailMappings = {};
        return {};
    }
}

// Assign email to flight
async function assignEmailToFlight(flightNumber, email) {
    try {
        console.log(`Assigning email ${email} to flight ${flightNumber}`);

        // Check if this email is already assigned to this flight
        const assignedEmails = flightEmailMappings[flightNumber] || [];
        if (assignedEmails.includes(email)) {
            throw new Error('Email is already assigned to this flight');
        }

        const response = await fetch('/api/flights/assign_email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ flight_number: flightNumber, email })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP greška! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Assignment response:', data);

        // Update local state with the new mappings from the server
        if (data && data.flight_email_mappings) {
            flightEmailMappings = data.flight_email_mappings;
            console.log('Updated flight email mappings:', flightEmailMappings);

            // Update the UI to show the assigned email
            // This is handled by renderTrackedFlights, but we'll make sure the mapping is updated first
            if (!flightEmailMappings[flightNumber]) {
                flightEmailMappings[flightNumber] = [];
            }

            if (!flightEmailMappings[flightNumber].includes(email)) {
                flightEmailMappings[flightNumber].push(email);
            }
        } else {
            console.warn('No flight_email_mappings in response');
            // Reload mappings from server to ensure we have the latest data
            await loadFlightEmailMappings();
        }

        // Re-render tracked flights to show updated email assignments
        renderTrackedFlights();

        return true;
    } catch (error) {
        console.error(`Greška prilikom dodjeljivanja e-maila ${email} letu ${flightNumber}:`, error);
        throw error;
    }
}

// Unassign email from flight
async function unassignEmailFromFlight(flightNumber, email) {
    try {
        console.log(`Unassigning email ${email} from flight ${flightNumber}`);

        // Check if this email is assigned to this flight
        const assignedEmails = flightEmailMappings[flightNumber] || [];
        if (!assignedEmails.includes(email)) {
            throw new Error('Email is not assigned to this flight');
        }

        const response = await fetch('/api/flights/unassign_email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ flight_number: flightNumber, email })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP greška! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Unassignment response:', data);

        // Update local state with the new mappings from the server
        if (data && data.flight_email_mappings) {
            flightEmailMappings = data.flight_email_mappings;
            console.log('Updated flight email mappings after unassign:', flightEmailMappings);

            // Update the UI to remove the unassigned email
            // This is handled by renderTrackedFlights, but we'll make sure the mapping is updated first
            if (flightEmailMappings[flightNumber]) {
                flightEmailMappings[flightNumber] = flightEmailMappings[flightNumber].filter(e => e !== email);

                // If no emails left for this flight, remove the flight entry
                if (flightEmailMappings[flightNumber].length === 0) {
                    delete flightEmailMappings[flightNumber];
                }
            }
        } else {
            console.warn('No flight_email_mappings in response');
            // Reload mappings from server to ensure we have the latest data
            await loadFlightEmailMappings();
        }

        // Re-render tracked flights to show updated email assignments
        renderTrackedFlights();

        return true;
    } catch (error) {
        console.error(`Greška prilikom uklanjanja e-maila ${email} s leta ${flightNumber}:`, error);
        throw error;
    }
}

// Helper function to get status class
function getStatusClass(status) {
    if (!status) return 'ontime';

    const statusLower = status.toLowerCase();
    if (statusLower.includes('kasni') || statusLower.includes('delay')) {
        return 'delayed';
    } else if (statusLower.includes('sletio') || statusLower.includes('arrived') || statusLower.includes('landed')) {
        return 'landed';
    } else if (statusLower.includes('otkazan') || statusLower.includes('cancel')) {
        return 'cancelled';
    } else {
        return 'ontime';
    }
}

// Helper function to translate status to Croatian
function translateStatus(status) {
    if (!status) return 'Nepoznato';

    const statusLower = status.toLowerCase();

    // English to Croatian translations
    if (statusLower.includes('on time')) {
        return 'Na vrijeme';
    } else if (statusLower.includes('delay')) {
        return 'Kasni';
    } else if (statusLower.includes('arrived')) {
        return 'Sletio';
    } else if (statusLower.includes('landed')) {
        return 'Sletio';
    } else if (statusLower.includes('cancel')) {
        return 'Otkazan';
    } else if (statusLower.includes('boarding')) {
        return 'Ukrcavanje';
    } else if (statusLower.includes('departed')) {
        return 'Poletio';
    } else if (statusLower.includes('scheduled')) {
        return 'Planiran';
    } else if (statusLower.includes('expected')) {
        return 'Očekivano';
    }

    // If already in Croatian or unknown status, return as is
    return status;
}

// Helper function to validate email
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Switch between tabs
function switchTab(tabId) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`tab-${tabId}`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-content-${tabId}`).classList.add('active');
}

// Show notification
function showNotification(title, message, type = 'success') {
    // Get template
    const template = document.getElementById('notification-template');
    const notificationNode = template.content.cloneNode(true).firstElementChild;

    // Set content and class
    notificationNode.classList.add(`notification-${type}`);
    notificationNode.querySelector('.notification-title').textContent = title + ': ';
    notificationNode.querySelector('.notification-message').textContent = message;

    // Add to container
    notificationsContainer.appendChild(notificationNode);

    // Add close event
    notificationNode.querySelector('.notification-close').addEventListener('click', () => {
        notificationNode.remove();
    });

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notificationNode.parentNode) {
            notificationNode.remove();
        }
    }, 5000);
}

// Show scraping confirmation dialog
function showScrapingConfirmationDialog() {
    // Get template
    const template = document.getElementById('confirmation-dialog-template');
    const dialogNode = template.content.cloneNode(true).firstElementChild;

    // Set content
    dialogNode.querySelector('.confirmation-dialog-title').textContent = 'Potvrda zaustavljanja prikupljanja podataka';
    dialogNode.querySelector('.confirmation-dialog-message').textContent =
        'Zaustavljanjem prikupljanja podataka, aplikacija više neće automatski osvježavati podatke o letovima. ' +
        'Ovo može pomoći u štednji resursa kada ne koristite aplikaciju aktivno.';

    // Set input label
    dialogNode.querySelector('.confirmation-dialog-label').textContent =
        'Za potvrdu, upišite "STOP" u polje ispod:';

    // Add to body
    document.body.appendChild(dialogNode);

    // Focus the input
    const inputField = dialogNode.querySelector('.confirmation-dialog-input');
    inputField.focus();

    // Add event listeners
    const closeButton = dialogNode.querySelector('.confirmation-dialog-close');
    const cancelButton = dialogNode.querySelector('.confirmation-dialog-cancel');
    const confirmButton = dialogNode.querySelector('.confirmation-dialog-confirm');

    // Close dialog function
    const closeDialog = () => {
        dialogNode.remove();
    };

    // Close button event
    closeButton.addEventListener('click', closeDialog);

    // Cancel button event
    cancelButton.addEventListener('click', closeDialog);

    // Confirm button event
    confirmButton.addEventListener('click', () => {
        const confirmationText = inputField.value.trim();

        if (confirmationText === 'STOP') {
            // Close dialog
            closeDialog();

            // Toggle scraping off
            toggleScraping(false, confirmationText);
        } else {
            // Show error
            inputField.style.borderColor = 'red';
            inputField.style.backgroundColor = 'rgba(255, 0, 0, 0.05)';

            // Shake animation
            inputField.classList.add('shake');
            setTimeout(() => {
                inputField.classList.remove('shake');
            }, 500);
        }
    });

    // Handle Enter key in input
    inputField.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            confirmButton.click();
        }
    });
}

// Toggle scraping on/off
async function toggleScraping(newStatus, confirmation = null) {
    try {
        // Prepare request data
        const requestData = {};

        // Add confirmation if provided
        if (confirmation) {
            requestData.confirmation = confirmation;
        }

        // Make API request
        const response = await fetch('/api/settings/toggle_scraping', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();

        // If requires confirmation, show confirmation dialog
        if (data.requires_confirmation) {
            showScrapingConfirmationDialog();
            return;
        }

        // If successful, update UI
        if (data.success) {
            // Update config
            if (config && config.app_settings) {
                config.app_settings.scraping_enabled = data.scraping_enabled;
            }

            // Update UI
            updateScrapingToggleUI(data.scraping_enabled);

            const statusText = data.scraping_enabled ? 'uključeno' : 'isključeno';
            showNotification('Uspjeh', `Prikupljanje podataka je ${statusText}.`, 'success');

            // If turning on, refresh data
            if (data.scraping_enabled) {
                try {
                    await loadFlightData(true);
                    updateLastRefreshTime();
                    updateNextRefreshTime(data.scraping_enabled);
                } catch (refreshError) {
                    console.error('Greška prilikom osvježavanja podataka:', refreshError);
                }
            }
        } else {
            showNotification('Greška', data.message || 'Došlo je do greške prilikom promjene statusa prikupljanja podataka.', 'error');
        }
    } catch (error) {
        console.error('Greška prilikom promjene statusa prikupljanja podataka:', error);
        showNotification('Greška', 'Došlo je do greške prilikom promjene statusa prikupljanja podataka.', 'error');
    }
}

// Update scraping toggle UI
function updateScrapingToggleUI(isEnabled) {
    // Update status text
    const statusText = document.getElementById('scraping-status-text');
    if (statusText) {
        statusText.textContent = isEnabled ? 'Aktivno' : 'Neaktivno';
        statusText.className = isEnabled ? 'status-active' : 'status-inactive';
    }

    // Update button
    const toggleButton = document.getElementById('toggle-scraping-btn');
    if (toggleButton) {
        if (isEnabled) {
            toggleButton.textContent = 'Zaustavi prikupljanje';
            toggleButton.className = 'btn btn-danger';
            toggleButton.innerHTML = '<i class="fas fa-power-off"></i> Zaustavi prikupljanje';
        } else {
            toggleButton.textContent = 'Pokreni prikupljanje';
            toggleButton.className = 'btn btn-success';
            toggleButton.innerHTML = '<i class="fas fa-play"></i> Pokreni prikupljanje';
        }
    }

    // Update banner visibility
    const banner = document.getElementById('scraping-disabled-banner');
    if (banner) {
        banner.style.display = isEnabled ? 'none' : 'block';
    }

    // Update the enable button in the banner
    const enableButton = document.getElementById('enable-scraping-btn');
    if (enableButton) {
        enableButton.addEventListener('click', () => {
            toggleScraping(true);
        });
    }

    // Update the next refresh time text to indicate scraping status
    updateNextRefreshTime(isEnabled);
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', initApp);