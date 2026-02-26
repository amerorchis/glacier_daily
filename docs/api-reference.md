# Glacier Daily Update: API and Data Sources Reference

## National Park Service (NPS) APIs

### NPS Events API

- Endpoint: `https://developer.nps.gov/api/v1/events`
- Module: `activities/events.py`
- Purpose: Ranger program schedules
- Authentication: NPS API key required (`X-Api-Key` header)

### NPS Carto GeoJSON API

All endpoints query `https://carto.nps.gov/user/glaclive/api/v2/sql` with table names passed as SQL query parameters (e.g., `?format=GeoJSON&q=SELECT * FROM table_name WHERE ...`). No authentication required. SSL verification is disabled due to certificate chain issues on some platforms.

Tables queried:
- `glac_road_nds` — Road segments, open/closed status. Module: `roads/roads.py`
- `glac_hiker_biker_closures` — Hiker/biker closures. Module: `roads/hiker_biker.py`
- `winter_rec_closure` — Winter recreation closures. Module: `roads/hiker_biker.py`
- `nps_trails` — Trail closures. Module: `trails_and_cgs/trails.py`
- `glac_front_country_campgrounds` — Campground status (uses `format=JSON`). Module: `trails_and_cgs/frontcountry_cgs.py`

### NPS Air Quality API

- Endpoint: `https://www.nps.gov/featurecontent/ard/currentdata/json/glac.json`
- Module: `weather/weather_aqi.py`
- Purpose: Air quality index data
- Authentication: None required (uses browser-like User-Agent header)

## Weather APIs

### Open-Meteo API

- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Module: `weather/forecast.py`
- Purpose: Weather forecasts for multiple park locations
- Authentication: None required

### National Weather Service API

- Endpoint: `https://api.weather.gov/alerts/active/area/MT`
- Module: `weather/weather_alerts.py`
- Purpose: Weather alerts, filtered to Glacier-area zones (MTZ301, MTZ302, MTC029, MTC035, MTZ002, MTZ003, MTZ105)
- Authentication: None required

### NOAA Space Weather API

- Endpoint: `https://services.swpc.noaa.gov/text/3-day-forecast.txt`
- Module: `weather/night_sky.py`
- Purpose: Aurora/Kp index forecasts
- Authentication: None required

### Sunset Hue API

- Endpoint: `https://api.sunsethue.com/event`
- Module: `weather/sunset_hue.py`
- Purpose: Sunset quality predictions
- Authentication: API key required (`x-api-key` header)

## Image and Media APIs

### Flickr API

- Library: `flickrapi` Python package (wraps `api.flickr.com`)
- Module: `image_otd/flickr.py`
- Methods used: `photos.search`, `photos.getSizes`
- Purpose: Daily image selection from GlacierNPS Flickr account
- Authentication: API key, secret, and GlacierNPS UID required

### Mapbox API

- Endpoint: `https://api.mapbox.com/styles/v1/{account}/{style}/static/{lon},{lat},{zoom},{bearing}/{dimensions}`
- Module: `peak/sat.py`
- Purpose: Satellite imagery for daily featured peak
- Authentication: Mapbox token required

## E-commerce and Marketing

### BigCommerce API

- Endpoints:
  - Products: `https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products`
  - Product images: `https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products/{id}/images`
- Module: `product_otd/product.py`
- Purpose: Featured product information and images
- Authentication: `BC_TOKEN` (`X-Auth-Token` header) and `BC_STORE_HASH` required

### Drip Email API

- Base: `https://api.getdrip.com/v2/{account_id}/`
- Module: `drip/drip_actions.py`, `drip/subscriber_list.py`, `drip/update_subscriber.py`
- Endpoints used:
  - `events` — Record single subscriber events
  - `events/batches` — Bulk workflow triggers for email delivery
  - `workflows/{campaign_id}/subscribers` — Send to campaign
  - `subscribers` — List and update subscribers
- Authentication: Bearer token (`DRIP_TOKEN`)

## Infrastructure APIs

### Cloudflare Cache Purge API

- Endpoint: `https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache`
- Module: `generate_and_upload.py`
- Purpose: Purge CDN cache after uploading new data
- Authentication: Bearer token (`CACHE_PURGE`)

### Gmail IMAP (Canary Verification)

