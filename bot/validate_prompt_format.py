"""
验证提示词输出格式
对比实际输出与示例文件，检查格式一致性
"""
from pathlib import Path
import re
import json
from bot.prompts.prompt_builder import PromptBuilder


def load_example_file():
    """加载示例文件"""
    example_path = Path("/Users/luosibao/Desktop/trade_prompt/out/last_render.md")
    if example_path.exists():
        return example_path.read_text(encoding='utf-8')
    return None


def create_mock_coin_data():
    """创建模拟的coin_data，使用示例中的数值"""
    return {
        'symbol': 'BTC',
        'current_price': 109321.5,
        'current_ema20': 109423.266,
        'current_macd': 13.094,
        'current_rsi7': 42.329,
        'oi_latest': 33088.2,
        'oi_avg': 33072.91,
        'funding_rate': 1.25e-05,
        'mid_prices': [109677.0, 109590.0, 109490.0, 109396.5, 109172.0, 109132.5, 109305.0, 109328.0, 109328.0, 109321.5],
        'ema20_series': [109557.964, 109559.015, 109553.966, 109538.826, 109497.319, 109467.003, 109449.384, 109443.347, 109433.505, 109423.266],
        'macd_series': [246.158, 216.72, 186.16, 151.242, 98.867, 62.768, 41.987, 33.524, 22.841, 13.094],
        'rsi7_series': [52.17, 43.404, 39.557, 33.461, 22.717, 29.583, 38.256, 46.079, 43.251, 42.329],
        'rsi14_series': [58.317, 53.543, 51.299, 47.521, 39.317, 42.118, 45.771, 49.254, 47.792, 47.331],
        'ema20_4h': 110987.214,
        'ema50_4h': 111473.679,
        'atr3_4h': 1552.587,
        'atr14_4h': 956.584,
        'current_volume_4h': 174.366,
        'avg_volume_4h': 4460.122,
        'macd_4h': [441.454, 235.813, 29.892, -197.595, -316.457, -353.247, -510.387, -797.123, -1093.258, -1164.359],
        'rsi14_4h': [50.493, 40.109, 37.594, 34.007, 39.411, 43.973, 36.537, 29.63, 27.014, 37.893],
    }


def extract_coin_section(text):
    """从文本中提取币种数据区块"""
    pattern = r'### ALL\s+(\w+)\s+DATA(.*?)(?=---|##\s|###|\Z)'
    matches = re.finditer(pattern, text, re.DOTALL)
    
    sections = {}
    for match in matches:
        symbol = match.group(1)
        content = match.group(2).strip()
        sections[symbol] = content
    
    return sections


def extract_json_arrays(text):
    """提取所有JSON数组"""
    pattern = r'```json\s*\n(.*?)\n```'
    matches = re.finditer(pattern, text, re.DOTALL)
    
    arrays = []
    for match in matches:
        json_str = match.group(1).strip()
        try:
            data = json.loads(json_str)
            arrays.append(data)
        except Exception as e:
            pass
    
    return arrays


def extract_numeric_values(text):
    """提取所有数值字段"""
    patterns = {
        'current_price': r'current_price:\s*\*\*([\d.]+)\*\*',
        'current_ema20': r'current_ema20:\s*\*\*([\d.]+)\*\*',
        'current_macd': r'current_macd:\s*\*\*([\d.-]+)\*\*',
        'current_rsi7': r'current_rsi.*?\(7 period\):\s*\*\*([\d.]+)\*\*',
        'oi_latest': r'Open Interest:.*?Latest:\s*\*\*([\d.]+)\*\*',
        'oi_avg': r'Open Interest:.*?Average:\s*\*\*([\d.]+)\*\*',
        'funding_rate': r'Funding Rate:\s*\*\*([\d.e\-+]+)\*\*',
    }
    
    values = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                val_str = match.group(1)
                # 处理科学计数法
                if 'e' in val_str.lower():
                    values[key] = float(val_str)
                else:
                    values[key] = float(val_str)
            except:
                pass
    
    return values


