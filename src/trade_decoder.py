import argparse
import json
from dataclasses import dataclass, asdict
from decimal import Decimal, getcontext
from typing import List, Optional

from web3 import Web3
from web3._utils.events import get_event_data

from .config import EXCHANGES, ORDER_FILLED_EVENT_ABI, ORDER_FILLED_TOPIC
from .utils.rpc import get_web3, get_transaction_receipt

getcontext().prec = 40


@dataclass(frozen=True)
class Trade:
    tx_hash: str
    log_index: int
    exchange: str
    order_hash: str
    maker: str
    taker: str
    maker_asset_id: str
    taker_asset_id: str
    maker_amount: str
    taker_amount: str
    fee: str
    price: str
    token_id: str
    side: str


def _decimal_to_str(value: Decimal) -> str:
    text = format(value, "f")
    if "." not in text:
        return text + ".0"
    return text


def _is_order_filled_log(log: dict) -> bool:
    topics = log.get("topics") or []
    if not topics:
        return False
    topic0 = Web3.to_hex(topics[0]).lower()
    if topic0 != ORDER_FILLED_TOPIC.lower():
        return False
    address = log.get("address")
    if address and address.lower() not in EXCHANGES:
        return False
    return True


def decode_order_filled(log: dict, tx_hash: str, w3: Web3) -> Optional[Trade]:
    decoded = get_event_data(w3.codec, ORDER_FILLED_EVENT_ABI, log)
    args = decoded["args"]

    exchange = log.get("address", "")
    maker = args["maker"]
    taker = args["taker"]

    if exchange and taker.lower() == exchange.lower():
        return None

    maker_asset_id = int(args["makerAssetId"])
    taker_asset_id = int(args["takerAssetId"])
    maker_amount = int(args["makerAmountFilled"])
    taker_amount = int(args["takerAmountFilled"])

    if maker_asset_id == 0 and taker_asset_id == 0:
        raise ValueError("Invalid OrderFilled: both asset ids are zero")

    if maker_asset_id == 0:
        price = Decimal(maker_amount) / Decimal(taker_amount)
        token_id = taker_asset_id
        side = "BUY"
    elif taker_asset_id == 0:
        price = Decimal(taker_amount) / Decimal(maker_amount)
        token_id = maker_asset_id
        side = "SELL"
    else:
        raise ValueError("OrderFilled has no USDC leg; cannot infer price")

    return Trade(
        tx_hash=tx_hash,
        log_index=int(log.get("logIndex", 0)),
        exchange=exchange,
        order_hash=Web3.to_hex(args["orderHash"]),
        maker=maker,
        taker=taker,
        maker_asset_id=str(maker_asset_id),
        taker_asset_id=str(taker_asset_id),
        maker_amount=str(maker_amount),
        taker_amount=str(taker_amount),
        fee=str(int(args["fee"])),
        price=_decimal_to_str(price),
        token_id=str(token_id),
        side=side,
    )


def decode_trades(tx_hash: str) -> List[Trade]:
    w3 = get_web3()
    receipt = get_transaction_receipt(tx_hash)
    trades: List[Trade] = []
    for log in receipt.get("logs", []):
        if not _is_order_filled_log(log):
            continue
        trade = decode_order_filled(log, tx_hash, w3)
        if trade is not None:
            trades.append(trade)
    return trades


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket Trade Decoder")
    parser.add_argument("--tx-hash", required=True, help="Transaction hash")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    trades = decode_trades(args.tx_hash)
    output = [asdict(t) for t in trades]

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
    else:
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
