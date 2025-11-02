"""模拟仓位和持仓管理模块 - 从数据库计算持仓，不调用交易所API"""
from .config import TRADE_CONFIG
from sim_data_manager import sim_data_manager


def get_current_position():
    """获取当前模拟持仓情况 - 从数据库计算"""
    try:
        # 从数据库获取所有未平仓的仓位记录
        # 直接访问sim_data_manager的内部方法_get_connection
        conn = sim_data_manager._get_connection()
        cursor = conn.cursor()
        
        # 获取所有开仓记录
        cursor.execute('''
            SELECT * FROM sim_position_records 
            WHERE action = 'open'
            ORDER BY timestamp DESC
        ''')
        
        open_positions = cursor.fetchall()
        conn.close()
        
        # 计算当前持仓（累加所有未平仓的开仓记录）
        total_long = 0
        total_short = 0
        long_entry_prices = []  # 用于计算平均成本
        short_entry_prices = []
        
        for pos in open_positions:
            pos_dict = dict(pos)
            side = pos_dict.get('side')
            amount = pos_dict.get('amount', 0)
            price = pos_dict.get('price', 0)
            
            if side == 'long':
                total_long += amount
                long_entry_prices.append({'price': price, 'amount': amount})
            elif side == 'short':
                total_short += amount
                short_entry_prices.append({'price': price, 'amount': amount})
        
        # 如果有持仓，返回持仓信息
        if total_long > 0:
            # 计算加权平均成本
            total_value = sum(p['price'] * p['amount'] for p in long_entry_prices)
            avg_entry_price = total_value / total_long if total_long > 0 else 0
            
            # 提取币种名称（BTC/USDT:USDT -> BTC）
            symbol_parts = TRADE_CONFIG['symbol'].split('/')
            coin_symbol = symbol_parts[0] if len(symbol_parts) > 0 else 'BTC'
            
            # 获取当前价格（需要从外部传入，这里先返回基本信息）
            return {
                'side': 'long',
                'size': total_long,
                'entry_price': avg_entry_price,
                'unrealized_pnl': 0,  # 需要当前价格才能计算，后续在trade_executor中更新
                'leverage': TRADE_CONFIG['leverage'],
                'symbol': coin_symbol  # 返回币种名称（如BTC），而不是完整交易对
            }
        elif total_short > 0:
            # 计算加权平均成本
            total_value = sum(p['price'] * p['amount'] for p in short_entry_prices)
            avg_entry_price = total_value / total_short if total_short > 0 else 0
            
            # 提取币种名称（BTC/USDT:USDT -> BTC）
            symbol_parts = TRADE_CONFIG['symbol'].split('/')
            coin_symbol = symbol_parts[0] if len(symbol_parts) > 0 else 'BTC'
            
            return {
                'side': 'short',
                'size': total_short,
                'entry_price': avg_entry_price,
                'unrealized_pnl': 0,  # 需要当前价格才能计算，后续在trade_executor中更新
                'leverage': TRADE_CONFIG['leverage'],
                'symbol': coin_symbol  # 返回币种名称（如BTC），而不是完整交易对
            }
        
        return None
        
    except Exception as e:
        print(f"获取模拟持仓失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def calculate_intelligent_position(signal_data, price_data, current_position):
    """计算智能仓位大小 - 使用模拟账户余额"""
    config = TRADE_CONFIG['position_management']
    
    # 🆕 新增：如果禁用智能仓位，使用固定仓位
    if not config.get('enable_intelligent_position', True):
        fixed_contracts = 0.1  # 固定仓位大小，可以根据需要调整
        print(f"🔧 智能仓位已禁用，使用固定仓位: {fixed_contracts} 张")
        return fixed_contracts
    
    try:
        # 获取模拟账户余额（从数据库）
        sim_balance = sim_data_manager.get_sim_balance()
        usdt_balance = sim_balance['balance']
        
        # 基础USDT投入
        base_usdt = config['base_usdt_amount']
        print(f"💰 模拟账户USDT余额: {usdt_balance:.2f}, 下单基数{base_usdt}")
        
        # 根据信心程度调整
        confidence_multiplier = {
            'HIGH': config['high_confidence_multiplier'],
            'MEDIUM': config['medium_confidence_multiplier'],
            'LOW': config['low_confidence_multiplier']
        }.get(signal_data['confidence'], 1.0)
        
        # 根据趋势强度调整
        trend = price_data['trend_analysis'].get('overall', '震荡整理')
        if trend in ['强势上涨', '强势下跌']:
            trend_multiplier = config['trend_strength_multiplier']
        else:
            trend_multiplier = 1.0
        
        # 根据RSI状态调整（超买超卖区域减仓）
        rsi = price_data['technical_data'].get('rsi', 50)
        if rsi > 75 or rsi < 25:
            rsi_multiplier = 0.7
        else:
            rsi_multiplier = 1.0
        
        # 计算建议投入USDT金额
        suggested_usdt = base_usdt * confidence_multiplier * trend_multiplier * rsi_multiplier
        
        # 风险管理：不超过总资金的指定比例
        max_usdt = usdt_balance * config['max_position_ratio']
        final_usdt = min(suggested_usdt, max_usdt)
        
        # 正确的合约张数计算！
        # 公式：合约张数 = (投入USDT) / (当前价格 * 合约乘数)
        contract_size = (final_usdt) / (price_data['price'] * TRADE_CONFIG.get('contract_size', 0.01))
        
        print(f"📊 模拟仓位计算详情:")
        print(f"   - 基础USDT: {base_usdt}")
        print(f"   - 信心倍数: {confidence_multiplier}")
        print(f"   - 趋势倍数: {trend_multiplier}")
        print(f"   - RSI倍数: {rsi_multiplier}")
        print(f"   - 建议USDT: {suggested_usdt:.2f}")
        print(f"   - 最终USDT: {final_usdt:.2f}")
        print(f"   - 合约乘数: {TRADE_CONFIG.get('contract_size', 0.01)}")
        print(f"   - 计算合约: {contract_size:.4f} 张")
        
        # 精度处理：OKX BTC合约最小交易单位为0.01张
        contract_size = round(contract_size, 2)  # 保留2位小数
        
        # 确保最小交易量
        min_contracts = TRADE_CONFIG.get('min_amount', 0.01)
        if contract_size < min_contracts:
            contract_size = min_contracts
            print(f"⚠️ 仓位小于最小值，调整为: {contract_size} 张")
        
        print(f"🎯 最终模拟仓位: {final_usdt:.2f} USDT → {contract_size:.2f} 张合约")
        return contract_size
        
    except Exception as e:
        print(f"❌ 模拟仓位计算失败，使用基础仓位: {e}")
        import traceback
        traceback.print_exc()
        # 紧急备用计算
        base_usdt = config['base_usdt_amount']
        contract_size = (base_usdt * TRADE_CONFIG['leverage']) / (
                    price_data['price'] * TRADE_CONFIG.get('contract_size', 0.01))
        return round(max(contract_size, TRADE_CONFIG.get('min_amount', 0.01)), 2)

