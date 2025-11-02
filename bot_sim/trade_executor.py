"""模拟交易执行模块 - 不调用交易所API，完全模拟交易流程"""
import time
import json
from datetime import datetime
from .config import TRADE_CONFIG
from .position_manager import get_current_position, calculate_intelligent_position
from sim_data_manager import sim_data_manager


def execute_intelligent_trade(signal_data, price_data):
    """执行模拟智能交易 - 完全模拟交易逻辑，不调用真实交易所API"""
    
    current_position = get_current_position()
    
    # 计算智能仓位
    position_size = calculate_intelligent_position(signal_data, price_data, current_position)
    
    print(f"[模拟] 交易信号: {signal_data['signal']}")
    print(f"[模拟] 信心程度: {signal_data['confidence']}")
    print(f"[模拟] 智能仓位: {position_size:.2f} 张")
    print(f"[模拟] 理由: {signal_data['reason']}")
    print(f"[模拟] 当前持仓: {current_position}")
    
    try:
        current_price = price_data['price']
        position_action = None  # 'open', 'close', 'add', 'reduce', 'hold'
        position_side = None
        trade_amount = 0  # 交易数量
        pnl = 0
        
        # 执行模拟交易逻辑 - 支持同方向加仓减仓
        if signal_data['signal'] == 'BUY':
            if current_position and current_position['side'] == 'short':
                # 平空仓并开多仓（方向反转）
                if current_position['size'] > 0:
                    print(f"[模拟] 平空仓 {current_position['size']:.2f} 张并开多仓 {position_size:.2f} 张...")
                    
                    position_action = 'close'
                    position_side = 'short'
                    trade_amount = current_position['size']
                    
                    # 先记录平仓，返回计算的盈亏
                    pnl = _update_sim_position('close', 'short', current_position['size'], current_price)
                    
                    # 等待1秒（模拟真实交易延迟）
                    time.sleep(0.1)
                    
                    # 再开多仓
                    _update_sim_position('open', 'long', position_size, current_price)
                    position_action = 'open'
                    position_side = 'long'
                    trade_amount = position_size
                    
                else:
                    print("[模拟] ⚠️ 检测到空头持仓但数量为0，直接开多仓")
                    _update_sim_position('open', 'long', position_size, current_price)
                    position_action = 'open'
                    position_side = 'long'
                    trade_amount = position_size
            
            elif current_position and current_position['side'] == 'long':
                # 同方向，检查是否需要调整仓位
                size_diff = position_size - current_position['size']
                
                if abs(size_diff) >= 0.01:  # 有可调整的差异
                    if size_diff > 0:
                        # 加仓
                        add_size = round(size_diff, 2)
                        print(f"[模拟] 多仓加仓 {add_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        _update_sim_position('open', 'long', add_size, current_price)
                        position_action = 'add'  # 标记为加仓
                        position_side = 'long'
                        trade_amount = add_size
                    else:
                        # 减仓（部分平仓）
                        reduce_size = round(abs(size_diff), 2)
                        print(f"[模拟] 多仓减仓 {reduce_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        
                        # 部分平仓，获取计算的盈亏
                        pnl = _update_sim_position('close', 'long', reduce_size, current_price)
                        position_action = 'reduce'  # 标记为减仓
                        position_side = 'long'
                        trade_amount = reduce_size
                else:
                    print(f"[模拟] 已有多头持仓，仓位合适保持现状 (当前:{current_position['size']:.2f}, 目标:{position_size:.2f})")
                    position_action = 'hold'  # 标记为保持仓位
                    position_side = 'long'
                    trade_amount = 0
            else:
                # 无持仓时开多仓
                print(f"[模拟] 开多仓 {position_size:.2f} 张...")
                _update_sim_position('open', 'long', position_size, current_price)
                position_action = 'open'
                position_side = 'long'
                trade_amount = position_size
        
        elif signal_data['signal'] == 'SELL':
            if current_position and current_position['side'] == 'long':
                # 平多仓并开空仓（方向反转）
                if current_position['size'] > 0:
                    print(f"[模拟] 平多仓 {current_position['size']:.2f} 张并开空仓 {position_size:.2f} 张...")
                    
                    position_action = 'close'
                    position_side = 'long'
                    trade_amount = current_position['size']
                    
                    # 先记录平仓，返回计算的盈亏
                    pnl = _update_sim_position('close', 'long', current_position['size'], current_price)
                    
                    # 等待1秒（模拟真实交易延迟）
                    time.sleep(0.1)
                    
                    # 再开空仓
                    _update_sim_position('open', 'short', position_size, current_price)
                    position_action = 'open'
                    position_side = 'short'
                    trade_amount = position_size
                    
                else:
                    print("[模拟] ⚠️ 检测到多头持仓但数量为0，直接开空仓")
                    _update_sim_position('open', 'short', position_size, current_price)
                    position_action = 'open'
                    position_side = 'short'
                    trade_amount = position_size
            
            elif current_position and current_position['side'] == 'short':
                # 同方向，检查是否需要调整仓位
                size_diff = position_size - current_position['size']
                
                if abs(size_diff) >= 0.01:  # 有可调整的差异
                    if size_diff > 0:
                        # 加仓
                        add_size = round(size_diff, 2)
                        print(f"[模拟] 空仓加仓 {add_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        _update_sim_position('open', 'short', add_size, current_price)
                        position_action = 'add'  # 标记为加仓
                        position_side = 'short'
                        trade_amount = add_size
                    else:
                        # 减仓（部分平仓）
                        reduce_size = round(abs(size_diff), 2)
                        print(f"[模拟] 空仓减仓 {reduce_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        
                        # 部分平仓，获取计算的盈亏
                        pnl = _update_sim_position('close', 'short', reduce_size, current_price)
                        position_action = 'reduce'  # 标记为减仓
                        position_side = 'short'
                        trade_amount = reduce_size
                else:
                    print(f"[模拟] 已有空头持仓，仓位合适保持现状 (当前:{current_position['size']:.2f}, 目标:{position_size:.2f})")
                    position_action = 'hold'  # 标记为保持仓位
                    position_side = 'short'
                    trade_amount = 0
            else:
                # 无持仓时开空仓
                print(f"[模拟] 开空仓 {position_size:.2f} 张...")
                _update_sim_position('open', 'short', position_size, current_price)
                position_action = 'open'
                position_side = 'short'
                trade_amount = position_size
        
        elif signal_data['signal'] == 'HOLD':
            print("[模拟] 建议观望，不执行交易")
            position_action = 'hold'
            position_side = current_position['side'] if current_position else None
            trade_amount = 0
        
        print("[模拟] 智能交易执行成功")
        
        # 获取交易后的持仓状态
        updated_position = get_current_position()
        print(f"[模拟] 更新后持仓: {updated_position}")
        
        # 更新模拟账户余额（根据盈亏）
        if pnl != 0:
            sim_balance = sim_data_manager.get_sim_balance()
            new_balance = sim_balance['balance'] + pnl
            new_equity = new_balance  # 简化处理，equity = balance
            sim_data_manager.update_sim_balance(new_balance, new_equity)
            print(f"[模拟] 账户余额更新: {sim_balance['balance']:.2f} → {new_balance:.2f} USDT (盈亏: {pnl:+.2f} USDT)")
        
        # 保存交易记录 - 确保每次AI信号都保存一条记录
        try:
            # 如果方向改变，需要额外记录开仓事件
            if current_position and updated_position and current_position['side'] != updated_position.get('side'):
                # 先保存平仓记录
                close_record = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'signal': signal_data['signal'],
                    'price': current_price,
                    'amount': current_position['size'],
                    'confidence': signal_data['confidence'],
                    'reason': signal_data['reason'],
                    'pnl': pnl,
                    'position_action': 'close',
                    'position_side': current_position['side'],
                    'notes': json.dumps({'mode': 'simulation'}, ensure_ascii=False)
                }
                sim_data_manager.save_trade_record(close_record)
                
                # 再保存开仓记录（新仓位）
                open_record = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'signal': signal_data['signal'],
                    'price': current_price,
                    'amount': position_size,
                    'confidence': signal_data['confidence'],
                    'reason': signal_data['reason'],
                    'pnl': 0,
                    'position_action': 'open',
                    'position_side': updated_position['side'],
                    'notes': json.dumps({'mode': 'simulation'}, ensure_ascii=False)
                }
                sim_data_manager.save_trade_record(open_record)
                print("[模拟] ✅ 交易记录已保存（平仓+开仓）")
            else:
                # 保存交易记录（包括开仓、平仓、加仓、减仓、保持）
                # 现在 position_action 可以是: 'open', 'close', 'add', 'reduce', 'hold'
                if position_action:  # 确保有操作记录
                    # 对于加仓/减仓，记录实际交易的数量
                    amount_to_record = trade_amount if trade_amount > 0 else (current_position['size'] if current_position else position_size)
                    
                    trade_record = {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'signal': signal_data['signal'],
                        'price': current_price,
                        'amount': amount_to_record,
                        'confidence': signal_data['confidence'],
                        'reason': signal_data['reason'],
                        'pnl': pnl,
                        'position_action': position_action,
                        'position_side': position_side,
                        'trade_type': position_action,  # 保存交易类型
                        'notes': json.dumps({'mode': 'simulation'}, ensure_ascii=False)
                    }
                    sim_data_manager.save_trade_record(trade_record)
                    
                    action_name = {'open': '开仓', 'close': '平仓', 'add': '加仓', 'reduce': '减仓', 'hold': '保持'}.get(position_action, position_action)
                    print(f"[模拟] ✅ 交易记录已保存 ({action_name})")
        except Exception as e:
            print(f"[模拟] 保存交易记录失败: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        print(f"[模拟] 交易执行失败: {e}")
        import traceback
        traceback.print_exc()


def _update_sim_position(action, side, amount, price):
    """更新模拟持仓到数据库（内部函数）
    
    Args:
        action: 'open' 或 'close'
        side: 'long' 或 'short'
        amount: 数量（张）
        price: 价格
    
    Returns:
        float: 如果action是'close'，返回计算的盈亏；如果是'open'，返回0
    """
    conn = sim_data_manager._get_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        if action == 'close':
            # 平仓：找到对应的开仓记录，使用FIFO方式
            # 获取所有同方向的开仓记录（按时间排序）
            cursor.execute('''
                SELECT * FROM sim_position_records 
                WHERE action = 'open' AND side = ?
                ORDER BY timestamp ASC
            ''', (side,))
            
            open_records = cursor.fetchall()
            remaining_to_close = amount
            total_pnl = 0  # 累计盈亏
            
            if not open_records:
                print(f"[模拟] ⚠️ 警告：尝试平仓但找不到对应的开仓记录")
                conn.close()
                return 0
            
            # 按FIFO顺序平仓
            for open_record in open_records:
                if remaining_to_close <= 0:
                    break
                
                open_record_dict = dict(open_record)
                open_amount = open_record_dict['amount']
                open_price = open_record_dict['price']
                
                # 计算本次平仓的数量（可能是部分平仓）
                close_amount = min(open_amount, remaining_to_close)
                
                # 计算本次平仓的盈亏
                if side == 'long':
                    close_pnl = (price - open_price) * close_amount * TRADE_CONFIG.get('contract_size', 0.01)
                else:  # short
                    close_pnl = (open_price - price) * close_amount * TRADE_CONFIG.get('contract_size', 0.01)
                
                # 插入平仓记录
                cursor.execute('''
                    INSERT INTO sim_position_records (timestamp, action, side, price, amount, pnl, created_at)
                    VALUES (?, 'close', ?, ?, ?, ?, ?)
                ''', (timestamp, side, price, close_amount, close_pnl, datetime.now().isoformat()))
                
                # 如果完全平仓，删除对应的开仓记录（FIFO）
                if close_amount >= open_amount:
                    cursor.execute('DELETE FROM sim_position_records WHERE id = ?', (open_record_dict['id'],))
                else:
                    # 部分平仓：更新开仓记录的amount
                    new_amount = open_amount - close_amount
                    cursor.execute('''
                        UPDATE sim_position_records 
                        SET amount = ? 
                        WHERE id = ?
                    ''', (new_amount, open_record_dict['id']))
                
                remaining_to_close -= close_amount
                
                # 累计总盈亏（用于返回）
                total_pnl += close_pnl
        
        elif action == 'open':
            # 开仓：直接插入开仓记录
            cursor.execute('''
                INSERT INTO sim_position_records (timestamp, action, side, price, amount, pnl, created_at)
                VALUES (?, 'open', ?, ?, ?, 0, ?)
            ''', (timestamp, side, price, amount, datetime.now().isoformat()))
            total_pnl = 0
        
        conn.commit()
        return total_pnl
        
    except Exception as e:
        print(f"[模拟] 更新持仓失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return 0
    finally:
        conn.close()

