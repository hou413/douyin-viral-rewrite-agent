"""
迭代优化Agent
负责：总结成功模式、更新爆款模式库、设计下一轮实验
输出：策略更新建议
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.core.models import DiagnosisReport, ExperimentRecord, KnowledgeEntry
from src.core.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class IterateAgent:
    """迭代优化Agent"""

    def __init__(self, knowledge_base: KnowledgeBase, ai_call_func=None):
        self.kb = knowledge_base
        self._call_ai = ai_call_func

    def analyze_and_iterate(
        self,
        reports: List[DiagnosisReport],
        account_name: str
    ) -> Dict:
        """分析诊断报告，生成迭代建议"""
        logger.info(f"分析 {len(reports)} 条诊断报告...")

        # 1. 总结成功模式
        success_patterns = self._extract_success_patterns(reports)

        # 2. 总结失败模式
        failure_patterns = self._extract_failure_patterns(reports)

        # 3. 设计下一轮实验
        experiments = self._design_experiments(success_patterns, failure_patterns)

        # 4. 更新知识库
        self._update_knowledge_base(success_patterns, failure_patterns, account_name)

        # 5. 生成策略建议
        strategy = self._generate_strategy(success_patterns, failure_patterns)

        result = {
            "analyzed_at": datetime.now().isoformat(),
            "report_count": len(reports),
            "success_patterns": success_patterns,
            "failure_patterns": failure_patterns,
            "experiments": [e.to_dict() for e in experiments],
            "strategy": strategy,
        }

        logger.info(f"迭代分析完成，发现{len(success_patterns)}个成功模式，{len(failure_patterns)}个失败模式")
        return result

    def _extract_success_patterns(self, reports: List[DiagnosisReport]) -> List[Dict]:
        """提取成功模式"""
        patterns = []
        
        # 找出表现好的视频（问题维度为"无明显问题"或严重程度为"低"）
        good_reports = [r for r in reports if r.severity == "低"]
        
        if not good_reports:
            return patterns

        # 分析共同特征
        for report in good_reports[:5]:  # 取前5个
            perf = report.performance
            pattern = {
                "video_id": perf.video_id,
                "title": perf.video_title,
                "metrics": {
                    "like_rate": perf.like_rate,
                    "share_rate": perf.share_rate,
                    "completion_rate": perf.completion_rate,
                },
                "strengths": self._identify_strengths(report),
            }
            patterns.append(pattern)

        return patterns

    def _identify_strengths(self, report: DiagnosisReport) -> List[str]:
        """识别优势"""
        strengths = []
        perf = report.performance

        if perf.like_rate > 0.08:
            strengths.append("点赞率高，内容引发共鸣")
        if perf.share_rate > 0.02:
            strengths.append("分享率高，有传播价值")
        if perf.completion_rate > 0.5:
            strengths.append("完播率高，内容吸引力强")
        if perf.follow_rate > 0.01:
            strengths.append("涨粉率高，账号价值明确")

        return strengths if strengths else ["整体表现均衡"]

    def _extract_failure_patterns(self, reports: List[DiagnosisReport]) -> List[Dict]:
        """提取失败模式"""
        patterns = []
        
        # 找出问题严重的视频
        bad_reports = [r for r in reports if r.severity in ["高", "中"]]
        
        for report in bad_reports[:5]:
            pattern = {
                "video_id": report.video_id,
                "title": report.performance.video_title,
                "problem": report.problem_dimension,
                "diagnosis": report.diagnosis,
                "suggestions": report.suggestions[:3],  # 取前3条建议
            }
            patterns.append(pattern)

        return patterns

    def _design_experiments(
        self,
        success_patterns: List[Dict],
        failure_patterns: List[Dict]
    ) -> List[ExperimentRecord]:
        """设计下一轮实验"""
        experiments = []

        # 基于失败模式设计实验
        if failure_patterns:
            # 统计最常见问题
            problem_count = {}
            for p in failure_patterns:
                prob = p["problem"]
                problem_count[prob] = problem_count.get(prob, 0) + 1

            top_problem = max(problem_count.items(), key=lambda x: x[1])[0]

            # 设计针对该问题的实验
            exp = ExperimentRecord(
                id=f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                experiment_name=f"优化{top_problem}",
                hypothesis=f"通过针对性优化{top_problem}，可提升整体表现20%",
                test_variable=top_problem,
                variant_a={"strategy": "当前策略", "description": "保持现有内容方向"},
                variant_b={
                    "strategy": f"优化{top_problem}",
                    "description": f"针对{top_problem}进行专项优化",
                },
                metric="like_rate",
            )
            experiments.append(exp)

        # 基于成功模式设计扩展实验
        if success_patterns:
            # 找出共同优势
            common_strengths = set()
            for p in success_patterns:
                common_strengths.update(p["strengths"])

            if common_strengths:
                strength = list(common_strengths)[0]
                exp = ExperimentRecord(
                    id=f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_2",
                    experiment_name=f"放大{strength}",
                    hypothesis=f"强化{strength}的特征，可进一步提升表现",
                    test_variable=strength,
                    variant_a={"strategy": "当前强度", "description": f"保持{strength}的当前水平"},
                    variant_b={
                        "strategy": f"强化{strength}",
                        "description": f"将{strength}发挥到极致",
                    },
                    metric="share_rate",
                )
                experiments.append(exp)

        return experiments

    def _update_knowledge_base(
        self,
        success_patterns: List[Dict],
        failure_patterns: List[Dict],
        account_name: str
    ):
        """更新知识库"""
        # 记录成功模式
        for pattern in success_patterns:
            entry = KnowledgeEntry(
                id=f"pattern_{pattern['video_id']}",
                entry_type="pattern",
                title=f"成功模式: {pattern['title']}",
                content=pattern,
                tags=["success", account_name],
                success_rate=0.8,  # 假设成功率80%
                usage_count=1,
            )
            self.kb.add_entry(entry)

        # 记录失败模式
        for pattern in failure_patterns:
            entry = KnowledgeEntry(
                id=f"failure_{pattern['video_id']}",
                entry_type="pattern",
                title=f"失败模式: {pattern['title']}",
                content=pattern,
                tags=["failure", account_name],
                success_rate=0.2,  # 假设成功率20%
                usage_count=1,
            )
            self.kb.add_entry(entry)

        logger.info(f"知识库已更新，新增{len(success_patterns) + len(failure_patterns)}条模式")

    def _generate_strategy(
        self,
        success_patterns: List[Dict],
        failure_patterns: List[Dict]
    ) -> Dict:
        """生成策略建议"""
        strategy = {
            "continue_doing": [],
            "stop_doing": [],
            "start_doing": [],
            "priority": "中",
        }

        # 继续做的事
        if success_patterns:
            for p in success_patterns[:3]:
                strategy["continue_doing"].extend(p["strengths"])

        # 停止做的事
        if failure_patterns:
            for p in failure_patterns[:3]:
                strategy["stop_doing"].append(p["problem"])

        # 开始做的事
        if failure_patterns:
            suggestions = set()
            for p in failure_patterns:
                suggestions.update(p["suggestions"][:2])
            strategy["start_doing"] = list(suggestions)[:5]

        # 优先级
        high_severity_count = sum(1 for p in failure_patterns if p.get("severity") == "高")
        if high_severity_count > len(failure_patterns) * 0.5:
            strategy["priority"] = "高"
        elif high_severity_count < len(failure_patterns) * 0.2:
            strategy["priority"] = "低"

        return strategy


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.core.models import PerformanceData, DiagnosisReport
    from datetime import datetime

    # 测试数据
    perf1 = PerformanceData(
        video_id="v001", video_title="机器人管家实测",
        publish_time=datetime.now(), views=50000, likes=4000,
        shares=500, comments=200, follows=100, completions=25000, avg_watch_time=12
    )
    report1 = DiagnosisReport(
        video_id="v001", performance=perf1,
        diagnosis="表现优秀", problem_dimension="无明显问题",
        severity="低", suggestions=["继续保持"], benchmark_comparison={}
    )

    kb = KnowledgeBase()
    agent = IterateAgent(knowledge_base=kb)
    result = agent.analyze_and_iterate([report1], "test_account")
    print(json.dumps(result, ensure_ascii=False, indent=2))
