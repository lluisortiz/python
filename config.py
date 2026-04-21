import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Mapillary API
MAPILLARY_ACCESS_TOKEN = os.getenv("MAPILLARY_ACCESS_TOKEN", "")
MAPILLARY_API_BASE = "https://graph.mapillary.com"

# Search parameters
DEFAULT_SEARCH_RADIUS_METERS = 50   # meters from route centerline
DEFAULT_SEGMENT_LENGTH_KM = 5       # km per API query chunk
BBOX_PADDING_DEGREES = 0.0015       # ~165 m padding around each bbox

# HTTP settings
REQUEST_DELAY_SECONDS = 0.4
MAX_RETRIES = 4
REQUEST_TIMEOUT = 30
