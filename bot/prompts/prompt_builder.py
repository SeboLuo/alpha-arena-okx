"""
提示词构建器 - 基于模板文件构建完整的提示词
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class PromptBuilder:
    """
    提示词构建器
    
    注意：占位符替换直接使用正则表达式完成，不需要分析器。
    占位符分析工具（PlaceholderAnalyzer）主要用于开发阶段的模板验证和文档生成。
    """
    
    # 占位符描述信息（硬编码，用于 get_required_fields）
    _PLACEHOLDER_DESCRIPTIONS = {
        # system.md
        'Exchange': '交易所名称',
        'MODEL_NAME': 'AI模型名称',
        'AssetUniverse': '资产范围',
        'StartingCapital': '起始资金',
        'MarketHours': '市场交易时间',
        'DecisionFrequency': '决策频率',
        'LeverageRange': '杠杆范围',
        'ContractType': '合约类型',
        'TradingFees': '交易手续费',
        'Slippage': '滑点',
        # user.md
        'MinutesElapsed': '已交易分钟数',
        'CurrentTime': '当前时间',
        'InvocationCount': '调用次数',
        'CoinSection': '币种数据区块（复合模板）',
        'CurrentTotalReturnPercent': '当前总回报百分比',
        'AvailableCash': '可用现金',
        'CurrentAccountValue': '当前账户总值',
        'Positions': '持仓列表（JSON数组）',
        # coin.md
        'Symbol': '币种符号',
        'CurrentPrice': '当前价格',
        'CurrentEMA20': '当前20周期EMA',
        'CurrentMACD': '当前MACD值',
        'CurrentRSI7': '当前7周期RSI',
        'OI_Latest': '最新持仓量',
        'OI_Avg': '平均持仓量',
        'FundingRate': '资金费率',
        'MidPrices': '中间价序列（JSON数组）',
        'EMA20Series': '20周期EMA序列（JSON数组）',
        'MACDSeries': 'MACD序列（JSON数组）',
        'RSI7Series': '7周期RSI序列（JSON数组）',
        'RSI14Series': '14周期RSI序列（JSON数组）',
        'EMA20_4h': '4小时20周期EMA',
        'EMA50_4h': '4小时50周期EMA',
        'ATR3_4h': '4小时3周期ATR',
        'ATR14_4h': '4小时14周期ATR',
        'CurrentVolume_4h': '4小时当前成交量',
        'AvgVolume_4h': '4小时平均成交量',
        'MACD4h': '4小时MACD序列（JSON数组）',
        'RSI14_4h': '4小时14周期RSI序列（JSON数组）',
    }
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent
        self.prompts_dir = Path(prompts_dir)
        
        # 加载模板文件
        self.system_template = self._load_template('system.md')
        self.user_template = self._load_template('user.md')
        self.coin_template = self._load_template('coin.md')
        
        # 占位符替换正则（支持 {{.Name}} 和 {{.Name | toJSON}} 格式）
        self.placeholder_pattern = re.compile(r'\{\{\s*\.([^}|]+?)(?:\s*\|\s*toJSON)?\s*\}\}')
    
    def _load_template(self, filename: str) -> str:
        """加载模板文件"""
        template_path = self.prompts_dir / filename
        if not template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_path}")
        return template_path.read_text(encoding='utf-8')
    
    def build_system_prompt(self, config: Dict[str, Any]) -> str:
        """
        构建系统提示词
        
        Args:
            config: 配置字典，包含以下字段：
                - exchange: 交易所名称
                - model_name: 模型名称
                - asset_universe: 资产范围
                - starting_capital: 起始资金
                - market_hours: 市场交易时间
                - decision_frequency: 决策频率
                - leverage_range: 杠杆范围
                - contract_type: 合约类型
                - trading_fees: 交易手续费
                - slippage: 滑点
        
        Returns:
            构建好的系统提示词
        """
        replacements = {
            'Exchange': config.get('exchange', 'OKX'),
            'MODEL_NAME': config.get('model_name', 'DeepSeek'),
            'AssetUniverse': config.get('asset_universe', 'BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, DOGE/USDT, XRP/USDT'),
            'StartingCapital': self._format_currency(config.get('starting_capital', 1000)),
            'MarketHours': config.get('market_hours', '24/7'),
            'DecisionFrequency': config.get('decision_frequency', 'Every 10 minutes'),
            'LeverageRange': config.get('leverage_range', '1-20x'),
            'ContractType': config.get('contract_type', 'Perpetual Swap'),
            'TradingFees': config.get('trading_fees', '0.02% maker, 0.05% taker'),
            'Slippage': config.get('slippage', '0.01-0.05%'),
        }
        
        return self._replace_placeholders(self.system_template, replacements)
    
    def build_coin_section(self, coin_data: Dict[str, Any]) -> str:
        """
        构建单个币种的数据区块
        
        Args:
            coin_data: 币种数据字典，包含以下字段：
                - symbol: 币种符号
                - current_price: 当前价格
                - current_ema20: 当前20周期EMA
                - current_macd: 当前MACD值
                - current_rsi7: 当前7周期RSI
                - oi_latest: 最新持仓量
                - oi_avg: 平均持仓量
                - funding_rate: 资金费率
                - mid_prices: 中间价序列（列表）
                - ema20_series: 20周期EMA序列（列表）
                - macd_series: MACD序列（列表）
                - rsi7_series: 7周期RSI序列（列表）
                - rsi14_series: 14周期RSI序列（列表）
                - ema20_4h: 4小时20周期EMA
                - ema50_4h: 4小时50周期EMA
                - atr3_4h: 4小时3周期ATR
                - atr14_4h: 4小时14周期ATR
                - current_volume_4h: 4小时当前成交量
                - avg_volume_4h: 4小时平均成交量
                - macd_4h: 4小时MACD序列（列表）
                - rsi14_4h: 4小时14周期RSI序列（列表）
        
        Returns:
            构建好的币种数据区块
        """
        # 根据示例格式，币种数据直接输出数值，不格式化
        replacements = {
            'Symbol': coin_data.get('symbol', 'BTC'),
            'CurrentPrice': coin_data.get('current_price', 0),
            'CurrentEMA20': coin_data.get('current_ema20', 0),
            'CurrentMACD': coin_data.get('current_macd', 0),
            'CurrentRSI7': coin_data.get('current_rsi7', 0),
            'OI_Latest': coin_data.get('oi_latest', 0),
            'OI_Avg': coin_data.get('oi_avg', 0),
            'FundingRate': coin_data.get('funding_rate', 0),  # 可能使用科学计数法
            'MidPrices': coin_data.get('mid_prices', []),
            'EMA20Series': coin_data.get('ema20_series', []),
            'MACDSeries': coin_data.get('macd_series', []),
            'RSI7Series': coin_data.get('rsi7_series', []),
            'RSI14Series': coin_data.get('rsi14_series', []),
            'EMA20_4h': coin_data.get('ema20_4h', 0),
            'EMA50_4h': coin_data.get('ema50_4h', 0),
            'ATR3_4h': coin_data.get('atr3_4h', 0),
            'ATR14_4h': coin_data.get('atr14_4h', 0),
            'CurrentVolume_4h': coin_data.get('current_volume_4h', 0),
            'AvgVolume_4h': coin_data.get('avg_volume_4h', 0),
            'MACD4h': coin_data.get('macd_4h', []),
            'RSI14_4h': coin_data.get('rsi14_4h', []),
        }
        
        return self._replace_placeholders(self.coin_template, replacements)
    
    def build_coin_sections(self, coins_data: list) -> str:
        """
        构建多个币种的数据区块
        
        Args:
            coins_data: 币种数据列表，每个元素都是币种数据字典
        
        Returns:
            所有币种数据区块拼接后的字符串
        """
        sections = []
        for coin_data in coins_data:
            section = self.build_coin_section(coin_data)
            sections.append(section)
        return '\n\n'.join(sections)
    
    def build_user_prompt(
        self,
        minutes_elapsed: int,
        current_time: Optional[str] = None,
        invocation_count: int = 0,
        coins_data: Optional[list] = None,
        current_total_return_percent: float = 0.0,
        available_cash: float = 0.0,
        current_account_value: float = 0.0,
        positions: Optional[list] = None
    ) -> str:
        """
        构建用户提示词
        
        Args:
            minutes_elapsed: 已交易分钟数
            current_time: 当前时间（字符串，如果为None则自动生成）
            invocation_count: 调用次数
            coins_data: 币种数据列表
            current_total_return_percent: 当前总回报百分比
            available_cash: 可用现金
            current_account_value: 当前账户总值
            positions: 持仓列表
        
        Returns:
            构建好的用户提示词
        """
        if current_time is None:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建币种区块
        coin_section = ""
        if coins_data:
            coin_section = self.build_coin_sections(coins_data)
        
        replacements = {
            'MinutesElapsed': str(minutes_elapsed),
            'CurrentTime': current_time,
            'InvocationCount': str(invocation_count),
            'CoinSection': coin_section,
            'CurrentTotalReturnPercent': self._format_percentage(current_total_return_percent / 100.0),
            'AvailableCash': self._format_currency(available_cash),
            'CurrentAccountValue': self._format_currency(current_account_value),
            'Positions': positions or [],
        }
        
        return self._replace_placeholders(self.user_template, replacements)
    
    def _replace_placeholders(self, template: str, replacements: Dict[str, Any]) -> str:
        """
        替换模板中的占位符
        
        Args:
            template: 模板字符串
            replacements: 替换值字典
        
        Returns:
            替换后的字符串
        """
        def replacer(match):
            full_match = match.group(0)
            placeholder_name = match.group(1).strip()
            has_json = 'toJSON' in full_match
            
            if placeholder_name not in replacements:
                # 如果找不到替换值，返回原始占位符（不修改模板）
                return full_match
            
            value = replacements[placeholder_name]
            
            # 如果需要JSON转换（示例格式是紧凑的，无缩进）
            if has_json:
                if isinstance(value, (list, dict)):
                    # 紧凑格式，与示例一致
                    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
                else:
                    # 如果不是可序列化对象，转换为JSON字符串
                    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            else:
                # 直接转换为字符串
                return str(value)
        
        return self.placeholder_pattern.sub(replacer, template)
    
    # ========== 格式化辅助方法 ==========
    
    def _format_currency(self, value: float) -> str:
        """格式化货币"""
        if value >= 1000000:
            return f"${value/1000000:.2f}M"
        elif value >= 1000:
            return f"${value/1000:.2f}K"
        else:
            return f"${value:,.2f}"
    
    def _format_price(self, value: float, decimals: int = 2) -> str:
        """格式化价格"""
        return f"{value:,.{decimals}f}"
    
    def _format_number(self, value: float) -> str:
        """格式化数字"""
        if value >= 1000000:
            return f"{value/1000000:.2f}M"
        elif value >= 1000:
            return f"{value/1000:.2f}K"
        else:
            return f"{value:,.2f}"
    
    def _format_percentage(self, value: float, decimals: int = 4) -> str:
        """格式化百分比"""
        return f"{value * 100:.{decimals}f}%"
    
    def _format_decimal(self, value: float, decimals: int = 4) -> str:
        """格式化小数"""
        return f"{value:.{decimals}f}"
    
    def get_required_fields(self, template_name: str) -> Dict[str, str]:
        """
        获取指定模板所需的所有字段
        
        Args:
            template_name: 模板名称 ('system', 'user', 'coin')
        
        Returns:
            字段名到描述的映射
        """
        if template_name == 'system':
            template = self.system_template
        elif template_name == 'user':
            template = self.user_template
        elif template_name == 'coin':
            template = self.coin_template
        else:
            raise ValueError(f"未知的模板名称: {template_name}")
        
        matches = self.placeholder_pattern.finditer(template)
        fields = {}
        
        for match in matches:
            name = match.group(1).strip()
            full = match.group(0)
            has_json = 'toJSON' in full
            
            # 从硬编码的描述字典获取描述
            description = self._PLACEHOLDER_DESCRIPTIONS.get(name, '')
            
            field_type = "JSON数组/对象" if has_json else "字符串/数字"
            fields[name] = f"{description} ({field_type})"
        
        return fields


def example_usage():
    """使用示例"""
    builder = PromptBuilder()
    
    # 1. 构建系统提示词
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
    print("系统提示词构建完成\n")
    
    # 2. 构建币种数据区块
    btc_data = {
        'symbol': 'BTC',
        'current_price': 95000.50,
        'current_ema20': 94800.00,
        'current_macd': 150.25,
        'current_rsi7': 65.5,
        'oi_latest': 1500000000,
        'oi_avg': 1450000000,
        'funding_rate': 0.0001,
        'mid_prices': [94500, 94600, 94700, 94800, 94900, 95000],
        'ema20_series': [94300, 94400, 94500, 94600, 94700, 94800],
        'macd_series': [100, 110, 120, 130, 140, 150],
        'rsi7_series': [60, 61, 62, 63, 64, 65],
        'rsi14_series': [58, 59, 60, 61, 62, 63],
        'ema20_4h': 94700.00,
        'ema50_4h': 94500.00,
        'atr3_4h': 500.00,
        'atr14_4h': 480.00,
        'current_volume_4h': 50000000,
        'avg_volume_4h': 48000000,
        'macd_4h': [120, 125, 130, 135, 140, 145],
        'rsi14_4h': [55, 56, 57, 58, 59, 60],
    }
    coin_section = builder.build_coin_section(btc_data)
    print("币种数据区块构建完成\n")
    
    # 3. 构建用户提示词
    user_prompt = builder.build_user_prompt(
        minutes_elapsed=120,
        invocation_count=12,
        coins_data=[btc_data],
        current_total_return_percent=5.5,
        available_cash=9500.0,
        current_account_value=10550.0,
        positions=[
            {
                'symbol': 'BTC',
                'quantity': 0.1,
                'entry_price': 94000.0,
                'current_price': 95000.50,
                'leverage': 10,
                'unrealized_pnl': 100.05
            }
        ]
    )
    print("用户提示词构建完成\n")
    
    return {
        'system': system_prompt,
        'user': user_prompt,
        'coin_section': coin_section
    }


if __name__ == "__main__":
    # 运行示例
    results = example_usage()
    
    # 打印部分内容验证
    print("=" * 80)
    print("系统提示词预览（前500字符）:")
    print("=" * 80)
    print(results['system'][:500])
    print("\n...\n")
    
    print("=" * 80)
    print("用户提示词预览（前500字符）:")
    print("=" * 80)
    print(results['user'][:500])
    print("\n...\n")

