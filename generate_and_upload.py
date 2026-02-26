#!/home/pi/.local/bin/uv run --python 3.11 python
"""
Generate all of the data with a ThreadPoolExecutor, then upload it to the glacier.org
server with FTP.
"""

import concurrent.futures
import json
import os
from dataclasses import asdict
from time import sleep

import requests

from activities.events import events_today
from activities.gnpc_events import get_gnpc_events
from image_otd.image_otd import get_image_otd, prepare_pic_otd
from notices.notices import get_notices
from peak.peak import peak
from peak.sat import prepare_peak_upload
from product_otd.product import get_product, prepare_potd_upload
from roads.hiker_biker import get_hiker_biker_status
from roads.roads import get_road_status
from shared.data_types import (
    CampgroundsResult,
    EventsResult,
    HikerBikerResult,
    NoticesResult,
    RoadsResult,
    TrailsResult,
    WeatherResult,
)
from shared.datetime_utils import (
    cross_platform_strftime,
    format_date_readable,
    now_mountain,
)
from shared.ftp import FTPSession, upload_file
from shared.lkg_cache import LKGCache
from shared.logging_config import get_logger
from shared.settings import get_settings
from shared.timing import timed
from sunrise_timelapse.get_timelapse import process_video
from trails_and_cgs.frontcountry_cgs import get_campground_status
from trails_and_cgs.trails import get_closed_trails
from weather.weather import weather_data
from weather.weather_img import prepare_weather_upload, weather_image
from web_version import web_version

logger = get_logger(__name__)


# Date-deterministic: checked BEFORE API call, skip if cached today
CACHED_MODULE_KEYS = {
    "peak": ["peak", "peak_image", "peak_map"],
    "image_otd": ["image_otd", "image_otd_title", "image_otd_link"],
    "product": ["product_title", "product_image", "product_link", "product_desc"],
}

# Dynamic: always fetch fresh, LKG used only as fallback on failure
FALLBACK_MODULE_KEYS = {
    "weather": ["weather", "weather_image"],
    "trails": ["trails"],
    "campgrounds": ["campgrounds"],
    "roads": ["roads"],
    "hiker_biker": ["hikerbiker"],
    "events": ["events"],
    "notices": ["notices"],
    "sunrise": ["sunrise_vid", "sunrise_still", "sunrise_str"],
}

_ALL_MODULE_KEYS = {**CACHED_MODULE_KEYS, **FALLBACK_MODULE_KEYS}

# Maps pending_upload field keys to their LKG module name
_FIELD_TO_MODULE = {
    "image_otd": "image_otd",
    "peak_image": "peak",
    "product_image": "product",
    "weather_image": "weather",
}


def _save_module_lkg(module_name, data):
    """Save successful module output to LKG cache.

    Dataclass values are serialized to JSON strings for storage.
    """
    try:
        cache = LKGCache.get_cache()
        serialized = {}
        for k, v in data.items():
            if not v:
                continue
            if hasattr(v, "__dataclass_fields__"):
                serialized[k] = json.dumps(_serialize_value(v))
            elif isinstance(v, str):
                serialized[k] = v
            else:
                serialized[k] = str(v)
        if serialized:
            cache.save(module_name, serialized)
    except Exception:
        logger.debug("Failed to save LKG for %s", module_name, exc_info=True)


def _load_module_lkg(module_name, keys):
    """Load today's LKG data for a module, or None."""
    try:
        return LKGCache.get_cache().load(module_name, keys)
    except Exception:
        logger.debug("Failed to load LKG for %s", module_name, exc_info=True)
        return None


def _submit_timed(executor, name, func, *args, **kwargs):
    """Submit a function to the executor with timing instrumentation."""

    @timed(name)
    def wrapped():
        return func(*args, **kwargs)

    return executor.submit(wrapped)


