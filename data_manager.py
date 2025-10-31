import json
import os
from datetime import datetime

class DataManager:
    def __init__(self):
        self.data_dir = "data"
        self.system_file = os.path.join(self.data_dir, "system_status.json")
        self.trades_file = os.path.join(self.data_dir, "trades.json")
        self.performance_file = os.path.join(self.data_dir, "performance.json")
        self.ai_analysis_file = os.path.join(self.data_dir, "ai_analysis_history.json")
        
        # 确保数据目录存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 初始化数据文件
        self._init_files()
    
    def _init_files(self):
        """初始化数据文件"""
        if not os.path.exists(self.system_file):
            self._save_json(self.system_file, {
                "status": "stopped",
                "last_update": datetime.now().isoformat(),
                "account_info": {},
                "btc_info": {},
                "position": {},
                "ai_signal": {}
            })
        
        if not os.path.exists(self.trades_file):
            self._save_json(self.trades_file, [])
        
        if not os.path.exists(self.performance_file):
            self._save_json(self.performance_file, {
                "total_trades": 0,
                "winning_trades": 0,
                "completed_trades": 0,  # 基于仓位配对完成的交易次数
                "total_pnl": 0,
                "daily_pnl": {},
                "monthly_pnl": {},
                "position_records": []  # 仓位记录：开仓和平仓配对
            })
        
        if not os.path.exists(self.ai_analysis_file):
            self._save_json(self.ai_analysis_file, [])
    
    def _save_json(self, filepath, data):
        """保存JSON数据"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存数据失败 {filepath}: {e}")
    
    def _load_json(self, filepath):
        """加载JSON数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def update_system_status(self, status, account_info=None, btc_info=None, position=None, ai_signal=None):
        """更新系统状态"""
        data = {
            "status": status,
            "last_update": datetime.now().isoformat(),
            "account_info": account_info or {},
            "btc_info": btc_info or {},
            "position": position or {},
            "ai_signal": ai_signal or {}
        }
        self._save_json(self.system_file, data)
    
    def save_trade_record(self, trade_record):
        """保存交易记录"""
        trades = self._load_json(self.trades_file)
        if not isinstance(trades, list):
            trades = []
        
        # 添加交易记录
        trades.append(trade_record)
        
        # 只保留最近100条记录
        if len(trades) > 100:
            trades = trades[-100:]
        
        self._save_json(self.trades_file, trades)
        
        # 更新绩效数据
        self._update_performance(trade_record)
    
    def _update_performance(self, trade_record):
        """更新绩效数据"""
        performance = self._load_json(self.performance_file)
        
        # 保持原始逻辑：每次保存交易记录都增加 total_trades
        performance["total_trades"] = performance.get("total_trades", 0) + 1
        
        pnl = trade_record.get("pnl", 0)
        position_action = trade_record.get("position_action")
        
        # 记录仓位事件（开仓或平仓），用于计算合约交易的胜率
        if position_action in ['open', 'close']:
            position_records = performance.get("position_records", [])
            position_records.append({
                'timestamp': trade_record.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'action': position_action,
                'side': trade_record.get('position_side'),
                'price': trade_record.get('price'),
                'amount': trade_record.get('amount'),
                'pnl': pnl
            })
            performance["position_records"] = position_records
        
        # 基于仓位记录计算胜率
        self._calculate_win_rate_from_positions(performance)
        
        # 总盈亏和每日/月度统计仍然基于所有交易的 pnl
        performance["total_pnl"] = performance.get("total_pnl", 0) + pnl
        
        # 更新每日绩效
        today = datetime.now().strftime("%Y-%m-%d")
        daily_pnl = performance.get("daily_pnl", {})
        daily_pnl[today] = daily_pnl.get(today, 0) + pnl
        performance["daily_pnl"] = daily_pnl
        
        # 更新月度绩效
        month = datetime.now().strftime("%Y-%m")
        monthly_pnl = performance.get("monthly_pnl", {})
        monthly_pnl[month] = monthly_pnl.get(month, 0) + pnl
        performance["monthly_pnl"] = monthly_pnl
        
        self._save_json(self.performance_file, performance)
    
    def _calculate_win_rate_from_positions(self, performance):
        """基于仓位记录计算胜率（开仓+平仓配对）"""
        position_records = performance.get("position_records", [])
        
        if not position_records:
            performance["completed_trades"] = 0
            performance["winning_trades"] = 0
            return
        
        # 配对开仓和平仓记录，计算完成的交易
        completed_trades = 0
        winning_trades = 0
        open_positions = {}  # {side: [open_record, ...]}
        
        for record in position_records:
            action = record.get('action')
            side = record.get('side')
            
            if action == 'open':
                # 记录开仓
                if side not in open_positions:
                    open_positions[side] = []
                open_positions[side].append(record)
            elif action == 'close':
                # 匹配最近的同方向开仓记录
                closed_side = record.get('side')
                if closed_side in open_positions and len(open_positions[closed_side]) > 0:
                    # 配对成功，完成一次交易
                    completed_trades += 1
                    if record.get('pnl', 0) > 0:
                        winning_trades += 1
                    # 移除已配对的开仓记录（FIFO）
                    open_positions[closed_side].pop(0)
                else:
                    # 没有匹配的开仓记录，可能是历史数据或数据不一致
                    # 仍然计算为一次交易（平仓时 pnl 不为 0）
                    if record.get('pnl', 0) != 0:
                        completed_trades += 1
                        if record.get('pnl', 0) > 0:
                            winning_trades += 1
        
        performance["completed_trades"] = completed_trades
        performance["winning_trades"] = winning_trades
    
    def get_system_status(self):
        """获取系统状态"""
        return self._load_json(self.system_file)
    
    def get_trade_history(self):
        """获取交易历史"""
        return self._load_json(self.trades_file)
    
    def get_performance(self):
        """获取绩效数据"""
        return self._load_json(self.performance_file)
    
    def save_ai_analysis_record(self, analysis_record):
        """保存AI分析记录"""
        analysis_history = self._load_json(self.ai_analysis_file)
        if not isinstance(analysis_history, list):
            analysis_history = []
        
        # 添加时间戳
        analysis_record['timestamp'] = datetime.now().isoformat()
        
        # 添加分析记录
        analysis_history.append(analysis_record)
        
        # 只保留最近50条记录
        if len(analysis_history) > 50:
            analysis_history = analysis_history[-50:]
        
        self._save_json(self.ai_analysis_file, analysis_history)
    
    def get_ai_analysis_history(self):
        """获取AI分析历史记录"""
        return self._load_json(self.ai_analysis_file)

# 全局数据管理器实例
data_manager = DataManager()

# 兼容性函数
def update_system_status(status, account_info=None, btc_info=None, position=None, ai_signal=None):
    data_manager.update_system_status(status, account_info, btc_info, position, ai_signal)

def save_trade_record(trade_record):
    data_manager.save_trade_record(trade_record)

def save_ai_analysis_record(analysis_record):
    data_manager.save_ai_analysis_record(analysis_record)