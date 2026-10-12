"""
数据反馈闭环
收集发布后数据 → 对比预期vs实际 → 更新知识库权重 → 生成复盘报告
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.core.models import (
    PerformanceData, DiagnosisReport, ExperimentRecord,
    KnowledgeEntry, ViralScore
)
from src.core.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class DataLoop:
    """数据反馈闭环 - 核心差异化功能"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.diagnosis_rules = self._init_diagnosis_rules()
    
    def _init_diagnosis_rules(self) -> List[Dict]:
        """初始化诊断规则引擎"""
        return [
            {
                "id": "rule_001",
                "name": "开头流失高",
                "condition": lambda p: p.completion_rate < 0.3 and p.views > 1000,
                "diagnosis": "开头流失高 → 钩子不够吸引",
                "problem_dimension": "开头吸引力",
                "severity": "高",
                "suggestions": [
                    "优化前3秒钩子，使用冲突型/悬念型开头",
                    "开头直接抛出核心冲突或利益点",
                    "避免铺垫过长，第一句话就要抓人",
                    "参考爆款案例的开头结构"
                ],
                "related_knowledge_type": "template",
                "related_tags": ["开头", "钩子"]
            },
            {
                "id": "rule_002",
                "name": "完播高但分享少",
                "condition": lambda p: p.completion_rate > 0.5 and p.share_rate < 0.01 and p.views > 1000,
                "diagnosis": "完播高但分享少 → 缺传播理由",
                "problem_dimension": "传播动机",
                "severity": "中",
                "suggestions": [
                    "增加社交货币属性：让用户分享后显得有见识/有趣",
                    "在结尾加入'转给需要的朋友'等引导",
                    "增加利他元素：'这个信息对你的朋友也有用'",
                    "制造讨论点，让用户有话题可聊"
                ],
                "related_knowledge_type": "pattern",
                "related_tags": ["传播", "分享"]
            },
            {
                "id": "rule_003",
                "name": "点赞高但涨粉少",
                "condition": lambda p: p.like_rate > 0.05 and p.follow_rate < 0.001 and p.views > 1000,
                "diagnosis": "点赞高但涨粉少 → 账号价值不明确",
                "problem_dimension": "账号匹配度",
                "severity": "中",
                "suggestions": [
                    "在视频中反复提及账号价值主张",
                    "加入'关注我，下期告诉你...'的悬念",
                    "建立系列内容，让用户有追更理由",
                    "强化账号人设和辨识度"
                ],
                "related_knowledge_type": "pattern",
                "related_tags": ["涨粉", "账号"]
            },
            {
                "id": "rule_004",
                "name": "播放高但成交低",
                "condition": lambda p: p.views > 10000 and p.follow_rate < 0.0005,
                "diagnosis": "播放高但成交低 → 人群不匹配",
                "problem_dimension": "内容价值",
                "severity": "高",
                "suggestions": [
                    "重新审视目标受众画像",
                    "内容是否吸引了非目标人群",
                    "增加筛选性内容，劝退非目标用户",
                    "优化CTA的转化路径"
                ],
                "related_knowledge_type": "case",
                "related_tags": ["转化", "人群"]
            },
            {
                "id": "rule_005",
                "name": "整体表现优秀",
                "condition": lambda p: p.completion_rate > 0.5 and p.share_rate > 0.02 and p.like_rate > 0.05,
                "diagnosis": "整体表现优秀 → 可复制成功模式",
                "problem_dimension": "",
                "severity": "低",
                "suggestions": [
                    "总结本次成功的核心要素",
                    "提取可复用的模式到知识库",
                    "考虑做系列内容延续热度",
                    "分析哪些元素可以A/B测试优化"
                ],
                "related_knowledge_type": "case",
                "related_tags": ["爆款", "成功"]
            }
        ]
    
    def collect_performance(self, performance: PerformanceData) -> PerformanceData:
        """收集视频表现数据"""
        entry = KnowledgeEntry(
            id=f"perf_{performance.video_id}",
            entry_type="performance",
            title=performance.video_title,
            content=performance.to_dict(),
            tags=[performance.video_title],
            created_at=performance.publish_time
        )
        self.kb.add(entry)
        logger.info(f"收集视频数据: {performance.video_title} ({performance.views} 播放)")
        return performance
    
    def diagnose(self, performance: PerformanceData) -> DiagnosisReport:
        """诊断视频表现问题"""
        # 遍历诊断规则
        for rule in self.diagnosis_rules:
            try:
                if rule["condition"](performance):
                    # 获取基线对比
                    benchmark = self._get_benchmark_comparison(performance)
                    
                    report = DiagnosisReport(
                        video_id=performance.video_id,
                        performance=performance,
                        diagnosis=rule["diagnosis"],
                        problem_dimension=rule["problem_dimension"],
                        severity=rule["severity"],
                        suggestions=rule["suggestions"],
                        benchmark_comparison=benchmark
                    )
                    
                    logger.info(f"诊断结果: {rule['diagnosis']}")
                    return report
            except Exception as e:
                logger.error(f"规则 {rule['id']} 执行失败: {e}")
                continue
        
        # 无匹配规则，返回默认诊断
        return DiagnosisReport(
            video_id=performance.video_id,
            performance=performance,
            diagnosis="数据量不足，暂无法诊断",
            problem_dimension="",
            severity="低",
            suggestions=["继续积累数据后再分析"],
            benchmark_comparison=self._get_benchmark_comparison(performance)
        )
    
    def _get_benchmark_comparison(self, performance: PerformanceData) -> Dict:
        """与历史基线对比"""
        perf_entries = self.kb.list_all("performance")
        if not perf_entries:
            return {"message": "无历史数据"}
        
        # 计算历史平均指标
        historical_rates = {
            "like_rate": [],
            "share_rate": [],
            "completion_rate": []
        }
        
        for entry in perf_entries:
            try:
                p = PerformanceData.from_dict(entry.content)
                if p.views > 1000:  # 过滤低播放
                    historical_rates["like_rate"].append(p.like_rate)
                    historical_rates["share_rate"].append(p.share_rate)
                    historical_rates["completion_rate"].append(p.completion_rate)
            except Exception:
                continue
        
        benchmark = {}
        for metric, rates in historical_rates.items():
            if rates:
                avg = sum(rates) / len(rates)
                current = getattr(performance, metric, None)
                if current is None:
                    current = getattr(performance, f"{metric.replace('_rate', '')}_rate", 0)
                benchmark[metric] = {
                    "current": round(current, 4),
                    "average": round(avg, 4),
                    "diff": round(current - avg, 4),
                    "trend": "↑" if current > avg else "↓"
                }
        
        return benchmark
    
    def compare_expected_vs_actual(
        self,
        expected: ViralScore,
        actual: PerformanceData
    ) -> Dict:
        """对比预期vs实际"""
        # 将实际数据转化为评分维度
        actual_metrics = {
            "开头吸引力": actual.completion_rate,
            "情绪共鸣": actual.like_rate,
            "传播动机": actual.share_rate,
            "账号匹配度": actual.follow_rate
        }
        
        comparison = {
            "video_id": actual.video_id,
            "expected_score": expected.total_score,
            "actual_performance": {
                "views": actual.views,
                "like_rate": f"{actual.like_rate:.2%}",
                "share_rate": f"{actual.share_rate:.2%}",
                "completion_rate": f"{actual.completion_rate:.2%}",
                "follow_rate": f"{actual.follow_rate:.2%}"
            },
            "deviation_analysis": []
        }
        
        # 分析偏差
        if expected.total_score >= 80 and actual.views < 5000:
            comparison["deviation_analysis"].append({
                "dimension": "整体",
                "issue": "高评分低播放，可能标题/封面/发布时间有问题",
                "suggestion": "检查标题关键词、封面吸引力、发布时间是否合适"
            })
        
        if expected.total_score < 60 and actual.views > 50000:
            comparison["deviation_analysis"].append({
                "dimension": "整体",
                "issue": "低评分高播放，评估模型需要校准",
                "suggestion": "分析该视频的成功要素，更新评估模型"
            })
        
        return comparison
    
    def update_knowledge_from_experiment(self, experiment: ExperimentRecord):
        """从实验结果更新知识库"""
        if not experiment.result or not experiment.conclusion:
            logger.warning("实验尚未完成")
            return
        
        # 记录实验
        entry = KnowledgeEntry(
            id=experiment.id,
            entry_type="experiment",
            title=experiment.experiment_name,
            content=experiment.to_dict(),
            tags=[experiment.test_variable],
            created_at=experiment.created_at
        )
        self.kb.add(entry)
        
        # 如果实验有明确结论，更新相关模板权重
        if "成功" in experiment.conclusion:
            # 找到相关模板并提升权重
            templates = self.kb.search_by_tags(
                [experiment.test_variable],
                entry_type="template"
            )
            for t in templates:
                self.kb.update_success_rate(t.id, "template", 0.9)
        elif "失败" in experiment.conclusion:
            templates = self.kb.search_by_tags(
                [experiment.test_variable],
                entry_type="template"
            )
            for t in templates:
                self.kb.update_success_rate(t.id, "template", 0.3)
        
        logger.info(f"实验结果已更新到知识库: {experiment.experiment_name}")
    
    def generate_review_report(
        self,
        performances: List[PerformanceData],
        period: str = "weekly"
    ) -> Dict:
        """生成复盘报告"""
        if not performances:
            return {"message": "无数据"}
        
        total_views = sum(p.views for p in performances)
        avg_like_rate = sum(p.like_rate for p in performances) / len(performances)
        avg_share_rate = sum(p.share_rate for p in performances) / len(performances)
        avg_completion_rate = sum(p.completion_rate for p in performances) / len(performances)
        
        # 找出表现最好和最差的
        best = max(performances, key=lambda p: p.views)
        worst = min(performances, key=lambda p: p.views)
        
        # 诊断所有视频
        diagnoses = [self.diagnose(p) for p in performances]
        common_problems = {}
        for d in diagnoses:
            if d.problem_dimension:
                common_problems[d.problem_dimension] = common_problems.get(d.problem_dimension, 0) + 1
        
        report = {
            "period": period,
            "video_count": len(performances),
            "total_views": total_views,
            "avg_metrics": {
                "like_rate": f"{avg_like_rate:.2%}",
                "share_rate": f"{avg_share_rate:.2%}",
                "completion_rate": f"{avg_completion_rate:.2%}"
            },
            "best_performer": {
                "title": best.video_title,
                "views": best.views,
                "like_rate": f"{best.like_rate:.2%}"
            },
            "worst_performer": {
                "title": worst.video_title,
                "views": worst.views
            },
            "common_problems": sorted(
                common_problems.items(),
                key=lambda x: x[1],
                reverse=True
            ),
            "action_items": self._generate_action_items(common_problems)
        }
        
        return report
    
    def _generate_action_items(self, common_problems: Dict) -> List[str]:
        """根据常见问题生成行动项"""
        actions = []
        for problem, count in sorted(common_problems.items(), key=lambda x: x[1], reverse=True):
            if problem == "开头吸引力":
                actions.append("【优先级高】优化开头钩子，A/B测试3种开头类型")
            elif problem == "传播动机":
                actions.append("【优先级中】增加内容的社交货币属性")
            elif problem == "账号匹配度":
                actions.append("【优先级中】强化账号价值主张和CTA")
            elif problem == "内容价值":
                actions.append("【优先级高】重新审视目标受众定位")
        
        if not actions:
            actions.append("保持当前策略，继续积累数据")
        
        return actions


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== 数据反馈闭环测试 ===\n")
    
    kb = KnowledgeBase(base_dir="data/knowledge_base")
    loop = DataLoop(kb)
    
    # 模拟视频数据
    perf = PerformanceData(
        video_id="video_test_001",
        video_title="机器人管家实测",
        publish_time=datetime.now(),
        views=50000,
        likes=3000,
        shares=200,
        comments=300,
        follows=50,
        completions=12000
    )
    
    # 收集数据
    loop.collect_performance(perf)
    
    # 诊断
    report = loop.diagnose(perf)
    print(f"诊断: {report.diagnosis}")
    print(f"严重程度: {report.severity}")
    print(f"建议:")
    for s in report.suggestions:
        print(f"  - {s}")
    
    print(f"\n基线对比:")
    for metric, info in report.benchmark_comparison.items():
        print(f"  {metric}: 当前 {info['current']}, 平均 {info['average']} {info['trend']}")
    
    # 复盘报告
    review = loop.generate_review_report([perf])
    print(f"\n复盘摘要:")
    print(f"  视频数: {review['video_count']}")
    print(f"  总播放: {review['total_views']}")
    print(f"  行动项: {review['action_items']}")
    
    print("\n✅ 数据反馈闭环测试通过")
