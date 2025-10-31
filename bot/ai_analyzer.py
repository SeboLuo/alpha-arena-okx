"""AI分析模块 - DeepSeek分析"""
from .config import deepseek_client, TRADE_CONFIG, signal_history
from .technical_analysis import generate_technical_analysis_text
from .sentiment import get_sentiment_indicators
from .position_manager import get_current_position
from .utils import safe_json_parse, create_fallback_signal


def analyze_with_deepseek(price_data):
    """使用DeepSeek分析市场并生成交易信号（增强版）"""

    # 生成技术分析文本
    technical_analysis = generate_technical_analysis_text(price_data)

    # 构建K线数据文本
    kline_text = f"【最近5根{TRADE_CONFIG['timeframe']}K线数据】\n"
    for i, kline in enumerate(price_data['kline_data'][-5:]):
        trend = "阳线" if kline['close'] > kline['open'] else "阴线"
        change = ((kline['close'] - kline['open']) / kline['open']) * 100
        kline_text += f"K线{i + 1}: {trend} 开盘:{kline['open']:.2f} 收盘:{kline['close']:.2f} 涨跌:{change:+.2f}%\n"

    # 添加上次交易信号
    signal_text = ""
    if signal_history:
        last_signal = signal_history[-1]
        signal_text = f"\n【上次交易信号】\n信号: {last_signal.get('signal', 'N/A')}\n信心: {last_signal.get('confidence', 'N/A')}"

    # 获取情绪数据
    sentiment_data = get_sentiment_indicators()
    # 简化情绪文本 多了没用
    if sentiment_data:
        sign = '+' if sentiment_data['net_sentiment'] >= 0 else ''
        sentiment_text = f"【市场情绪】乐观{sentiment_data['positive_ratio']:.1%} 悲观{sentiment_data['negative_ratio']:.1%} 净值{sign}{sentiment_data['net_sentiment']:.3f}"
    else:
        sentiment_text = "【市场情绪】数据暂不可用"

    # 添加当前持仓信息
    current_pos = get_current_position()
    position_text = "无持仓" if not current_pos else f"{current_pos['side']}仓, 数量: {current_pos['size']}, 盈亏: {current_pos['unrealized_pnl']:.2f}USDT"
    pnl_text = f", 持仓盈亏: {current_pos['unrealized_pnl']:.2f} USDT" if current_pos else ""

    prompt = f"""
    你是一个专业的加密货币交易分析师。请基于以下BTC/USDT {TRADE_CONFIG['timeframe']}周期数据进行分析：

    {kline_text}

    {technical_analysis}

    {signal_text}

    {sentiment_text}  # 添加情绪分析

    【当前行情】
    - 当前价格: ${price_data['price']:,.2f}
    - 时间: {price_data['timestamp']}
    - 本K线最高: ${price_data['high']:,.2f}
    - 本K线最低: ${price_data['low']:,.2f}
    - 本K线成交量: {price_data['volume']:.2f} BTC
    - 价格变化: {price_data['price_change']:+.2f}%
    - 当前持仓: {position_text}{pnl_text}

    【防频繁交易重要原则】
    1. **趋势持续性优先**: 不要因单根K线或短期波动改变整体趋势判断
    2. **持仓稳定性**: 除非趋势明确强烈反转，否则保持现有持仓方向
    3. **反转确认**: 需要至少2-3个技术指标同时确认趋势反转才改变信号
    4. **成本意识**: 减少不必要的仓位调整，每次交易都有成本

    【交易指导原则 - 必须遵守】
    1. **技术分析主导** (权重60%)：趋势、支撑阻力、K线形态是主要依据
    2. **市场情绪辅助** (权重30%)：情绪数据用于验证技术信号，不能单独作为交易理由  
    - 情绪与技术同向 → 增强信号信心
    - 情绪与技术背离 → 以技术分析为主，情绪仅作参考
    - 情绪数据延迟 → 降低权重，以实时技术指标为准
    3. **风险管理** (权重10%)：考虑持仓、盈亏状况和止损位置
    4. **趋势跟随**: 明确趋势出现时立即行动，不要过度等待
    5. 因为做的是btc，做多权重可以大一点点
    6. **信号明确性**:
    - 强势上涨趋势 → BUY信号
    - 强势下跌趋势 → SELL信号  
    - 仅在窄幅震荡、无明确方向时 → HOLD信号
    7. **技术指标权重**:
    - 趋势(均线排列) > RSI > MACD > 布林带
    - 价格突破关键支撑/阻力位是重要信号 


    【当前技术状况分析】
    - 整体趋势: {price_data['trend_analysis'].get('overall', 'N/A')}
    - 短期趋势: {price_data['trend_analysis'].get('short_term', 'N/A')} 
    - RSI状态: {price_data['technical_data'].get('rsi', 0):.1f} ({'超买' if price_data['technical_data'].get('rsi', 0) > 70 else '超卖' if price_data['technical_data'].get('rsi', 0) < 30 else '中性'})
    - MACD方向: {price_data['trend_analysis'].get('macd', 'N/A')}

    【智能仓位管理规则 - 必须遵守】

    1. **减少过度保守**：
       - 明确趋势中不要因轻微超买/超卖而过度HOLD
       - RSI在30-70区间属于健康范围，不应作为主要HOLD理由
       - 布林带位置在20%-80%属于正常波动区间

    2. **趋势跟随优先**：
       - 强势上涨趋势 + 任何RSI值 → 积极BUY信号
       - 强势下跌趋势 + 任何RSI值 → 积极SELL信号
       - 震荡整理 + 无明确方向 → HOLD信号

    3. **突破交易信号**：
       - 价格突破关键阻力 + 成交量放大 → 高信心BUY
       - 价格跌破关键支撑 + 成交量放大 → 高信心SELL

    4. **持仓优化逻辑**：
       - 已有持仓且趋势延续 → 保持或BUY/SELL信号
       - 趋势明确反转 → 及时反向信号
       - 不要因为已有持仓而过度HOLD

    【重要】请基于技术分析做出明确判断，避免因过度谨慎而错过趋势行情！

    【分析要求】
    基于以上分析，请给出明确的交易信号

    请用以下JSON格式回复：
    {{
        "signal": "BUY|SELL|HOLD",
        "reason": "简要分析理由(包含趋势判断和技术依据)",
        "stop_loss": 具体价格,
        "take_profit": 具体价格, 
        "confidence": "HIGH|MEDIUM|LOW"
    }}
    """

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system",
                 "content": f"您是一位专业的交易员，专注于{TRADE_CONFIG['timeframe']}周期趋势分析。请结合K线形态和技术指标做出判断，并严格遵循JSON格式要求。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            temperature=0.1
        )

        # 安全解析JSON
        result = response.choices[0].message.content
        print(f"DeepSeek原始回复: {result}")

        # 提取JSON部分
        start_idx = result.find('{')
        end_idx = result.rfind('}') + 1

        if start_idx != -1 and end_idx != 0:
            json_str = result[start_idx:end_idx]
            signal_data = safe_json_parse(json_str)

            if signal_data is None:
                signal_data = create_fallback_signal(price_data)
        else:
            signal_data = create_fallback_signal(price_data)

        # 验证必需字段
        required_fields = ['signal', 'reason', 'stop_loss', 'take_profit', 'confidence']
        if not all(field in signal_data for field in required_fields):
            signal_data = create_fallback_signal(price_data)

        # 保存信号到历史记录
        signal_data['timestamp'] = price_data['timestamp']
        signal_history.append(signal_data)
        if len(signal_history) > 30:
            signal_history.pop(0)

        # 信号统计
        signal_count = len([s for s in signal_history if s.get('signal') == signal_data['signal']])
        total_signals = len(signal_history)
        print(f"信号统计: {signal_data['signal']} (最近{total_signals}次中出现{signal_count}次)")

        # 信号连续性检查
        if len(signal_history) >= 3:
            last_three = [s['signal'] for s in signal_history[-3:]]
            if len(set(last_three)) == 1:
                print(f"⚠️ 注意：连续3次{signal_data['signal']}信号")

        return signal_data

    except Exception as e:
        print(f"DeepSeek分析失败: {e}")
        return create_fallback_signal(price_data)


def analyze_with_deepseek_with_retry(price_data, max_retries=2):
    """带重试的DeepSeek分析"""
    for attempt in range(max_retries):
        try:
            signal_data = analyze_with_deepseek(price_data)
            if signal_data and not signal_data.get('is_fallback', False):
                return signal_data

            print(f"第{attempt + 1}次尝试失败，进行重试...")
            import time
            time.sleep(1)

        except Exception as e:
            print(f"第{attempt + 1}次尝试异常: {e}")
            if attempt == max_retries - 1:
                return create_fallback_signal(price_data)
            import time
            time.sleep(1)

    return create_fallback_signal(price_data)

