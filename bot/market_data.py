"""市场数据获取模块"""
import pandas as pd
import ccxt
from datetime import datetime
from .config import exchange, TRADE_CONFIG
from .technical_analysis import (
    calculate_technical_indicators,
    get_market_trend,
    get_support_resistance_levels
)


def get_btc_ohlcv_enhanced():
    """增强版：获取BTC K线数据并计算技术指标"""
    try:
        # 尝试获取K线数据（K线数据是公开的，不需要认证）
        print(f"正在获取K线数据: {TRADE_CONFIG['symbol']}, {TRADE_CONFIG['timeframe']}")
        
        # 首先尝试直接获取K线（不加载markets，避免触发currencies接口）
        ohlcv = None
        first_error = None
        try:
            # 直接调用fetch_ohlcv，不加载markets
            ohlcv = exchange.fetch_ohlcv(
                TRADE_CONFIG['symbol'], 
                TRADE_CONFIG['timeframe'],
                limit=TRADE_CONFIG['data_points']
            )
            print(f"✓ K线数据获取成功: {len(ohlcv)} 条记录")
        except Exception as e:
            first_error = e
            # 如果失败，尝试使用公共API（不认证）
            print(f"⚠️ 认证API失败，尝试使用公共API...")
            try:
                print("   尝试使用公共API（不认证）获取K线数据...")
                public_exchange = ccxt.okx({
                    'options': {
                        'defaultType': 'swap',
                    },
                    # 不提供API密钥，使用公共接口
                })
                ohlcv = public_exchange.fetch_ohlcv(
                    TRADE_CONFIG['symbol'], 
                    TRADE_CONFIG['timeframe'],
                    limit=TRADE_CONFIG['data_points']
                )
                print(f"✓ 公共API成功: 获取到 {len(ohlcv)} 条K线数据")
            except Exception as public_error:
                # 如果公共API也失败，使用第一个错误进行详细分析
                api_error = first_error
                error_str = str(api_error)
                print(f"\n❌ API调用失败（认证和公共API都失败）")
                print(f"错误信息: {error_str}")
                print(f"错误类型: {type(api_error).__name__}")
                
                # 详细错误分析
                if hasattr(api_error, 'status'):
                    print(f"HTTP状态码: {api_error.status}")
                
                if hasattr(api_error, 'response'):
                    print(f"API响应: {api_error.response}")
                
                # 提供解决建议
                error_lower = error_str.lower()
                if '401' in error_str or 'unauthorized' in error_lower or 'auth' in error_lower:
                    print("\n⚠️ API密钥认证失败")
                    print("   请检查.env文件中的配置：")
                    print("   - OKX_API_KEY")
                    print("   - OKX_SECRET") 
                    print("   - OKX_PASSWORD (这是创建API时设置的passphrase)")
                    print("\n   注意：密码(passphrase)与登录密码不同，是创建API密钥时设置的")
                elif '403' in error_str or 'forbidden' in error_lower:
                    print("\n⚠️ API权限不足或被拒绝")
                    print("   可能原因：")
                    print("   1. API密钥没有读取权限")
                    print("   2. IP地址未添加到白名单（如果设置了）")
                    print("   3. API密钥已过期或被禁用")
                elif '429' in error_str or 'rate limit' in error_lower:
                    print("\n⚠️ API调用频率限制")
                    print("   请稍后重试（等待几分钟）")
                elif 'currencies' in error_str:
                    print("\n⚠️ 获取币种信息失败")
                    print("   这可能是因为：")
                    print("   1. 网络连接问题")
                    print("   2. OKX API服务暂时不可用")
                    print("   3. API密钥配置问题")
                    print("\n   建议：")
                    print("   - 运行 'python3 -m bot.test_okx_connection' 进行详细诊断")
                    print("   - 检查.env文件中的API配置是否正确")
                    print("   - 确认网络可以访问 www.okx.com")
                
                raise api_error
        
        if ohlcv is None:
            raise ValueError("未能获取K线数据")

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 计算技术指标
        df = calculate_technical_indicators(df)

        current_data = df.iloc[-1]
        previous_data = df.iloc[-2]

        # 获取技术分析数据
        trend_analysis = get_market_trend(df)
        levels_analysis = get_support_resistance_levels(df)

        return {
            'price': current_data['close'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'high': current_data['high'],
            'low': current_data['low'],
            'volume': current_data['volume'],
            'timeframe': TRADE_CONFIG['timeframe'],
            'price_change': ((current_data['close'] - previous_data['close']) / previous_data['close']) * 100,
            'kline_data': df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(10).to_dict('records'),
            'technical_data': {
                'sma_5': current_data.get('sma_5', 0),
                'sma_20': current_data.get('sma_20', 0),
                'sma_50': current_data.get('sma_50', 0),
                'rsi': current_data.get('rsi', 0),
                'macd': current_data.get('macd', 0),
                'macd_signal': current_data.get('macd_signal', 0),
                'macd_histogram': current_data.get('macd_histogram', 0),
                'bb_upper': current_data.get('bb_upper', 0),
                'bb_lower': current_data.get('bb_lower', 0),
                'bb_position': current_data.get('bb_position', 0),
                'volume_ratio': current_data.get('volume_ratio', 0)
            },
            'trend_analysis': trend_analysis,
            'levels_analysis': levels_analysis,
            'full_data': df
        }
    except Exception as e:
        print(f"获取增强K线数据失败: {e}")
        return None

