"""
数据分析Agent
负责：视频表现数据录入、诊断规则引擎、与历史基线对比
输出：诊断报告+优化建议
核心：诊断规则引擎（根据数据表现推断问题）
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.core.models import PerformanceData, DiagnosisReport

logger = logging.getLogger(__name__)


class DataAgent:
    """数据分析Agent"""

    def __init__(self, baseline_metrics: Optional[Dict] = None):
        """
        Args:
            baseline_metrics: 账号历史基线指标
                {
                    "avg_like_rate": 0.05,  # 平均点赞率5%
                    "avg_share_rate": 0.01,  # 平均分享率1%
                    "avg_completion_rate": 0.4,  # 平均完播率40%
                    "avg_follow_rate": 0.005  # 平均涨粉率0.5%
                }
        """
        self.baseline = baseline_metrics or {
            "avg_like_rate": 0.05,
            "avg_share_rate": 0.01,
            "avg_completion_rate": 0.4,
            "avg_follow_rate": 0.005,
        }

    def diagnose(self, perf: PerformanceData) -> DiagnosisReport:
        """诊断单条视频表现"""
        logger.info(f"诊断视频: {perf.video_title}")
        
        # 计算各项指标
        metrics = {
            "like_rate": perf.like_rate,
            "share_rate": perf.share_rate,
            "comment_rate": perf.comment_rate,
            "follow_rate": perf.follow_rate,
            "completion_rate": perf.completion_rate,
            "avg_watch_time": perf.avg_watch_time,
        }

        # 与基线对比
        comparison = {}
        for key, value in metrics.items():
            baseline_key = f"avg_{key}"
            if baseline_key in self.baseline:
                baseline_val = self.baseline[baseline_key]
                diff = value - baseline_val
                comparison[key] = {
                    "current": value,
                    "baseline": baseline_val,
                    "diff": diff,
                    "status": "高于基线" if diff > 0 else "低于基线",
                }

        # 诊断规则引擎
        diagnosis, problem, severity, suggestions = self._diagnose_rules(metrics, comparison)

        report = DiagnosisReport(
            video_id=perf.video_id,
            performance=perf,
            diagnosis=diagnosis,
            problem_dimension=problem,
            severity=severity,
            suggestions=suggestions,
            benchmark_comparison=comparison,
        )

        logger.info(f"诊断完成: {problem} (严重程度: {severity})")
        return report

    def _diagnose_rules(
        self, metrics: Dict, comparison: Dict
    ) -> tuple:
        """
        诊断规则引擎
        返回: (diagnosis, problem_dimension, severity, suggestions)
        """
        issues = []

        # 规则1: 开头流失高（平均观看时长短）
        if metrics["avg_watch_time"] < 5:
            issues.append({
                "problem": "开头流失严重",
                "dimension": "开头吸引力",
                "severity": "高",
                "suggestions": [
                    "前3秒钩子不够吸引，尝试冲突型/悬念型开头",
                    "开头语速太慢，加快节奏",
                    "开头没有明确承诺，用户不知道能得到什么",
                ],
            })

        # 规则2: 完播率高但分享少
        if metrics["completion_rate"] > self.baseline["avg_completion_rate"] * 1.2:
            if metrics["share_rate"] < self.baseline["avg_share_rate"] * 0.8:
                issues.append({
                    "problem": "完播高但分享少",
                    "dimension": "传播动机",
                    "severity": "中",
                    "suggestions": [
                        "内容有价值但缺少传播理由",
                        "增加'分享后显得有见识'的社交货币元素",
                        "结尾明确引导分享：'转发给需要的朋友'",
                    ],
                })

        # 规则3: 点赞高但涨粉少
        if metrics["like_rate"] > self.baseline["avg_like_rate"] * 1.5:
            if metrics["follow_rate"] < self.baseline["avg_follow_rate"] * 0.5:
                issues.append({
                    "problem": "点赞高但涨粉少",
                    "dimension": "账号价值",
                    "severity": "中",
                    "suggestions": [
                        "单条内容受欢迎，但账号长期价值不明确",
                        "加强账号定位，让用户知道'关注我能持续获得什么'",
                        "结尾增加系列化引导：'关注我，下期告诉你...'",
                    ],
                })

        # 规则4: 播放高但转化低（点赞、评论、分享都低）
        if perf.views > 10000:  # 假设播放量>1万算高
            if (
                metrics["like_rate"] < self.baseline["avg_like_rate"] * 0.5
                and metrics["share_rate"] < self.baseline["avg_share_rate"] * 0.5
            ):
                issues.append({
                    "problem": "播放高但互动低",
                    "dimension": "内容匹配度",
                    "severity": "高",
                    "suggestions": [
                        "流量进来了但内容不匹配，用户快速流失",
                        "检查标题/封面是否过度承诺",
                        "内容与目标受众需求不符，重新定位选题",
                    ],
                })

        # 规则5: 评论率低
        if metrics["comment_rate"] < 0.005:  # 评论率<0.5%
            issues.append({
                "problem": "评论率低",
                "dimension": "互动设计",
                "severity": "低",
                "suggestions": [
                    "结尾没有引导评论，增加开放性问题",
                    "内容没有争议点或讨论空间",
                    "尝试抛出'你觉得A还是B？'的二选一问题",
                ],
            })

        # 选择最严重的问题
        if not issues:
            return (
                "视频表现正常，各项指标在基线范围内",
                "无明显问题",
                "低",
                ["继续保持当前内容策略"],
            )

        # 按严重程度排序
        severity_order = {"高": 0, "中": 1, "低": 2}
        issues.sort(key=lambda x: severity_order[x["severity"]])
        main_issue = issues[0]

        # 合并所有建议
        all_suggestions = []
        for issue in issues:
            all_suggestions.extend(issue["suggestions"])

        diagnosis = f"发现{len(issues)}个问题，最严重的是「{main_issue['problem']}」"
        return (
            diagnosis,
            main_issue["dimension"],
            main_issue["severity"],
            all_suggestions,
        )

    def batch_diagnose(self, perfs: List[PerformanceData]) -> List[DiagnosisReport]:
        """批量诊断"""
        return [self.diagnose(p) for p in perfs]

    def generate_summary(self, reports: List[DiagnosisReport]) -> Dict:
        """生成诊断汇总"""
        if not reports:
            return {"total": 0, "summary": "无诊断数据"}

        severity_count = {"高": 0, "中": 0, "低": 0}
        dimension_count = {}

        for r in reports:
            severity_count[r.severity] += 1
            dim = r.problem_dimension
            dimension_count[dim] = dimension_count.get(dim, 0) + 1

        # 找出最常见问题
        top_problem = max(dimension_count.items(), key=lambda x: x[1]) if dimension_count else ("无", 0)

        summary = {
            "total": len(reports),
            "severity_distribution": severity_count,
            "dimension_distribution": dimension_count,
            "top_problem": top_problem[0],
            "top_problem_count": top_problem[1],
            "reports": [r.to_dict() for r in reports],
        }

        return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from datetime import datetime

    # 测试数据
    perf = PerformanceData(
        video_id="v001",
        video_title="机器人管家实测",
        publish_time=datetime.now(),
        views=50000,
        likes=3000,  # 点赞率6%
        shares=200,  # 分享率0.4%
        comments=100,  # 评论率0.2%
        follows=50,  # 涨粉率0.1%
        completions=20000,  # 完播率40%
        avg_watch_time=8.5,  # 平均观看8.5秒
    )

    agent = DataAgent()
    report = agent.diagnose(perf)
    print(f"诊断: {report.diagnosis}")
    print(f"问题维度: {report.problem_dimension}")
    print(f"严重程度: {report.severity}")
    print(f"建议:\n" + "\n".join(f"  - {s}" for s in report.suggestions))