- Host: `imap.gmail.com:993`
- Module: `drip/canary_check.py`
- Purpose: End-to-end email delivery verification by checking a Gmail mailbox via IMAP
- Authentication: `CANARY_EMAIL` and `CANARY_IMAP_PASSWORD` (Gmail app-specific password)

### Main FTP Server

- Host: `ftp.glacier.org` (configurable via `FTP_SERVER`)
- Module: `shared/ftp.py`
- Purpose: Image storage and web content hosting (JSON data, HTML templates)
- Authentication: FTP credentials required

## Web Scraping

### GNPC Event Listings

- URLs:
  - `https://glacier.org/glacier-conversations`
  - `https://glacier.org/glacier-book-club`
- Module: `activities/gnpc_events.py`
- Purpose: Glacier National Park Conservancy event schedules (conversations, book clubs)
- Authentication: None (HTML scraping)

### Glacier Conservancy Timelapse

- Endpoints:
  - `http://timelapse.glacierconservancy.org/daily_timelapse_data.json`
  - `http://timelapse.glacierconservancy.org/sunrise_thumbnails.json`
- Module: `sunrise_timelapse/get_timelapse.py`
- Purpose: Timelapse video data and thumbnail images
- Authentication: None

### Cache Refresh Endpoint

- URL: `https://api.glacierconservancy.org/email.json`
- Module: `generate_and_upload.py`
- Purpose: Hit CDN endpoint to warm cache after uploading new data
- Authentication: None

## Google Services

### Google Sheets API

- Library: `gspread` Python package
- Module: `notices/notices.py`
- Purpose: Administrative notices and announcements
- Authentication: Service account credentials (`GOOGLE_APPLICATION_CREDENTIALS` JSON file) and spreadsheet ID (`NOTICES_SPREADSHEET_ID`)

## Offline Data Generation

### Wikipedia API

- Endpoint: `https://en.wikipedia.org/w/api.php`
- Module: `peak/fetch_wikipedia.py`
- Purpose: Fetch Wikipedia article summaries for peaks (offline script, generates `peak/peaks_wikipedia.json`)
- Authentication: None

## Local Data Sources

### CSV Files

- `peak/PeaksCSV.csv` — Peak information for daily selection

### JSON Files

- `weather/descriptions.json` — Weather code descriptions
- `peak/peaks_wikipedia.json` — Pre-fetched Wikipedia summaries for peaks
- `server/email.json` — Cached email data (generated at runtime)

## Environment Variables

All environment variables are defined in `email.env` and accessed through the centralized `Settings` dataclass in `shared/settings.py`. Modules use `get_settings()` instead of reading `os.environ` directly.

### Required (app exits at startup if missing)

```bash
NPS=your_nps_api_key
DRIP_TOKEN=your_drip_token
DRIP_ACCOUNT=your_drip_account_id
FTP_USERNAME=your_ftp_username
FTP_PASSWORD=your_ftp_password
MAPBOX_TOKEN=your_mapbox_token
```

### Service Keys (default to empty string; modules degrade gracefully if missing)

```bash
flickr_key=your_flickr_key
flickr_secret=your_flickr_secret
glaciernps_uid=your_glaciernps_user_id
BC_TOKEN=your_bigcommerce_token
BC_STORE_HASH=your_store_hash
SUNSETHUE_KEY=your_sunsethue_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/service_account.json
NOTICES_SPREADSHEET_ID=your_spreadsheet_id
```

### Optional with Defaults

```bash
MAPBOX_ACCOUNT=mapbox                  # default: "mapbox"
MAPBOX_STYLE=satellite-streets-v12     # default: "satellite-streets-v12"
FTP_SERVER=ftp.glacier.org             # default: "ftp.glacier.org"
ENVIRONMENT=development                # default: "development"
DRIP_CAMPAIGN_ID=169298893             # default: "169298893"
```

### Optional Cloudflare (default to empty string)

```bash
CACHE_PURGE=your_cloudflare_api_key
ZONE_ID=your_cloudflare_zone_id
```

### Optional Canary Email Verification (default to empty string)

```bash
CANARY_EMAIL=your_canary@gmail.com           # Gmail address for delivery verification
CANARY_IMAP_PASSWORD=xxxx-xxxx-xxxx-xxxx     # Gmail app-specific password
```
