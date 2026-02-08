# 实施计划：Polymarket 链上数据解码器 (Stage 1)

## 任务类型
- [x] 后端 (→ Codex)
- [x] 前端 CLI (→ Gemini)
- [x] 全栈 (→ 并行)

---

## 技术方案

### 项目概述
实现 Polymarket 链上数据解码器，包含两个核心任务：
1. **Trade Decoder** - 解析 Polygon 链上的 `OrderFilled` 事件，提取交易详情
2. **Market Decoder** - 解析 `ConditionPreparation` 事件或从 Gamma API 获取市场信息，计算 YES/NO TokenId

### 架构决策
- **分层架构**：CLI 层 → 业务逻辑层 → 数据访问层（RPC/API）
- **纯函数设计**：CTF TokenId 计算使用纯函数，便于单元测试
- **精度安全**：使用 `Decimal` 处理价格计算，避免浮点误差
- **链上优先**：链上计算为权威，Gamma API 作为校验源

### 项目结构
```
stage1/
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
├── src/
│   ├── __init__.py
│   ├── config.py             # 常量配置（合约地址、ABI 等）
│   ├── trade_decoder.py      # 交易解码器 CLI
│   ├── market_decoder.py     # 市场解码器 CLI
│   ├── demo.py               # 综合演示
│   ├── ctf/
│   │   ├── __init__.py
│   │   └── derive.py         # TokenId 计算（纯函数）
│   ├── indexer/
│   │   ├── __init__.py
│   │   └── gamma.py          # Gamma API 客户端
│   └── utils/
│       ├── __init__.py
│       └── rpc.py            # RPC 客户端封装
├── data/                     # 输出目录
└── fixtures/                 # 测试数据
```

---

## 实施步骤

### Step 1: 基础设施搭建
**预期产物**: `.env.example`, `requirements.txt`, `src/__init__.py`, `src/config.py`

1.1 创建 `.env.example`
```
RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY
GAMMA_BASE_URL=https://gamma.polymarket.com
```

1.2 创建 `requirements.txt`
```
web3>=6.0.0
requests>=2.28.0
python-dotenv>=1.0.0
```

1.3 创建 `src/config.py` - 核心常量
```python
# 合约地址
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEGRISK_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
EXCHANGES = [CTF_EXCHANGE.lower(), NEGRISK_EXCHANGE.lower()]
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

# OrderFilled 事件签名
ORDER_FILLED_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65b8...（完整哈希）"
```

---

### Step 2: CTF TokenId 计算模块
**预期产物**: `src/ctf/__init__.py`, `src/ctf/derive.py`

2.1 实现 `derive.py` - 纯函数实现 TokenId 派生
```python
from dataclasses import dataclass
from web3 import Web3

@dataclass(frozen=True)
class BinaryPositions:
    condition_id: str
    oracle: str
    question_id: str
    collateral_token: str
    position_yes: str
    position_no: str

def derive_collection_id(parent_collection_id: str, condition_id: str, index_set: int) -> str:
    """计算 collectionId = keccak256(parent, conditionId, indexSet)"""
    return Web3.solidity_keccak(
        ["bytes32", "bytes32", "uint256"],
        [parent_collection_id, condition_id, index_set]
    ).hex()

def derive_position_id(collateral_token: str, collection_id: str) -> str:
    """计算 positionId = keccak256(collateralToken, collectionId)"""
    return Web3.solidity_keccak(
        ["address", "bytes32"],
        [collateral_token, collection_id]
    ).hex()

def derive_binary_positions(
    oracle: str,
    question_id: str,
    condition_id: str,
    collateral_token: str
) -> BinaryPositions:
    """派生二元市场的 YES/NO TokenId"""
    parent = "0x" + "00" * 32  # bytes32(0)

    # YES: indexSet = 1 (0b01)
    yes_collection = derive_collection_id(parent, condition_id, 1)
    position_yes = derive_position_id(collateral_token, yes_collection)

    # NO: indexSet = 2 (0b10)
    no_collection = derive_collection_id(parent, condition_id, 2)
    position_no = derive_position_id(collateral_token, no_collection)

    return BinaryPositions(
        condition_id=condition_id,
        oracle=oracle,
        question_id=question_id,
        collateral_token=collateral_token,
        position_yes=position_yes,
        position_no=position_no
    )
```

---

### Step 3: Gamma API 客户端
**预期产物**: `src/indexer/__init__.py`, `src/indexer/gamma.py`

