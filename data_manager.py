import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, List

class DataManager:
    """使用SQLite数据库的数据管理器"""
    
    def __init__(self, db_path: str = "data/trading_data.db"):
        self.db_path = db_path
        self.data_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else "data"
        
        # 确保数据目录存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 初始化数据库
        self._init_database()
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使返回结果为字典形式
        return conn
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. 系统状态表（单行记录）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                status TEXT NOT NULL DEFAULT 'stopped',
                last_update TEXT NOT NULL,
                account_info TEXT,
                btc_info TEXT,
                position TEXT,
                ai_signal TEXT,
                UNIQUE(id)
            )
        ''')
        
        # 2. 交易记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trade_type TEXT,
                position_action TEXT,
                position_side TEXT,
                price REAL,
                amount REAL,
                pnl REAL DEFAULT 0,
                signal TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_position_action ON trades(position_action)')
        
        # 3. 绩效统计表（单行记录）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                completed_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                daily_pnl TEXT,
                monthly_pnl TEXT,
                last_updated TEXT,
                UNIQUE(id)
            )
        ''')
        
        # 4. 仓位记录表（用于计算胜率）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS position_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                side TEXT,
                price REAL,
                amount REAL,
                pnl REAL DEFAULT 0,
                trade_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_position_records_timestamp ON position_records(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_position_records_action ON position_records(action)')
        
        # 5. AI分析记录表（包含完整提示词和响应）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                system_prompt TEXT,
                user_prompt TEXT,
                ai_response TEXT,
                analysis_data TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_analysis_timestamp ON ai_analysis_history(timestamp)')
        
        # 如果表已存在但缺少新字段，尝试添加（忽略错误，如果字段已存在）
        try:
            cursor.execute('ALTER TABLE ai_analysis_history ADD COLUMN system_prompt TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE ai_analysis_history ADD COLUMN user_prompt TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE ai_analysis_history ADD COLUMN ai_response TEXT')
        except:
            pass
        
        # 6. 系统统计表（用于记录累计运行时间和调用次数）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                first_start_time TEXT NOT NULL,
                total_minutes_elapsed REAL DEFAULT 0,
                total_invocation_count INTEGER DEFAULT 0,
                last_update_time TEXT NOT NULL,
                UNIQUE(id)
            )
        ''')
        
        # 初始化默认数据
        self._init_default_data(cursor)
        
        conn.commit()
        conn.close()
    
    def _init_default_data(self, cursor):
        """初始化默认数据"""
        # 初始化系统状态
        cursor.execute('SELECT COUNT(*) FROM system_status')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO system_status (id, status, last_update, account_info, btc_info, position, ai_signal)
                VALUES (1, 'stopped', ?, '{}', '{}', '{}', '{}')
            ''', (datetime.now().isoformat(),))
        
        # 初始化绩效数据
        cursor.execute('SELECT COUNT(*) FROM performance')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO performance (id, total_trades, winning_trades, completed_trades, total_pnl, 
                                       daily_pnl, monthly_pnl, last_updated)
                VALUES (1, 0, 0, 0, 0, '{}', '{}', ?)
            ''', (datetime.now().isoformat(),))
        
        # 初始化系统统计数据
        cursor.execute('SELECT COUNT(*) FROM system_stats')
        if cursor.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO system_stats (id, first_start_time, total_minutes_elapsed, 
                                        total_invocation_count, last_update_time)
                VALUES (1, ?, 0, 0, ?)
            ''', (now, now))
    
    # ========== 系统状态管理 ==========
    
    def update_system_status(self, status, account_info=None, btc_info=None, position=None, ai_signal=None):
        """更新系统状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE system_status 
            SET status = ?, 
                last_update = ?,
                account_info = ?,
                btc_info = ?,
                position = ?,
                ai_signal = ?
            WHERE id = 1
        ''', (
            status,
            datetime.now().isoformat(),
            json.dumps(account_info or {}, ensure_ascii=False),
            json.dumps(btc_info or {}, ensure_ascii=False),
            json.dumps(position or {}, ensure_ascii=False),
            json.dumps(ai_signal or {}, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def get_system_status(self):
        """获取系统状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM system_status WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'status': row['status'],
                'last_update': row['last_update'],
                'account_info': json.loads(row['account_info'] or '{}'),
                'btc_info': json.loads(row['btc_info'] or '{}'),
                'position': json.loads(row['position'] or '{}'),
                'ai_signal': json.loads(row['ai_signal'] or '{}')
            }
        return {}
    
    # ========== 交易记录管理 ==========
    
    def save_trade_record(self, trade_record):
        """保存交易记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 插入交易记录
        cursor.execute('''
            INSERT INTO trades (timestamp, trade_type, position_action, position_side, 
                              price, amount, pnl, signal, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_record.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            trade_record.get('trade_type'),
            trade_record.get('position_action'),
            trade_record.get('position_side'),
            trade_record.get('price'),
            trade_record.get('amount'),
            trade_record.get('pnl', 0),
            trade_record.get('signal'),
            trade_record.get('notes'),
            datetime.now().isoformat()
        ))
        
        trade_id = cursor.lastrowid
        
        # 如果有仓位动作，保存到仓位记录表
        if trade_record.get('position_action') in ['open', 'close']:
            cursor.execute('''
                INSERT INTO position_records (timestamp, action, side, price, amount, pnl, trade_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_record.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                trade_record.get('position_action'),
                trade_record.get('position_side'),
                trade_record.get('price'),
                trade_record.get('amount'),
                trade_record.get('pnl', 0),
                trade_id,
                datetime.now().isoformat()
            ))
        
        # 保持只保留最近100条交易记录
        cursor.execute('SELECT COUNT(*) FROM trades')
        count = cursor.fetchone()[0]
        if count > 100:
            cursor.execute('''
                DELETE FROM trades 
                WHERE id IN (
                    SELECT id FROM trades 
                    ORDER BY created_at ASC 
                    LIMIT ?
                )
            ''', (count - 100,))
        
        conn.commit()
        conn.close()
        
        # 更新绩效数据
        self._update_performance(trade_record)
    
    def get_trade_history(self, page: int = 1, page_size: int = 10, show_hold: bool = False):
        """获取交易历史（支持分页和过滤HOLD交易）
        
        Args:
            page: 页码，从1开始
            page_size: 每页数量
            show_hold: 是否显示HOLD交易，默认False（不显示）
            
        Returns:
            dict: {
                'data': 交易记录列表,
                'total': 总记录数（过滤后）,
                'page': 当前页码,
                'page_size': 每页数量,
                'total_pages': 总页数（过滤后）
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 获取总记录数（应用过滤条件）
        if not show_hold:
            cursor.execute('SELECT COUNT(*) FROM trades WHERE signal != ? OR signal IS NULL', ('HOLD',))
        else:
            cursor.execute('SELECT COUNT(*) FROM trades')
        total = cursor.fetchone()[0]
        
        # 计算分页
        offset = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        # 获取分页数据（应用过滤条件）
        if not show_hold:
            cursor.execute('''
                SELECT * FROM trades 
                WHERE signal != ? OR signal IS NULL
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', ('HOLD', page_size, offset))
        else:
            cursor.execute('''
                SELECT * FROM trades 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (page_size, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            'data': [dict(row) for row in rows],
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }
    
    # ========== 绩效数据管理 ==========
    
    def _update_performance(self, trade_record):
        """更新绩效数据"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 获取当前绩效数据
        cursor.execute('SELECT * FROM performance WHERE id = 1')
        perf = cursor.fetchone()
        
        total_trades = (perf['total_trades'] or 0) + 1
        pnl = trade_record.get('pnl', 0)
        total_pnl = (perf['total_pnl'] or 0) + pnl
        
        # 更新每日绩效
        today = datetime.now().strftime("%Y-%m-%d")
        daily_pnl = json.loads(perf['daily_pnl'] or '{}')
        daily_pnl[today] = daily_pnl.get(today, 0) + pnl
        
        # 更新月度绩效
        month = datetime.now().strftime("%Y-%m")
        monthly_pnl = json.loads(perf['monthly_pnl'] or '{}')
        monthly_pnl[month] = monthly_pnl.get(month, 0) + pnl
        
        # 计算胜率（基于仓位记录）
        completed_trades, winning_trades = self._calculate_win_rate_from_positions()
        
        # 更新绩效表
        cursor.execute('''
            UPDATE performance 
            SET total_trades = ?,
                winning_trades = ?,
                completed_trades = ?,
                total_pnl = ?,
                daily_pnl = ?,
                monthly_pnl = ?,
                last_updated = ?
            WHERE id = 1
        ''', (
            total_trades,
            winning_trades,
            completed_trades,
            total_pnl,
            json.dumps(daily_pnl, ensure_ascii=False),
            json.dumps(monthly_pnl, ensure_ascii=False),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _calculate_win_rate_from_positions(self):
        """基于仓位记录计算胜率（开仓+平仓配对）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 获取所有仓位记录，按时间排序
        cursor.execute('''
            SELECT * FROM position_records 
            ORDER BY timestamp ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return (0, 0)
        
        completed_trades = 0
        winning_trades = 0
        open_positions = {}  # {side: [open_record, ...]}
        
        for row in rows:
            record = dict(row)
            action = record.get('action')
            side = record.get('side')
            
            if action == 'open':
                # 记录开仓
                if side not in open_positions:
                    open_positions[side] = []
                open_positions[side].append(record)
            elif action == 'close':
                # 匹配最近的同方向开仓记录
                if side in open_positions and len(open_positions[side]) > 0:
                    # 配对成功，完成一次交易
                    completed_trades += 1
                    if record.get('pnl', 0) > 0:
                        winning_trades += 1
                    # 移除已配对的开仓记录（FIFO）
                    open_positions[side].pop(0)
                else:
                    # 没有匹配的开仓记录，可能是历史数据或数据不一致
                    # 仍然计算为一次交易（平仓时 pnl 不为 0）
                    if record.get('pnl', 0) != 0:
                        completed_trades += 1
                        if record.get('pnl', 0) > 0:
                            winning_trades += 1
        
        return (completed_trades, winning_trades)
    
    def get_performance(self):
        """获取绩效数据"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM performance WHERE id = 1')
        row = cursor.fetchone()
        
        if row:
            # 获取仓位记录（用于兼容原有接口）
            position_records = self._get_position_records(cursor)
            
            result = {
                'total_trades': row['total_trades'] or 0,
                'winning_trades': row['winning_trades'] or 0,
                'completed_trades': row['completed_trades'] or 0,
                'total_pnl': row['total_pnl'] or 0,
                'daily_pnl': json.loads(row['daily_pnl'] or '{}'),
                'monthly_pnl': json.loads(row['monthly_pnl'] or '{}'),
                'position_records': position_records  # 为了兼容原有接口
            }
            conn.close()
            return result
        
        conn.close()
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'completed_trades': 0,
            'total_pnl': 0,
            'daily_pnl': {},
            'monthly_pnl': {},
            'position_records': []
        }
    
    def _get_position_records(self, cursor=None):
        """获取仓位记录（用于兼容原有接口）"""
        should_close = False
        if cursor is None:
            conn = self._get_connection()
            cursor = conn.cursor()
            should_close = True
        
        cursor.execute('''
            SELECT timestamp, action, side, price, amount, pnl 
            FROM position_records 
            ORDER BY timestamp DESC
        ''')
        
        rows = cursor.fetchall()
        
        if should_close:
            conn.close()
        
        return [dict(row) for row in rows]
    
    # ========== AI分析记录管理 ==========
    
    def save_ai_analysis_record(self, analysis_record):
        """保存AI分析记录（包含完整提示词和响应）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 添加时间戳
        timestamp = analysis_record.get('timestamp', datetime.now().isoformat())
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        
        # 提取各字段
        system_prompt = analysis_record.get('system_prompt', '')
        user_prompt = analysis_record.get('user_prompt', '')
        ai_response = analysis_record.get('ai_response', '')
        
        # 分析数据（移除已单独存储的字段，避免重复）
        analysis_data = {k: v for k, v in analysis_record.items() 
                        if k not in ['system_prompt', 'user_prompt', 'ai_response', 'timestamp']}
        
        # 插入分析记录
        cursor.execute('''
            INSERT INTO ai_analysis_history (timestamp, system_prompt, user_prompt, ai_response, analysis_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            system_prompt,
            user_prompt,
            ai_response,
            json.dumps(analysis_data, ensure_ascii=False),
            datetime.now().isoformat()
        ))
        
        # 保持只保留最近50条记录
        cursor.execute('SELECT COUNT(*) FROM ai_analysis_history')
        count = cursor.fetchone()[0]
        if count > 50:
            cursor.execute('''
                DELETE FROM ai_analysis_history 
                WHERE id IN (
                    SELECT id FROM ai_analysis_history 
                    ORDER BY created_at ASC 
                    LIMIT ?
                )
            ''', (count - 50,))
        
        conn.commit()
        conn.close()
    
    def get_ai_analysis_history(self, page: int = 1, page_size: int = 10):
        """获取AI分析历史记录（支持分页）
        
        Args:
            page: 页码，从1开始
            page_size: 每页数量
            
        Returns:
            dict: {
                'data': AI分析记录列表,
                'total': 总记录数,
                'page': 当前页码,
                'page_size': 每页数量,
                'total_pages': 总页数
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute('SELECT COUNT(*) FROM ai_analysis_history')
        total = cursor.fetchone()[0]
        
        # 计算分页
        offset = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        # 获取分页数据（包含完整提示词和响应）
        cursor.execute('''
            SELECT timestamp, system_prompt, user_prompt, ai_response, analysis_data 
            FROM ai_analysis_history 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (page_size, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 组合数据
        data = []
        for row in rows:
            record = json.loads(row['analysis_data']) if row['analysis_data'] else {}
            record.update({
                'timestamp': row['timestamp'],
                'system_prompt': row['system_prompt'],
                'user_prompt': row['user_prompt'],
                'ai_response': row['ai_response']
            })
            data.append(record)
        
        return {
            'data': data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }
    
    # ========== 系统统计管理 ==========
    
    def get_system_stats(self):
        """获取系统统计数据（累计时间、调用次数）
        
        Returns:
            dict: {
                'first_start_time': str,  # 首次启动时间
                'total_minutes_elapsed': float,  # 累计分钟数
                'total_invocation_count': int,  # 总调用次数
                'last_update_time': str  # 最后更新时间
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM system_stats WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'first_start_time': row['first_start_time'],
                'total_minutes_elapsed': row['total_minutes_elapsed'] or 0,
                'total_invocation_count': row['total_invocation_count'] or 0,
                'last_update_time': row['last_update_time']
            }
        else:
            # 如果不存在，初始化
            now = datetime.now().isoformat()
            return {
                'first_start_time': now,
                'total_minutes_elapsed': 0,
                'total_invocation_count': 0,
                'last_update_time': now
            }
    
    def update_system_stats(self, minutes_elapsed, invocation_count):
        """更新系统统计数据
        
        Args:
            minutes_elapsed: 累计运行分钟数
            invocation_count: 总调用次数
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # 检查是否存在
        cursor.execute('SELECT COUNT(*) FROM system_stats WHERE id = 1')
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            # 更新现有记录
            cursor.execute('''
                UPDATE system_stats 
                SET total_minutes_elapsed = ?, 
                    total_invocation_count = ?, 
                    last_update_time = ?
                WHERE id = 1
            ''', (minutes_elapsed, invocation_count, now))
        else:
            # 创建新记录
            cursor.execute('''
                INSERT INTO system_stats (id, first_start_time, total_minutes_elapsed, 
                                        total_invocation_count, last_update_time)
                VALUES (1, ?, ?, ?, ?)
            ''', (now, minutes_elapsed, invocation_count, now))
        
        conn.commit()
        conn.close()

# 全局数据管理器实例
data_manager = DataManager()

# 兼容性函数
def update_system_status(status, account_info=None, btc_info=None, position=None, ai_signal=None):
    data_manager.update_system_status(status, account_info, btc_info, position, ai_signal)

def save_trade_record(trade_record):
    data_manager.save_trade_record(trade_record)

def save_ai_analysis_record(analysis_record):
    data_manager.save_ai_analysis_record(analysis_record)

def get_system_stats():
    """获取系统统计数据（累计时间、调用次数）"""
    return data_manager.get_system_stats()

def update_system_stats(minutes_elapsed, invocation_count):
    """更新系统统计数据"""
    data_manager.update_system_stats(minutes_elapsed, invocation_count)