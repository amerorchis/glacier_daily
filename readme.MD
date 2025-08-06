# Glacier Daily Update Emails

[![codecov](https://codecov.io/github/amerorchis/glacier_daily/graph/badge.svg?token=JS85YV7E68)](https://codecov.io/github/amerorchis/glacier_daily) [![Tests](https://github.com/amerorchis/glacier_daily/actions/workflows/tests.yml/badge.svg)](https://github.com/amerorchis/glacier_daily/actions/workflows/tests.yml) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive system that automatically generates and distributes daily email updates about conditions at Glacier National Park. The system aggregates data from multiple sources, processes it, and delivers personalized updates to subscribers through the Drip email platform.

View the result [here.](https://glacier.org/glacier-daily-updates-signup/#iFrame1)

## Features

- Real-time park conditions and updates
- Weather forecasts and alerts
- Trail and road status tracking
- Daily featured peak with satellite imagery
- Sunrise timelapse videos
- Park ranger activity schedules
- Featured product and image of the day
- Automated email delivery

## Prerequisites

- Python 3.9 or higher
- Access to required API keys (see Configuration section)
- FTP access to glacier.org
- Drip email marketing account

## Installation

1. Clone the repository:

```bash
git clone [repository-url]
cd glacier-daily-update
```

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. Create required directories:

```bash
mkdir -p email_images/today/
mkdir -p notices/
```

4. Set up environment variables in `email.env`:

```
NPS=your_nps_api_key
DRIP_TOKEN=your_drip_token
DRIP_ACCOUNT=your_drip_account_id
flickr_key=your_flickr_key
flickr_secret=your_flickr_secret
glaciernps_uid=your_glaciernps_user_id
MAPBOX_TOKEN=your_mapbox_token
BC_TOKEN=your_bigcommerce_token
BC_STORE_HASH=your_store_hash
FTP_USERNAME=your_ftp_username
FTP_PASSWORD=your_ftp_password
```

## Development Environment

### Code Quality and Pre-commit Hooks

This project uses Black for code formatting and pre-commit hooks to maintain code quality.

1. Install pre-commit hooks:

```bash
pre-commit install
```

2. Format code manually with Black:

```bash
black .
```

The pre-commit hooks will automatically run Black formatting and other checks on every commit. If you need to bypass the hooks temporarily, use:

```bash
git commit --no-verify
```

### Running Tests

Run the full test suite with coverage:

```bash
pytest test/ --cov=. --cov-report xml
```

Run specific tests:

```bash
# Test a specific file
pytest test/test_weather.py

# Test a specific module
pytest test/weather/
```

### Development Commands

```bash
# Generate data without sending emails
python generate_and_upload.py

# Run in test mode (test subscribers only)
python main.py --tag "Test Glacier Daily Update"
```

## Usage

### Standard Operation

Run the main script to generate and send daily updates:

```bash
python main.py
```

### Test Mode

To run in test mode (sends only to test subscribers):

```bash
python main.py --tag "Test Glacier Daily Update"
```

## Organization

### Modules

- **activities/**: Manages ranger activities and events

  - Fetches from NPS API
  - Processes GNPC events and conversations
  - Formats event schedules
- **weather/**: Comprehensive weather information

  - Forecasts from Open-Meteo API
  - Air quality monitoring
  - Aurora forecasts from NOAA
  - Weather alerts from NWS
  - Interactive park weather map generation
- **roads/**: Road status tracking

  - Real-time closure information
  - Hiker/biker access updates
  - Location-based status reporting
- **trails_and_cgs/**: Trail and campground monitoring

  - Trail closure tracking
  - Campground availability
  - Condition reports
- **drip/**: Email delivery system

  - Subscriber management
  - Email template handling
  - Delivery scheduling
  - Subscription updates
- **image_otd/**: Daily image selection and processing

  - Integration with Flickr API
  - Image resizing and optimization
- **peak/**: Daily peak feature

  - Random peak selection
  - Satellite imagery from Mapbox
  - Location mapping
- **product_otd/**: Daily product showcase

  - BigCommerce integration
  - Product information formatting
- **sunrise_timelapse/**: Sunrise video processing

  - Timelapse compilation
  - Thumbnail generation
  - FTP upload management
- **shared/**: Utility functions

  - FTP operations
  - JSON handling
  - Retry mechanisms

## Data Flow

1. Data Collection:

   - Multiple API endpoints queried concurrently
   - Real-time information gathered
   - Images and videos processed
2. Data Processing:

   - Information formatted for email
   - Images resized and optimized
   - Content sanitized and validated
3. Distribution:

   - Content uploaded to FTP server
   - JSON data prepared for Drip
   - Emails triggered through Drip API

## Credits

Made by Andrew Smith for the Glacier National Park Conservancy, 2023.
