"""AI分析模块 - DeepSeek分析"""
from .config import deepseek_client, TRADE_CONFIG, signal_history, exchange
from .prompts import PromptBuilder
from .technical_analysis import (
    calculate_rsi_series,
    calculate_ema_series,
    calculate_macd_series,
    calculate_atr_series
)
from .position_manager import get_current_position
from .utils import safe_json_parse, create_fallback_signal
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# 初始化提示词构建器（模块级，避免重复初始化）
_builder = PromptBuilder()

# 交易开始时间计数器（用于计算minutes_elapsed）
_start_time = None
_invocation_count = 0


def _get_oi_and_funding_rate(symbol):
    """获取Open Interest和Funding Rate"""
    try:
        # OKX获取持仓量
        ticker = exchange.fetch_ticker(symbol)
        oi_latest = ticker.get('openInterest', 0) or 0
        
        # 获取资金费率（需要调用特定API）
        try:
            funding_rate_info = exchange.fetch_funding_rate(symbol)
            funding_rate = funding_rate_info.get('fundingRate', 0) if funding_rate_info else 0
        except:
            # 如果API不支持，尝试从ticker获取
            funding_rate = ticker.get('info', {}).get('fundingRate', 0) or 0
        
        # 计算平均OI（简化处理，使用当前值）
        oi_avg = oi_latest
        
        return {
            'oi_latest': float(oi_latest),
            'oi_avg': float(oi_avg),
            'funding_rate': float(funding_rate) if funding_rate else 0.0
        }
    except Exception as e:
        print(f"获取OI和Funding Rate失败: {e}")
        return {
            'oi_latest': 0.0,
            'oi_avg': 0.0,
            'funding_rate': 0.0
        }


def _get_4h_data(symbol):
    """获取4小时时间框架的数据"""
    try:
        # 获取4小时K线数据
        ohlcv_4h = exchange.fetch_ohlcv(symbol, '4h', limit=60)
        df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 计算技术指标
        df_4h['ema_20'] = df_4h['close'].ewm(span=20, adjust=False).mean()
        df_4h['ema_50'] = df_4h['close'].ewm(span=50, adjust=False).mean()
        
        # MACD
        ema_12_4h = df_4h['close'].ewm(span=12).mean()
        ema_26_4h = df_4h['close'].ewm(span=26).mean()
        df_4h['macd_4h'] = ema_12_4h - ema_26_4h
        
        # RSI14
        delta_4h = df_4h['close'].diff()
        gain_4h = (delta_4h.where(delta_4h > 0, 0)).rolling(14).mean()
        loss_4h = (-delta_4h.where(delta_4h < 0, 0)).rolling(14).mean()
        rs_4h = gain_4h / loss_4h
        df_4h['rsi14_4h'] = 100 - (100 / (1 + rs_4h))
        
        # ATR
        high_low_4h = df_4h['high'] - df_4h['low']
        high_close_4h = abs(df_4h['high'] - df_4h['close'].shift())
        low_close_4h = abs(df_4h['low'] - df_4h['close'].shift())
        tr_4h = pd.concat([high_low_4h, high_close_4h, low_close_4h], axis=1).max(axis=1)
        df_4h['atr3_4h'] = tr_4h.rolling(3).mean()
        df_4h['atr14_4h'] = tr_4h.rolling(14).mean()
        
        # 填充NaN
        df_4h = df_4h.bfill().ffill().fillna(0)
        
        current = df_4h.iloc[-1]
        
        return {
            'ema20_4h': float(current['ema_20']),
            'ema50_4h': float(current['ema_50']),
            'atr3_4h': float(current['atr3_4h']),
            'atr14_4h': float(current['atr14_4h']),
            'current_volume_4h': float(current['volume']),
            'avg_volume_4h': float(df_4h['volume'].tail(20).mean()),
            'macd_4h': df_4h['macd_4h'].tail(10).fillna(0).tolist(),
            'rsi14_4h': df_4h['rsi14_4h'].tail(10).fillna(50).tolist(),
        }
    except Exception as e:
        print(f"获取4小时数据失败: {e}")
        return {
            'ema20_4h': 0.0,
            'ema50_4h': 0.0,
            'atr3_4h': 0.0,
            'atr14_4h': 0.0,
            'current_volume_4h': 0.0,
            'avg_volume_4h': 0.0,
            'macd_4h': [],
            'rsi14_4h': [],
        }


