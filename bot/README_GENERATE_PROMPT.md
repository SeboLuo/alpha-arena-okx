# 生成实时提示词脚本使用说明

## 功能

`generate_prompt_from_live_data.py` 脚本可以从OKX交易所获取最新的BTC数据，并生成完整的提示词保存到本地文件。

## 使用方法

### 1. 确保环境配置

确保已安装所有依赖：
```bash
pip install pandas ccxt python-dotenv openai
```

确保 `.env` 文件中配置了OKX API密钥：
```env
OKX_API_KEY=your_api_key
OKX_SECRET=your_secret
OKX_PASSWORD=your_password
```

### 2. 运行脚本

```bash
# 方式1：作为模块运行
python3 -m bot.generate_prompt_from_live_data

# 方式2：直接运行（如果在bot目录下）
cd bot
python3 generate_prompt_from_live_data.py
```

### 3. 输出文件

脚本会在项目根目录的 `output/` 文件夹中生成提示词文件：
- 文件名格式：`prompt_YYYYMMDD_HHMMSS.md`
- 包含完整的系统提示词和用户提示词

## 脚本流程

1. **获取实时数据**
   - 从OKX交易所获取最新BTC K线数据
   - 获取Open Interest和Funding Rate
   - 获取4小时时间框架数据

2. **数据转换**
   - 将价格数据转换为币种数据格式
   - 计算技术指标序列

3. **构建提示词**
   - 生成系统提示词（交易规则等）
   - 生成用户提示词（市场数据等）

4. **保存文件**
   - 保存到 `output/` 目录
   - 显示预览信息

## 示例输出

生成的文件将包含：
- 完整的系统提示词（交易规则、输出格式等）
- 实时市场数据（价格、技术指标、序列数据等）
- 账户信息和持仓信息

## 注意事项

- 需要网络连接访问OKX API
- 需要有效的API密钥和权限
- 如果获取数据失败，脚本会输出错误信息并提示

