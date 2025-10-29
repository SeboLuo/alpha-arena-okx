FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p data

# 暴露端口
EXPOSE 5002

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 启动命令（使用supervisord管理多个进程）
CMD ["python", "web_app.py"]