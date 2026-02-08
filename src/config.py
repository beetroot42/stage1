from web3 import Web3

CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEGRISK_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
EXCHANGES = [CTF_EXCHANGE.lower(), NEGRISK_EXCHANGE.lower()]

USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_DECIMALS = 6

DEFAULT_GAMMA_BASE_URL = "https://gamma.polymarket.com"
UMA_ORACLE = "0x157Ce2d672854c848c9b79C49a8Cc6cc89176a49"
CONDITIONAL_TOKENS = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"

ORDER_FILLED_EVENT_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "internalType": "bytes32", "name": "orderHash", "type": "bytes32"},
        {"indexed": True, "internalType": "address", "name": "maker", "type": "address"},
        {"indexed": True, "internalType": "address", "name": "taker", "type": "address"},
        {"indexed": False, "internalType": "uint256", "name": "makerAssetId", "type": "uint256"},
        {"indexed": False, "internalType": "uint256", "name": "takerAssetId", "type": "uint256"},
        {"indexed": False, "internalType": "uint256", "name": "makerAmountFilled", "type": "uint256"},
        {"indexed": False, "internalType": "uint256", "name": "takerAmountFilled", "type": "uint256"},
        {"indexed": False, "internalType": "uint256", "name": "fee", "type": "uint256"},
    ],
    "name": "OrderFilled",
    "type": "event",
}

ORDER_FILLED_TOPIC = Web3.to_hex(
    Web3.keccak(
        text="OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)"
    )
)

CONDITION_PREPARATION_EVENT_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "internalType": "bytes32", "name": "conditionId", "type": "bytes32"},
        {"indexed": True, "internalType": "address", "name": "oracle", "type": "address"},
        {"indexed": True, "internalType": "bytes32", "name": "questionId", "type": "bytes32"},
        {"indexed": False, "internalType": "uint256", "name": "outcomeSlotCount", "type": "uint256"},
    ],
    "name": "ConditionPreparation",
    "type": "event",
}

CONDITION_PREPARATION_TOPIC = Web3.to_hex(
    Web3.keccak(text="ConditionPreparation(bytes32,address,bytes32,uint256)")
)
