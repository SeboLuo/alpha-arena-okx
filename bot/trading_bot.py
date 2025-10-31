"""主交易机器人模块"""
import time
from datetime import datetime
from .config import exchange, TRADE_CONFIG
from .exchange_setup import setup_exchange
from .market_data import get_btc_ohlcv_enhanced
from .position_manager import get_current_position
from .ai_analyzer import analyze_with_deepseek_with_retry
from .trade_executor import execute_intelligent_trade
from .utils import wait_for_next_period
from data_manager import update_system_status, save_ai_analysis_record


def trading_bot():
    """主交易机器人函数"""
    # 等待到整点再执行
    wait_seconds = wait_for_next_period(TRADE_CONFIG['interval_minutes'])
    if wait_seconds > 0:
        print(f"⏰ 等待 {wait_seconds} 秒到下一个整点...")
        # 分段等待，避免长时间阻塞导致进程退出
        while wait_seconds > 0:
            chunk = min(wait_seconds, 30)  # 每次最多等待30秒
            time.sleep(chunk)
            wait_seconds -= chunk
            if wait_seconds > 0:
                print(f"⏰ 剩余等待时间: {wait_seconds} 秒...")

    print("\n" + "=" * 60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 获取增强版K线数据
    price_data = get_btc_ohlcv_enhanced()
    if not price_data:
        print("❌ 获取K线数据失败，跳过本次执行")
        return False  # 返回False表示本次执行失败，但进程继续运行

    print(f"BTC当前价格: ${price_data['price']:,.2f}")
    print(f"数据周期: {TRADE_CONFIG['timeframe']}")
    print(f"价格变化: {price_data['price_change']:+.2f}%")

    # 2. 获取账户信息
    try:
        balance = exchange.fetch_balance()
        account_info = {
            'balance': float(balance['USDT'].get('free', 0)),
            'equity': float(balance['USDT'].get('total', 0)),
            'leverage': TRADE_CONFIG['leverage']
        }
    except Exception as e:
        print(f"获取账户信息失败: {e}")
        account_info = None

    # 3. 获取当前持仓
    current_position = get_current_position()
    position_info = None
    if current_position:
        position_info = {
            'side': current_position['side'],
            'size': current_position['size'],
            'entry_price': current_position['entry_price'],
            'unrealized_pnl': current_position['unrealized_pnl']
        }

    # 4. 使用DeepSeek分析（带重试）
    signal_data = analyze_with_deepseek_with_retry(price_data)

    if signal_data.get('is_fallback', False):
        print("⚠️ 使用备用交易信号")

    # 5. 保存AI分析历史记录
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
            'position_size': current_position['size'] if current_position else 0
        }
        save_ai_analysis_record(analysis_record)
        print("✅ AI分析记录已保存")
    except Exception as e:
        print(f"保存AI分析记录失败: {e}")

    # 6. 更新系统状态到Web界面
    try:
        update_system_status(
            status='running',
            account_info=account_info,
            btc_info={
                'price': price_data['price'],
                'change': price_data['price_change'],
                'timeframe': TRADE_CONFIG['timeframe'],
                'mode': '全仓-单向'
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
        print("✅ 系统状态已更新到Web界面")
    except Exception as e:
        print(f"更新系统状态失败: {e}")

    # 7. 执行智能交易
    execute_intelligent_trade(signal_data, price_data)


def main():
    """主函数"""
    print("BTC/USDT OKX自动交易机器人启动成功！")
    print("融合技术指标策略 + OKX实盘接口")

    if TRADE_CONFIG['test_mode']:
        print("当前为模拟模式，不会真实下单")
    else:
        print("实盘交易模式，请谨慎操作！")

    print(f"交易周期: {TRADE_CONFIG['timeframe']}")
    print("已启用完整技术指标分析和持仓跟踪功能")

    # 设置交易所
    if not setup_exchange():
        print("交易所初始化失败，程序退出")
        return
    
    # 初始化Web界面数据文件
    print("🌐 初始化Web界面数据...")
    try:
        # 获取初始账户信息
        balance = exchange.fetch_balance()
        initial_account = {
            'balance': float(balance['USDT'].get('free', 0)),
            'equity': float(balance['USDT'].get('total', 0)),
            'leverage': TRADE_CONFIG['leverage']
        }
        
        # 获取当前BTC价格
        ticker = exchange.fetch_ticker(TRADE_CONFIG['symbol'])
        initial_btc = {
            'price': float(ticker['last']),
            'change': float(ticker['percentage']) if ticker.get('percentage') else 0,
            'timeframe': TRADE_CONFIG['timeframe'],
            'mode': '全仓-单向'
        }
        
        # 获取当前持仓
        current_pos = get_current_position()
        initial_position = None
        if current_pos:
            initial_position = {
                'side': current_pos['side'],
                'size': current_pos['size'],
                'entry_price': current_pos['entry_price'],
                'unrealized_pnl': current_pos['unrealized_pnl']
            }
        
        # 初始化系统状态
        update_system_status(
            status='running',
            account_info=initial_account,
            btc_info=initial_btc,
            position=initial_position,
            ai_signal={
                'signal': 'HOLD',
                'confidence': 'N/A',
                'reason': '系统启动中，等待首次分析...',
                'stop_loss': 0,
                'take_profit': 0
            }
        )
        print("✅ Web界面数据初始化完成")
    except Exception as e:
        print(f"⚠️ Web界面数据初始化失败: {e}")
        print("继续运行，将在首次交易时创建数据")

    print(f"执行频率: 每{TRADE_CONFIG['interval_minutes']}分钟整点执行")

    # 循环执行（简化逻辑，避免冲突）
    while True:
        try:
            # 直接调用交易机器人，函数内部会处理等待逻辑
            result = trading_bot()
            
            # 如果执行成功，等待一段时间再检查
            if result is not False:
                print("✅ 本次交易分析执行完成，等待下一次执行...")
                time.sleep(60)  # 每分钟检查一次
            else:
                # 如果执行失败，等待更长时间再重试
                print("⚠️ 本次执行失败，等待5分钟后重试...")
                time.sleep(300)  # 5分钟后重试
                
        except Exception as e:
            print(f"交易机器人执行异常: {e}")
            # 异常后等待一段时间再重试
            time.sleep(300)  # 5分钟后重试


if __name__ == "__main__":
    main()

