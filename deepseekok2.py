"""
主入口文件 - 根据TEST_MODE环境变量切换真实交易或模拟交易
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 检查TEST_MODE环境变量
test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'

if test_mode:
    # 模拟交易模式
    print("=" * 60)
    print("🚀 启动模拟交易系统")
    print("=" * 60)
    from bot_sim.trading_bot import main
else:
    # 真实交易模式
    print("=" * 60)
    print("🚀 启动真实交易系统")
    print("=" * 60)
    from bot.trading_bot import main

if __name__ == "__main__":
    main()