3.1 实现 `gamma.py`
```python
import requests
from typing import Optional, Dict, Any, List

DEFAULT_TIMEOUT = 10

def gamma_get(base_url: str, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """通用 Gamma API GET 请求"""
    resp = requests.get(f"{base_url}{path}", params=params, timeout=DEFAULT_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Gamma API error: HTTP {resp.status_code}")
    return resp.json()

def fetch_event_by_slug(base_url: str, slug: str) -> Dict[str, Any]:
    """通过 slug 获取事件信息"""
    data = gamma_get(base_url, f"/events/{slug}")
    if not data:
        raise ValueError(f"Event not found: {slug}")
    return data

def fetch_market_by_slug(base_url: str, slug: str) -> Dict[str, Any]:
    """通过 slug 获取市场信息"""
    data = gamma_get(base_url, f"/markets/{slug}")
    if not data:
        raise ValueError(f"Market not found: {slug}")
    return data

def fetch_market_by_condition_or_tokens(
    base_url: str,
    condition_id: Optional[str] = None,
    token_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """通过 conditionId 或 tokenIds 查找市场"""
    params = {}
    if condition_id:
        params["condition_id"] = condition_id
    if token_ids:
        params["clob_token_ids"] = ",".join(token_ids)
    data = gamma_get(base_url, "/markets", params=params)
    if not data:
        raise ValueError("No markets matched")
    return data[0] if isinstance(data, list) else data
```

---

### Step 4: RPC 客户端封装
**预期产物**: `src/utils/__init__.py`, `src/utils/rpc.py`

4.1 实现 `rpc.py`
```python
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

def get_web3() -> Web3:
    """获取 Web3 实例"""
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        raise ValueError("RPC_URL not configured in .env")
    return Web3(Web3.HTTPProvider(rpc_url))

def get_transaction_receipt(tx_hash: str) -> dict:
    """获取交易回执"""
    w3 = get_web3()
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    if not receipt:
        raise ValueError(f"Transaction not found: {tx_hash}")
    return dict(receipt)
```

---

### Step 5: Trade Decoder 实现
**预期产物**: `src/trade_decoder.py`

5.1 核心数据结构
```python
from dataclasses import dataclass, asdict
from decimal import Decimal

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
```

5.2 解码逻辑
```python
def decode_order_filled(log, tx_hash: str) -> Optional[Trade]:
    """解析 OrderFilled 事件日志"""
    # 1. 提取事件数据
    # 2. 过滤重复日志：taker == exchange 时跳过
    if taker.lower() == log["address"].lower():
        return None

    # 3. 计算价格和方向
    maker_asset_id = int(event["makerAssetId"])
    taker_asset_id = int(event["takerAssetId"])

    if maker_asset_id == 0:  # maker 出 USDC → BUY
        price = Decimal(maker_amount) / Decimal(taker_amount)
        token_id = str(taker_asset_id)
        side = "BUY"
    else:  # maker 出 Token → SELL
        price = Decimal(taker_amount) / Decimal(maker_amount)
        token_id = str(maker_asset_id)
        side = "SELL"

    return Trade(...)
```

5.3 CLI 入口
```python
def main():
    parser = argparse.ArgumentParser(description="Polymarket Trade Decoder")
    parser.add_argument("--tx-hash", required=True, help="Transaction hash")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    trades = decode_trades(args.tx_hash)
    output = [asdict(t) for t in trades]

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
    else:
        print(json.dumps(output, indent=2))
```

---

### Step 6: Market Decoder 实现
**预期产物**: `src/market_decoder.py`