def _convert_price_data_to_coin_data(price_data):
    """将price_data转换为coin_data格式"""
    try:
        df = price_data.get('full_data')
        if df is None or df.empty:
            raise ValueError("full_data不可用")
        
        # 获取最新数据（最后10根K线用于序列）
        recent_count = min(10, len(df))
        df_recent = df.tail(recent_count)
        
        # 计算序列数据
        mid_prices = ((df_recent['high'] + df_recent['low']) / 2).tolist()
        ema20_series = calculate_ema_series(df_recent, 20)[-recent_count:]
        macd_series = calculate_macd_series(df_recent)[-recent_count:]
        rsi7_series = calculate_rsi_series(df_recent, 7)[-recent_count:]
        rsi14_series = calculate_rsi_series(df_recent, 14)[-recent_count:]
        
        # 当前值
        current = df.iloc[-1]
        tech = price_data.get('technical_data', {})
        
        # 计算EMA20（如果不存在）
        if 'ema_20' not in df.columns:
            df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        current_ema20 = float(df['ema_20'].iloc[-1])
        
        # 计算RSI7（如果不存在）
        if 'rsi_7' not in df.columns:
            rsi7_series_full = calculate_rsi_series(df, 7)
            current_rsi7 = rsi7_series_full[-1]
        else:
            current_rsi7 = float(df['rsi_7'].iloc[-1])
        
        # 获取OI和Funding Rate
        symbol = TRADE_CONFIG['symbol']
        oi_data = _get_oi_and_funding_rate(symbol)
        
        # 获取4小时数据
        data_4h = _get_4h_data(symbol)
        
        # 从symbol中提取币种名称（BTC/USDT:USDT -> BTC）
        coin_symbol = symbol.split('/')[0]
        
        coin_data = {
            'symbol': coin_symbol,
            'current_price': float(price_data['price']),
            'current_ema20': current_ema20,
            'current_macd': float(tech.get('macd', 0)),
            'current_rsi7': float(current_rsi7),
            'oi_latest': oi_data['oi_latest'],
            'oi_avg': oi_data['oi_avg'],
            'funding_rate': oi_data['funding_rate'],
            'mid_prices': [float(x) for x in mid_prices],
            'ema20_series': [float(x) for x in ema20_series],
            'macd_series': [float(x) for x in macd_series],
            'rsi7_series': [float(x) for x in rsi7_series],
            'rsi14_series': [float(x) for x in rsi14_series],
            'ema20_4h': data_4h['ema20_4h'],
            'ema50_4h': data_4h['ema50_4h'],
            'atr3_4h': data_4h['atr3_4h'],
            'atr14_4h': data_4h['atr14_4h'],
            'current_volume_4h': data_4h['current_volume_4h'],
            'avg_volume_4h': data_4h['avg_volume_4h'],
            'macd_4h': [float(x) for x in data_4h['macd_4h']],
            'rsi14_4h': [float(x) for x in data_4h['rsi14_4h']],
        }
        
        return coin_data
    except Exception as e:
        print(f"数据转换失败: {e}")
        import traceback
        traceback.print_exc()
        # 返回最小可用数据
        return {
            'symbol': 'BTC',
            'current_price': float(price_data.get('price', 0)),
            'current_ema20': 0.0,
            'current_macd': 0.0,
            'current_rsi7': 0.0,
            'oi_latest': 0.0,
            'oi_avg': 0.0,
            'funding_rate': 0.0,
            'mid_prices': [],
            'ema20_series': [],
            'macd_series': [],
            'rsi7_series': [],
            'rsi14_series': [],
            'ema20_4h': 0.0,
            'ema50_4h': 0.0,
            'atr3_4h': 0.0,
            'atr14_4h': 0.0,
            'current_volume_4h': 0.0,
            'avg_volume_4h': 0.0,
            'macd_4h': [],
            'rsi14_4h': [],
        }