def compare_formats(actual_text, example_text):
    """对比实际输出和示例格式"""
    print("=" * 80)
    print("格式验证报告")
    print("=" * 80)
    
    # 1. 提取币种数据区块
    actual_coins = extract_coin_section(actual_text)
    example_coins = extract_coin_section(example_text)
    
    print("\n1. 币种数据区块检查:")
    print(f"   实际输出包含币种: {list(actual_coins.keys())}")
    print(f"   示例文件包含币种: {list(example_coins.keys())}")
    
    if not actual_coins or not example_coins:
        print("   ⚠ 无法提取币种数据区块，请检查格式")
        return
    
    # 2. 检查数值格式
    actual_coin_text = list(actual_coins.values())[0]
    example_coin_text = list(example_coins.values())[0]
    
    print("\n2. 数值格式检查:")
    actual_values = extract_numeric_values(actual_coin_text)
    example_values = extract_numeric_values(example_coin_text)
    
    all_match = True
    for key in set(list(actual_values.keys()) + list(example_values.keys())):
        actual_val = actual_values.get(key, None)
        example_val = example_values.get(key, None)
        
        if actual_val is not None and example_val is not None:
            # 对于小数，允许小的误差
            if abs(actual_val) > 1:
                diff_pct = abs(actual_val - example_val) / abs(example_val) * 100
                match = diff_pct < 0.01
            else:
                diff = abs(actual_val - example_val)
                match = diff < 0.0001
            
            status = "✓" if match else "✗"
            if not match:
                all_match = False
            
            print(f"   {status} {key:15s}: 实际={actual_val:12.6f}, 示例={example_val:12.6f}, "
                  f"差异={abs(actual_val - example_val):.6f}")
        elif actual_val is not None:
            print(f"   ⚠ {key:15s}: 实际={actual_val:12.6f}, 示例中缺失")
            all_match = False
        elif example_val is not None:
            print(f"   ⚠ {key:15s}: 实际中缺失, 示例={example_val:12.6f}")
            all_match = False
    
    # 3. 检查JSON数组格式
    print("\n3. JSON数组格式检查:")
    actual_arrays = extract_json_arrays(actual_text)
    example_arrays = extract_json_arrays(example_text)
    
    print(f"   实际输出JSON数组数量: {len(actual_arrays)}")
    print(f"   示例文件JSON数组数量: {len(example_arrays)}")
    
    if actual_arrays and example_arrays:
        # 检查数组格式
        for i, (actual_arr, example_arr) in enumerate(zip(actual_arrays[:5], example_arrays[:5])):
            if isinstance(actual_arr, list) and isinstance(example_arr, list):
                # 检查JSON字符串格式（是否紧凑）
                actual_json_str = json.dumps(actual_arr, separators=(',', ':'))
                example_json_str = json.dumps(example_arr, separators=(',', ':'))
                
                # 检查是否包含空格和换行（紧凑格式不应有空格）
                actual_is_compact = ' ' not in actual_json_str and '\n' not in actual_json_str
                example_is_compact = ' ' not in example_json_str and '\n' not in example_json_str
                
                status = "✓" if actual_is_compact and example_is_compact else "✗"
                print(f"   {status} 数组{i+1}: 长度={len(actual_arr)}, 类型={type(actual_arr[0]).__name__ if actual_arr else 'empty'}, "
                      f"紧凑格式={'✓' if actual_is_compact else '✗'}")
    
    # 4. 检查关键字段存在性
    print("\n4. 关键字段存在性检查:")
    required_fields = [
        'current_price',
        'current_ema20',
        'current_macd',
        'current_rsi',
        'Open Interest',
        'Funding Rate',
        'Mid prices',
        'EMA (20-period)',
        'MACD',
        'RSI (7-Period)',
        'RSI (14-Period)',
    ]
    
    fields_match = True
    for field in required_fields:
        actual_has = field.lower() in actual_coin_text.lower()
        example_has = field.lower() in example_coin_text.lower()
        
        status = "✓" if actual_has and example_has else ("⚠" if actual_has != example_has else "✗")
        if status != "✓":
            fields_match = False
        
        print(f"   {status} {field:20s}: 实际={'✓' if actual_has else '✗'}, 示例={'✓' if example_has else '✗'}")
    
    # 5. 检查4小时数据格式
    print("\n5. 4小时数据格式检查:")
    four_hour_fields = [
        '20-Period EMA',
        '50-Period EMA',
        '3-Period ATR',
        '14-Period ATR',
        'Current Volume',
        'Average Volume',
        'MACD (4h)',
        'RSI (14-Period, 4h)',
    ]
    
    four_hour_match = True
    for field in four_hour_fields:
        actual_has = field.lower() in actual_coin_text.lower()
        example_has = field.lower() in example_coin_text.lower()
        
        status = "✓" if actual_has and example_has else ("⚠" if actual_has != example_has else "✗")
        if status != "✓":
            four_hour_match = False
        
        print(f"   {status} {field:25s}: 实际={'✓' if actual_has else '✗'}, 示例={'✓' if example_has else '✗'}")
    
    # 6. 输出币种数据区块预览对比
    print("\n6. 币种数据区块预览对比:")
    print("\n   实际输出（前800字符）:")
    print("   " + "-" * 76)
    preview = actual_coin_text[:800]
    for line in preview.split('\n')[:15]:
        print(f"   {line[:76]}")
    if len(preview) > 800:
        print("   ...")
    
    print("\n   示例文件（前800字符）:")
    print("   " + "-" * 76)
    preview = example_coin_text[:800]
    for line in preview.split('\n')[:15]:
        print(f"   {line[:76]}")
    if len(preview) > 800:
        print("   ...")
    
    # 7. 总结
    print("\n" + "=" * 80)
    print("验证总结:")
    print("=" * 80)
    
    if all_match and fields_match and four_hour_match:
        print("✅ 格式验证通过！输出格式与示例一致")
    else:
        issues = []
        if not all_match:
            issues.append("数值格式")
        if not fields_match:
            issues.append("字段存在性")
        if not four_hour_match:
            issues.append("4小时数据")
        
        print(f"⚠️  发现以下问题: {', '.join(issues)}")
        print("   请检查上述详细信息")


