import os
from dotenv import load_dotenv
from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware as poa_middleware
except ImportError:  # web3 v7+
    from web3.middleware import ExtraDataToPOAMiddleware as poa_middleware

load_dotenv()


def get_web3() -> Web3:
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        raise ValueError("RPC_URL not configured in .env")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    # Polygon uses POA-style headers; inject middleware for block decoding.
    w3.middleware_onion.inject(poa_middleware, layer=0)
    return w3


def get_transaction_receipt(tx_hash: str) -> dict:
    w3 = get_web3()
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    if receipt is None:
        raise ValueError(f"Transaction not found: {tx_hash}")
    return receipt
