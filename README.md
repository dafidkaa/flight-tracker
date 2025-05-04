# Zagreb Airport Flight Tracker

## Overview / Pregled

### English
A comprehensive flight tracking system for Zagreb Airport arrivals that monitors flight status updates every 5 minutes and sends email notifications in Croatian. The system allows users to track up to 20 flights, manage email recipients, and receive notifications about status changes, delays, gate changes, and arrivals.

### Hrvatski
Sveobuhvatni sustav za praćenje dolaznih letova Zračne luke Zagreb koji provjerava ažuriranja statusa letova svakih 5 minuta i šalje e-mail obavijesti na hrvatskom jeziku. Sustav omogućuje korisnicima praćenje do 20 letova, upravljanje primateljima e-pošte i primanje obavijesti o promjenama statusa, kašnjenjima, promjenama izlaza i dolascima.

## Features / Značajke

### English
- Real-time monitoring of Zagreb Airport arrivals
- Track up to 20 flight numbers simultaneously
- Email notifications for flight status changes, delays, gate changes, and arrivals
- User-friendly web interface in Croatian language
- Responsive design for desktop and mobile devices
- Configurable notification settings
- Automatic data refresh every 5 minutes

### Hrvatski
- Praćenje dolazaka na Zračnu luku Zagreb u stvarnom vremenu
- Istovremeno praćenje do 20 brojeva letova
- E-mail obavijesti o promjenama statusa leta, kašnjenjima, promjenama izlaza i dolascima
- Korisničko sučelje na hrvatskom jeziku
- Responzivni dizajn za desktop i mobilne uređaje
- Prilagodljive postavke obavijesti
- Automatsko osvježavanje podataka svakih 5 minuta

## System Architecture / Arhitektura sustava

### English
The system consists of the following components:

1. **Frontend**: HTML, CSS, and JavaScript web interface that allows users to interact with the system
2. **Backend API**: Flask-based REST API that handles requests from the frontend
3. **Scraper**: Python module that fetches flight data from the Zagreb Airport website
4. **Scheduler**: Background service that periodically checks for flight updates
5. **Email Service**: Module that sends email notifications when flight status changes are detected
6. **Configuration**: JSON-based configuration system for storing user preferences

### Hrvatski
Sustav se sastoji od sljedećih komponenti:

1. **Frontend**: HTML, CSS i JavaScript web sučelje koje omogućuje korisnicima interakciju sa sustavom
2. **Backend API**: REST API baziran na Flask-u koji obrađuje zahtjeve s frontenda
3. **Scraper**: Python modul koji dohvaća podatke o letovima s web stranice Zračne luke Zagreb
4. **Scheduler**: Pozadinski servis koji periodički provjerava ažuriranja letova
5. **Email Service**: Modul koji šalje e-mail obavijesti kada se otkriju promjene statusa leta
6. **Konfiguracija**: Sustav konfiguracije baziran na JSON-u za pohranu korisničkih postavki

## Installation / Instalacija

### English
#### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Internet connection to access Zagreb Airport website
- Resend.com account for email notifications

#### Local Development
1. Clone the repository:
   ```
   git clone https://github.com/lemonmedia/zagreb-airport-flight-tracker.git
   cd zagreb-airport-flight-tracker
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure email settings:
   - Open `config.json`
   - Update the `email_settings` section with your email service details

5. Start the application:
   ```
   cd app
   python app.py
   ```

6. Access the web interface:
   - Open your browser and navigate to `http://localhost:5000`

#### Vercel Deployment
This application is configured to be deployed on Vercel as a serverless application.

1. **Prerequisites**
   - A Vercel account
   - Vercel CLI installed (optional, for local testing)

