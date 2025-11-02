from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 根据TEST_MODE环境变量选择数据管理器
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'
TRADE_MODE = 'simulation' if TEST_MODE else 'real'

print(f"[Web应用] TEST_MODE={os.getenv('TEST_MODE')}, 交易模式={TRADE_MODE}")

if TEST_MODE:
    from sim_data_manager import sim_data_manager as data_manager
    print("[Web应用] ✅ 已加载模拟交易数据管理器 (sim_data_manager)")
else:
    from data_manager import data_manager
    print("[Web应用] ✅ 已加载真实交易数据管理器 (data_manager)")

# 设置模板目录路径
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)
CORS(app)  # 启用CORS支持

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/system-status')
def get_system_status():
    """获取系统状态"""
    status = data_manager.get_system_status()
    # 添加调试信息（仅在开发时有用）
    if not status:
        print(f"[Web应用] 警告: 系统状态为空 (模式={TRADE_MODE})")
    return jsonify(status)

@app.route('/api/trade-history')
def get_trade_history():
    """获取交易历史（支持分页）"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    
    # 限制每页最大数量
    page_size = min(page_size, 100)
    page = max(page, 1)
    
    result = data_manager.get_trade_history(page=page, page_size=page_size)
    return jsonify(result)

@app.route('/api/performance')
def get_performance():
    """获取绩效数据"""
    performance = data_manager.get_performance()
    return jsonify(performance)

@app.route('/api/chart-data')
def get_chart_data():
    """获取图表数据"""
    # 获取所有交易数据（不传分页参数会返回第一页，但我们需要获取全部数据用于图表）
    result = data_manager.get_trade_history(page=1, page_size=100)
    trades = result.get('data', [])
    
    # 生成价格走势数据
    price_data = []
    pnl_data = []
    
    for i, trade in enumerate(trades):
        if trade.get('price'):
            price_data.append({
                'x': i,
                'y': trade['price'],
                'timestamp': trade.get('timestamp', ''),
                'signal': trade.get('signal', '')
            })
        
        if trade.get('pnl'):
            pnl_data.append({
                'x': i,
                'y': trade['pnl'],
                'timestamp': trade.get('timestamp', '')
            })
    
    return jsonify({
        'price_data': price_data,
        'pnl_data': pnl_data
    })

@app.route('/api/update-settings', methods=['POST'])
def update_settings():
    """更新系统设置"""
    try:
        data = request.get_json()
        # 这里可以添加设置更新逻辑
        return jsonify({'status': 'success', 'message': '设置已更新'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/ai-analysis-history')
def get_ai_analysis_history():
    """获取AI分析历史记录（支持分页）"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        
        # 限制每页最大数量
        page_size = min(page_size, 100)
        page = max(page, 1)
        
        result = data_manager.get_ai_analysis_history(page=page, page_size=page_size)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/trade-mode')
def get_trade_mode():
    """获取当前交易模式（模拟/实盘）"""
    return jsonify({
        'mode': TRADE_MODE,
        'mode_name': '模拟交易' if TRADE_MODE == 'simulation' else '实盘交易',
        'is_simulation': TRADE_MODE == 'simulation'
    })

if __name__ == '__main__':
    # 确保模板目录存在
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    # 修复Web服务器配置，避免CLOSE_WAIT连接问题
    app.run(debug=False, host='0.0.0.0', port=5002, threaded=True)