# Polymarket Indexer

Polymarket 链上市场与交易数据索引器，用于扫描 Polygon 链上的 Polymarket 交易事件，将市场和交易信息存储到本地数据库，并提供 REST API 查询接口。

## 功能特性

- **Market Discovery** - 从 Gamma API 获取市场元数据，包括 conditionId、tokenIds 等
- **Trades Indexer** - 扫描 OrderFilled 事件，解析交易数据并关联市场
- **REST API** - 提供市场和交易数据的查询接口，支持分页和区块范围过滤
- **断点续传** - 通过 sync_state 表记录同步进度，支持中断后继续
- **幂等写入** - 使用 UNIQUE 约束防止重复数据

## 项目结构

```
stage2/
├── src/
│   ├── api/
│   │   └── server.py      # FastAPI REST API 服务
│   ├── db/
│   │   ├── schema.py      # 数据库表结构定义
│   │   └── store.py       # 数据访问层
│   ├── ctf/
│   │   └── derive.py      # CTF TokenId 计算
│   ├── indexer/
│   │   ├── gamma.py       # Gamma API 客户端
│   │   ├── market_discovery.py  # 市场发现服务
│   │   └── run.py         # 核心索引器逻辑
│   ├── config.py          # 配置和常量
│   └── demo.py            # 演示脚本
├── data/                  # 数据库文件目录
├── .env.example           # 环境变量示例
├── requirements.txt       # Python 依赖
└── README.md
```

## 快速开始

### 1. 环境配置

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑 .env 填入 RPC URL
# RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行索引器

```bash
# 索引特定交易所在的区块
python -m src.demo \
    --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
    --event-slug will-there-be-another-us-government-shutdown-by-january-31 \
    --reset-db \
    --output ./data/demo_output.json

# 索引指定区块范围
python -m src.demo \
    --from-block 81324000 \
    --to-block 81325000 \
    --event-slug will-there-be-another-us-government-shutdown-by-january-31 \
    --db ./data/indexer.db
```

### 4. 启动 API 服务

```bash
python -m src.api.server --db ./data/demo_indexer.db --port 8000
```

## API 文档

### 端点列表

| 端点 | 描述 |
|------|------|
| `GET /` | API 信息 |
| `GET /events/{slug}` | 获取事件详情 |
| `GET /events/{slug}/markets` | 获取事件下的所有市场 |
| `GET /markets/{slug}` | 获取市场详情 |
| `GET /markets/{slug}/trades` | 获取市场交易记录 |
| `GET /tokens/{token_id}/trades` | 按 TokenId 获取交易 |

### 查询参数

| 参数 | 类型 | 描述 |
|------|------|------|
| `limit` | int | 返回条数限制 (1-1000，默认 100) |
| `cursor` | int | 分页偏移量 (默认 0) |
| `fromBlock` | int | 起始区块过滤 |
| `toBlock` | int | 结束区块过滤 |

### 示例请求

```bash
# 获取市场信息
curl http://127.0.0.1:8000/markets/will-there-be-another-us-government-shutdown-by-january-31

# 获取交易记录（带分页）
curl "http://127.0.0.1:8000/markets/will-there-be-another-us-government-shutdown-by-january-31/trades?limit=10&cursor=0"

# 按区块范围过滤
curl "http://127.0.0.1:8000/markets/will-there-be-another-us-government-shutdown-by-january-31/trades?fromBlock=81324000&toBlock=81325000"
```

### 响应示例

**GET /markets/{slug}**
```json
{
  "market_id": 1,
  "slug": "will-there-be-another-us-government-shutdown-by-january-31",
  "condition_id": "0x43ec78527bd98a0588dd9455685b2cc82f5743140cb3a154603dc03c02b57de5",
  "question_id": "",
  "oracle": "",
  "collateral_token": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
  "yes_token_id": "52607315900507156846622820770453728082833251091510131025984187712529448877245",
  "no_token_id": "108988271800978168213949343685406694292284061166193819357568013088568150075789",
  "enable_neg_risk": false,
  "status": "active"
}
```

**GET /markets/{slug}/trades**
```json
[
  {
    "trade_id": 1,
    "market_id": 1,
    "tx_hash": "0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946",
    "log_index": 1263,
    "block_number": 81324595,
    "timestamp": "2026-01-07T06:47:29",
    "maker": "0x7bb244d0c70293E66dEe84f3D0623fbBbF7D682c",
    "taker": "0x38E59B36Aae31b164200d0Cad7C3fE5e0eE795E7",
    "side": "BUY",
    "outcome": "NO",
    "price": "0.77",
    "size": "13"
  }
]
```

## 数据库结构

### events 表
| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER | 主键 |
| slug | TEXT | 事件标识符 |
| title | TEXT | 事件标题 |
| neg_risk | BOOLEAN | 是否负风险事件 |
| created_at | TIMESTAMP | 创建时间 |

### markets 表
| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER | 主键 |
| event_id | INTEGER | 关联事件 ID |
| slug | TEXT | 市场标识符 |
| condition_id | TEXT | 链上条件 ID |
| question_id | TEXT | 链上问题 ID |
| oracle | TEXT | 预言机地址 |
| collateral_token | TEXT | 抵押品代币地址 |
| yes_token_id | TEXT | YES 头寸 Token ID |
| no_token_id | TEXT | NO 头寸 Token ID |
| enable_neg_risk | BOOLEAN | 是否负风险市场 |
| status | TEXT | 市场状态 |
| created_at | TIMESTAMP | 创建时间 |

### trades 表
| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER | 主键 |
| market_id | INTEGER | 关联市场 ID |
| tx_hash | TEXT | 交易哈希 |
| log_index | INTEGER | 日志索引 |
| block_number | INTEGER | 区块号 |
| token_id | TEXT | 交易的 Token ID |
| maker | TEXT | 挂单方地址 |
| taker | TEXT | 吃单方地址 |
| side | TEXT | 买卖方向 (BUY/SELL) |
| outcome | TEXT | 结果类型 (YES/NO) |
| price | TEXT | 成交价格 |
| size | TEXT | 成交数量 |
| timestamp | TIMESTAMP | 成交时间 |

### sync_state 表
| 字段 | 类型 | 描述 |
|------|------|------|
| key | TEXT | 状态键名 |
| last_block | INTEGER | 最后处理的区块 |
| updated_at | TIMESTAMP | 更新时间 |

## 合约地址

| 合约 | 地址 |
|------|------|
| CTF Exchange | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` |
| NegRisk Exchange | `0xC5d563A36AE78145C45a50134d48A1215220f80a` |
| CTF Contract | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` |
| USDC.e | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` |

## 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| RPC_URL | Polygon RPC URL | (必填) |
| DB_PATH | 数据库路径 | ./data/indexer.db |
| GAMMA_BASE_URL | Gamma API URL | https://gamma-api.polymarket.com |
| START_BLOCK | 起始区块 | 60000000 |
| BLOCK_BATCH | 批处理区块数 | 5000 |
| CONFIRMATIONS | 确认区块数 | 5 |

## 技术栈

- **Python 3.10+**
- **Web3.py** - 以太坊交互
- **FastAPI** - REST API 框架
- **SQLite** - 本地数据库
- **Requests** - HTTP 客户端

## License

MIT