def _prepare_system_config(account_balance=None):
    """准备系统提示词配置
    
    Args:
        account_balance: 账户余额（USDT），如果提供则使用此值作为起始资金
    """
    symbol = TRADE_CONFIG['symbol']
    asset_universe = symbol.split('/')[0]  # 提取BTC
    
    # 如果没有提供账户余额，尝试从交易所获取
    if account_balance is None:
        try:
            balance = exchange.fetch_balance()
            account_balance = float(balance['USDT'].get('total', 0))  # 使用total作为账户总值
            print(f"📊 从交易所获取账户余额: {account_balance:.2f} USDT")
        except Exception as e:
            print(f"⚠️ 获取账户余额失败: {e}，使用默认值: 10000")
            account_balance = 10000
    
    return {
        'exchange': 'OKX',
        'model_name': 'DeepSeek-v1',
        'asset_universe': asset_universe,
        'starting_capital': account_balance,  # 使用实际账户余额
        'market_hours': '24/7',
        'decision_frequency': f'Every {TRADE_CONFIG["interval_minutes"]} minutes',
        'leverage_range': f'1-{TRADE_CONFIG["leverage"]}x',
        'contract_type': 'Perpetual Swap',
        'trading_fees': '0.02% maker, 0.05% taker',
        'slippage': '0.01-0.05%',
    }


