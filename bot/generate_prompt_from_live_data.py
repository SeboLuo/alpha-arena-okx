"""
从实时数据生成提示词并保存到本地
"""
import sys
from pathlib import Path
from datetime import datetime
import traceback

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bot.market_data import get_btc_ohlcv_enhanced
from bot.ai_analyzer import (
    _convert_price_data_to_coin_data,
    _prepare_system_config,
    _prepare_user_prompt_params
)
from bot.prompts import PromptBuilder
from bot.config import TRADE_CONFIG


def main():
    """主函数"""
    print("=" * 80)
    print("从实时数据生成提示词")
    print("=" * 80)
    print()
    
    try:
        # 1. 获取最新BTC数据
        print("1. 正在从OKX交易所获取最新BTC数据...")
        try:
            price_data = get_btc_ohlcv_enhanced()
        except ModuleNotFoundError as e:
            print(f"❌ 缺少必要的Python包: {e}")
            print("\n   请先安装依赖:")
            print("   pip install pandas ccxt python-dotenv openai")
            return None
        except Exception as e:
            print(f"⚠️ 获取数据时出现错误: {e}")
            print("   这可能是因为API配置或网络问题")
            traceback.print_exc()
            return None
        
        if not price_data:
            print("❌ 获取数据失败，请检查网络连接和API配置")
            print("   提示：确保.env文件中配置了OKX_API_KEY等环境变量")
            return None
        
        print(f"✅ 数据获取成功")
        print(f"   - 当前价格: ${price_data['price']:,.2f}")
        print(f"   - 时间框架: {price_data['timeframe']}")
        print(f"   - 价格变化: {price_data['price_change']:+.2f}%")
        print()
        
        # 2. 转换为币种数据格式
        print("2. 正在转换数据格式...")
        try:
            coin_data = _convert_price_data_to_coin_data(price_data)
            print(f"✅ 数据转换成功")
            print(f"   - 币种: {coin_data['symbol']}")
            print(f"   - EMA20: {coin_data['current_ema20']:,.2f}")
            print(f"   - MACD: {coin_data['current_macd']:.4f}")
            print(f"   - RSI7: {coin_data['current_rsi7']:.2f}")
            print(f"   - 序列数据点数: {len(coin_data['mid_prices'])}")
            print()
        except Exception as e:
            print(f"⚠️ 数据转换警告: {e}")
            print("   将使用最小可用数据继续...")
            traceback.print_exc()
            print()
        
        # 3. 构建提示词
        print("3. 正在构建提示词...")
        builder = PromptBuilder()
        
        # 系统提示词
        system_config = _prepare_system_config()
        system_prompt = builder.build_system_prompt(system_config)
        print(f"   ✓ 系统提示词: {len(system_prompt)} 字符")
        
        # 用户提示词
        try:
            user_params = _prepare_user_prompt_params(price_data, coin_data)
            user_prompt = builder.build_user_prompt(**user_params)
            print(f"   ✓ 用户提示词: {len(user_prompt)} 字符")
        except Exception as e:
            print(f"   ⚠️ 用户提示词构建警告: {e}")
            # 使用最小参数
            user_params = {
                'minutes_elapsed': 0,
                'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'invocation_count': 1,
                'coins_data': [coin_data],
                'current_total_return_percent': 0.0,
                'available_cash': 0.0,
                'current_account_value': 0.0,
                'positions': [],
            }
            user_prompt = builder.build_user_prompt(**user_params)
            print(f"   ✓ 用户提示词（使用默认参数）: {len(user_prompt)} 字符")
        
        print()
        
        # 4. 组合完整提示词
        full_prompt = system_prompt + "\n\n" + user_prompt
        
        # 5. 保存到文件
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"prompt_{timestamp}.md"
        
        output_file.write_text(full_prompt, encoding='utf-8')
        
        print("4. 提示词已保存:")
        print(f"   📄 文件路径: {output_file}")
        print(f"   📊 总长度: {len(full_prompt):,} 字符")
        print()
        
        # 6. 显示预览
        print("=" * 80)
        print("提示词预览（币种数据部分）:")
        print("=" * 80)
        
        coin_section = builder.build_coin_section(coin_data)
        preview_lines = coin_section.split('\n')[:30]
        for line in preview_lines:
            print(line)
        if len(coin_section.split('\n')) > 30:
            print("...")
        
        print()
        print("=" * 80)
        print("✅ 完成！提示词已保存到本地文件")
        print("=" * 80)
        
        return output_file
        
    except Exception as e:
        print(f"\n❌ 生成提示词失败: {e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()