2. **Deployment Steps**
   - Option 1: Using Vercel CLI
     ```bash
     npm install -g vercel  # Install Vercel CLI
     vercel login           # Login to Vercel
     vercel                 # Deploy the application
     ```

   - Option 2: Using Vercel Dashboard
     - Push your code to a GitHub repository
     - Log in to your Vercel dashboard
     - Click "New Project"
     - Import your GitHub repository
     - Configure the project settings
     - Click "Deploy"

3. **Environment Variables**
   Set the following environment variables in your Vercel project settings:
   - `RESEND_API_KEY`: Your Resend API key for sending emails

4. **Notes on Vercel Deployment**
   - The application uses `/tmp` directory for temporary file storage on Vercel
   - Background tasks are not supported in serverless environments, so automatic data updates will be triggered by API calls
   - Configuration is stored in the `/tmp` directory and will be reset periodically by Vercel

### Hrvatski
#### Preduvjeti
- Python 3.8 ili noviji
- pip (Python upravitelj paketa)
- Internet veza za pristup web stranici Zračne luke Zagreb
- Resend.com račun za e-mail obavijesti

#### Lokalni razvoj
1. Klonirajte repozitorij:
   ```
   git clone https://github.com/lemonmedia/zagreb-airport-flight-tracker.git
   cd zagreb-airport-flight-tracker
   ```

2. Stvorite virtualno okruženje:
   ```
   python -m venv venv
   source venv/bin/activate  # Na Windowsu: venv\Scripts\activate
   ```

3. Instalirajte ovisnosti:
   ```
   pip install -r requirements.txt
   ```

4. Konfigurirajte postavke e-pošte:
   - Otvorite `config.json`
   - Ažurirajte odjeljak `email_settings` s podacima vašeg servisa za e-poštu

5. Pokrenite aplikaciju:
   ```
   cd app
   python app.py
   ```

6. Pristupite web sučelju:
   - Otvorite preglednik i navigirajte do `http://localhost:5000`

#### Vercel Deployment
Ova aplikacija je konfigurirana za implementaciju na Vercel kao serverless aplikacija.

1. **Preduvjeti**
   - Vercel račun
   - Vercel CLI instaliran (opcionalno, za lokalno testiranje)

2. **Koraci za implementaciju**
   - Opcija 1: Korištenje Vercel CLI
     ```bash
     npm install -g vercel  # Instalirajte Vercel CLI
     vercel login           # Prijavite se na Vercel
     vercel                 # Implementirajte aplikaciju
     ```

   - Opcija 2: Korištenje Vercel nadzorne ploče
     - Pošaljite svoj kod na GitHub repozitorij
     - Prijavite se na Vercel nadzornu ploču
     - Kliknite "New Project"
     - Uvezite svoj GitHub repozitorij
     - Konfigurirajte postavke projekta
     - Kliknite "Deploy"

3. **Varijable okruženja**
   Postavite sljedeće varijable okruženja u postavkama vašeg Vercel projekta:
   - `RESEND_API_KEY`: Vaš Resend API ključ za slanje e-pošte

4. **Napomene o Vercel implementaciji**
   - Aplikacija koristi `/tmp` direktorij za privremenu pohranu datoteka na Vercel
   - Pozadinski zadaci nisu podržani u serverless okruženjima, pa će automatska ažuriranja podataka biti pokrenuta API pozivima
   - Konfiguracija se pohranjuje u `/tmp` direktoriju i bit će periodički resetirana od strane Vercel

## Usage Guide / Vodič za korištenje

### English
#### Tracking Flights
1. Navigate to the main page
2. View current arrivals in the "Current Flights" table
3. Click "Track" button next to a flight you want to monitor
4. Alternatively, enter a flight number manually in the "Add new flight to track" form

#### Managing Email Recipients
1. Go to the "Email Notifications" section
2. View current recipients in the list
3. Add new recipients using the form
4. Remove recipients by clicking the "Remove" button next to their email

#### Configuring Notifications
1. Go to the "Notification Settings" section
2. Check/uncheck the types of notifications you want to receive
3. Click "Save Settings" to apply changes