def _prepare_user_prompt_params(price_data, coin_data, position_data=None, account_data=None):
    """准备用户提示词参数
    
    Args:
        price_data: 价格数据
        coin_data: 币种数据
        position_data: 可选的持仓数据（用于模拟模式），如果提供则使用此数据而不是调用get_current_position()
        account_data: 可选的账户数据（用于模拟模式），如果提供则使用此数据而不是调用exchange.fetch_balance()
    """
    global _start_time, _invocation_count
    
    # 判断是模拟模式还是真实模式（通过检查TEST_MODE环境变量或position_data参数）
    is_simulation = os.getenv('TEST_MODE', 'false').lower() == 'true' or position_data is not None
    
    # 从数据库获取统计数据
    try:
        if is_simulation:
            from sim_data_manager import sim_data_manager
            stats = sim_data_manager.get_system_stats()
        else:
            from data_manager import data_manager
            stats = data_manager.get_system_stats()
        
        # 计算累计时间
        # 如果数据库中有最后更新时间，计算从最后更新到现在的间隔
        last_update_str = stats.get('last_update_time')
        first_start_str = stats.get('first_start_time')
        total_minutes_from_db = stats.get('total_minutes_elapsed', 0) or 0
        total_invocation_from_db = stats.get('total_invocation_count', 0) or 0
        
        now = datetime.now()
        
        if total_minutes_from_db == 0 and first_start_str:
            # 第一次调用：从首次启动时间开始计算
            try:
                first_start_time = datetime.fromisoformat(first_start_str)
                total_minutes_elapsed = (now - first_start_time).total_seconds() / 60
            except:
                total_minutes_elapsed = 0
        elif last_update_str:
            # 非第一次调用：累计分钟数 = 数据库中的累计分钟数 + 上次更新到现在的分钟数
            try:
                last_update_time = datetime.fromisoformat(last_update_str)
                minutes_since_last_update = (now - last_update_time).total_seconds() / 60
                total_minutes_elapsed = total_minutes_from_db + minutes_since_last_update
            except:
                # 如果解析失败，使用数据库中的值
                total_minutes_elapsed = total_minutes_from_db
        else:
            total_minutes_elapsed = total_minutes_from_db
        
        # 调用次数 = 数据库中的次数 + 1（本次调用）
        total_invocation_count = total_invocation_from_db + 1
        
        # 更新数据库中的统计数据
        try:
            if is_simulation:
                sim_data_manager.update_system_stats(total_minutes_elapsed, total_invocation_count)
            else:
                data_manager.update_system_stats(total_minutes_elapsed, total_invocation_count)
        except Exception as e:
            print(f"⚠️ 更新系统统计数据失败: {e}")
        
        # 使用累计数据
        elapsed = total_minutes_elapsed
        _invocation_count = total_invocation_count
        
    except Exception as e:
        # 如果从数据库读取失败，回退到原来的逻辑
        print(f"⚠️ 从数据库读取统计数据失败，使用会话级统计: {e}")
        if _start_time is None:
            _start_time = datetime.now()
        elapsed = (datetime.now() - _start_time).total_seconds() / 60
        _invocation_count += 1
    
    # 获取持仓信息
    if position_data is not None:
        # 使用提供的持仓数据（模拟模式）
        current_pos = position_data
    else:
        # 从真实交易所获取持仓（真实交易模式）
        current_pos = get_current_position()
    
    positions = []
    if current_pos:
        # 从完整交易对中提取币种名称（如 BTC/USDT:USDT -> BTC）
        raw_symbol = current_pos.get('symbol', 'BTC/USDT:USDT')
        symbol_parts = raw_symbol.split('/')
        coin_symbol = symbol_parts[0] if len(symbol_parts) > 0 else 'BTC'
        
        positions = [{
            'symbol': coin_symbol,  # 使用币种名称（如BTC），而不是完整交易对
            'side': current_pos.get('side', 'long'),
            'size': current_pos.get('size', 0),
            'entry_price': current_pos.get('entry_price', 0),
            'current_price': float(price_data['price']),
            'unrealized_pnl': current_pos.get('unrealized_pnl', 0),
            'leverage': current_pos.get('leverage', TRADE_CONFIG['leverage']),
        }]
    
    # 获取账户信息
    if account_data is not None:
        # 使用提供的账户数据（模拟模式）
        # available_cash: 可用余额（总余额 - 占用保证金）
        # current_account_value: 账户净值（总余额 + 未实现盈亏）
        available_cash = float(account_data.get('available_cash', account_data.get('balance', 0)))
        current_account_value = float(account_data.get('equity', account_data.get('balance', 0)))
        current_total_return_percent = 0.0  # 可以从历史记录计算
    else:
        # 从真实交易所获取账户信息（真实交易模式）
        try:
            balance = exchange.fetch_balance()
            available_cash = float(balance['USDT'].get('free', 0))
            total_value = float(balance['USDT'].get('total', 0))
            
            # 计算总回报（简化处理）
            current_total_return_percent = 0.0  # 可以从历史记录计算
            current_account_value = total_value
        except:
            available_cash = 0.0
            current_account_value = 0.0
            current_total_return_percent = 0.0
    
    return {
        'minutes_elapsed': int(elapsed),  # 累计分钟数（从首次启动开始）
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'invocation_count': _invocation_count,  # 累计调用次数（从首次启动开始）
        'coins_data': [coin_data],
        'current_total_return_percent': current_total_return_percent,
        'available_cash': available_cash,
        'current_account_value': current_account_value,
        'positions': positions,
    }


