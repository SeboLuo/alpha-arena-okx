# Docker 部署指南

## 前置要求

1. 安装 Docker 和 Docker Compose
2. 确保系统有足够的内存和CPU资源

## 快速开始

### 1. 配置环境变量

复制环境变量模板文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件，设置您的API密钥：
```env
DEEPSEEK_API_KEY=your_actual_deepseek_api_key
OKX_API_KEY=your_actual_okx_api_key
OKX_SECRET=your_actual_okx_secret
OKX_PASSWORD=your_actual_okx_password
```

### 2. 启动服务

**Linux/Mac:**
```bash
chmod +x docker-start.sh
./docker-start.sh
```

**Windows:**
```cmd
docker-start.bat
```

或者手动启动：
```bash
docker-compose up -d
```

### 3. 验证服务

检查服务状态：
```bash
docker-compose ps
```

查看日志：
```bash
docker-compose logs -f
```

访问Web界面：http://localhost:5002

## 服务说明

### Web应用服务 (web-app)
- 端口：5002
- 功能：Web界面展示
- 数据：实时显示交易状态和绩效

### 交易机器人服务 (trading-bot)
- 功能：自动交易执行
- 频率：每15分钟执行一次分析
- 数据：与Web服务共享数据目录

## 数据持久化

- 交易数据存储在 `./data` 目录
- 数据在容器重启后保留
- 支持数据备份和恢复

## 常用命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看实时日志
```bash
docker-compose logs -f
```

### 查看特定服务日志
```bash
docker-compose logs -f web-app
docker-compose logs -f trading-bot
```

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 重新构建镜像
```bash
docker-compose build --no-cache
```

### 清理数据（谨慎使用）
```bash
docker-compose down -v
```

## 故障排除

### 1. 端口冲突
如果5002端口被占用，修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "8080:5002"  # 改为其他端口
```

### 2. 环境变量问题
确保 `.env` 文件存在且格式正确：
```bash
# 检查环境变量
docker-compose config
```

### 3. 权限问题
如果遇到权限错误，尝试：
```bash
sudo chown -R $USER:$USER ./data
```

### 4. 容器启动失败
查看详细错误信息：
```bash
docker-compose logs
```

## 性能优化

### 资源限制
在 `docker-compose.yml` 中添加资源限制：
```yaml
services:
  web-app:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    
  trading-bot:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
```

### 日志管理
配置日志轮转：
```yaml
services:
  web-app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 备份和恢复

### 备份数据
```bash
# 备份数据目录
tar -czf backup-$(date +%Y%m%d).tar.gz data/
```

### 恢复数据
```bash
# 停止服务
docker-compose down

# 恢复备份
tar -xzf backup-20231201.tar.gz

# 重新启动
docker-compose up -d
```

## 安全建议

1. 定期更新Docker镜像
2. 使用强密码保护API密钥
3. 限制容器网络访问
4. 定期备份重要数据
5. 监控容器资源使用情况