# Polymarket 链上解码器（Stage 1）

一个面向 Polymarket 的链上数据解析项目，聚焦两类核心能力：
- 交易解码：从交易哈希还原 `OrderFilled` 成交详情。
- 市场解码：从市场信息或链上日志恢复 `conditionId`、`questionId`、`YES/NO TokenId`。

适合用于：
- 链上数据分析与研究
- 交易索引器/监控系统原型
- 预测市场数据工程练习

## 功能亮点

- 支持 Polymarket 两类交易所合约（CTF Exchange / NegRisk CTF Exchange）
- 自动过滤重复统计日志（`taker == exchange`）
- 自动计算 `price`、`side`、`token_id`
- 支持通过 Gamma API 与链上推导结果做一致性校验
- 提供一条命令跑通的 Demo 脚本

## 技术栈

- Python
- web3.py
- requests
- python-dotenv

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

在 `.env` 中填写：

```env
RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY
GAMMA_BASE_URL=https://gamma.polymarket.com
```

## 使用示例

### 交易解码

```bash
python -m src.trade_decoder \
  --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946
```

输出到文件：

```bash
python -m src.trade_decoder \
  --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
  --output ./data/trades.json
```

### 市场解码

通过市场 slug：

```bash
python -m src.market_decoder \
  --market-slug will-there-be-another-us-government-shutdown-by-january-31
```

通过链上 `ConditionPreparation` 日志：

```bash
python -m src.market_decoder \
  --tx-hash <condition_preparation_tx_hash> \
  --log-index <log_index>
```

### 一体化 Demo

```bash
python -m src.demo \
  --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
  --event-slug will-there-be-another-us-government-shutdown-by-january-31 \
  --output ./data/demo_output.json
```

## 输出结构

### Trade Decoder

字段包含：
- `tx_hash`, `log_index`, `exchange`, `order_hash`
- `maker`, `taker`
- `maker_asset_id`, `taker_asset_id`
- `maker_amount`, `taker_amount`, `fee`
- `price`, `token_id`, `side`

### Market Decoder

字段包含：
- `conditionId`, `oracle`, `questionId`, `outcomeSlotCount`
- `collateralToken`, `yesTokenId`, `noTokenId`
- `gamma`

## 项目结构

```text
stage1/
├─ src/
│  ├─ trade_decoder.py      # 交易日志解码
│  ├─ market_decoder.py     # 市场参数解码
│  ├─ demo.py               # 综合演示入口
│  ├─ ctf/derive.py         # CTF tokenId 推导
│  ├─ indexer/gamma.py      # Gamma API 封装
│  └─ utils/rpc.py          # RPC 连接与回执读取
├─ data/                    # 输出样例
├─ fixtures/                # 本地固化测试数据
├─ requirements.txt
└─ .env.example
```

## 常见问题

- 报错 `RPC_URL not configured in .env`
  - 说明 `.env` 未配置或未生效。

- 报错 `TokenId mismatch: calculated vs Gamma API`
  - 说明输入市场信息与链上推导结果不一致，需检查 `slug` 或数据来源。

- Gamma 请求失败
  - 检查网络与 `GAMMA_BASE_URL` 配置。

## 免责声明

本项目用于学习与工程实践，不构成任何投资建议或交易建议。