6.1 核心逻辑
```python
def decode_market(market_slug: str = None, tx_hash: str = None, log_index: int = None) -> dict:
    """解码市场参数"""
    base_url = os.getenv("GAMMA_BASE_URL", "https://gamma.polymarket.com")

    if market_slug:
        # 从 Gamma API 获取
        market = fetch_market_by_slug(base_url, market_slug)
        condition_id = market["conditionId"]
        oracle = market["oracle"]
        question_id = market["questionId"]
    elif tx_hash and log_index is not None:
        # 从链上事件解析
        receipt = get_transaction_receipt(tx_hash)
        log = receipt["logs"][log_index]
        # 解析 ConditionPreparation 事件...
    else:
        raise ValueError("Either --market-slug or (--tx-hash AND --log-index) required")

    # 计算 TokenId
    positions = derive_binary_positions(oracle, question_id, condition_id, USDC_E)

    # 交叉验证（如果从 Gamma 获取）
    if market_slug and "clobTokenIds" in market:
        gamma_ids = set(t.lower() for t in market["clobTokenIds"])
        calc_ids = {positions.position_yes.lower(), positions.position_no.lower()}
        if gamma_ids != calc_ids:
            raise ValueError("TokenId mismatch: calculated vs Gamma API")

    return {
        "conditionId": condition_id,
        "oracle": oracle,
        "questionId": question_id,
        "outcomeSlotCount": 2,
        "collateralToken": USDC_E,
        "yesTokenId": positions.position_yes,
        "noTokenId": positions.position_no,
        "gamma": market if market_slug else None
    }
```

---

### Step 7: Demo 脚本实现
**预期产物**: `src/demo.py`

7.1 综合演示
```python
def main():
    parser = argparse.ArgumentParser(description="Polymarket Demo")
    parser.add_argument("--tx-hash", required=True)
    parser.add_argument("--event-slug", required=True)
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    # 执行交易解析
    trades = decode_trades(args.tx_hash)

    # 执行市场解码（通过 event slug 获取关联市场）
    event = fetch_event_by_slug(GAMMA_BASE_URL, args.event_slug)
    markets = event.get("markets", [])
    market_info = decode_market(market_slug=markets[0]["slug"]) if markets else None

    output = {
        "stage1": {
            "tx_hash": args.tx_hash,
            "trades": [asdict(t) for t in trades],
            "market": market_info,
            "gamma": event
        }
    }

    # 输出
    json_str = json.dumps(output, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(json_str)
    else:
        print(json_str)
```

---

### Step 8: 创建目录和配置文件
**预期产物**: `data/`, `fixtures/`

8.1 创建目录结构
```bash
mkdir -p data fixtures
```

---

## 关键文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `.env.example` | 新建 | RPC_URL 配置模板 |
| `requirements.txt` | 新建 | Python 依赖：web3, requests, python-dotenv |
| `src/__init__.py` | 新建 | 包初始化 |
| `src/config.py` | 新建 | 常量配置（合约地址、事件签名） |
| `src/ctf/__init__.py` | 新建 | CTF 模块初始化 |
| `src/ctf/derive.py` | 新建 | TokenId 计算纯函数 |
| `src/indexer/__init__.py` | 新建 | Indexer 模块初始化 |
| `src/indexer/gamma.py` | 新建 | Gamma API 客户端 |
| `src/utils/__init__.py` | 新建 | Utils 模块初始化 |
| `src/utils/rpc.py` | 新建 | RPC 客户端封装 |
| `src/trade_decoder.py` | 新建 | 交易解码器 CLI |
| `src/market_decoder.py` | 新建 | 市场解码器 CLI |
| `src/demo.py` | 新建 | 综合演示脚本 |

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| RPC 超时/限流 | 使用重试机制，配置超时参数 |
| OrderFilled 重复计数 | 过滤 `taker == exchange` 的日志 |
| 浮点精度误差 | 使用 `Decimal` 进行价格计算 |
| Gamma API 与链上不一致 | 交叉验证 TokenId，不一致时报错 |
| 复杂市场（NegRisk） | 初版明确只支持二元市场，复杂场景后续迭代 |

---

## 验收清单

- [ ] `python -m src.trade_decoder --tx-hash 0x916cad...` 正确输出交易列表
- [ ] `price`, `side`, `token_id` 计算正确
- [ ] 过滤 `taker == exchange` 的重复日志
- [ ] `python -m src.market_decoder --market-slug ...` 正确输出市场信息
- [ ] `yesTokenId`, `noTokenId` 计算正确
- [ ] 计算结果与 Gamma API `clobTokenIds` 一致
- [ ] `python -m src.demo --tx-hash ... --event-slug ...` 综合输出完整

---

## SESSION_ID（供 /ccg:execute 使用）

- CODEX_SESSION: `019c3b1b-545f-7ae1-ad1a-bf1eda1b706d` (分析) / `019c3b1f-7769-7911-97f6-f8c85f212207` (规划)
- GEMINI_SESSION: `2d1dd7f0-8a35-412e-908c-3171765fe37f` (分析) / `f6d64ed2-3a18-457d-957a-d8b5ae73c5d4` (规划)
