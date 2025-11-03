"""交易执行模块"""
import time
from datetime import datetime
from .config import exchange, TRADE_CONFIG
from .position_manager import get_current_position
from data_manager import save_trade_record


def execute_intelligent_trade(signal_data, price_data):
    """执行智能交易 - OKX版本（支持同方向加仓减仓）"""

    current_position = get_current_position()

    # 防止频繁反转的逻辑保持不变
    if current_position and signal_data['signal'] != 'HOLD':
        current_side = current_position['side']  # 'long' 或 'short'

        if signal_data['signal'] == 'BUY':
            new_side = 'long'
        elif signal_data['signal'] == 'SELL':
            new_side = 'short'
        else:
            new_side = None

        # 如果方向相反，需要高信心才执行
        # if new_side != current_side:
        #     if signal_data['confidence'] != 'HIGH':
        #         print(f"🔒 非高信心反转信号，保持现有{current_side}仓")
        #         return

        #     if len(signal_history) >= 2:
        #         last_signals = [s['signal'] for s in signal_history[-2:]]
        #         if signal_data['signal'] in last_signals:
        #             print(f"🔒 近期已出现{signal_data['signal']}信号，避免频繁反转")
        #             return

    # 完全使用AI返回的quantity和leverage，如果无效则停止交易
    signal = signal_data.get('signal', '').upper()
    
    # HOLD和CLOSE信号不需要quantity和leverage
    if signal in ['HOLD', 'CLOSE']:
        print(f"交易信号: {signal_data['signal']}")
        print(f"信心程度: {signal_data['confidence']}")
        print(f"理由: {signal_data['reason']}")
        print(f"当前持仓: {current_position}")
        # HOLD和CLOSE可以直接执行，不需要验证quantity和leverage
    else:
        # BUY和SELL信号必须要有有效的quantity和leverage
        ai_quantity = signal_data.get('quantity')
        ai_leverage = signal_data.get('leverage')
        
        # 验证quantity
        if ai_quantity is None:
            print(f"❌ AI策略无效：缺少quantity字段")
            print(f"   交易信号: {signal_data['signal']}")
            print(f"   停止交易，等待下次AI信号")
            return
        
        if not isinstance(ai_quantity, (int, float)) or ai_quantity <= 0:
            print(f"❌ AI策略无效：quantity值无效 ({ai_quantity})")
            print(f"   交易信号: {signal_data['signal']}")
            print(f"   停止交易，等待下次AI信号")
            return
        
        # 验证leverage
        if ai_leverage is None:
            print(f"❌ AI策略无效：缺少leverage字段")
            print(f"   交易信号: {signal_data['signal']}")
            print(f"   停止交易，等待下次AI信号")
            return
        
        if not isinstance(ai_leverage, (int, float)):
            print(f"❌ AI策略无效：leverage类型错误 ({type(ai_leverage)})")
            print(f"   交易信号: {signal_data['signal']}")
            print(f"   停止交易，等待下次AI信号")
            return
        
        ai_leverage = int(ai_leverage)
        if not (1 <= ai_leverage <= 20):
            print(f"❌ AI策略无效：leverage值超出有效范围 ({ai_leverage})，有效范围: 1-20")
            print(f"   交易信号: {signal_data['signal']}")
            print(f"   停止交易，等待下次AI信号")
            return
        
        # AI返回的quantity是币的数量（如BTC数量），需要转换为合约张数
        # 合约张数 = 币的数量 / 合约乘数
        contract_size = TRADE_CONFIG.get('contract_size', 0.01)  # 默认0.01（1张=0.01 BTC）
        
        # 将币数量转换为合约张数
        position_size_coins = float(ai_quantity)
        position_size = position_size_coins / contract_size
        
        # 验证转换后的仓位是否合理
        max_reasonable_contracts = 1000  # 假设最大合理仓位是1000张
        if position_size > max_reasonable_contracts:
            print(f"❌ AI策略无效：quantity({position_size_coins}币)转换后仓位({position_size:.2f}张)过大")
            print(f"   交易信号: {signal_data['signal']}")
            print(f"   停止交易，等待下次AI信号")
            return
        
        # 精度处理：OKX BTC合约最小交易单位为0.01张
        position_size = round(position_size, 2)
        
        # 确保最小交易量
        min_contracts = TRADE_CONFIG.get('min_amount', 0.01)
        if position_size < min_contracts:
            print(f"⚠️ AI返回的仓位({position_size:.2f}张)小于最小值({min_contracts}张)，调整为最小值")
            position_size = min_contracts
        
        # 验证账户余额是否足够支付保证金
        try:
            balance = exchange.fetch_balance()
            available_balance = float(balance['USDT'].get('free', 0))  # 可用余额
            
            # 计算合约价值（开仓方向调整仓位时，只计算新增部分的保证金）
            contract_size = TRADE_CONFIG.get('contract_size', 0.01)
            current_price = price_data['price']
            
            # 如果已有同方向持仓，计算需要调整的仓位
            if current_position and current_position['side'] == 'long' and signal == 'BUY':
                # 做多加仓：计算新增部分的保证金
                size_diff = position_size - current_position['size']
                if size_diff > 0:
                    # 加仓：只需要新增部分的保证金
                    contract_value = size_diff * current_price * contract_size
                    required_margin = contract_value / ai_leverage
                else:
                    # 减仓：不需要额外保证金
                    contract_value = 0
                    required_margin = 0
            elif current_position and current_position['side'] == 'short' and signal == 'SELL':
                # 做空加仓：计算新增部分的保证金
                size_diff = position_size - current_position['size']
                if size_diff > 0:
                    # 加仓：只需要新增部分的保证金
                    contract_value = size_diff * current_price * contract_size
                    required_margin = contract_value / ai_leverage
                else:
                    # 减仓：不需要额外保证金
                    contract_value = 0
                    required_margin = 0
            elif current_position and ((current_position['side'] == 'short' and signal == 'BUY') or 
                                        (current_position['side'] == 'long' and signal == 'SELL')):
                # 方向反转：需要先平仓（可能有盈亏），然后开新仓
                # 需要新仓位的全额保证金
                contract_value = position_size * current_price * contract_size
                required_margin = contract_value / ai_leverage
            else:
                # 无持仓或开新仓：需要全额保证金
                contract_value = position_size * current_price * contract_size
                required_margin = contract_value / ai_leverage
            
            # 验证余额是否足够（留5%的安全边际）
            safety_margin = 1.05
            required_with_safety = required_margin * safety_margin
            
            print(f"💰 账户可用余额: {available_balance:.2f} USDT")
            print(f"📊 合约价值: {contract_value:.2f} USDT")
            print(f"📊 所需保证金: {required_margin:.2f} USDT (杠杆: {ai_leverage}x)")
            print(f"📊 考虑安全边际: {required_with_safety:.2f} USDT")
            
            if available_balance < required_with_safety:
                # 余额不足，按比例缩减仓位
                max_contract_value = available_balance * ai_leverage / safety_margin
                max_position_size = max_contract_value / (current_price * contract_size)
                max_position_size = round(max_position_size, 2)
                
                # 确保不小于最小交易量
                if max_position_size < min_contracts:
                    print(f"❌ AI策略无法执行：账户余额不足，所需保证金: {required_margin:.2f} USDT，可用余额: {available_balance:.2f} USDT")
                    print(f"   交易信号: {signal_data['signal']}")
                    print(f"   停止交易，等待下次AI信号")
                    return
                
                # 如果缩减后仓位比AI要求的少太多（少于50%），则拒绝执行
                if max_position_size < position_size * 0.5:
                    print(f"❌ AI策略无法执行：账户余额严重不足")
                    print(f"   AI要求仓位: {position_size:.2f} 张，但余额仅支持: {max_position_size:.2f} 张")
                    print(f"   所需保证金: {required_margin:.2f} USDT，可用余额: {available_balance:.2f} USDT")
                    print(f"   交易信号: {signal_data['signal']}")
                    print(f"   停止交易，等待下次AI信号")
                    return
                
                print(f"⚠️ 账户余额不足，AI要求仓位: {position_size:.2f} 张")
                print(f"   缩减仓位至: {max_position_size:.2f} 张 (基于可用余额: {available_balance:.2f} USDT)")
                position_size = max_position_size
            else:
                print(f"✅ 账户余额充足，可以执行AI策略")
        except Exception as e:
            print(f"❌ 验证账户余额失败: {e}")
            print(f"   交易信号: {signal_data['signal']}")
            print(f"   停止交易，等待下次AI信号")
            import traceback
            traceback.print_exc()
            return
        
        # 设置AI返回的杠杆（在开仓前设置）
        try:
            exchange.set_leverage(
                ai_leverage,
                TRADE_CONFIG['symbol'],
                {'mgnMode': 'cross'}  # 全仓模式
            )
            print(f"✅ 使用AI返回的杠杆倍数: {ai_leverage}x")
        except Exception as e:
            print(f"❌ AI策略执行失败：设置杠杆失败: {e}")
            print(f"   交易信号: {signal_data['signal']}")
            print(f"   停止交易，等待下次AI信号")
            return
        
        print(f"✅ 使用AI返回的仓位: {position_size_coins}币 → {position_size:.2f} 张合约")
        print(f"交易信号: {signal_data['signal']}")
        print(f"信心程度: {signal_data['confidence']}")
        print(f"仓位大小: {position_size:.2f} 张 (来源: AI返回的quantity)")
        print(f"理由: {signal_data['reason']}")
        print(f"当前持仓: {current_position}")

    # 完全使用AI返回的策略，包括低信心信号（AI已经在策略中考虑了风险）

    try:
        # 执行交易逻辑 - 支持同方向加仓减仓
        if signal_data['signal'] == 'BUY':
            if current_position and current_position['side'] == 'short':
                # 先检查空头持仓是否真实存在且数量正确
                if current_position['size'] > 0:
                    print(f"平空仓 {current_position['size']:.2f} 张并开多仓 {position_size:.2f} 张...")
                    # 平空仓
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'buy',
                        current_position['size'],
                        params={'reduceOnly': True, 'tag': '60bb4a8d3416BCDE'}
                    )
                    time.sleep(1)
                    # 开多仓
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'buy',
                        position_size,
                        params={'tag': '60bb4a8d3416BCDE'}
                    )
                else:
                    print("⚠️ 检测到空头持仓但数量为0，直接开多仓")
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'buy',
                        position_size,
                        params={'tag': '60bb4a8d3416BCDE'}
                    )

            elif current_position and current_position['side'] == 'long':
                # 同方向，检查是否需要调整仓位
                size_diff = position_size - current_position['size']

                if abs(size_diff) >= 0.01:  # 有可调整的差异
                    if size_diff > 0:
                        # 加仓
                        add_size = round(size_diff, 2)
                        print(
                            f"多仓加仓 {add_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'buy',
                            add_size,
                            params={'tag': '60bb4a8d3416BCDE'}
                        )
                    else:
                        # 减仓
                        reduce_size = round(abs(size_diff), 2)
                        print(
                            f"多仓减仓 {reduce_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'sell',
                            reduce_size,
                            params={'reduceOnly': True, 'tag': '60bb4a8d3416BCDE'}
                        )
                else:
                    print(
                        f"已有多头持仓，仓位合适保持现状 (当前:{current_position['size']:.2f}, 目标:{position_size:.2f})")
            else:
                # 无持仓时开多仓
                print(f"开多仓 {position_size:.2f} 张...")
                exchange.create_market_order(
                    TRADE_CONFIG['symbol'],
                    'buy',
                    position_size,
                    params={'tag': '60bb4a8d3416BCDE'}
                )

        elif signal_data['signal'] == 'SELL':
            if current_position and current_position['side'] == 'long':
                # 先检查多头持仓是否真实存在且数量正确
                if current_position['size'] > 0:
                    print(f"平多仓 {current_position['size']:.2f} 张并开空仓 {position_size:.2f} 张...")
                    # 平多仓
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'sell',
                        current_position['size'],
                        params={'reduceOnly': True, 'tag': '60bb4a8d3416BCDE'}
                    )
                    time.sleep(1)
                    # 开空仓
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'sell',
                        position_size,
                        params={'tag': '60bb4a8d3416BCDE'}
                    )
                else:
                    print("⚠️ 检测到多头持仓但数量为0，直接开空仓")
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'sell',
                        position_size,
                        params={'tag': '60bb4a8d3416BCDE'}
                    )

            elif current_position and current_position['side'] == 'short':
                # 同方向，检查是否需要调整仓位
                size_diff = position_size - current_position['size']

                if abs(size_diff) >= 0.01:  # 有可调整的差异
                    if size_diff > 0:
                        # 加仓
                        add_size = round(size_diff, 2)
                        print(
                            f"空仓加仓 {add_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'sell',
                            add_size,
                            params={'tag': '60bb4a8d3416BCDE'}
                        )
                    else:
                        # 减仓
                        reduce_size = round(abs(size_diff), 2)
                        print(
                            f"空仓减仓 {reduce_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'buy',
                            reduce_size,
                            params={'reduceOnly': True, 'tag': '60bb4a8d3416BCDE'}
                        )
                else:
                    print(
                        f"已有空头持仓，仓位合适保持现状 (当前:{current_position['size']:.2f}, 目标:{position_size:.2f})")
            else:
                # 无持仓时开空仓
                print(f"开空仓 {position_size:.2f} 张...")
                exchange.create_market_order(
                    TRADE_CONFIG['symbol'],
                    'sell',
                    position_size,
                    params={'tag': '60bb4a8d3416BCDE'}
                )

        elif signal_data['signal'] == 'HOLD':
            print("建议观望，不执行交易")
            return
        
        elif signal_data['signal'] == 'CLOSE':
            # CLOSE信号：完全平掉当前持仓（如果有）
            if current_position and current_position['size'] > 0:
                print(f"CLOSE信号：平仓 {current_position['size']:.2f} 张 ({current_position['side']})")
                try:
                    # 平仓：与当前持仓方向相反的下单
                    if current_position['side'] == 'long':
                        # 平多仓：下卖单
                        order = exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'sell',
                            current_position['size'],
                            None,
                            None,
                            {'tdMode': 'cross'}  # 全仓模式
                        )
                    else:  # short
                        # 平空仓：下买单
                        order = exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'buy',
                            current_position['size'],
                            None,
                            None,
                            {'tdMode': 'cross'}  # 全仓模式
                        )
                    print(f"✅ 平仓成功: {order}")
                except Exception as e:
                    print(f"❌ 平仓失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return
            else:
                print("CLOSE信号：当前无持仓，无需操作")
            return

        print("智能交易执行成功")
        time.sleep(2)
        # 获取交易后的持仓状态，用于比较和计算盈亏
        updated_position = get_current_position()
        print(f"更新后持仓: {updated_position}")
        
        # 保存交易记录
        try:
            # 计算实际盈亏（如果有持仓）和识别仓位操作类型
            pnl = 0
            position_action = None  # 'open', 'close', None (加仓/减仓不记录)
            position_side = None
            
            if current_position:
                # 情况1: 完全平仓（从有持仓变成无持仓）
                if updated_position is None:
                    position_action = 'close'
                    position_side = current_position['side']
                    if current_position['side'] == 'long':
                        pnl = (price_data['price'] - current_position['entry_price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
                    else:
                        pnl = (current_position['entry_price'] - price_data['price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
                # 情况2: 方向改变（平仓并开新仓）
                elif current_position['side'] != updated_position.get('side'):
                    position_action = 'close'  # 当前操作是平仓
                    position_side = current_position['side']
                    if current_position['side'] == 'long':
                        pnl = (price_data['price'] - current_position['entry_price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
                    else:
                        pnl = (current_position['entry_price'] - price_data['price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
            else:
                # 情况3: 从无持仓到有持仓（开仓）
                if updated_position:
                    position_action = 'open'
                    position_side = updated_position['side']
            
            # 如果方向改变，需要额外记录开仓事件
            if current_position and updated_position and current_position['side'] != updated_position.get('side'):
                # 先保存平仓记录
                close_record = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'signal': signal_data['signal'],
                    'price': price_data['price'],
                    'amount': current_position['size'],
                    'confidence': signal_data['confidence'],
                    'reason': signal_data['reason'],
                    'pnl': pnl,
                    'position_action': 'close',
                    'position_side': current_position['side']
                }
                save_trade_record(close_record)
                
                # 再保存开仓记录（新仓位）
                open_record = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'signal': signal_data['signal'],
                    'price': price_data['price'],
                    'amount': position_size,
                    'confidence': signal_data['confidence'],
                    'reason': signal_data['reason'],
                    'pnl': 0,
                    'position_action': 'open',
                    'position_side': updated_position['side']
                }
                save_trade_record(open_record)
                print("✅ 交易记录已保存（平仓+开仓）")
            else:
                # 普通交易记录（开仓、平仓、加仓、减仓）
                trade_record = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'signal': signal_data['signal'],
                    'price': price_data['price'],
                    'amount': position_size,
                    'confidence': signal_data['confidence'],
                    'reason': signal_data['reason'],
                    'pnl': pnl
                }
                # 只有开仓或平仓时才添加仓位标识
                if position_action:
                    trade_record['position_action'] = position_action
                    trade_record['position_side'] = position_side
                
                save_trade_record(trade_record)
                print("✅ 交易记录已保存")
        except Exception as e:
            print(f"保存交易记录失败: {e}")

    except Exception as e:
        print(f"交易执行失败: {e}")

        # 如果是持仓不存在的错误，尝试直接开新仓
        if "don't have any positions" in str(e):
            print("尝试直接开新仓...")
            try:
                if signal_data['signal'] == 'BUY':
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'buy',
                        position_size,
                        params={'tag': '60bb4a8d3416BCDE'}
                    )
                elif signal_data['signal'] == 'SELL':
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'sell',
                        position_size,
                        params={'tag': '60bb4a8d3416BCDE'}
                    )
                print("直接开仓成功")
            except Exception as e2:
                print(f"直接开仓也失败: {e2}")

        import traceback
        traceback.print_exc()

