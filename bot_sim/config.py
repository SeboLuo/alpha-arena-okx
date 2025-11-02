"""模拟交易配置文件 - 从环境变量读取TEST_MODE，配置模拟交易参数"""
import os
from dotenv import load_dotenv
from openai import OpenAI
# 注意：不导入ccxt，因为模拟交易不需要真实的交易所连接

load_dotenv()

# 初始化DeepSeek客户端（共享使用，不影响模拟交易）
deepseek_client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

# 交易参数配置 - 复用真实交易的配置
TRADE_CONFIG = {
    'symbol': 'BTC/USDT:USDT',  # OKX的合约符号格式
    'leverage': 10,  # 杠杆倍数,只影响保证金不影响下单价值
    'timeframe': '3m',  # 使用3分钟K线
    'interval_minutes': 3,  # 执行间隔（分钟），服务将在此时间间隔的整点执行
    'data_points': 96,  # 96根timeframe周期的K线（用于获取历史K线数据）
    'contract_size': 0.01,  # 合约乘数（BTC/USDT永续合约通常是0.01）
    'min_amount': 0.01,  # 最小交易量
    'initial_balance': 1000,  # 模拟账户初始余额（USDT），与实盘配置方式保持一致
    # 智能仓位参数（与实盘保持一致）
    'position_management': {
        'enable_intelligent_position': True,  # 是否启用智能仓位管理
        'base_usdt_amount': 100,  # USDT投入下单基数
        'high_confidence_multiplier': 1.5,
        'medium_confidence_multiplier': 1.0,
        'low_confidence_multiplier': 0.5,
        'max_position_ratio': 0.1,  # 单次最大仓位比例（10%）
        'trend_strength_multiplier': 1.2
    }
}

# 初始化模拟数据管理器
from sim_data_manager import sim_data_manager

# 全局变量存储历史数据（模拟交易可以共享使用）
price_history = []
signal_history = []
position = None

