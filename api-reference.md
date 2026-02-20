# Glacier Daily Update: API and Data Sources Reference

## National Park Service (NPS) APIs

### NPS Events API

- Endpoint: `developer.nps.gov/api/v1/events`
- Purpose: Ranger program schedules
- Authentication: NPS API key required

### NPS Carto APIs

Multiple endpoints on `carto.nps.gov`:

- Road closures: `glaclive/api/v2/sql/glac_road_nds`
- Hiker/biker closures: `glaclive/api/v2/sql/glac_hiker_biker_closures`
- Winter recreation closures: `glaclive/api/v2/sql/winter_rec_closure`
- Trail status: `glaclive/api/v2/sql/nps_trails`
- Frontcountry campgrounds: `glaclive/api/v2/sql/glac_front_country_campgrounds`

### NPS Air Quality API

- Endpoint: `www.nps.gov/featurecontent/ard/currentdata/json/glac.json`
- Purpose: Air quality index data
- Authentication: None required

## Weather APIs

### Open-Meteo API

- Endpoint: `api.open-meteo.com/v1/forecast`
- Purpose: Weather forecasts for multiple park locations
- Authentication: None required

### National Weather Service API

- Endpoint: `api.weather.gov/alerts/active/area/MT`
- Purpose: Weather alerts
- Authentication: None required

### NOAA Space Weather API

- Endpoint: `services.swpc.noaa.gov/text/3-day-forecast.txt`
- Purpose: Aurora forecasts
- Authentication: None required

### Sunset Hue API

- Endpoint: `api.sunsethue.com/event`
- Purpose: Sunset quality predictions
- Authentication: API key required

## Image and Media APIs

### Flickr API

- Purpose: Access to GlacierNPS Flickr account
- Authentication:
  - API key and secret required
  - GlacierNPS UID required

### Mapbox API

- Purpose: Satellite imagery for peaks
- Features: Custom style support
- Authentication: Mapbox token required

## E-commerce and Marketing

### BigCommerce API

- Endpoint: `api.bigcommerce.com/stores/{store_hash}/v3/catalog/products`
- Purpose: Product information
- Authentication: BC_TOKEN and BC_STORE_HASH required

### Drip Email API

- Endpoint: `api.getdrip.com/v2/`
- Purpose:
  - Subscriber management
  - Email delivery
- Authentication: DRIP_TOKEN and DRIP_ACCOUNT required

## File Storage

### Main FTP Server

- Host: glacier.org
- Purpose:
  - Image storage
  - Web content hosting
- Authentication: FTP credentials required

## Google Services

### Google Sheets API

- Purpose: Notices/announcements
- Authentication: Service account credentials required
- Configuration: Accesses spreadsheet ID designated in email.env

## Local Data Sources

### CSV Files

- Location: `peak/PeaksCSV.csv`
- Purpose: Peak information for random selection

### JSON Files

- Weather codes: `weather/descriptions.json`
- Cached data: `server/email.json`

## Required Environment Variables

```bash
# NPS
NPS=your_nps_api_key

# Drip Email
DRIP_TOKEN=your_drip_token
DRIP_ACCOUNT=your_drip_account_id

# Flickr
flickr_key=your_flickr_key
flickr_secret=your_flickr_secret
glaciernps_uid=your_glaciernps_user_id

# Mapbox
MAPBOX_TOKEN=your_mapbox_token
MAPBOX_ACCOUNT=your_mapbox_account  # optional
MAPBOX_STYLE=your_mapbox_style      # optional

# BigCommerce
BC_TOKEN=your_bigcommerce_token
BC_STORE_HASH=your_store_hash

# Main FTP
FTP_USERNAME=your_ftp_username
FTP_PASSWORD=your_ftp_password

# Google Services
GOOGLE_APPLICATION_CREDENTIALS=path/to/service_account.json
NOTICES_SPREADSHEET_ID=your_spreadsheet_id

# Cloudflare Cache (optional)
CACHE_PURGE=your_cloudflare_api_key
ZONE_ID=your_cloudflare_zone_id

# Other
SUNSETHUE_KEY=your_sunsethue_key
ENVIRONMENT=development  # "development" or "production"
```
