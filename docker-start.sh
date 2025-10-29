#!/bin/bash

echo "🚀 启动OKX BTC交易机器人Docker服务..."

# 检查.env文件是否存在
if [ ! -f .env ]; then
    echo "❌ 错误: .env文件不存在"
    echo "请创建.env文件并设置以下环境变量:"
    echo "DEEPSEEK_API_KEY=your_deepseek_api_key"
    echo "OKX_API_KEY=your_okx_api_key"
    echo "OKX_SECRET=your_okx_secret"
    echo "OKX_PASSWORD=your_okx_password"
    exit 1
fi

# 检查数据目录
mkdir -p data

# 构建镜像
echo "📦 构建Docker镜像..."
docker-compose build

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

echo "✅ 服务启动完成!"
echo ""
echo "📊 Web界面: http://localhost:5002"
echo "🤖 交易机器人: 运行中"
echo ""
echo "📋 常用命令:"
echo "  查看日志: docker-compose logs -f"
echo "  停止服务: docker-compose down"
echo "  重启服务: docker-compose restart"
echo "  查看状态: docker-compose ps"