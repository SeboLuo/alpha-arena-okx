#!/bin/bash
# 重启Web应用的脚本

cd "$(dirname "$0")"

# 停止旧的Web应用进程
echo "正在停止旧的Web应用..."
pkill -f "python.*web_app.py" || pkill -f "web_app.py" || true
sleep 1

# 启动新的Web应用
echo "正在启动Web应用..."
python3 web_app.py > web_app.log 2>&1 &

# 等待一下确保启动
sleep 2

# 检查是否成功启动
if pgrep -f "web_app.py" > /dev/null; then
    echo "✅ Web应用已启动"
    echo "查看日志: tail -f web_app.log"
    echo "访问: http://localhost:5002"
else
    echo "❌ Web应用启动失败，请查看 web_app.log"
fi
