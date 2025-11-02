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
        account_info = {
            'balance': sim_balance['balance'],
            'equity': sim_balance['equity'],
            'leverage': TRADE_CONFIG['leverage']
        }
        print(f"[模拟] 账户余额: {account_info['balance']:.2f} USDT")
    except Exception as e:
        print(f"[模拟] 获取账户信息失败: {e}")
        account_info = None

    # 3. 获取当前模拟持仓（从数据库计算）
    current_position = get_current_position()
    position_info = None
    if current_position:
        # 计算未实现盈亏（需要当前价格）
        if current_position['side'] == 'long':
            unrealized_pnl = (price_data['price'] - current_position['entry_price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
        else:  # short
            unrealized_pnl = (current_position['entry_price'] - price_data['price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
        
        position_info = {
            'side': current_position['side'],
            'size': current_position['size'],
            'entry_price': current_position['entry_price'],
            'unrealized_pnl': unrealized_pnl
        }
        print(f"[模拟] 当前持仓: {position_info['side']} {position_info['size']:.2f} 张, 未实现盈亏: {unrealized_pnl:+.2f} USDT")

    # 4. 使用DeepSeek分析（共享AI分析，带重试）
    signal_data = analyze_with_deepseek_with_retry(price_data)

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

    # 6. 更新模拟系统状态到Web界面
    try:
        sim_data_manager.update_system_status(
            status='running',
            account_info=account_info,
            btc_info={
                'price': price_data['price'],
                'change': price_data['price_change'],
                'timeframe': TRADE_CONFIG['timeframe'],
                'mode': '模拟交易-全仓-单向'
            },
            position=position_info,
            ai_signal={
                'signal': signal_data['signal'],
                'confidence': signal_data['confidence'],
                'reason': signal_data['reason'],
                'stop_loss': signal_data['stop_loss'],
                'take_profit': signal_data['take_profit']
            }
        )
        print("[模拟] ✅ 系统状态已更新到Web界面")
    except Exception as e:
        print(f"[模拟] 更新系统状态失败: {e}")

    # 7. 执行模拟智能交易
    execute_intelligent_trade(signal_data, price_data)


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