def analyze_with_deepseek(price_data, position_data=None, account_data=None):
    """使用DeepSeek分析市场并生成交易信号（使用新模板系统）
    
    Args:
        price_data: 价格数据
        position_data: 可选的持仓数据（用于模拟模式）
        account_data: 可选的账户数据（用于模拟模式）
    """
    # 在函数开始时初始化提示词变量（用于异常时保存）
    system_prompt = ''
    user_prompt = ''
    ai_response = ''
    
    try:
        # 1. 获取账户余额用于系统提示词
        account_balance_for_system = None
        if account_data is not None:
            # 模拟模式：使用提供的账户数据
            account_balance_for_system = float(account_data.get('balance', account_data.get('equity', 0)))
        else:
            # 真实模式：从交易所获取
            try:
                balance = exchange.fetch_balance()
                account_balance_for_system = float(balance['USDT'].get('total', 0))
            except Exception as e:
                print(f"⚠️ 获取账户余额用于系统提示词失败: {e}")
        
        # 2. 准备系统提示词
        system_config = _prepare_system_config(account_balance_for_system)
        system_prompt = _builder.build_system_prompt(system_config)
        
        # 3. 转换币种数据
        coin_data = _convert_price_data_to_coin_data(price_data)
        
        # 4. 准备用户提示词参数（传递模拟模式的数据）
        user_params = _prepare_user_prompt_params(price_data, coin_data, position_data, account_data)
        
        # 4. 构建用户提示词
        user_prompt = _builder.build_user_prompt(**user_params)
        
        # 5. 调用DeepSeek API
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False,
            temperature=0.1
        )
        
        # 6. 解析响应
        result = response.choices[0].message.content
        ai_response = result  # 保存响应
        print(f"DeepSeek原始回复: {result}")
        
        # 提取JSON部分
        start_idx = result.find('{')
        end_idx = result.rfind('}') + 1
        
        # 解析后的信号数据
        parsed_signal_data = None
        
        if start_idx != -1 and end_idx != 0:
            json_str = result[start_idx:end_idx]
            parsed_signal_data = safe_json_parse(json_str)
            
            if parsed_signal_data is None:
                parsed_signal_data = create_fallback_signal(price_data)
        else:
            parsed_signal_data = create_fallback_signal(price_data)
        
        # 在解析后的数据中添加提示词和响应（用于后续存储）
        parsed_signal_data['system_prompt'] = system_prompt
        parsed_signal_data['user_prompt'] = user_prompt
        parsed_signal_data['ai_response'] = ai_response
        
        signal_data = parsed_signal_data
        
        # 保存原始信号类型（用于验证止损止盈）
        original_signal_type = signal_data.get('signal', '').upper() if signal_data else ''
        
        # 7. 适配输出格式（新格式→旧格式）
        if signal_data:
            # 7.1 适配signal字段：新格式可能是 "buy_to_enter" | "sell_to_enter" | "hold" | "close"
            # 需要转换为 "BUY" | "SELL" | "HOLD" | "CLOSE"
            if 'signal' in signal_data:
                signal_mapping = {
                    'buy_to_enter': 'BUY',
                    'sell_to_enter': 'SELL',
                    'hold': 'HOLD',
                    'close': 'CLOSE'  # close信号需要平掉当前持仓
                }
                original_signal = signal_data['signal']
                signal_data['signal'] = signal_mapping.get(original_signal.lower(), original_signal.upper())
            
            # 7.2 适配confidence格式：新格式是0-1浮点数，需要转换为HIGH|MEDIUM|LOW
            if 'confidence' in signal_data:
                conf = signal_data['confidence']
                if isinstance(conf, (int, float)):
                    if conf >= 0.7:
                        signal_data['confidence'] = 'HIGH'
                    elif conf >= 0.4:
                        signal_data['confidence'] = 'MEDIUM'
                    else:
                        signal_data['confidence'] = 'LOW'
            
            # 7.3 适配字段名称映射（新格式→旧格式）
            # justification → reason
            if 'justification' in signal_data and 'reason' not in signal_data:
                signal_data['reason'] = signal_data['justification']
            
            # profit_target → take_profit
            if 'profit_target' in signal_data and 'take_profit' not in signal_data:
                signal_data['take_profit'] = signal_data['profit_target']
            
            # 保留新格式的额外字段（quantity, leverage, coin, risk_usd, invalidation_condition）
            # 这些字段可能在后续的交易执行逻辑中使用，所以保留它们
            # 如果新格式有这些字段，保留在原位置
            # 如果旧代码需要，可以从这些字段获取
        
        # 8. 验证必需字段（旧格式要求的字段）
        required_fields = ['signal', 'reason', 'stop_loss', 'take_profit', 'confidence']
        missing_fields = [f for f in required_fields if f not in signal_data]
        
        if missing_fields:
            print(f"⚠️ 信号数据缺少必需字段: {missing_fields}，使用fallback信号")
            signal_data = create_fallback_signal(price_data)
        
        # 8.1 验证止损和止盈价格是否合理
        current_price = price_data['price']
        stop_loss = signal_data.get('stop_loss')
        take_profit = signal_data.get('take_profit')
        
        # 检查止损和止盈是否相同或无效
        if stop_loss is not None and take_profit is not None:
            # 转换为浮点数进行比较
            try:
                stop_loss = float(stop_loss)
                take_profit = float(take_profit)
                
                # 如果止损和止盈相同，或者都等于当前价格，需要修正
                if abs(stop_loss - take_profit) < 0.01 or abs(stop_loss - current_price) < 0.01 or abs(take_profit - current_price) < 0.01:
                    # 使用原始信号类型（在映射之前保存的）
                    if original_signal_type in ['CLOSE', 'CLOSE_POSITION']:
                        # CLOSE信号：修正止损和止盈，但保留原始信号意图
                        print(f"⚠️ CLOSE信号的止损({stop_loss})和止盈({take_profit})价格相同，修正为合理值")
                        signal_data['stop_loss'] = current_price * 0.98  # -2%
                        signal_data['take_profit'] = current_price * 1.02  # +2%
                        print(f"✅ 已修正：止损={signal_data['stop_loss']:.2f}, 止盈={signal_data['take_profit']:.2f}（保留CLOSE信号意图）")
                    else:
                        # 其他信号：使用fallback逻辑
                        print(f"⚠️ 止损({stop_loss})和止盈({take_profit})价格相同或等于当前价格({current_price})，使用fallback逻辑")
                        signal_data = create_fallback_signal(price_data)
                else:
                    # 确保止损和止盈相对于当前价格的方向正确
                    # 对于做多：止损应该低于当前价格，止盈应该高于当前价格
                    # 对于做空：止损应该高于当前价格，止盈应该低于当前价格
                    signal_type = signal_data.get('signal', '').upper()
                    if signal_type in ['BUY', 'BUY_TO_ENTER']:
                        # 做多信号：止损应该 < 当前价格 < 止盈
                        if stop_loss >= current_price or take_profit <= current_price:
                            print(f"⚠️ 做多信号的止损/止盈方向不正确，调整中...")
                            # 修正止损（当前价格的-2%）
                            signal_data['stop_loss'] = current_price * 0.98
                            # 修正止盈（当前价格的+2%）
                            signal_data['take_profit'] = current_price * 1.02
                            print(f"✅ 已修正：止损={signal_data['stop_loss']:.2f}, 止盈={signal_data['take_profit']:.2f}")
                    elif signal_type in ['SELL', 'SELL_TO_ENTER']:
                        # 做空信号：止损应该 > 当前价格 > 止盈
                        if stop_loss <= current_price or take_profit >= current_price:
                            print(f"⚠️ 做空信号的止损/止盈方向不正确，调整中...")
                            # 修正止损（当前价格的+2%）
                            signal_data['stop_loss'] = current_price * 1.02
                            # 修正止盈（当前价格的-2%）
                            signal_data['take_profit'] = current_price * 0.98
                            print(f"✅ 已修正：止损={signal_data['stop_loss']:.2f}, 止盈={signal_data['take_profit']:.2f}")
                    else:
                        # HOLD或CLOSE信号：对于HOLD/CLOSE，止损止盈可能不需要，但确保它们不同
                        if abs(stop_loss - take_profit) < 0.01:
                            # 如果HOLD/CLOSE信号中止损止盈相同，使用fallback逻辑生成合理的值
                            print(f"⚠️ HOLD/CLOSE信号的止损和止盈相同，使用fallback逻辑")
                            signal_data = create_fallback_signal(price_data)
            except (ValueError, TypeError) as e:
                print(f"⚠️ 止损/止盈价格格式错误: {e}，使用fallback信号")
                signal_data = create_fallback_signal(price_data)
        
        # 9. 保存信号到历史记录
        signal_data['timestamp'] = price_data['timestamp']
        signal_history.append(signal_data)
        if len(signal_history) > 30:
            signal_history.pop(0)
        
        # 10. 信号统计
        signal_count = len([s for s in signal_history if s.get('signal') == signal_data['signal']])
        total_signals = len(signal_history)
        print(f"信号统计: {signal_data['signal']} (最近{total_signals}次中出现{signal_count}次)")
        
        # 11. 信号连续性检查
        if len(signal_history) >= 3:
            last_three = [s['signal'] for s in signal_history[-3:]]
            if len(set(last_three)) == 1:
                print(f"⚠️ 注意：连续3次{signal_data['signal']}信号")
        
        return signal_data
        
    except Exception as e:
        print(f"DeepSeek分析失败: {e}")
        import traceback
        traceback.print_exc()
        # 即使是异常，也尝试保存已生成的提示词（如果存在）
        fallback_signal = create_fallback_signal(price_data)
        if system_prompt or user_prompt:
            fallback_signal['system_prompt'] = system_prompt
            fallback_signal['user_prompt'] = user_prompt
            fallback_signal['ai_response'] = ai_response if ai_response else f"API调用异常: {str(e)}"
        return fallback_signal