### Hrvatski
#### Praćenje letova
1. Navigirajte do glavne stranice
2. Pregledajte trenutne dolaske u tablici "Trenutni letovi"
3. Kliknite gumb "Prati" pored leta koji želite pratiti
4. Alternativno, unesite broj leta ručno u obrazac "Dodaj novi let za praćenje"

#### Upravljanje primateljima e-pošte
1. Idite na odjeljak "E-mail obavijesti"
2. Pregledajte trenutne primatelje na popisu
3. Dodajte nove primatelje pomoću obrasca
4. Uklonite primatelje klikom na gumb "Ukloni" pored njihove e-mail adrese

#### Konfiguriranje obavijesti
1. Idite na odjeljak "Postavke obavijesti"
2. Označite/odznačite vrste obavijesti koje želite primati
3. Kliknite "Spremi postavke" za primjenu promjena

## API Documentation / API dokumentacija

### English
The system provides the following API endpoints:

#### Flight Data
- `GET /api/flights` - Get all flight data
- `GET /api/flights/tracked` - Get data for tracked flights only

#### Flight Tracking
- `POST /api/flights/track` - Track a new flight
  - Body: `{ "flight_number": "XX 123" }`
- `POST /api/flights/untrack` - Stop tracking a flight
  - Body: `{ "flight_number": "XX 123" }`

#### Email Management
- `POST /api/email/add` - Add a new email recipient
  - Body: `{ "email": "example@example.com" }`
- `POST /api/email/remove` - Remove an email recipient
  - Body: `{ "email": "example@example.com" }`

#### Settings
- `GET /api/config` - Get current configuration
- `POST /api/settings/notifications` - Update notification settings
  - Body: `{ "notification_events": { "status_change": true, "delay": true, "gate_change": true, "arrival": true } }`
- `POST /api/settings/email` - Update email settings
- `POST /api/settings/app` - Update application settings

#### Data Refresh
- `POST /api/refresh` - Manually refresh flight data

### Hrvatski
Sustav pruža sljedeće API krajnje točke:

#### Podaci o letovima
- `GET /api/flights` - Dohvati sve podatke o letovima
- `GET /api/flights/tracked` - Dohvati podatke samo za praćene letove

#### Praćenje letova
- `POST /api/flights/track` - Prati novi let
  - Tijelo: `{ "flight_number": "XX 123" }`
- `POST /api/flights/untrack` - Prestani pratiti let
  - Tijelo: `{ "flight_number": "XX 123" }`

#### Upravljanje e-poštom
- `POST /api/email/add` - Dodaj novog primatelja e-pošte
  - Tijelo: `{ "email": "primjer@primjer.com" }`
- `POST /api/email/remove` - Ukloni primatelja e-pošte
  - Tijelo: `{ "email": "primjer@primjer.com" }`

#### Postavke
- `GET /api/config` - Dohvati trenutnu konfiguraciju
- `POST /api/settings/notifications` - Ažuriraj postavke obavijesti
  - Tijelo: `{ "notification_events": { "status_change": true, "delay": true, "gate_change": true, "arrival": true } }`
- `POST /api/settings/email` - Ažuriraj postavke e-pošte
- `POST /api/settings/app` - Ažuriraj postavke aplikacije

#### Osvježavanje podataka
- `POST /api/refresh` - Ručno osvježi podatke o letovima

## Project Structure / Struktura projekta

