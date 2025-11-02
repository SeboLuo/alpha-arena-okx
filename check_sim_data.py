#!/usr/bin/env python3
"""检查模拟交易数据的脚本"""
import os
from dotenv import load_dotenv

load_dotenv()

TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'
print(f"当前 TEST_MODE = {os.getenv('TEST_MODE')}")

if TEST_MODE:
    from sim_data_manager import sim_data_manager
    print("\n✅ 使用模拟交易数据管理器")
    
    # 检查系统状态
    status = sim_data_manager.get_system_status()
    print(f"\n系统状态:")
    print(f"  - 状态: {status.get('status', 'N/A')}")
    if status.get('account_info'):
        print(f"  - 账户余额: {status['account_info'].get('balance', 'N/A')} USDT")
    if status.get('btc_info'):
        print(f"  - BTC价格: {status['btc_info'].get('price', 'N/A')}")
    if status.get('ai_signal'):
        print(f"  - AI信号: {status['ai_signal'].get('signal', 'N/A')}")
    
    # 检查交易历史
    trades = sim_data_manager.get_trade_history(page=1, page_size=10)
    print(f"\n交易历史:")
    print(f"  - 总记录数: {trades.get('total', 0)}")
    if trades.get('data'):
        print(f"  - 最近交易:")
        for trade in trades['data'][:3]:
            print(f"    * {trade.get('timestamp', 'N/A')}: {trade.get('signal', 'N/A')} @ {trade.get('price', 'N/A')}")
    
    # 检查绩效
    perf = sim_data_manager.get_performance()
    print(f"\n绩效数据:")
    print(f"  - 总交易数: {perf.get('total_trades', 0)}")
    print(f"  - 总盈亏: {perf.get('total_pnl', 0):.2f} USDT")
    
else:
    from data_manager import data_manager
    print("\n⚠️ 使用真实交易数据管理器（不是模拟交易）")
