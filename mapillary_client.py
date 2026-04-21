import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from config import (
    MAPILLARY_API_BASE,
    MAX_RETRIES,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT,
)

# Fields requested from the API (images → first image ID for thumbnail)
_FEATURE_FIELDS = "id,object_value,geometry,first_seen_at,last_seen_at,images"


class MapillaryClient:
    """Thin wrapper around the Mapillary Graph API v4 map-features endpoint."""

    def __init__(self, access_token: str) -> None:
        if not access_token:
            raise ValueError(
                "Se necesita un token de acceso a Mapillary.\n"
                "  1. Crea una cuenta en https://www.mapillary.com\n"
                "  2. Ve a https://www.mapillary.com/developer/api-documentation\n"
                "  3. Genera un token y ponlo en MAPILLARY_ACCESS_TOKEN"
            )
        self._token = access_token
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"OAuth {access_token}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_map_features(
        self,
        bbox: Tuple[float, float, float, float],
        object_values: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve map features inside a bounding box.

        Args:
            bbox: (west, south, east, north) in decimal degrees.
            object_values: optional server-side filter by sign category.

        Returns:
            List of feature dicts from the API (all pages combined).
        """
        west, south, east, north = bbox
        params: Dict[str, Any] = {
            "access_token": self._token,
            "fields": _FEATURE_FIELDS,
            "bbox": f"{west},{south},{east},{north}",
        }
        if object_values:
            params["object_values"] = ",".join(object_values)

        url = f"{MAPILLARY_API_BASE}/map_features"
        return self._fetch_all_pages(url, params)

    def get_image_thumbnail_url(self, image_id: str, size: int = 256) -> Optional[str]:
        """
        Return the signed thumbnail URL for a Mapillary image.
        size: 256, 1024 or 2048.
        """
        body = self._get(
            f"{MAPILLARY_API_BASE}/{image_id}",
            {"access_token": self._token, "fields": f"thumb_{size}_url"},
        )
        return body.get(f"thumb_{size}_url") if body else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_all_pages(
        self,
        url: str,
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Follow the paging.next cursor until exhausted."""
        results: List[Dict[str, Any]] = []
        current_url = url
        current_params: Optional[Dict[str, Any]] = params

        while current_url:
            body = self._get(current_url, current_params)
            if body is None:
                break

            results.extend(body.get("data", []))

            next_url = body.get("paging", {}).get("next")
            if not next_url:
                break

            # The next URL already includes all query params
            current_url = next_url
            current_params = None          # don't double-encode params
            time.sleep(REQUEST_DELAY_SECONDS)

        return results

    def _get(
        self,
        url: str,
        params: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """HTTP GET with exponential-backoff retry."""
        backoff = 1.0
        for attempt in range(MAX_RETRIES):
            try:
                resp = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 429:
                    wait = backoff * (2 ** attempt) * 5
                    print(f"\n  [API] Rate limit alcanzado. Esperando {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code == 400:
                    print(f"\n  [API] Petición incorrecta: {resp.text[:200]}")
                    return None
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as exc:
                if attempt < MAX_RETRIES - 1:
                    wait = backoff * (2 ** attempt)
                    print(f"\n  [API] Error ({exc}). Reintento en {wait:.0f}s...")
                    time.sleep(wait)
                else:
                    print(f"\n  [API] Error permanente: {exc}")
                    return None
        return None
