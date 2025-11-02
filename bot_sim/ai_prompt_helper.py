"""模拟交易模式的AI提示词参数准备辅助模块"""
from datetime import datetime
from bot.ai_analyzer import _convert_price_data_to_coin_data, _start_time, _invocation_count
from bot.prompts import PromptBuilder
from .position_manager import get_current_position
from .config import TRADE_CONFIG
from sim_data_manager import sim_data_manager


def _prepare_user_prompt_params_sim(price_data, coin_data):
    """为模拟交易模式准备用户提示词参数（覆盖bot.ai_analyzer中的函数）"""
    global _start_time, _invocation_count
    
    # 初始化开始时间
    if _start_time is None:
        _start_time = datetime.now()
    
    # 计算已过分钟数
    elapsed = (datetime.now() - _start_time).total_seconds() / 60
    
    # 增加调用计数
    _invocation_count += 1
    
    # 获取模拟持仓信息（从模拟数据管理器）
    current_pos = get_current_position()
    positions = []
    if current_pos:
        # 计算未实现盈亏
        if current_pos['side'] == 'long':
            unrealized_pnl = (float(price_data['price']) - current_pos['entry_price']) * current_pos['size'] * TRADE_CONFIG.get('contract_size', 0.01)
        else:  # short
            unrealized_pnl = (current_pos['entry_price'] - float(price_data['price'])) * current_pos['size'] * TRADE_CONFIG.get('contract_size', 0.01)
        
        positions = [{
            'symbol': 'BTC',
            'side': current_pos.get('side', 'long'),
            'size': current_pos.get('size', 0),
            'entry_price': current_pos.get('entry_price', 0),
            'current_price': float(price_data['price']),
            'unrealized_pnl': unrealized_pnl,
            'leverage': current_pos.get('leverage', TRADE_CONFIG['leverage']),
        }]
        print(f"[模拟] AI提示词包含持仓: {positions[0]}")
    
    # 获取模拟账户信息（从数据库）
    try:
        sim_balance = sim_data_manager.get_sim_balance()
        available_cash = sim_balance['balance']
        current_account_value = sim_balance['equity']
        
        # 计算总回报（简化处理，可以从历史记录计算）
        initial_balance = TRADE_CONFIG.get('initial_balance', 1000)
        current_total_return_percent = ((current_account_value - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0.0
    except Exception as e:
        print(f"[模拟] 获取模拟账户信息失败: {e}")
        available_cash = 0.0
        current_account_value = TRADE_CONFIG.get('initial_balance', 1000)
        current_total_return_percent = 0.0
    
    return {
        'minutes_elapsed': int(elapsed),
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'invocation_count': _invocation_count,
        'coins_data': [coin_data],
        'current_total_return_percent': current_total_return_percent,
        'available_cash': available_cash,
        'current_account_value': current_account_value,
        'positions': positions,
    }