def main():
    """主函数"""
    print("开始验证提示词格式...")
    print()
    
    # 加载示例文件
    example_text = load_example_file()
    if not example_text:
        print("❌ 无法加载示例文件")
        print(f"   请确保文件存在: /Users/luosibao/Desktop/trade_prompt/out/last_render.md")
        return
    
    print("✓ 示例文件加载成功")
    
    # 创建模拟数据并生成实际输出
    try:
        coin_data = create_mock_coin_data()
        
        builder = PromptBuilder()
        coin_section = builder.build_coin_section(coin_data)
        
        # 为了完整对比，也生成系统提示词和用户提示词
        system_config = {
            'exchange': 'OKX',
            'model_name': 'DeepSeek-v1',
            'asset_universe': 'BTC',
            'starting_capital': 10000,
            'market_hours': '24/7',
            'decision_frequency': 'Every 10 minutes',
            'leverage_range': '1-10x',
            'contract_type': 'Perpetual Swap',
            'trading_fees': '0.02% maker, 0.05% taker',
            'slippage': '0.01-0.05%',
        }
        
        system_prompt = builder.build_system_prompt(system_config)
        
        user_params = {
            'minutes_elapsed': 12326,
            'current_time': '2025-10-31 02:29:07',
            'invocation_count': 4964,
            'coins_data': [coin_data],
            'current_total_return_percent': -74.53,
            'available_cash': 1238.64,
            'current_account_value': 2547.35,
            'positions': [],
        }
        
        user_prompt = builder.build_user_prompt(**user_params)
        
        actual_text = system_prompt + "\n\n" + user_prompt
        
        print("✓ 实际输出生成成功")
        
        # 保存实际输出到文件
        output_file = Path(__file__).parent / "test_actual_output.md"
        output_file.write_text(actual_text, encoding='utf-8')
        print(f"✓ 实际输出已保存到: {output_file}")
        print()
        
        # 对比格式
        compare_formats(actual_text, example_text)
        
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