```
flight_tracker/
├── app/                         # Main application code
│   ├── static/                  # Frontend assets
│   │   ├── css/                 # CSS stylesheets
│   │   │   └── style.css        # Main stylesheet
│   │   ├── js/                  # JavaScript files
│   │   │   └── app.js           # Main frontend logic
│   │   └── images/              # Image assets
│   ├── templates/               # HTML templates
│   │   ├── index.html           # Main page template
│   │   └── email_notification.html # Email template
│   ├── data/                    # Data storage
│   │   ├── current_data.json    # Current flight data
│   │   └── previous_data.json   # Previous flight data
│   ├── app.py                   # Flask application and API endpoints
│   ├── scraper.py               # Zagreb Airport web scraper
│   ├── email_service.py         # Email notification service
│   ├── scheduler.py             # Background task scheduler
│   ├── main.py                  # Main entry point
│   └── logging_config.py        # Logging configuration
├── config.json                  # Application configuration
└── logs/                        # Application logs
    ├── main.log                 # Main application log
    ├── scraper.log              # Scraper log
    ├── scheduler.log            # Scheduler log
    └── email.log                # Email service log
```

## Troubleshooting / Rješavanje problema

### English
#### Common Issues
1. **No flight data appears**
   - Check your internet connection
   - Verify that the Zagreb Airport website is accessible
   - Check the scraper logs for errors

2. **Email notifications not being sent**
   - Verify your SMTP server settings in `config.json`
   - Check if your email provider allows sending through SMTP
   - Review the email service logs for errors

3. **Application crashes on startup**
   - Ensure all dependencies are installed
   - Check if the required ports are available
   - Review the main application log for errors

#### Logs
Log files are stored in the `logs/` directory and can be used to diagnose issues:
- `main.log` - General application logs
- `scraper.log` - Web scraping related logs
- `scheduler.log` - Scheduler related logs
- `email.log` - Email service related logs

### Hrvatski
#### Česti problemi
1. **Ne pojavljuju se podaci o letovima**
   - Provjerite vašu internet vezu
   - Provjerite je li web stranica Zračne luke Zagreb dostupna
   - Provjerite log datoteke scraper-a za greške

2. **E-mail obavijesti se ne šalju**
   - Provjerite postavke SMTP poslužitelja u `config.json`
   - Provjerite dopušta li vaš pružatelj e-pošte slanje putem SMTP-a
   - Pregledajte log datoteke email servisa za greške

3. **Aplikacija se ruši pri pokretanju**
   - Provjerite jesu li sve ovisnosti instalirane
   - Provjerite jesu li potrebni portovi dostupni
   - Pregledajte glavnu log datoteku aplikacije za greške

#### Log datoteke
Log datoteke pohranjene su u direktoriju `logs/` i mogu se koristiti za dijagnosticiranje problema:
- `main.log` - Opći logovi aplikacije
- `scraper.log` - Logovi vezani uz web scraping
- `scheduler.log` - Logovi vezani uz scheduler
- `email.log` - Logovi vezani uz email servis

## Limitations and Future Improvements / Ograničenja i buduća poboljšanja

### English
#### Current Limitations
- Maximum of 20 tracked flights
- Only supports Zagreb Airport arrivals (not departures)
- Relies on the structure of the Zagreb Airport website (may break if they change their layout)
- Email is the only notification method

#### Future Improvements
- Add support for departure flights
- Implement SMS notifications
- Create a mobile application
- Add multi-language support
- Implement user accounts for personalized tracking
- Add historical flight data analysis

### Hrvatski
#### Trenutna ograničenja
- Maksimalno 20 praćenih letova
- Podržava samo dolaske na Zračnu luku Zagreb (ne odlaske)
- Oslanja se na strukturu web stranice Zračne luke Zagreb (može prestati raditi ako promijene izgled)
- E-mail je jedina metoda obavještavanja

#### Buduća poboljšanja
- Dodavanje podrške za odlazne letove
- Implementacija SMS obavijesti
- Izrada mobilne aplikacije
- Dodavanje podrške za više jezika
- Implementacija korisničkih računa za personalizirano praćenje
- Dodavanje analize povijesnih podataka o letovima

## License / Licenca

### English
This project is licensed under the MIT License - see the LICENSE file for details.

### Hrvatski
Ovaj projekt je licenciran pod MIT licencom - pogledajte datoteku LICENSE za detalje.