# Glacier Daily Update Emails

[![codecov](https://codecov.io/github/amerorchis/glacier_daily/graph/badge.svg?token=JS85YV7E68)](https://codecov.io/github/amerorchis/glacier_daily) [![Tests](https://github.com/amerorchis/glacier_daily/actions/workflows/tests.yml/badge.svg)](https://github.com/amerorchis/glacier_daily/actions/workflows/tests.yml) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

An automated system that generates and distributes daily email updates about conditions at Glacier National Park. The system aggregates data from multiple sources and delivers personalized updates to subscribers through the Drip email platform.

**View the live emails [here](https://glacier.org/glacier-daily-updates-signup/#iFrame1).**

## Features

- Real-time park conditions and updates
- Weather forecasts, alerts, and air quality
- Trail and road status tracking
- Daily featured peak with satellite imagery
- Sunrise timelapse videos
- Ranger-led activity schedules
- Featured product and image of the day

## Quick Start (For Users)

### Prerequisites
- Python 3.9
- [uv](https://docs.astral.sh/uv/) package manager
- API keys and FTP access (see Configuration)

### Installation
```bash
# Clone and setup
git clone [repository-url]
cd glacier-daily
uv sync

# Create required directories
mkdir -p email_images/today/
mkdir -p notices/

# Configure environment variables in email.env (see Configuration section)
```

### Usage
```bash
# Run daily update (production)
uv run python main.py

# Run in test mode (test subscribers only)
uv run python main.py --tag "Test Glacier Daily Update"

# Force re-fetch all data (clear cache)
uv run python main.py --force

# Generate data without sending emails
uv run python generate_and_upload.py
```

### Configuration

Create `email.env` with your API keys and credentials. Use `TEMPLATE.env` as a reference for all required environment variables:

```bash
# Copy template and add your credentials
cp TEMPLATE.env email.env
# Edit email.env with your actual API keys and credentials
```

---

## Contributing & Development

### Development Setup

1. **Install development dependencies:**
   ```bash
   uv sync --extra dev
   ```

2. **Install pre-commit hooks:**
   ```bash
   uv run pre-commit install
   ```

3. **Set up Google Sheets API:**
   - Create Google service account JSON and update file location.

### Code Quality

This project uses automated code formatting and quality checks:

- **Ruff** for Python code formatting, linting, and import sorting
- **ty** for type checking
- **Pre-commit hooks** for automated checks

```bash
# Format code manually
uv run ruff format .

# Run all quality checks
uv run pre-commit run --all-files
```

### Testing

Tests automatically use `TEMPLATE.env` (with empty API keys) to ensure no real credentials are needed:

```bash
# Run full test suite with coverage
uv run pytest test/ --cov=. --cov-report xml

# Run specific tests
uv run pytest test/weather/test_weather.py
uv run pytest test/weather/
```

### Running Individual Modules

With the package structure, run modules as:
```bash
# Run specific module
uv run python -m peak.peak
uv run python -m weather.weather

# Suppress urllib3 SSL warnings on macOS (harmless)
uv run python -W ignore -m peak.peak
```

### Architecture Overview

**Data Collection:** Uses `ThreadPoolExecutor` to gather data from multiple APIs concurrently.

**Core Modules:**
- `weather/` - Weather forecasts, alerts, air quality, aurora predictions
- `activities/` - Park ranger events from NPS and GNPC
- `roads/` - Road closures and hiker/biker access
- `trails_and_cgs/` - Trail closures and campground availability
- `peak/` - Daily featured peak with satellite imagery
- `image_otd/` - Daily image selection from Flickr
- `product_otd/` - Featured product from BigCommerce
- `sunrise_timelapse/` - Video processing and timelapse compilation
- `notices/` - Administrative notices from Google Sheets
- `drip/` - Email delivery and subscriber management
- `shared/` - FTP operations, retry mechanisms, centralized settings, config validation, logging, LKG fallback cache, utilities
- `server/` - PHP templates and web interface components
- `frontend_files/` - JavaScript and PHP for the web interface

**Data Flow:**
1. **Collection**: Concurrent API calls gather real-time data
2. **Processing**: Format data for HTML email templates
3. **Distribution**: Upload to glacier.org via FTP and trigger emails through Drip

### Error Handling & Data Reliability

The system uses a custom retry decorator (`shared/retry.py`) with exponential backoff for API calls. When a module fails despite retries, a Last Known Good (LKG) cache (`shared/lkg_cache.py`) provides today's most recent successful output as a fallback, so subscribers receive an email with stale-but-valid data rather than missing sections. Date-deterministic modules (peak, image of the day, product) are cached after first successful fetch each day; dynamic modules (weather, roads, trails, etc.) always attempt a fresh fetch with LKG as a safety net.

---

## Credits

Made by Andrew Smith for the Glacier National Park Conservancy, 2023.
