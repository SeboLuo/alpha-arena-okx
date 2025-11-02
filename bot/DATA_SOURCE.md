# 数据来源说明

本文档说明提示词中币种数值的数据来源。

## 数据来源概览

**所有币种数值数据均来自OKX交易所接口**，然后经过本地计算得到技术指标。

## 详细数据来源

### 1. 主时间框架数据（如10分钟K线）

**来源：** `bot/market_data.py` → `get_btc_ohlcv_enhanced()`

- **OKX API调用：** `exchange.fetch_ohlcv(symbol, timeframe, limit=96)`
- **获取的数据：**
  - 开盘价 (open)
  - 最高价 (high)
  - 最低价 (low)
  - 收盘价 (close)
  - 成交量 (volume)
  - 时间戳 (timestamp)

- **本地计算的技术指标：**
  - EMA20 (指数移动平均)
  - MACD (从EMA12和EMA26计算)
  - RSI7 (7周期相对强弱指标)
  - RSI14 (14周期相对强弱指标)
  - SMA (简单移动平均)

**对应到提示词中的字段：**
- `current_price` → 来自OKX的K线收盘价
- `current_ema20` → 基于OKX数据本地计算
- `current_macd` → 基于OKX数据本地计算
- `current_rsi7` → 基于OKX数据本地计算
- `mid_prices` → 基于OKX的high和low计算
- `ema20_series` → 基于OKX数据本地计算
- `macd_series` → 基于OKX数据本地计算
- `rsi7_series` → 基于OKX数据本地计算
- `rsi14_series` → 基于OKX数据本地计算

### 2. Open Interest 和 Funding Rate

**来源：** `bot/ai_analyzer.py` → `_get_oi_and_funding_rate()`

- **OKX API调用：**
  - `exchange.fetch_ticker(symbol)` → 获取持仓量
  - `exchange.fetch_funding_rate(symbol)` → 获取资金费率

- **获取的数据：**
  - `oi_latest` → 最新持仓量（来自ticker）
  - `oi_avg` → 平均持仓量（目前使用最新值）
  - `funding_rate` → 资金费率

**对应到提示词中的字段：**
- `OI_Latest` → 直接来自OKX API
- `OI_Avg` → 来自OKX API（简化处理）
- `FundingRate` → 直接来自OKX API

### 3. 4小时时间框架数据

**来源：** `bot/ai_analyzer.py` → `_get_4h_data()`

- **OKX API调用：** `exchange.fetch_ohlcv(symbol, '4h', limit=60)`
- **获取的数据：**
  - 4小时K线数据（OHLCV）

- **本地计算的技术指标：**
  - EMA20_4h
  - EMA50_4h
  - MACD_4h
  - RSI14_4h
  - ATR3_4h
  - ATR14_4h

**对应到提示词中的字段：**
- `EMA20_4h` → 基于OKX 4小时数据计算
- `EMA50_4h` → 基于OKX 4小时数据计算
- `ATR3_4h` → 基于OKX 4小时数据计算
- `ATR14_4h` → 基于OKX 4小时数据计算
- `CurrentVolume_4h` → 来自OKX 4小时K线
- `AvgVolume_4h` → 基于OKX 4小时数据计算平均值
- `MACD4h` → 基于OKX 4小时数据计算的序列
- `RSI14_4h` → 基于OKX 4小时数据计算的序列

## 数据流图

```
OKX交易所接口
    ↓
exchange.fetch_ohlcv() → 主时间框架K线数据
    ↓
本地计算技术指标 (EMA, MACD, RSI等)
    ↓
price_data (包含 full_data DataFrame)
    ↓
_convert_price_data_to_coin_data()
    ↓
coin_data (币种数据)
    ↓
PromptBuilder.build_coin_section()
    ↓
提示词中的币种数据区块
```

## 代码位置

1. **主K线数据获取：**
   - 文件：`bot/market_data.py`
   - 函数：`get_btc_ohlcv_enhanced()`
   - API调用：第16行 `exchange.fetch_ohlcv()`

2. **OI和Funding Rate获取：**
   - 文件：`bot/ai_analyzer.py`
   - 函数：`_get_oi_and_funding_rate()` (第24-53行)
   - API调用：
     - 第28行：`exchange.fetch_ticker()`
     - 第33行：`exchange.fetch_funding_rate()`

3. **4小时数据获取：**
   - 文件：`bot/ai_analyzer.py`
   - 函数：`_get_4h_data()` (第56-113行)
   - API调用：第60行 `exchange.fetch_ohlcv(symbol, '4h')`

4. **数据转换：**
   - 文件：`bot/ai_analyzer.py`
   - 函数：`_convert_price_data_to_coin_data()` (第116-212行)

## 总结

✅ **所有币种数值数据的原始来源都是OKX交易所接口**

- 价格数据：来自 `exchange.fetch_ohlcv()`
- 持仓量：来自 `exchange.fetch_ticker()`
- 资金费率：来自 `exchange.fetch_funding_rate()`

- 技术指标：基于OKX的原始数据本地计算得出
  - EMA、MACD、RSI等都是在本地使用pandas计算的
  - 计算逻辑在 `bot/technical_analysis.py` 中

**没有使用模拟数据或硬编码数据，所有数值都来自实时交易所接口。**

