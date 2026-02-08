import requests
from typing import Optional, Dict, Any, List

DEFAULT_TIMEOUT = 10


def _join_url(base_url: str, path: str) -> str:
    if base_url.endswith("/") and path.startswith("/"):
        return base_url[:-1] + path
    if not base_url.endswith("/") and not path.startswith("/"):
        return base_url + "/" + path
    return base_url + path


def gamma_get(base_url: str, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    resp = requests.get(_join_url(base_url, path), params=params, timeout=DEFAULT_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Gamma API error: HTTP {resp.status_code}")
    return resp.json()


def fetch_event_by_slug(base_url: str, slug: str) -> Dict[str, Any]:
    try:
        data = gamma_get(base_url, f"/events/{slug}")
    except Exception:
        data = gamma_get(base_url, "/events", params={"slug": slug})
    if isinstance(data, list):
        if not data:
            raise ValueError(f"Event not found: {slug}")
        return data[0]
    if not data:
        raise ValueError(f"Event not found: {slug}")
    return data


def fetch_market_by_slug(base_url: str, slug: str) -> Dict[str, Any]:
    try:
        data = gamma_get(base_url, f"/markets/{slug}")
    except Exception:
        data = gamma_get(base_url, "/markets", params={"slug": slug})
    if isinstance(data, list):
        if not data:
            raise ValueError(f"Market not found: {slug}")
        return data[0]
    if not data:
        raise ValueError(f"Market not found: {slug}")
    return data


def fetch_market_by_condition_or_tokens(
    base_url: str,
    condition_id: Optional[str] = None,
    token_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if condition_id:
        params["condition_id"] = condition_id
    if token_ids:
        params["clob_token_ids"] = ",".join(token_ids)
    data = gamma_get(base_url, "/markets", params=params)
    if not data:
        raise ValueError("No markets matched")
    return data[0] if isinstance(data, list) else data