def _safe_result(future, name, default, lkg_keys=None):
    """Safely get a future's result, falling back to LKG then default."""
    try:
        return future.result()
    except Exception as e:
        logger.error("Module '%s' failed: %s", name, e, exc_info=True)
        if lkg_keys:
            lkg_data = _load_module_lkg(name, lkg_keys)
            if lkg_data:
                logger.info("Using LKG fallback for '%s'", name)
                if len(lkg_keys) == 1:
                    return lkg_data[lkg_keys[0]]
                return tuple(lkg_data.get(k, "") for k in lkg_keys)
        return default


def gen_data() -> tuple[dict, list]:
    """
    Use threads to gather the data from every module, then store it in a dictionary.
    Make sure text is all HTML safe, then return it.

    Date-deterministic modules (peak, image_otd, product) are checked in
    the LKG cache first and skipped if today's data already exists.
    Dynamic modules always fetch fresh data, with LKG as a fallback on
    failure.

    Image uploads are always deferred — callers handle uploading via the
    returned pending_uploads list so the FTP connection is only opened
    after all data collection is complete.

    Returns:
        tuple: (drip_template_fields dict, pending_uploads list)
            pending_uploads contains (field_key, upload_args) tuples for
            images that still need to be uploaded via FTPSession.upload().
    """

    # Check LKG cache for date-deterministic modules
    cached = {}
    for module_name, keys in CACHED_MODULE_KEYS.items():
        lkg_data = _load_module_lkg(module_name, keys)
        if lkg_data:
            cached[module_name] = lkg_data
            logger.info("Using cached data for '%s' (date-deterministic)", module_name)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Dynamic modules: always fetch fresh
        weather_future = _submit_timed(executor, "weather", weather_data)
        trails_future = _submit_timed(executor, "trails", get_closed_trails)
        cg_future = _submit_timed(executor, "campgrounds", get_campground_status)
        roads_future = _submit_timed(executor, "roads", get_road_status)
        hiker_biker_future = _submit_timed(
            executor, "hiker_biker", get_hiker_biker_status
        )
        events_future = _submit_timed(executor, "events", events_today)
        sunrise_future = _submit_timed(executor, "sunrise", process_video)
        notices_future = _submit_timed(executor, "notices", get_notices)

        # Date-deterministic modules: skip if cached today
        image_future = None
        if "image_otd" not in cached:
            image_future = _submit_timed(
                executor, "image_otd", get_image_otd, skip_upload=True
            )
        peak_future = None
        if "peak" not in cached:
            peak_future = _submit_timed(executor, "peak", peak, skip_upload=True)
        product_future = None
        if "product" not in cached:
            product_future = _submit_timed(
                executor, "product", get_product, skip_upload=True
            )

        # Extract dynamic module results (with LKG fallback)
        sunrise_vid, sunrise_still, sunrise_str = _safe_result(
            sunrise_future,
            "sunrise",
            ("", "", ""),
            lkg_keys=["sunrise_vid", "sunrise_still", "sunrise_str"],
        )
        weather = _safe_result(weather_future, "weather", WeatherResult())

        # Extract date-deterministic results from cache or futures
        if "image_otd" in cached:
            c = cached["image_otd"]
            image_otd = c.get("image_otd", "")
            image_otd_title = c.get("image_otd_title", "")
            image_otd_link = c.get("image_otd_link", "")
        else:
            image_otd, image_otd_title, image_otd_link = _safe_result(
                image_future, "image_otd", ("", "", "")
            )

        if "peak" in cached:
            c = cached["peak"]
            peak_name = c.get("peak", "")
            peak_img = c.get("peak_image")
            peak_map = c.get("peak_map", "")
        else:
            peak_name, peak_img, peak_map = _safe_result(
                peak_future, "peak", ("", None, "")
            )

        if "product" in cached:
            c = cached["product"]
            potd_title = c.get("product_title", "")
            potd_image = c.get("product_image")
            potd_link = c.get("product_link", "")
            potd_desc = c.get("product_desc", "")
        else:
            potd_title, potd_image, potd_link, potd_desc = _safe_result(
                product_future, "product", ("", None, "", "")
            )

    weather_img = weather_image(weather.forecasts, skip_upload=True)

    # Collect deferred image uploads for the caller to process
    pending_uploads = []
    if image_otd is None:
        pending_uploads.append(("image_otd", prepare_pic_otd()))
    if peak_img is None:
        pending_uploads.append(("peak_image", prepare_peak_upload()))
    if potd_image is None:
        pending_uploads.append(("product_image", prepare_potd_upload()))
    if weather_img is None:
        pending_uploads.append(("weather_image", prepare_weather_upload()))

    drip_template_fields = {
        "date": now_mountain().strftime("%Y-%m-%d"),
        "today": format_date_readable(now_mountain()),
        "events": _safe_result(
            events_future, "events", EventsResult(), lkg_keys=["events"]
        ),
        "weather": weather,
        "weather_image": weather_img,
        "trails": _safe_result(
            trails_future, "trails", TrailsResult(), lkg_keys=["trails"]
        ),
        "campgrounds": _safe_result(
            cg_future, "campgrounds", CampgroundsResult(), lkg_keys=["campgrounds"]
        ),
        "roads": _safe_result(roads_future, "roads", RoadsResult(), lkg_keys=["roads"]),
        "hikerbiker": _safe_result(
            hiker_biker_future,
            "hiker_biker",
            HikerBikerResult(),
            lkg_keys=["hikerbiker"],
        ),
        "notices": _safe_result(
            notices_future, "notices", NoticesResult(), lkg_keys=["notices"]
        ),
        "peak": peak_name,
        "peak_image": peak_img,
        "peak_map": peak_map,
        "product_link": potd_link,
        "product_image": potd_image,
        "product_title": potd_title,
        "product_desc": potd_desc,
        "image_otd": image_otd,
        "image_otd_title": image_otd_title,
        "image_otd_link": image_otd_link,
        "sunrise_vid": sunrise_vid,
        "sunrise_still": sunrise_still,
        "sunrise_str": sunrise_str,
    }

    # LKG: Apply weather fallback if weather module failed
    if not drip_template_fields["weather"].daylight_message:
        lkg = _load_module_lkg("weather", ["weather", "weather_image"])
        if lkg:
            logger.info("Using LKG fallback for 'weather'")
            drip_template_fields["weather"] = lkg.get("weather", WeatherResult())
            if lkg.get("weather_image"):
                drip_template_fields["weather_image"] = lkg["weather_image"]
                pending_uploads[:] = [
                    (k, v) for k, v in pending_uploads if k != "weather_image"
                ]

    # LKG: Save successful module data
    for module_name, keys in _ALL_MODULE_KEYS.items():
        module_data = {
            k: drip_template_fields[k] for k in keys if drip_template_fields.get(k)
        }
        if module_data:
            _save_module_lkg(module_name, module_data)

    # Replace None with "" for simple string fields
    for key, value in drip_template_fields.items():
        if value is None:
            drip_template_fields[key] = ""

    return drip_template_fields, pending_uploads


