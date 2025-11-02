"""模拟主交易机器人模块"""
import time
from datetime import datetime
from .config import TRADE_CONFIG, deepseek_client
# 注意：不导入exchange和setup_exchange，因为模拟交易不需要真实交易所连接
from bot.market_data import get_btc_ohlcv_enhanced  # 共享市场数据获取
from bot.ai_analyzer import analyze_with_deepseek_with_retry  # 共享AI分析
from bot.utils import wait_for_next_period  # 共享工具函数
from .position_manager import get_current_position
from .trade_executor import execute_intelligent_trade
from sim_data_manager import sim_data_manager


def trading_bot():
    """模拟主交易机器人函数"""
    # 等待到整点再执行
    wait_seconds = wait_for_next_period(TRADE_CONFIG['interval_minutes'])
    if wait_seconds > 0:
        print(f"[模拟] ⏰ 等待 {wait_seconds} 秒到下一个整点...")
        # 分段等待，避免长时间阻塞导致进程退出
        while wait_seconds > 0:
            chunk = min(wait_seconds, 30)  # 每次最多等待30秒
            time.sleep(chunk)
            wait_seconds -= chunk
            if wait_seconds > 0:
                print(f"[模拟] ⏰ 剩余等待时间: {wait_seconds} 秒...")

    print("\n" + "=" * 60)
    print(f"[模拟] 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 获取增强版K线数据（共享市场数据）
    price_data = get_btc_ohlcv_enhanced()
    if not price_data:
        print("[模拟] ❌ 获取K线数据失败，跳过本次执行")
        return False  # 返回False表示本次执行失败，但进程继续运行

    print(f"[模拟] BTC当前价格: ${price_data['price']:,.2f}")
    print(f"[模拟] 数据周期: {TRADE_CONFIG['timeframe']}")
    print(f"[模拟] 价格变化: {price_data['price_change']:+.2f}%")

    # 2. 获取模拟账户信息（从数据库）
    try:
        sim_balance = sim_data_manager.get_sim_balance()
        base_balance = sim_balance['balance']  # 基础余额（总余额）
        leverage = TRADE_CONFIG['leverage']
        
        account_info = {
            'balance': base_balance,
            'leverage': leverage
        }
        print(f"[模拟] 账户总余额: {base_balance:.2f} USDT")
    except Exception as e:
        print(f"[模拟] 获取账户信息失败: {e}")
        account_info = None
        base_balance = 0
        leverage = TRADE_CONFIG['leverage']

    # 3. 获取当前模拟持仓（从数据库计算）
    current_position = get_current_position()
    position_info = None
    unrealized_pnl = 0
    used_margin = 0  # 占用保证金
    
    if current_position:
        # 计算未实现盈亏（需要当前价格）
        if current_position['side'] == 'long':
            unrealized_pnl = (price_data['price'] - current_position['entry_price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
        else:  # short
            unrealized_pnl = (current_position['entry_price'] - price_data['price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
        
        # 计算占用保证金：合约价值 / 杠杆
        # 合约价值 = 持仓数量 * 当前价格 * 合约乘数
        position_value = current_position['size'] * price_data['price'] * TRADE_CONFIG.get('contract_size', 0.01)
        used_margin = position_value / leverage
        
        position_info = {
            'side': current_position['side'],
            'size': current_position['size'],
            'entry_price': current_position['entry_price'],
            'unrealized_pnl': unrealized_pnl
        }
        print(f"[模拟] 当前持仓: {position_info['side']} {position_info['size']:.2f} 张")
        print(f"[模拟] 占用保证金: {used_margin:.2f} USDT, 未实现盈亏: {unrealized_pnl:+.2f} USDT")
    
    # 计算账户净值（Equity）= 总余额 + 未实现盈亏
    equity = base_balance + unrealized_pnl
    # 计算可用余额（Available Cash）= 总余额 - 占用保证金
    available_cash = base_balance - used_margin
    
    if account_info:
        account_info['equity'] = equity
        account_info['available_cash'] = available_cash
        account_info['used_margin'] = used_margin
        print(f"[模拟] 账户净值: {equity:.2f} USDT, 可用余额: {available_cash:.2f} USDT")

    # 4. 使用DeepSeek分析（共享AI分析，带重试）
    # 传递模拟持仓和账户数据给AI分析器，以便在提示词中正确显示
    sim_account_info = {
        'balance': base_balance,
        'equity': equity,
        'available_cash': available_cash,
        'used_margin': used_margin
    } if account_info else None
    
    position_info_for_ai = position_info if position_info else None
    
    signal_data = analyze_with_deepseek_with_retry(
        price_data, 
        position_data=position_info_for_ai,
        account_data=sim_account_info
    )

    if signal_data.get('is_fallback', False):
        print("[模拟] ⚠️ 使用备用交易信号")

    # 5. 保存AI分析历史记录（模拟系统，包含完整提示词和响应）
    try:
        analysis_record = {
            'signal': signal_data['signal'],
            'confidence': signal_data['confidence'],
            'reason': signal_data['reason'],
            'stop_loss': signal_data['stop_loss'],
            'take_profit': signal_data['take_profit'],
            'btc_price': price_data['price'],
            'price_change': price_data['price_change'],
            'has_position': current_position is not None,
            'position_side': current_position['side'] if current_position else None,
            'position_size': current_position['size'] if current_position else 0,
            'mode': 'simulation',
            # 保存完整提示词和响应
            'system_prompt': signal_data.get('system_prompt', ''),
            'user_prompt': signal_data.get('user_prompt', ''),
            'ai_response': signal_data.get('ai_response', '')
        }
        sim_data_manager.save_ai_analysis_record(analysis_record)
        print("[模拟] ✅ AI分析记录已保存（包含完整提示词和响应）")
    except Exception as e:
        print(f"[模拟] 保存AI分析记录失败: {e}")

    # 6. 执行模拟智能交易（先执行交易，再更新状态）
    execute_intelligent_trade(signal_data, price_data)

    # 7. 交易执行后，重新获取最新的账户和持仓信息并更新系统状态
    try:
        # 重新获取最新的模拟账户余额（交易后可能已变化）
        updated_sim_balance = sim_data_manager.get_sim_balance()
        updated_base_balance = updated_sim_balance['balance']
        
        # 重新获取最新的持仓（交易后可能已变化）
        updated_position = get_current_position()
        updated_position_info = None
        updated_unrealized_pnl = 0
        updated_used_margin = 0
        
        if updated_position:
            # 重新计算未实现盈亏
            if updated_position['side'] == 'long':
                updated_unrealized_pnl = (price_data['price'] - updated_position['entry_price']) * updated_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
            else:  # short
                updated_unrealized_pnl = (updated_position['entry_price'] - price_data['price']) * updated_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
            
            # 重新计算占用保证金
            updated_position_value = updated_position['size'] * price_data['price'] * TRADE_CONFIG.get('contract_size', 0.01)
            updated_used_margin = updated_position_value / TRADE_CONFIG['leverage']
            
            updated_position_info = {
                'side': updated_position['side'],
                'size': updated_position['size'],
                'entry_price': updated_position['entry_price'],
                'unrealized_pnl': updated_unrealized_pnl
            }
        
        # 重新计算账户净值和可用余额
        updated_equity = updated_base_balance + updated_unrealized_pnl
        updated_available_cash = updated_base_balance - updated_used_margin
        
        updated_account_info = {
            'balance': updated_base_balance,
            'equity': updated_equity,
            'available_cash': updated_available_cash,
            'leverage': TRADE_CONFIG['leverage']
        }
        
        # 更新模拟系统状态到Web界面（使用最新的账户和持仓信息）
        sim_data_manager.update_system_status(
            status='running',
            account_info=updated_account_info,
            btc_info={
                'price': price_data['price'],
                'change': price_data['price_change'],
                'timeframe': TRADE_CONFIG['timeframe'],
                'mode': '模拟交易-全仓-单向'
            },
            position=updated_position_info,
            ai_signal={
                'signal': signal_data['signal'],
                'confidence': signal_data['confidence'],
                'reason': signal_data['reason'],
                'stop_loss': signal_data['stop_loss'],
                'take_profit': signal_data['take_profit']
            }
        )
        print("[模拟] ✅ 系统状态已更新到Web界面（交易后最新数据）")
    except Exception as e:
        print(f"[模拟] 更新系统状态失败: {e}")


def main():
    """模拟交易主函数"""
    print("=" * 60)
    print("BTC/USDT 模拟交易机器人启动成功！")
    print("融合技术指标策略 + 完全模拟交易系统")
    print("=" * 60)
    print("[模拟] 当前为模拟模式，不会真实下单")
    print(f"[模拟] 交易周期: {TRADE_CONFIG['timeframe']}")
    print("[模拟] 已启用完整技术指标分析和持仓跟踪功能")

    # 初始化模拟账户（如果不存在）
    sim_balance = sim_data_manager.get_sim_balance()
    print(f"[模拟] 模拟账户余额: {sim_balance['balance']:.2f} USDT")

    # 初始化Web界面数据
    print("[模拟] 🌐 初始化Web界面数据...")
    try:
        # 获取当前BTC价格（需要导入真实交易所来获取价格，但这里我们可以先跳过）
        # 或者使用模拟数据管理器获取上次的价格
        initial_account = {
            'balance': sim_balance['balance'],
            'equity': sim_balance['equity'],
            'leverage': TRADE_CONFIG['leverage']
        }
        
        # 获取当前持仓
        current_pos = get_current_position()
        initial_position = None
        if current_pos:
            initial_position = {
                'side': current_pos['side'],
                'size': current_pos['size'],
                'entry_price': current_pos['entry_price'],
                'unrealized_pnl': 0  # 需要当前价格才能计算
            }
        
        # 初始化模拟系统状态
        sim_data_manager.update_system_status(
            status='running',
            account_info=initial_account,
            btc_info={
                'price': 0,
                'change': 0,
                'timeframe': TRADE_CONFIG['timeframe'],
                'mode': '模拟交易-全仓-单向'
            },
            position=initial_position,
            ai_signal={
                'signal': 'HOLD',
                'confidence': 'N/A',
                'reason': '模拟交易系统启动中，等待首次分析...',
                'stop_loss': 0,
                'take_profit': 0
            }
        )
        print("[模拟] ✅ Web界面数据初始化完成")
    except Exception as e:
        print(f"[模拟] ⚠️ Web界面数据初始化失败: {e}")
        print("[模拟] 继续运行，将在首次交易时创建数据")

    print(f"[模拟] 执行频率: 每{TRADE_CONFIG['interval_minutes']}分钟整点执行")
    print("[模拟] 开始模拟交易循环...")

    # 循环执行
    while True:
        try:
            # 直接调用交易机器人，函数内部会处理等待逻辑
            result = trading_bot()
            
            # 如果执行成功，等待一段时间再检查
            if result is not False:
                print("[模拟] ✅ 本次交易分析执行完成，等待下一次执行...")
                time.sleep(60)  # 每分钟检查一次
            else:
                # 如果执行失败，等待更长时间再重试
                print("[模拟] ⚠️ 本次执行失败，等待5分钟后重试...")
                time.sleep(300)  # 5分钟后重试
                
        except Exception as e:
            print(f"[模拟] 交易机器人执行异常: {e}")
            import traceback
            traceback.print_exc()
            # 异常后等待一段时间再重试
            time.sleep(300)  # 5分钟后重试


if __name__ == "__main__":
    main()

