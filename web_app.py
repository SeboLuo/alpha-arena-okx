from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from data_manager import data_manager

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
    trades = data_manager.get_trade_history()
    
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

if __name__ == '__main__':
    # 确保模板目录存在
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    # 修复Web服务器配置，避免CLOSE_WAIT连接问题
    app.run(debug=False, host='0.0.0.0', port=5002, threaded=True)