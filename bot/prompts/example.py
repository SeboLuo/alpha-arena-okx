"""
提示词构建示例

演示如何使用 PromptBuilder 构建提示词
"""

from bot.prompts import PromptBuilder


def main():
    builder = PromptBuilder()
    
    print("=" * 80)
    print("示例1: 构建系统提示词")
    print("=" * 80)
    
    system_config = {
        'exchange': 'OKX',
        'model_name': 'DeepSeek-v2',
        'asset_universe': 'BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, DOGE/USDT, XRP/USDT',
        'starting_capital': 10000,
        'market_hours': '24/7',
        'decision_frequency': 'Every 10 minutes',
        'leverage_range': '1-20x',
        'contract_type': 'Perpetual Swap',
        'trading_fees': '0.02% maker, 0.05% taker',
        'slippage': '0.01-0.05%',
    }
    
    system_prompt = builder.build_system_prompt(system_config)
    print(f"系统提示词长度: {len(system_prompt)} 字符")
    print(f"前200字符预览:\n{system_prompt[:200]}...\n")
    
    print("=" * 80)
    print("示例2: 构建币种数据区块")
    print("=" * 80)
    
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
    print(f"币种数据区块长度: {len(coin_section)} 字符")
    print(f"前300字符预览:\n{coin_section[:300]}...\n")
    
    print("=" * 80)
    print("示例3: 构建用户提示词")
    print("=" * 80)
    
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
    
    print(f"用户提示词长度: {len(user_prompt)} 字符")
    print(f"前300字符预览:\n{user_prompt[:300]}...\n")
    
    print("=" * 80)
    print("示例4: 获取所需字段")
    print("=" * 80)
    
    for template_name in ['system', 'user', 'coin']:
        fields = builder.get_required_fields(template_name)
        print(f"\n{template_name.upper()} 模板所需字段 ({len(fields)} 个):")
        for field, desc in fields.items():
            print(f"  - {field}: {desc}")


if __name__ == "__main__":
    main()