def _serialize_value(value):
    """Convert dataclass instances to dicts for JSON serialization."""
    if hasattr(value, "__dataclass_fields__"):
        d = asdict(value)
        # Remove Event.sortable (datetime, not JSON-serializable, not needed in API)
        if "events" in d and isinstance(d["events"], list):
            for event in d["events"]:
                event.pop("sortable", None)
        return d
    return value


def write_data_to_json(data: dict, doctype: str) -> str:
    """
    Serialize structured data to clean JSON for API.
    """
    serializable = {key: _serialize_value(value) for key, value in data.items()}

    serializable["date"] = now_mountain().strftime("%Y-%m-%d")
    serializable["time_generated"] = cross_platform_strftime(
        now_mountain(), "%-I:%M %p"
    ).lower()
    serializable["gnpc-events"] = get_gnpc_events()

    filepath = f"server/{doctype}"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serializable, f)

    return filepath


def send_to_server(file: str, directory: str) -> None:
    """
    Upload file to glacier.org using FTP.
    :return None.
    """

    filename = file.split("/")[-1]
    upload_file(directory, filename, file)


def purge_cache():
    """
    Purge the Cloudflare cache for the site.
    """
    settings = get_settings()
    purge_key = settings.CACHE_PURGE
    zone_id = settings.ZONE_ID
    if not purge_key or not zone_id:
        logger.warning("No CACHE_PURGE key or ZONE_ID set, skipping cache purge.")
        return

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {purge_key}",
    }
    data = {"purge_everything": True}

    response = requests.post(url, headers=headers, json=data, timeout=30)
    if response.status_code == 200:
        logger.info("Cache purged successfully.")
    else:
        logger.error(f"Failed to purge cache: {response.status_code} - {response.text}")


