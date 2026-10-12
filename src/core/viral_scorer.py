"""
爆款潜力评估器
6维度评分：开头吸引力、情绪共鸣、认知反差、内容价值、传播动机、账号匹配度
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.core.models import (
    ViralScore, ViralScoreDimension, ViralGrade,
    CandidateTopic, Script, VideoPlan, AccountProfile
)

logger = logging.getLogger(__name__)


# 默认权重配置
DEFAULT_WEIGHTS = {
    "开头吸引力": 0.25,
    "情绪共鸣": 0.20,
    "认知反差": 0.20,
    "内容价值": 0.15,
    "传播动机": 0.10,
    "账号匹配度": 0.10
}


class ViralScorer:
    """爆款潜力评估器"""
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        ai_call_func=None
    ):
        """
        初始化评估器
        
        Args:
            weights: 自定义权重，key为维度名，value为权重（总和需为1.0）
            ai_call_func: AI调用函数，签名为 func(prompt, system_prompt) -> str
        """
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self._validate_weights()
        self._call_ai = ai_call_func
    
    def _validate_weights(self):
        """验证权重总和"""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"权重总和为 {total}，将自动归一化")
            self.weights = {k: v / total for k, v in self.weights.items()}
    
    def score_topic(
        self,
        topic: CandidateTopic,
        account: Optional[AccountProfile] = None
    ) -> ViralScore:
        """评估选题的爆款潜力"""
        dimensions = []
        
        for dim_name, weight in self.weights.items():
            score, reasoning, suggestions = self._score_dimension(
                dim_name, topic=topic, account=account
            )
            dimensions.append(ViralScoreDimension(
                name=dim_name,
                weight=weight,
                score=score,
                reasoning=reasoning,
                improvement_suggestions=suggestions
            ))
        
        total = sum(d.score * d.weight * 10 for d in dimensions)
        grade = self._to_grade(total)
        summary = self._generate_summary(dimensions, total, grade)
        
        return ViralScore(
            content_id=topic.id,
            content_type="topic",
            dimensions=dimensions,
            total_score=round(total, 1),
            grade=grade,
            summary=summary
        )
    
    def score_script(
        self,
        script: Script,
        account: Optional[AccountProfile] = None
    ) -> ViralScore:
        """评估脚本的爆款潜力"""
        dimensions = []
        
        for dim_name, weight in self.weights.items():
            score, reasoning, suggestions = self._score_dimension(
                dim_name, script=script, account=account
            )
            dimensions.append(ViralScoreDimension(
                name=dim_name,
                weight=weight,
                score=score,
                reasoning=reasoning,
                improvement_suggestions=suggestions
            ))
        
        total = sum(d.score * d.weight * 10 for d in dimensions)
        grade = self._to_grade(total)
        summary = self._generate_summary(dimensions, total, grade)
        
        return ViralScore(
            content_id=script.id,
            content_type="script",
            dimensions=dimensions,
            total_score=round(total, 1),
            grade=grade,
            summary=summary
        )
    
    def _score_dimension(
        self,
        dim_name: str,
        topic: Optional[CandidateTopic] = None,
        script: Optional[Script] = None,
        account: Optional[AccountProfile] = None
    ) -> tuple:
        """
        评估单个维度
        返回: (score, reasoning, suggestions)
        """
        # 如果有AI，优先使用AI评估
        if self._call_ai:
            return self._ai_score_dimension(dim_name, topic, script, account)
        
        # 否则使用规则评估
        return self._rule_score_dimension(dim_name, topic, script, account)
    
    def _ai_score_dimension(
        self,
        dim_name: str,
        topic: Optional[CandidateTopic],
        script: Optional[Script],
        account: Optional[AccountProfile]
    ) -> tuple:
        """使用AI评估维度"""
        context_parts = []
        if topic:
            context_parts.append(f"选题: {topic.title}")
            context_parts.append(f"情绪: {topic.emotion.value}")
            context_parts.append(f"冲突点: {topic.conflict_point}")
        if script:
            context_parts.append(f"脚本标题: {script.title}")
            context_parts.append(f"推荐开头: {script.openings[script.recommended_opening_idx].content}")
            context_parts.append(f"完整脚本摘要: {script.full_script[:300]}...")
        if account:
            context_parts.append(f"账号定位: {account.niche}")
            context_parts.append(f"目标受众: {account.target_audience}")
        
        context = "\n".join(context_parts)
        
        prompt = f"""请评估以下内容的「{dim_name}」维度。

