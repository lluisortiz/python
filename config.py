import os


def _load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader (no external dependencies needed)."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass


_load_dotenv()

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