def refresh_cache():
    """
    Refresh the Drip cache by hitting the endpoint.
    """
    url = "https://api.glacierconservancy.org/email.json"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            logger.info("Cache refreshed successfully.")
        else:
            logger.error(
                f"Failed to refresh cache: {response.status_code} - {response.text}"
            )
    except requests.RequestException as e:
        logger.error(f"Error refreshing cache: {e}")


def clear_cache():
    """Remove cached email.json and date-deterministic LKG data."""
    cache_file = "server/email.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)
    try:
        LKGCache.get_cache().clear_modules(list(CACHED_MODULE_KEYS))
    except Exception:
        logger.debug("Failed to clear LKG cache", exc_info=True)


def serve_api(force: bool = False):
    """
    Get the data, then upload it to server for API.
    FTP session is created after data collection to avoid idle timeouts.
    """
    if force:
        clear_cache()

    data, pending_uploads = gen_data()

    with FTPSession() as ftp:
        for field_key, upload_args in pending_uploads:
            url, _ = ftp.upload(*upload_args)
            data[field_key] = url if url else ""
            # Save resolved image URL to LKG for future cache hits
            module = _FIELD_TO_MODULE.get(field_key)
            if module and url:
                _save_module_lkg(module, {field_key: url})

        web = web_version(data)
        printable = web_version(data, "server/printable.html", "printable.html")
        json_file = write_data_to_json(data, "email.json")
        ftp.upload("api", json_file.split("/")[-1], json_file)
        ftp.upload("email", web.split("/")[-1], web)
        ftp.upload("printable", printable.split("/")[-1], printable)

    purge_cache()
    sleep(3)  # Wait for cache to purge
    refresh_cache()


if __name__ == "__main__":  # pragma: no cover
    import argparse as _argparse

    from shared.logging_config import setup_logging
    from shared.run_context import start_run
    from shared.run_report import build_report, upload_status_report

    settings = get_settings()  # Load email.env so ENVIRONMENT is available
    run = start_run("web_update")
    setup_logging()
    logger.info("Starting run %s (type=%s)", run.run_id, run.run_type)

    _parser = _argparse.ArgumentParser(description="Generate and upload data")
    _parser.add_argument(
        "--force",
        action="store_true",
        help="Clear cached data and re-fetch everything fresh",
    )
    _args = _parser.parse_args()

    if _args.force:
        clear_cache()

    try:
        environment = settings.ENVIRONMENT
        if environment == "development":
            gen_data()  # Pending uploads ignored in development
        elif environment == "production":
            serve_api(force=_args.force)
    finally:
        report = build_report(environment=settings.ENVIRONMENT)
        logger.info("Run complete: %s", report.overall_status)
        logger.info("Run report: %s", report.to_json())
        if settings.ENVIRONMENT == "production":
            try:
                upload_status_report(report)
            except Exception:
                logger.error("Failed to upload status report", exc_info=True)