评估维度说明：
{self._get_dimension_description(dim_name)}

内容信息：
{context}

请严格按以下JSON格式返回（不要包含其他内容）：
{{
    "score": <1-10的整数>,
    "reasoning": "<评分理由，50字以内>",
    "suggestions": ["<改进建议1>", "<改进建议2>"]
}}"""
        
        try:
            response = self._call_ai(
                prompt,
                system_prompt="你是抖音爆款内容评估专家。请严格按JSON格式返回评估结果。"
            )
            # 解析JSON
            result = json.loads(response.strip())
            return (
                int(result["score"]),
                result["reasoning"],
                result["suggestions"]
            )
        except Exception as e:
            logger.warning(f"AI评估失败，降级为规则评估: {e}")
            return self._rule_score_dimension(dim_name, topic, script, account)
    
    def _rule_score_dimension(
        self,
        dim_name: str,
        topic: Optional[CandidateTopic],
        script: Optional[Script],
        account: Optional[AccountProfile]
    ) -> tuple:
        """基于规则的评估"""
        score = 5  # 默认中等
        reasoning = ""
        suggestions = []
        
        if dim_name == "开头吸引力":
            if script:
                opening = script.openings[script.recommended_opening_idx]
                if opening.hook_type.value == "冲突型":
                    score = 8
                    reasoning = "冲突型开头能有效抓住注意力"
                elif opening.hook_type.value == "悬念型":
                    score = 7
                    reasoning = "悬念型开头有吸引力但需配合后续"
                else:
                    score = 6
                    reasoning = "利益型开头直接但缺乏惊喜"
                suggestions.append("可尝试多种开头A/B测试")
            elif topic:
                score = 6
                reasoning = "选题阶段，开头设计待确定"
                suggestions.append("建议设计冲突型开头")
        
        elif dim_name == "情绪共鸣":
            if topic:
                emotion_scores = {
                    "愤怒": 7, "焦虑": 7, "好奇": 8, "共鸣": 9, "搞笑": 7
                }
                score = emotion_scores.get(topic.emotion.value, 6)
                reasoning = f"{topic.emotion.value}情绪在抖音有较强传播力"
                suggestions.append("可叠加多种情绪增强效果")
            else:
                score = 5
                reasoning = "待确定情绪方向"
        
        elif dim_name == "认知反差":
            if topic:
                if "误解" in topic.conflict_point or "真相" in topic.conflict_point:
                    score = 9
                    reasoning = "认知反差强烈，能打破常识"
                elif "vs" in topic.conflict_point:
                    score = 7
                    reasoning = "有对比冲突"
                else:
                    score = 5
                    reasoning = "冲突点不够尖锐"
                suggestions.append("强化'你以为...其实...'的反差结构")
            else:
                score = 5
                reasoning = "待评估"
        
        elif dim_name == "内容价值":
            score = 7
            reasoning = "提供实用信息或洞察"
            suggestions.append("确保观众看完能学到至少一个知识点")
        
        elif dim_name == "传播动机":
            if topic:
                if "社交货币" in topic.reasoning or "谈资" in topic.reasoning:
                    score = 8
                    reasoning = "提供社交货币，用户愿意分享"
                else:
                    score = 6
                    reasoning = "有一定传播动机但不够强"
                suggestions.append("增加'分享后显得有见识'的元素")
            else:
                score = 5
                reasoning = "待评估"
        
        elif dim_name == "账号匹配度":
            if account and topic:
                # 简单关键词匹配
                niche_keywords = account.niche.lower()
                topic_text = (topic.title + topic.content_angle).lower()
                if any(kw in topic_text for kw in niche_keywords.split("/")):
                    score = 9
                    reasoning = f"与账号定位'{account.niche}'高度匹配"
                else:
                    score = 5
                    reasoning = f"与账号定位'{account.niche}'匹配度一般"
                suggestions.append("确保内容与账号定位一致")
            else:
                score = 5
                reasoning = "缺少账号信息"
        
        return (score, reasoning, suggestions)
    
    def _get_dimension_description(self, dim_name: str) -> str:
        """获取维度说明"""
        descriptions = {
            "开头吸引力": "评估前3秒能否抓住用户注意力。冲突型、悬念型、利益型哪种更有效？是否有足够的'停不下来'的吸引力？",
            "情绪共鸣": "评估内容能否引发强烈情绪。愤怒、焦虑、好奇、共鸣、搞笑，哪种情绪最突出？情绪强度如何？",
            "认知反差": "评估内容是否打破常识、制造认知冲突。是否有'原来如此'的顿悟感？反差是否足够大？",
            "内容价值": "评估用户能否获得实用信息或洞察。看完是否有收获感？信息密度如何？",
            "传播动机": "评估用户分享的理由。是社交货币（分享后显得有见识）？是利他（对朋友有用）？是表达（代表我的态度）？",
            "账号匹配度": "评估内容与账号定位、目标受众的契合度。是否符合账号调性？受众是否感兴趣？"
        }
        return descriptions.get(dim_name, "请评估该维度")
    
    def _to_grade(self, score: float) -> ViralGrade:
        """分数转评级"""
        if score >= 90:
            return ViralGrade.S
        elif score >= 80:
            return ViralGrade.A
        elif score >= 70:
            return ViralGrade.B
        elif score >= 60:
            return ViralGrade.C
        else:
            return ViralGrade.D
    
    def _generate_summary(
        self,
        dimensions: List[ViralScoreDimension],
        total: float,
        grade: ViralGrade
    ) -> str:
        """生成评估总结"""
        # 找到最强和最弱维度
        strongest = max(dimensions, key=lambda d: d.score)
        weakest = min(dimensions, key=lambda d: d.score)
        
        summary = (
            f"总评{grade.value}（{total:.1f}分）。"
            f"最强维度：{strongest.name}（{strongest.score}分），"
            f"最弱维度：{weakest.name}（{weakest.score}分）。"
        )
        
        if grade in (ViralGrade.S, ViralGrade.A):
            summary += "建议立即执行。"
        elif grade == ViralGrade.B:
            summary += f"建议优化{weakest.name}后执行。"
        else:
            summary += f"建议大幅优化{weakest.name}和{strongest.name}。"
        
        return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== 爆款评估器测试 ===\n")
    
    from src.core.models import (
        HotTopic, CandidateTopic, EmotionType, TrendDirection,
        Script, ScriptOpening, HookType, AccountProfile
    )
    
    # 创建测试数据
    hot_topic = HotTopic(
        id="hot_001",
        title="人形机器人进入家庭",
        hot_value=9500000,
        category="科技",
        trend=TrendDirection.RISING,
        source="抖音热榜"
    )
    
    topic = CandidateTopic(
        id="topic_001",
        title="机器人管家真的能替代保姆吗？",
        source_hot_topic=hot_topic,
        emotion=EmotionType.CURIOSITY,
        conflict_point="技术理想vs现实局限",
        viral_score=85.5,
        target_audience="科技爱好者",
        content_angle="实测体验",
        reasoning="提供社交货币和谈资"
    )
    
    # 评估选题（规则模式）
    scorer = ViralScorer()
    result = scorer.score_topic(topic)
    
    print(f"选题评估: {topic.title}")
    print(f"总分: {result.total_score} - {result.grade.value}")
    print(f"总结: {result.summary}")
    print("\n各维度得分:")
    for d in result.dimensions:
        print(f"  {d.name}: {d.score}/10 (权重{d.weight:.0%}) - {d.reasoning}")
    
    print("\n✅ 爆款评估器测试通过")
