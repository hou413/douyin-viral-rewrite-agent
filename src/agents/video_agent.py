"""
视频制作Agent
负责：分镜脚本、字幕方案、配音指导、素材建议
输出：可执行的视频制作方案
"""

import json
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from src.core.models import Script, VideoPlan

logger = logging.getLogger(__name__)


class VideoAgent:
    """视频制作Agent"""

    def __init__(self, ai_call_func=None):
        self._call_ai = ai_call_func

    def create_video_plans(self, scripts: List[Script]) -> List[VideoPlan]:
        """为脚本生成制作方案"""
        logger.info(f"为 {len(scripts)} 个脚本生成制作方案...")
        plans = []
        for script in scripts:
            try:
                plan = self._create_plan(script)
                if plan:
                    plans.append(plan)
            except Exception as e:
                logger.warning(f"生成制作方案失败 [{script.title}]: {e}")
        logger.info(f"生成 {len(plans)} 个制作方案")
        return plans

    def _create_plan(self, script: Script) -> Optional[VideoPlan]:
        if self._call_ai:
            return self._ai_create_plan(script)
        return self._rule_create_plan(script)

    def _ai_create_plan(self, script: Script) -> Optional[VideoPlan]:
        prompt = f"""为以下脚本生成视频制作方案。

脚本标题: {script.title}
预估时长: {script.estimated_duration}秒
完整脚本:
{script.full_script}

请严格按JSON格式返回：
{{
    "storyboard": [
        {{"time": "0-3s", "scene": "<画面描述>", "text_overlay": "<文字覆盖>", "note": "<拍摄要点>"}},
        {{"time": "3-10s", "scene": "<画面描述>", "text_overlay": "<文字覆盖>", "note": "<拍摄要点>"}},
        {{"time": "10-25s", "scene": "<画面描述>", "text_overlay": "<文字覆盖>", "note": "<拍摄要点>"}},
        {{"time": "25-40s", "scene": "<画面描述>", "text_overlay": "<文字覆盖>", "note": "<拍摄要点>"}},
        {{"time": "40-45s", "scene": "<画面描述>", "text_overlay": "<文字覆盖>", "note": "<拍摄要点>"}}
    ],
    "subtitle_style": {{"font": "<字体>", "color": "<颜色>", "position": "<位置>", "animation": "<动效>"}},
    "voice_direction": "<配音风格指导>",
    "material_suggestions": ["<素材建议1>", "<素材建议2>", "<素材建议3>"],
    "bgm_mood": "<背景音乐风格>",
    "editing_notes": "<剪辑要点>"
}}"""
        try:
            resp = self._call_ai(prompt, "你是短视频制作总监，擅长分镜设计和视觉表达。")
            data = json.loads(resp.strip())
            return VideoPlan(
                id=str(uuid.uuid4())[:8],
                script=script,
                storyboard=data["storyboard"],
                subtitle_style=data["subtitle_style"],
                voice_direction=data["voice_direction"],
                material_suggestions=data["material_suggestions"],
                bgm_mood=data["bgm_mood"],
                editing_notes=data["editing_notes"],
            )
        except Exception as e:
            logger.warning(f"AI制作方案失败，降级: {e}")
            return self._rule_create_plan(script)

    def _rule_create_plan(self, script: Script) -> Optional[VideoPlan]:
        duration = script.estimated_duration
        # 根据脚本结构自动生成分镜
        storyboard = [
            {"time": "0-3s", "scene": "开场hook，面对镜头直接说", "text_overlay": script.openings[script.recommended_opening_idx].content[:20], "note": "表情要有张力，语速快"},
            {"time": "3-10s", "scene": "痛点场景展示", "text_overlay": "你是不是也遇到过...", "note": "用真实场景或动画演示"},
            {"time": "10-25s", "scene": "核心内容展开，配合图文卡片", "text_overlay": "关键数据/观点", "note": "信息密度要高，节奏紧凑"},
            {"time": "25-35s", "scene": "反转/高潮部分", "text_overlay": "真相是...", "note": "语气变化，制造惊喜感"},
            {"time": f"35-{duration}s", "scene": "CTA，引导互动", "text_overlay": "评论区告诉我", "note": "真诚、有感染力"},
        ]

        return VideoPlan(
            id=str(uuid.uuid4())[:8],
            script=script,
            storyboard=storyboard,
            subtitle_style={"font": "思源黑体", "color": "#FFFFFF", "position": "底部居中", "animation": "逐字出现"},
            voice_direction="语速中偏快，有节奏感，关键处加重语气，整体自信有力",
            material_suggestions=["产品实拍/演示画面", "数据图表动画", "用户反馈截图", "场景化B-roll"],
            bgm_mood="轻快科技感，节奏感强，不抢人声",
            editing_notes="每2-3秒切一次画面，保持视觉新鲜感；关键信息用放大/高亮强调",
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.core.models import HotTopic, CandidateTopic, EmotionType, TrendDirection, Script, ScriptOpening, HookType
    hot = HotTopic(id="h1", title="机器人进入家庭", hot_value=9000000, category="科技", trend=TrendDirection.RISING, source="热榜")
    topic = CandidateTopic(id="t1", title="机器人管家能替代保姆吗", source_hot_topic=hot, emotion=EmotionType.CURIOSITY, conflict_point="理想vs现实", viral_score=85, target_audience="科技爱好者", content_angle="实测", reasoning="好奇驱动")
    opening = ScriptOpening(hook_type=HookType.CONFLICT, content="你以为机器人还在实验室？错了。", reasoning="反常识", estimated_impact="留存+40%")
    script = Script(id="s1", topic=topic, title="机器人管家实测", openings=[opening], recommended_opening_idx=0, pain_point_section="", twist_section="", cta_section="", full_script="测试脚本", viral_mechanism={}, estimated_duration=45)
    agent = VideoAgent()
    plans = agent.create_video_plans([script])
    for p in plans:
        print(f"制作方案: {p.script.title}")
        for s in p.storyboard:
            print(f"  {s['time']}: {s['scene']}")
