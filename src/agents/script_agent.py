"""
脚本导演Agent
负责：黄金开头设计、节奏设计、传播机制提取
输出：完整脚本+3种开头方案
核心理念：不模仿表面形式，而是提取传播机制
"""

import json
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from src.core.models import (
    CandidateTopic, Script, ScriptOpening, HookType, EmotionType, AccountProfile
)

logger = logging.getLogger(__name__)


class ScriptAgent:
    """脚本导演Agent"""

    def __init__(self, ai_call_func=None, account: Optional[AccountProfile] = None):
        self._call_ai = ai_call_func
        self.account = account

    def create_scripts(
        self,
        topics: List[CandidateTopic],
        style: str = "口播"
    ) -> List[Script]:
        """为每个选题创建脚本"""
        logger.info(f"为 {len(topics)} 个选题创建脚本...")
        scripts = []
        for topic in topics:
            try:
                script = self._create_script(topic, style)
                if script:
                    scripts.append(script)
            except Exception as e:
                logger.warning(f"创建脚本失败 [{topic.title}]: {e}")
        logger.info(f"创建 {len(scripts)} 个脚本")
        return scripts

    def _create_script(self, topic: CandidateTopic, style: str) -> Optional[Script]:
        """创建单个脚本"""
        if self._call_ai:
            return self._ai_create_script(topic, style)
        return self._rule_create_script(topic, style)

    def _ai_create_script(self, topic: CandidateTopic, style: str) -> Optional[Script]:
        """用AI创建脚本"""
        prompt = f"""为以下选题创作抖音短视频脚本。

选题: {topic.title}
情绪: {topic.emotion.value}
冲突点: {topic.conflict_point}
目标受众: {topic.target_audience}
内容角度: {topic.content_angle}
风格: {style}

请严格按JSON格式返回：
{{
    "title": "<视频标题>",
    "openings": [
        {{"type": "冲突型", "content": "<开头文案，3秒内抓住注意力>", "reasoning": "<设计理由>", "impact": "<预期效果>"}},
        {{"type": "悬念型", "content": "<开头文案>", "reasoning": "<设计理由>", "impact": "<预期效果>"}},
        {{"type": "利益型", "content": "<开头文案>", "reasoning": "<设计理由>", "impact": "<预期效果>"}}
    ],
    "recommended_opening": 0,
    "pain_point": "<痛点展开段落>",
    "twist": "<反转设计段落>",
    "cta": "<CTA行动号召>",
    "full_script": "<完整脚本>",
    "viral_mechanism": {{
        "target_group": "<目标人群>",
        "emotion_trigger": "<情绪触发点>",
        "cognitive_conflict": "<认知冲突>",
        "content_promise": "<内容承诺>",
        "share_motivation": "<传播动机>"
    }},
    "duration": <预估时长秒数>
}}"""
        try:
            resp = self._call_ai(prompt, "你是抖音爆款脚本导演，擅长设计黄金开头和传播机制。")
            data = json.loads(resp.strip())
            openings = [
                ScriptOpening(
                    hook_type=HookType(o["type"].replace("冲突型", "冲突").replace("悬念型", "悬念").replace("利益型", "利益")
                                     if "型" in o["type"] else o["type"]),
                    content=o["content"],
                    reasoning=o["reasoning"],
                    estimated_impact=o["impact"],
                )
                for o in data["openings"]
            ]
            return Script(
                id=str(uuid.uuid4())[:8],
                topic=topic,
                title=data["title"],
                openings=openings,
                recommended_opening_idx=data.get("recommended_opening", 0),
                pain_point_section=data["pain_point"],
                twist_section=data["twist"],
                cta_section=data["cta"],
                full_script=data["full_script"],
                viral_mechanism=data["viral_mechanism"],
                estimated_duration=data.get("duration", 45),
            )
        except Exception as e:
            logger.warning(f"AI创建脚本失败，降级: {e}")
            return self._rule_create_script(topic, style)

    def _rule_create_script(self, topic: CandidateTopic, style: str) -> Optional[Script]:
        """规则创建脚本（模板化）"""
        title = topic.title
        emotion = topic.emotion
        conflict = topic.conflict_point

        # 3种开头
        openings = [
            ScriptOpening(
                hook_type=HookType.CONFLICT,
                content=f"你以为{conflict.split('vs')[0].strip() if 'vs' in conflict else '事情是这样的'}？大错特错。",
                reasoning="用反常识打破认知，3秒内制造悬念",
                estimated_impact="前3秒留存率提升40%",
            ),
            ScriptOpening(
                hook_type=HookType.SUSPENSE,
                content=f"关于{title.split('——')[0] if '——' in title else title}，90%的人都不知道这个真相。",
                reasoning="用数据和悬念激发好奇心",
                estimated_impact="完播率提升25%",
            ),
            ScriptOpening(
                hook_type=HookType.BENEFIT,
                content=f"看完这条视频，你能省下至少30%的试错成本。",
                reasoning="直接给出利益承诺",
                estimated_impact="收藏率提升35%",
            ),
        ]

        # 传播机制提取
        viral_mechanism = {
            "target_group": topic.target_audience,
            "emotion_trigger": f"{emotion.value}情绪引发共鸣",
            "cognitive_conflict": conflict,
            "content_promise": f"揭示{title}的真相",
            "share_motivation": "提供社交货币，分享后显得有见识",
        }

        full_script = f"""【开头：{openings[0].content}】

【痛点展开】
你是不是也遇到过这种情况？
{topic.content_angle}

很多人以为事情很简单，但其实...

【反转】
真相是：{conflict}

这背后的原因是——
第一，大多数人只看到表面现象
第二，真正的方法其实很简单
第三，关键在于执行

【CTA】
如果你也有同样的困惑，评论区告诉我。
关注我，下期告诉你具体怎么做。"""

        return Script(
            id=str(uuid.uuid4())[:8],
            topic=topic,
            title=title,
            openings=openings,
            recommended_opening_idx=0,
            pain_point_section="痛点展开：描述目标用户的真实困境",
            twist_section=f"反转：{conflict}",
            cta_section="评论区互动 + 关注引导",
            full_script=full_script,
            viral_mechanism=viral_mechanism,
            estimated_duration=45,
        )

    def extract_viral_mechanism(self, script: Script) -> Dict:
        """提取传播机制（不是表面模仿）"""
        return script.viral_mechanism


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.core.models import HotTopic, TrendDirection
    hot = HotTopic(
        id="test_001", title="人形机器人进入家庭", hot_value=9500000,
        category="科技", trend=TrendDirection.RISING, source="抖音热榜"
    )
    from src.agents.topic_agent import TopicAgent
    topic_agent = TopicAgent()
    topics = topic_agent.generate_topics([hot])
    if topics:
        agent = ScriptAgent()
        scripts = agent.create_scripts(topics[:1])
        for s in scripts:
            print(f"脚本: {s.title}")
            print(f"传播机制: {json.dumps(s.viral_mechanism, ensure_ascii=False, indent=2)}")
            print(f"\n完整脚本:\n{s.full_script}")
