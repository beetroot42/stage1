import argparse
import json
import os
from typing import Any, Dict, Optional

from web3 import Web3
from web3._utils.events import get_event_data

from .config import (
    CONDITION_PREPARATION_EVENT_ABI,
    CONDITION_PREPARATION_TOPIC,
    DEFAULT_GAMMA_BASE_URL,
    UMA_ORACLE,
    USDC_E,
)
from .ctf.derive import derive_binary_positions
from .indexer.gamma import fetch_market_by_slug
from .utils.rpc import get_web3, get_transaction_receipt


def _normalize_hex(value: Any) -> str:
    if isinstance(value, bytes):
        return Web3.to_hex(value)
    if isinstance(value, int):
        return hex(value)
    if isinstance(value, str):
        return value if value.startswith("0x") else f"0x{value}"
    raise TypeError("Unsupported hex value type")


def _get_market_field(market: Dict[str, Any], *names: str) -> Optional[Any]:
    for name in names:
        if name in market and market[name] is not None:
            return market[name]
    return None


def _token_id_to_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 16) if value.startswith("0x") else int(value)
    raise TypeError("Unsupported token id type")


def _decode_condition_preparation(w3: Web3, log: Dict[str, Any]) -> Dict[str, Any]:
    topics = log.get("topics") or []
    if not topics:
        raise ValueError("Log has no topics")
    if Web3.to_hex(topics[0]).lower() != CONDITION_PREPARATION_TOPIC.lower():
        raise ValueError("Log is not ConditionPreparation")
    decoded = get_event_data(w3.codec, CONDITION_PREPARATION_EVENT_ABI, log)
    args = decoded["args"]
    return {
        "conditionId": _normalize_hex(args["conditionId"]),
        "oracle": args["oracle"],
        "questionId": _normalize_hex(args["questionId"]),
        "outcomeSlotCount": int(args["outcomeSlotCount"]),
    }


def decode_market(
    market_slug: Optional[str] = None,
    tx_hash: Optional[str] = None,
    log_index: Optional[int] = None,
) -> Dict[str, Any]:
    base_url = os.getenv("GAMMA_BASE_URL", DEFAULT_GAMMA_BASE_URL)

    condition_id = None
    oracle = None
    question_id = None
    outcome_slot_count = None
    market = None

    if market_slug:
        market = fetch_market_by_slug(base_url, market_slug)
        condition_id = _get_market_field(market, "conditionId", "condition_id")
        oracle = _get_market_field(market, "oracle", "oracleAddress", "oracle_address") or UMA_ORACLE
        question_id = _get_market_field(
            market, "questionId", "question_id", "questionID", "questionID".lower()
        )
        outcome_slot_count = _get_market_field(market, "outcomeSlotCount", "outcome_slot_count")
    elif tx_hash is not None and log_index is not None:
        w3 = get_web3()
        receipt = get_transaction_receipt(tx_hash)
        logs = receipt.get("logs", [])
        if log_index < 0 or log_index >= len(logs):
            raise IndexError("log_index out of range")
        decoded = _decode_condition_preparation(w3, logs[log_index])
        condition_id = decoded["conditionId"]
        oracle = decoded["oracle"]
        question_id = decoded["questionId"]
        outcome_slot_count = decoded["outcomeSlotCount"]
    else:
        raise ValueError("Either --market-slug or (--tx-hash AND --log-index) required")

    if not condition_id or not oracle or not question_id:
        raise ValueError("Missing market fields for decoding")

    condition_id = _normalize_hex(condition_id)
    question_id = _normalize_hex(question_id)
    outcome_slot_count = int(outcome_slot_count or 2)

    positions = derive_binary_positions(
        oracle=oracle,
        question_id=question_id,
        condition_id=condition_id,
        collateral_token=USDC_E,
    )

    if market_slug and market and market.get("clobTokenIds"):
        gamma_tokens = market["clobTokenIds"]
        if isinstance(gamma_tokens, str):
            gamma_tokens = json.loads(gamma_tokens)
        gamma_ids = {_token_id_to_int(t) for t in gamma_tokens}
        calc_ids = {
            _token_id_to_int(positions.position_yes),
            _token_id_to_int(positions.position_no),
        }
        if gamma_ids != calc_ids:
            raise ValueError("TokenId mismatch: calculated vs Gamma API")

    return {
        "conditionId": condition_id,
        "oracle": oracle,
        "questionId": question_id,
        "outcomeSlotCount": outcome_slot_count,
        "collateralToken": USDC_E,
        "yesTokenId": positions.position_yes,
        "noTokenId": positions.position_no,
        "gamma": market if market_slug else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket Market Decoder")
    parser.add_argument("--market-slug", help="Market slug (Gamma API)")
    parser.add_argument("--tx-hash", help="Transaction hash")
    parser.add_argument("--log-index", type=int, help="Log index in receipt")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    result = decode_market(
        market_slug=args.market_slug,
        tx_hash=args.tx_hash,
        log_index=args.log_index,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
