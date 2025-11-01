"""
占位符分析器 - 提取和分类提示词模板中的所有占位符

用途说明：
这是一个开发/调试工具，主要用于：
1. 模板验证：检查模板中的占位符是否完整、格式是否正确
2. 文档生成：自动生成占位符列表和分类文档
3. 开发调试：查看和分析模板结构

注意：
- PromptBuilder 在运行时不需要此分析器（直接使用正则表达式替换）
- 此工具通常在开发阶段使用，而不是每次生成提示词时调用
- 模板文件不会频繁变化，分析结果可以复用
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Any
from dataclasses import dataclass
from enum import Enum


class PlaceholderType(Enum):
    """占位符类型枚举"""
    STRING = "string"  # 普通字符串
    NUMBER = "number"  # 数字
    JSON = "json"  # 需要JSON序列化的对象
    TIME = "time"  # 时间相关
    CURRENCY = "currency"  # 货币/金额
    PERCENTAGE = "percentage"  # 百分比
    TEMPLATE = "template"  # 模板片段（如CoinSection）


@dataclass
class Placeholder:
    """占位符信息"""
    name: str
    template_file: str
    full_placeholder: str  # 完整的占位符文本，如 "{{.Symbol}}" 或 "{{.Positions | toJSON}}"
    placeholder_type: PlaceholderType
    has_json_conversion: bool = False  # 是否包含 | toJSON
    description: str = ""  # 描述信息


class PlaceholderAnalyzer:
    """占位符分析器"""
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent
        self.prompts_dir = Path(prompts_dir)
        
        # 占位符正则表达式（支持 {{.Name}} 和 {{.Name | toJSON}} 格式）
        self.placeholder_pattern = re.compile(r'\{\{\s*\.([^}|]+?)(?:\s*\|\s*toJSON)?\s*\}\}')
        
        # 所有发现的占位符
        self.placeholders: Dict[str, Placeholder] = {}
        
        # 分类存储
        self.placeholders_by_file: Dict[str, List[Placeholder]] = {}
        self.placeholders_by_type: Dict[PlaceholderType, List[Placeholder]] = {}
        
    def analyze(self) -> Dict[str, Any]:
        """
        分析所有模板文件中的占位符
        
        Returns:
            分析结果字典
        """
        # 扫描所有 .md 文件
        template_files = list(self.prompts_dir.glob("*.md"))
        
        for template_file in template_files:
            self._analyze_file(template_file)
        
        # 分类统计
        self._categorize_placeholders()
        
        return self._generate_report()
    
    def _analyze_file(self, template_file: Path):
        """分析单个模板文件"""
        content = template_file.read_text(encoding='utf-8')
        file_name = template_file.name
        
        # 查找所有占位符
        matches = self.placeholder_pattern.findall(content)
        full_matches = self.placeholder_pattern.finditer(content)
        
        seen = set()
        
        for match, full_match in zip(matches, full_matches):
            placeholder_name = match.strip()
            
            # 避免重复（考虑大小写和空格）
            key = placeholder_name.lower()
            if key in seen:
                continue
            seen.add(key)
            
            # 检查是否包含 toJSON
            full_text = full_match.group(0)
            has_json = 'toJSON' in full_text
            
            # 确定类型
            p_type = self._determine_type(placeholder_name, file_name)
            
            placeholder = Placeholder(
                name=placeholder_name,
                template_file=file_name,
                full_placeholder=full_text,
                placeholder_type=p_type,
                has_json_conversion=has_json,
                description=self._get_description(placeholder_name)
            )
            
            # 使用完整名称作为key（包括文件前缀避免冲突）
            key = f"{file_name}:{placeholder_name}"
            self.placeholders[key] = placeholder
            
            # 按文件分组
            if file_name not in self.placeholders_by_file:
                self.placeholders_by_file[file_name] = []
            self.placeholders_by_file[file_name].append(placeholder)
    
    def _determine_type(self, name: str, file_name: str) -> PlaceholderType:
        """根据名称推断占位符类型"""
        name_lower = name.lower()
        
        # JSON类型（明确标记的）
        if any(x in name_lower for x in ['series', 'prices', 'positions', 'macd', 'rsi']):
            if 'series' in name_lower or 'prices' in name_lower or 'positions' in name_lower:
                return PlaceholderType.JSON
        
        # 时间类型
        if any(x in name_lower for x in ['time', 'elapsed', 'minutes', 'invocation']):
            return PlaceholderType.TIME
        
        # 货币类型
        if any(x in name_lower for x in ['capital', 'cash', 'value', 'price', 'pnl', 'usd']):
            return PlaceholderType.CURRENCY
        
        # 百分比类型
        if 'percent' in name_lower or 'ratio' in name_lower:
            return PlaceholderType.PERCENTAGE
        
        # 模板类型（复合内容）
        if name == 'CoinSection':
            return PlaceholderType.TEMPLATE
        
        # 数字类型
        if any(x in name_lower for x in ['count', 'leverage', 'range', 'rate', 'rsi', 'macd', 'ema', 'atr', 'volume', 'oi']):
            return PlaceholderType.NUMBER
        
        # 默认字符串
        return PlaceholderType.STRING
    
    def _get_description(self, name: str) -> str:
        """获取占位符的描述"""
        descriptions = {
            # system.md
            'Exchange': '交易所名称',
            'MODEL_NAME': 'AI模型名称',
            'AssetUniverse': '资产范围',
            'StartingCapital': '起始资金',
            'MarketHours': '市场交易时间',
            'DecisionFrequency': '决策频率',
            'LeverageRange': '杠杆范围',
            'ContractType': '合约类型',
            'TradingFees': '交易手续费',
            'Slippage': '滑点',
            
            # user.md
            'MinutesElapsed': '已交易分钟数',
            'CurrentTime': '当前时间',
            'InvocationCount': '调用次数',
            'CoinSection': '币种数据区块（复合模板）',
            'CurrentTotalReturnPercent': '当前总回报百分比',
            'AvailableCash': '可用现金',
            'CurrentAccountValue': '当前账户总值',
            'Positions': '持仓列表（JSON数组）',
            
            # coin.md
            'Symbol': '币种符号',
            'CurrentPrice': '当前价格',
            'CurrentEMA20': '当前20周期EMA',
            'CurrentMACD': '当前MACD值',
            'CurrentRSI7': '当前7周期RSI',
            'OI_Latest': '最新持仓量',
            'OI_Avg': '平均持仓量',
            'FundingRate': '资金费率',
            'MidPrices': '中间价序列（JSON数组）',
            'EMA20Series': '20周期EMA序列（JSON数组）',
            'MACDSeries': 'MACD序列（JSON数组）',
            'RSI7Series': '7周期RSI序列（JSON数组）',
            'RSI14Series': '14周期RSI序列（JSON数组）',
            'EMA20_4h': '4小时20周期EMA',
            'EMA50_4h': '4小时50周期EMA',
            'ATR3_4h': '4小时3周期ATR',
            'ATR14_4h': '4小时14周期ATR',
            'CurrentVolume_4h': '4小时当前成交量',
            'AvgVolume_4h': '4小时平均成交量',
            'MACD4h': '4小时MACD序列（JSON数组）',
            'RSI14_4h': '4小时14周期RSI序列（JSON数组）',
        }
        return descriptions.get(name, '')
    
    def _categorize_placeholders(self):
        """按类型分类占位符"""
        for placeholder in self.placeholders.values():
            p_type = placeholder.placeholder_type
            if p_type not in self.placeholders_by_type:
                self.placeholders_by_type[p_type] = []
            self.placeholders_by_type[p_type].append(placeholder)
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成分析报告"""
        # 统计信息
        total_count = len(self.placeholders)
        json_count = sum(1 for p in self.placeholders.values() if p.has_json_conversion)
        
        # 按文件统计
        by_file = {
            file: {
                'count': len(placeholders),
                'placeholders': [
                    {
                        'name': p.name,
                        'full': p.full_placeholder,
                        'type': p.placeholder_type.value,
                        'has_json': p.has_json_conversion,
                        'description': p.description
                    }
                    for p in placeholders
                ]
            }
            for file, placeholders in self.placeholders_by_file.items()
        }
        
        # 按类型统计
        by_type = {
            p_type.value: {
                'count': len(placeholders),
                'names': [p.name for p in placeholders]
            }
            for p_type, placeholders in self.placeholders_by_type.items()
        }
        
        # 需要JSON转换的占位符列表
        json_placeholders = [
            {
                'name': p.name,
                'file': p.template_file,
                'full': p.full_placeholder
            }
            for p in self.placeholders.values() if p.has_json_conversion
        ]
        
        return {
            'summary': {
                'total_placeholders': total_count,
                'json_placeholders': json_count,
                'files_analyzed': len(self.placeholders_by_file)
            },
            'by_file': by_file,
            'by_type': by_type,
            'json_placeholders': json_placeholders,
            'all_placeholders': {
                p.name: {
                    'full_placeholder': p.full_placeholder,
                    'type': p.placeholder_type.value,
                    'has_json': p.has_json_conversion,
                    'file': p.template_file,
                    'description': p.description
                }
                for p in self.placeholders.values()
            }
        }
    
    def print_report(self):
        """打印分析报告"""
        report = self._generate_report()
        
        print("=" * 80)
        print("占位符分析报告")
        print("=" * 80)
        print(f"\n总计: {report['summary']['total_placeholders']} 个占位符")
        print(f"需要JSON转换: {report['summary']['json_placeholders']} 个")
        print(f"分析文件数: {report['summary']['files_analyzed']}")
        
        print("\n" + "-" * 80)
        print("按文件分类:")
        print("-" * 80)
        for file, data in report['by_file'].items():
            print(f"\n📄 {file} ({data['count']} 个占位符)")
            for p in data['placeholders']:
                json_mark = " [JSON]" if p['has_json'] else ""
                print(f"  • {p['full']} ({p['type']}){json_mark}")
                if p['description']:
                    print(f"    {p['description']}")
        
        print("\n" + "-" * 80)
        print("按类型分类:")
        print("-" * 80)
        for p_type, data in report['by_type'].items():
            print(f"\n📊 {p_type.upper()} ({data['count']} 个)")
            print(f"  {', '.join(data['names'])}")
        
        print("\n" + "-" * 80)
        print("需要JSON转换的占位符:")
        print("-" * 80)
        for p in report['json_placeholders']:
            print(f"  • {p['full']} ({p['file']})")


if __name__ == "__main__":
    analyzer = PlaceholderAnalyzer()
    analyzer.analyze()
    analyzer.print_report()

