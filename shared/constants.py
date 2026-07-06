"""
Shared constants used across multiple modules.
"""

# West Glacier / Glacier National Park representative coordinates
WEST_GLACIER_LAT = 48.528556
WEST_GLACIER_LON = -113.991674

# Drip API maximum batch/page size
DRIP_BATCH_SIZE = 1000

# Drip subscriber tags
DAILY_UPDATE_TAG = "Glacier Daily Update"
TEST_DAILY_UPDATE_TAG = "Test Glacier Daily Update"
SUNSET_TIMELAPSE_TAG = "Sunset Timelapse"
TEST_SUNSET_TIMELAPSE_TAG = "Test Sunset Timelapse"

# Tags used to build send lists — subscriber_list returns bare email
# addresses for these instead of full subscriber records
EMAIL_LIST_TAGS = (
    DAILY_UPDATE_TAG,
    TEST_DAILY_UPDATE_TAG,
    SUNSET_TIMELAPSE_TAG,
    TEST_SUNSET_TIMELAPSE_TAG,
)

# Drip workflow-trigger event actions
DAILY_UPDATE_EVENT_ACTION = "Glacier Daily Update trigger"
SUNSET_TIMELAPSE_EVENT_ACTION = "Sunset Timelapse trigger"
