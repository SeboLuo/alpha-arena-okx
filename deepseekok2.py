"""
主入口文件 - 保持向后兼容性
本文件现在作为入口点，实际功能已拆分到bot模块中
"""

from bot.trading_bot import main

if __name__ == "__main__":
    main()