# 提示词模板系统

这个目录包含提示词模板和相关的构建工具。

## 文件结构

- `system.md` - 系统提示词模板（角色定义、交易规则等）
- `user.md` - 用户提示词模板（市场数据、账户信息等）
- `coin.md` - 币种数据模板（单个币种的技术指标数据）
- `placeholder_analyzer.py` - 占位符分析工具
- `prompt_builder.py` - 提示词构建器

## 占位符分类

### 系统提示词 (system.md) - 10个占位符

| 占位符 | 类型 | 描述 |
|--------|------|------|
| `{{.Exchange}}` | STRING | 交易所名称 |
| `{{.MODEL_NAME}}` | STRING | AI模型名称 |
| `{{.AssetUniverse}}` | STRING | 资产范围 |
| `{{.StartingCapital}}` | CURRENCY | 起始资金 |
| `{{.MarketHours}}` | STRING | 市场交易时间 |
| `{{.DecisionFrequency}}` | STRING | 决策频率 |
| `{{.LeverageRange}}` | NUMBER | 杠杆范围 |
| `{{.ContractType}}` | STRING | 合约类型 |
| `{{.TradingFees}}` | STRING | 交易手续费 |
| `{{.Slippage}}` | STRING | 滑点 |

### 用户提示词 (user.md) - 8个占位符

| 占位符 | 类型 | 描述 | 需要JSON |
|--------|------|------|----------|
| `{{.MinutesElapsed}}` | TIME | 已交易分钟数 | ❌ |
| `{{.CurrentTime}}` | TIME | 当前时间 | ❌ |
| `{{.InvocationCount}}` | TIME | 调用次数 | ❌ |
| `{{.CoinSection}}` | TEMPLATE | 币种数据区块（复合模板） | ❌ |
| `{{.CurrentTotalReturnPercent}}` | PERCENTAGE | 当前总回报百分比 | ❌ |
| `{{.AvailableCash}}` | CURRENCY | 可用现金 | ❌ |
| `{{.CurrentAccountValue}}` | CURRENCY | 当前账户总值 | ❌ |
| `{{ .Positions \| toJSON }}` | JSON | 持仓列表 | ✅ |

### 币种数据模板 (coin.md) - 21个占位符

| 占位符 | 类型 | 描述 | 需要JSON |
|--------|------|------|----------|
| `{{.Symbol}}` | STRING | 币种符号 | ❌ |
| `{{.CurrentPrice}}` | CURRENCY | 当前价格 | ❌ |
| `{{.CurrentEMA20}}` | NUMBER | 当前20周期EMA | ❌ |
| `{{.CurrentMACD}}` | NUMBER | 当前MACD值 | ❌ |
| `{{.CurrentRSI7}}` | NUMBER | 当前7周期RSI | ❌ |
| `{{.OI_Latest}}` | NUMBER | 最新持仓量 | ❌ |
| `{{.OI_Avg}}` | NUMBER | 平均持仓量 | ❌ |
| `{{.FundingRate}}` | NUMBER | 资金费率 | ❌ |
| `{{ .MidPrices \| toJSON }}` | JSON | 中间价序列 | ✅ |
| `{{ .EMA20Series \| toJSON }}` | JSON | 20周期EMA序列 | ✅ |
| `{{ .MACDSeries \| toJSON }}` | JSON | MACD序列 | ✅ |
| `{{ .RSI7Series \| toJSON }}` | JSON | 7周期RSI序列 | ✅ |
| `{{ .RSI14Series \| toJSON }}` | JSON | 14周期RSI序列 | ✅ |
| `{{.EMA20_4h}}` | NUMBER | 4小时20周期EMA | ❌ |
| `{{.EMA50_4h}}` | NUMBER | 4小时50周期EMA | ❌ |
| `{{.ATR3_4h}}` | NUMBER | 4小时3周期ATR | ❌ |
| `{{.ATR14_4h}}` | NUMBER | 4小时14周期ATR | ❌ |
| `{{.CurrentVolume_4h}}` | NUMBER | 4小时当前成交量 | ❌ |
| `{{.AvgVolume_4h}}` | NUMBER | 4小时平均成交量 | ❌ |
| `{{ .MACD4h \| toJSON }}` | JSON | 4小时MACD序列 | ✅ |
| `{{ .RSI14_4h \| toJSON }}` | JSON | 4小时14周期RSI序列 | ✅ |

