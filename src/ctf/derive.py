from dataclasses import dataclass
from web3 import Web3

from ..config import CONDITIONAL_TOKENS
from ..utils.rpc import get_web3

CTF_ABI = [
    {
        "inputs": [
            {"name": "parentCollectionId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "indexSet", "type": "uint256"},
        ],
        "name": "getCollectionId",
        "outputs": [{"type": "bytes32"}],
        "stateMutability": "pure",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "collateralToken", "type": "address"},
            {"name": "collectionId", "type": "bytes32"},
        ],
        "name": "getPositionId",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "pure",
        "type": "function",
    },
]


def _get_ctf_contract(w3: Web3):
    return w3.eth.contract(address=Web3.to_checksum_address(CONDITIONAL_TOKENS), abi=CTF_ABI)


@dataclass(frozen=True)
class BinaryPositions:
    condition_id: str
    oracle: str
    question_id: str
    collateral_token: str
    position_yes: str
    position_no: str


def _normalize_bytes32(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Expected hex string for bytes32")
    hex_value = value if value.startswith("0x") else f"0x{value}"
    raw = Web3.to_bytes(hexstr=hex_value)
    if len(raw) != 32:
        raise ValueError("Expected 32-byte hex string")
    return Web3.to_hex(raw)


def derive_collection_id(parent_collection_id: str, condition_id: str, index_set: int) -> str:
    parent = _normalize_bytes32(parent_collection_id)
    condition = _normalize_bytes32(condition_id)
    w3 = get_web3()
    contract = _get_ctf_contract(w3)
    collection = contract.functions.getCollectionId(parent, condition, int(index_set)).call()
    return Web3.to_hex(collection)


def derive_position_id(collateral_token: str, collection_id: str) -> str:
    collection = _normalize_bytes32(collection_id)
    token = Web3.to_checksum_address(collateral_token)
    position_id = Web3.solidity_keccak(["address", "bytes32"], [token, collection])
    return Web3.to_hex(position_id)


def derive_binary_positions(
    oracle: str,
    question_id: str,
    condition_id: str,
    collateral_token: str,
) -> BinaryPositions:
    parent = "0x" + "00" * 32

    w3 = get_web3()
    contract = _get_ctf_contract(w3)
    parent_b = _normalize_bytes32(parent)
    condition_b = _normalize_bytes32(condition_id)

    yes_collection = contract.functions.getCollectionId(parent_b, condition_b, 1).call()
    no_collection = contract.functions.getCollectionId(parent_b, condition_b, 2).call()

    position_yes = derive_position_id(collateral_token, Web3.to_hex(yes_collection))
    position_no = derive_position_id(collateral_token, Web3.to_hex(no_collection))

    return BinaryPositions(
        condition_id=condition_id,
        oracle=oracle,
        question_id=question_id,
        collateral_token=collateral_token,
        position_yes=position_yes,
        position_no=position_no,
    )
