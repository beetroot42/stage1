import argparse
import json
import os
from dataclasses import asdict
from typing import Any, Dict, Optional

from .config import DEFAULT_GAMMA_BASE_URL
from .indexer.gamma import fetch_event_by_slug
from .market_decoder import decode_market
from .trade_decoder import decode_trades


def _get_market_slug(market: Dict[str, Any]) -> Optional[str]:
    for key in ("slug", "marketSlug", "market_slug"):
        value = market.get(key)
        if value:
            return value
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket Demo")
    parser.add_argument("--tx-hash", required=True)
    parser.add_argument("--event-slug", required=True)
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    trades = decode_trades(args.tx_hash)

    base_url = os.getenv("GAMMA_BASE_URL", DEFAULT_GAMMA_BASE_URL)
    event = fetch_event_by_slug(base_url, args.event_slug)
    markets = event.get("markets") or []

    market_info = None
    if markets:
        slug = _get_market_slug(markets[0])
        if slug:
            market_info = decode_market(market_slug=slug)

    output = {
        "stage1": {
            "tx_hash": args.tx_hash,
            "trades": [asdict(t) for t in trades],
            "market": market_info,
            "gamma": event,
        }
    }

    json_str = json.dumps(output, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