## 使用方法

### 1. 占位符分析工具（开发/调试用）

**注意**：`PlaceholderAnalyzer` 是一个**独立的开发和调试工具**，不是 `PromptBuilder` 的依赖。

**用途**：
- ✅ 开发阶段：验证模板完整性，检查占位符格式
- ✅ 文档生成：自动生成占位符列表和分类报告
- ✅ 调试：查看模板结构，排查问题
- ❌ **不用于运行时**：`PromptBuilder` 直接用正则表达式替换，不需要分析器

```python
from bot.prompts.placeholder_analyzer import PlaceholderAnalyzer

# 在开发/调试时使用
analyzer = PlaceholderAnalyzer()
analyzer.analyze()
analyzer.print_report()

# 或作为脚本运行
# python -m bot.prompts.placeholder_analyzer
```

### 2. 构建提示词

```python
from bot.prompts.prompt_builder import PromptBuilder

builder = PromptBuilder()

# 构建系统提示词
system_config = {
    'exchange': 'OKX',
    'model_name': 'DeepSeek-v2',
    'asset_universe': 'BTC/USDT, ETH/USDT, SOL/USDT',
    'starting_capital': 10000,
    'market_hours': '24/7',
    'decision_frequency': 'Every 10 minutes',
    'leverage_range': '1-20x',
    'contract_type': 'Perpetual Swap',
    'trading_fees': '0.02% maker, 0.05% taker',
    'slippage': '0.01-0.05%',
}
system_prompt = builder.build_system_prompt(system_config)

# 构建币种数据区块
btc_data = {
    'symbol': 'BTC',
    'current_price': 95000.50,
    'current_ema20': 94800.00,
    'current_macd': 150.25,
    'current_rsi7': 65.5,
    # ... 其他字段
    'mid_prices': [94500, 94600, 94700, 94800, 94900, 95000],
    'ema20_series': [94300, 94400, 94500, 94600, 94700, 94800],
    # ... 其他序列数据
}
coin_section = builder.build_coin_section(btc_data)

# 构建用户提示词
user_prompt = builder.build_user_prompt(
    minutes_elapsed=120,
    invocation_count=12,
    coins_data=[btc_data],
    current_total_return_percent=5.5,
    available_cash=9500.0,
    current_account_value=10550.0,
    positions=[...]
)
```

## 占位符替换规则

1. **普通占位符**: 直接替换为字符串值
   - `{{.Symbol}}` → `"BTC"`

2. **JSON占位符**: 自动转换为JSON格式
   - `{{ .Positions \| toJSON }}` → JSON数组字符串

3. **数值格式化**: 根据类型自动格式化
   - 货币: `$1,000.00` 或 `$1.00K`
   - 百分比: `5.50%`
   - 数字: 保留适当小数位

## 注意事项

1. **模板不可修改**: 请勿直接修改模板文件中的任何字符，包括占位符格式
2. **占位符格式**: 支持 `{{.Name}}` 和 `{{ .Name \| toJSON }}` 两种格式
3. **缺失值处理**: 如果某个占位符没有提供值，将保留原始占位符文本（不替换）
4. **JSON序列化**: 带 `\| toJSON` 的占位符会自动将列表/字典序列化为JSON字符串

## API参考

### PromptBuilder 类

- `build_system_prompt(config)`: 构建系统提示词
- `build_coin_section(coin_data)`: 构建单个币种数据区块
- `build_coin_sections(coins_data)`: 构建多个币种数据区块
- `build_user_prompt(...)`: 构建用户提示词
- `get_required_fields(template_name)`: 获取模板所需字段列表

### PlaceholderAnalyzer 类（开发工具）

**注意**：这是开发阶段的工具，不是 `PromptBuilder` 的运行时依赖。

- `analyze()`: 分析所有模板文件中的占位符
- `print_report()`: 打印分析报告
- `_generate_report()`: 生成分析报告字典

**何时使用**：
- 修改模板后验证占位符
- 生成文档和报告
- 调试模板问题