def analyze_with_deepseek_with_retry(price_data, max_retries=2, position_data=None, account_data=None):
    """带重试的DeepSeek分析
    
    Args:
        price_data: 价格数据
        max_retries: 最大重试次数
        position_data: 可选的持仓数据（用于模拟模式）
        account_data: 可选的账户数据（用于模拟模式）
    """
    # 保存最后一次的提示词（用于fallback时保存）
    last_system_prompt = None
    last_user_prompt = None
    last_ai_response = None
    
    for attempt in range(max_retries):
        try:
            signal_data = analyze_with_deepseek(price_data, position_data, account_data)
            
            # 保存提示词和响应（即使是fallback也保存）
            if signal_data:
                last_system_prompt = signal_data.get('system_prompt', '')
                last_user_prompt = signal_data.get('user_prompt', '')
                last_ai_response = signal_data.get('ai_response', '')
            
            if signal_data and not signal_data.get('is_fallback', False):
                return signal_data
            
            print(f"第{attempt + 1}次尝试失败，进行重试...")
            import time
            time.sleep(1)
            
        except Exception as e:
            print(f"第{attempt + 1}次尝试异常: {e}")
            if attempt == max_retries - 1:
                fallback_signal = create_fallback_signal(price_data)
                # 即使是fallback也尝试保存提示词（如果之前有）
                if last_system_prompt or last_user_prompt or last_ai_response:
                    fallback_signal['system_prompt'] = last_system_prompt or ''
                    fallback_signal['user_prompt'] = last_user_prompt or ''
                    fallback_signal['ai_response'] = last_ai_response or ''
                return fallback_signal
            import time
            time.sleep(1)
    
    # 最后一次尝试失败
    fallback_signal = create_fallback_signal(price_data)
    # 尝试保存最后一次的提示词（如果存在）
    if last_system_prompt or last_user_prompt or last_ai_response:
        fallback_signal['system_prompt'] = last_system_prompt or ''
        fallback_signal['user_prompt'] = last_user_prompt or ''
        fallback_signal['ai_response'] = last_ai_response or ''
    return fallback_signal
