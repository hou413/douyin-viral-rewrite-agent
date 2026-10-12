"""
爆款选题Agent
负责：从热点中提取选题、情绪分析、冲突点识别、传播潜力评分
输出：候选选题列表+评分
"""

import json
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from src.core.models import (
    HotTopic, CandidateTopic, EmotionType, TrendDirection, AccountProfile
)

logger = logging.getLogger(__name__)


class TopicAgent:
    """爆款选题Agent"""

    def __init__(self, ai_call_func=None, account: Optional[AccountProfile] = None):
        self._call_ai = ai_call_func
        self.account = account

    def generate_topics(
        self,
        hot_topics: List[HotTopic],
        max_topics: int = 20
    ) -> List[CandidateTopic]:
        """从热点生成候选选题"""
        logger.info(f"从 {len(hot_topics)} 条热点生成选题...")
        candidates = []

        for topic in hot_topics[:max_topics]:
            try:
                candidate = self._topic_from_hot(topic)
                if candidate:
                    candidates.append(candidate)
            except Exception as e:
                logger.warning(f"生成选题失败 [{topic.title}]: {e}")

        # 按传播潜力排序
        candidates.sort(key=lambda c: c.viral_score, reverse=True)
        logger.info(f"生成 {len(candidates)} 个候选选题")
        return candidates

    def _topic_from_hot(self, hot: HotTopic) -> Optional[CandidateTopic]:
        """从单条热点生成选题"""
        if self._call_ai:
            return self._ai_generate_topic(hot)
        return self._rule_generate_topic(hot)

    def _ai_generate_topic(self, hot: HotTopic) -> Optional[CandidateTopic]:
        """用AI生成选题"""
        prompt = f"""分析以下抖音热搜话题，生成一个爆款选题方案。

热搜话题: {hot.title}
热度值: {hot.hot_value}
趋势: {hot.trend.value}
分类: {hot.category}

请严格按JSON格式返回：
{{
    "title": "<选题标题，要有吸引力>",
    "emotion": "<愤怒|焦虑|好奇|共鸣|搞笑>",
    "conflict_point": "<核心冲突点，如'技术理想vs现实局限'>",
    "viral_score": <0-100的评分>,
    "target_audience": "<目标受众描述>",
    "content_angle": "<内容切入角度>",
    "reasoning": "<为什么这个选题有爆款潜力>"
}}"""
        try:
            resp = self._call_ai(prompt, "你是抖音爆款选题策划专家。")
            data = json.loads(resp.strip())
            return CandidateTopic(
                id=str(uuid.uuid4())[:8],
                title=data["title"],
                source_hot_topic=hot,
                emotion=EmotionType(data["emotion"]),
                conflict_point=data["conflict_point"],
                viral_score=float(data["viral_score"]),
                target_audience=data["target_audience"],
                content_angle=data["content_angle"],
                reasoning=data["reasoning"],
            )
        except Exception as e:
            logger.warning(f"AI选题失败，降级为规则: {e}")
            return self._rule_generate_topic(hot)

    def _rule_generate_topic(self, hot: HotTopic) -> Optional[CandidateTopic]:
        """规则生成选题"""
        title = hot.title
        emotion = self._infer_emotion(title)
        conflict = self._infer_conflict(title)
        score = self._calc_viral_score(hot, emotion, conflict)

        return CandidateTopic(
            id=str(uuid.uuid4())[:8],
            title=f"{title}——你不知道的真相",
            source_hot_topic=hot,
            emotion=emotion,
            conflict_point=conflict,
            viral_score=score,
            target_audience=self.account.target_audience if self.account else "泛科技人群",
            content_angle="深度解读+实用建议",
            reasoning=f"热度{hot.hot_value}，{emotion.value}情绪驱动，{conflict}",
        )

    def _infer_emotion(self, title: str) -> EmotionType:
        """推断情绪类型"""
        emotion_keywords = {
            EmotionType.ANGER: ["不公", "黑幕", "骗局", "坑", "割韭菜", "太过分"],
            EmotionType.ANXIETY: ["淘汰", "失业", "危机", "焦虑", "来不及", "完了"],
            EmotionType.CURIOSITY: ["为什么", "真相", "秘密", "竟然", "没想到", "真相"],
            EmotionType.RESONANCE: ["终于", "说出了", "心声", "终于有人", "太真实"],
            EmotionType.HUMOR: ["笑死", "离谱", "绝了", "神操作", "整活"],
        }
        for emo, kws in emotion_keywords.items():
            if any(kw in title for kw in kws):
                return emo
        return EmotionType.CURIOSITY

    def _infer_conflict(self, title: str) -> str:
        """推断冲突点"""
        if "vs" in title or "对比" in title:
            return "正反对比冲突"
        if "真相" in title or "误解" in title:
            return "认知反差：你以为的vs真实的"
        if "为什么" in title:
            return "反直觉：常识被打破"
        return "期待vs现实的落差"

    def _calc_viral_score(self, hot: HotTopic, emotion: EmotionType, conflict: str) -> float:
        """计算传播潜力评分"""
        base = 50.0
        # 热度加成
        if hot.hot_value >= 10000000:
            base += 20
        elif hot.hot_value >= 5000000:
            base += 15
        elif hot.hot_value >= 1000000:
            base += 10
        # 趋势加成
        if hot.trend == TrendDirection.RISING:
            base += 10
        # 情绪加成
        emotion_bonus = {EmotionType.RESONANCE: 10, EmotionType.CURIOSITY: 8, EmotionType.ANGER: 7, EmotionType.ANXIETY: 6, EmotionType.HUMOR: 5}
        base += emotion_bonus.get(emotion, 5)
        # 冲突加成
        if "反差" in conflict or "认知" in conflict:
            base += 5
        return min(base, 100)

    def filter_top_topics(
        self,
        candidates: List[CandidateTopic],
        top_n: int = 5,
        min_score: float = 60
    ) -> List[CandidateTopic]:
        """筛选高分选题"""
        filtered = [c for c in candidates if c.viral_score >= min_score]
        return filtered[:top_n]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.core.models import HotTopic, TrendDirection
    hot = HotTopic(
        id="test_001", title="人形机器人进入家庭", hot_value=9500000,
        category="科技", trend=TrendDirection.RISING, source="抖音热榜"
    )
    agent = TopicAgent()
    topics = agent.generate_topics([hot])
    for t in topics:
        print(f"[{t.viral_score:.0f}分] {t.title} | {t.emotion.value} | {t.conflict_point}")
