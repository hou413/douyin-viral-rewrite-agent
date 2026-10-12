"""
数据模型定义
所有Agent之间通信的数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from enum import Enum


class EmotionType(str, Enum):
    """情绪类型"""
    ANGER = "愤怒"
    ANXIETY = "焦虑"
    CURIOSITY = "好奇"
    RESONANCE = "共鸣"
    HUMOR = "搞笑"


class HookType(str, Enum):
    """钩子类型"""
    CONFLICT = "冲突型"
    SUSPENSE = "悬念型"
    BENEFIT = "利益型"


class TrendDirection(str, Enum):
    """趋势方向"""
    RISING = "上升"
    FALLING = "下降"
    STABLE = "稳定"


class ViralGrade(str, Enum):
    """爆款评级"""
    S = "S级（必爆）"
    A = "A级（高潜力）"
    B = "B级（中等）"
    C = "C级（需优化）"
    D = "D级（不建议）"


@dataclass
class HotTopic:
    """热点话题"""
    id: str
    title: str
    hot_value: int  # 热度值
    category: str  # 分类
    trend: TrendDirection  # 趋势
    source: str  # 来源
    discovered_at: datetime = field(default_factory=datetime.now)
    keywords: List[str] = field(default_factory=list)
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "hot_value": self.hot_value,
            "category": self.category,
            "trend": self.trend.value,
            "source": self.source,
            "discovered_at": self.discovered_at.isoformat(),
            "keywords": self.keywords,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "HotTopic":
        return cls(
            id=data["id"],
            title=data["title"],
            hot_value=data["hot_value"],
            category=data["category"],
            trend=TrendDirection(data["trend"]),
            source=data["source"],
            discovered_at=datetime.fromisoformat(data["discovered_at"]),
            keywords=data.get("keywords", []),
            description=data.get("description", "")
        )


@dataclass
class CandidateTopic:
    """候选选题"""
    id: str
    title: str
    source_hot_topic: HotTopic
    emotion: EmotionType  # 主要情绪
    conflict_point: str  # 冲突点
    viral_score: float  # 传播潜力评分 0-100
    target_audience: str  # 目标受众
    content_angle: str  # 内容角度
    reasoning: str  # 推荐理由
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "source_hot_topic": self.source_hot_topic.to_dict(),
            "emotion": self.emotion.value,
            "conflict_point": self.conflict_point,
            "viral_score": self.viral_score,
            "target_audience": self.target_audience,
            "content_angle": self.content_angle,
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "CandidateTopic":
        return cls(
            id=data["id"],
            title=data["title"],
            source_hot_topic=HotTopic.from_dict(data["source_hot_topic"]),
            emotion=EmotionType(data["emotion"]),
            conflict_point=data["conflict_point"],
            viral_score=data["viral_score"],
            target_audience=data["target_audience"],
            content_angle=data["content_angle"],
            reasoning=data["reasoning"],
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class ScriptOpening:
    """脚本开头方案"""
    hook_type: HookType
    content: str  # 开头文案
    reasoning: str  # 设计理由
    estimated_impact: str  # 预期效果


@dataclass
class Script:
    """完整脚本"""
    id: str
    topic: CandidateTopic
    title: str
    openings: List[ScriptOpening]  # 3种开头方案
    recommended_opening_idx: int  # 推荐开头索引
    pain_point_section: str  # 痛点展开
    twist_section: str  # 反转设计
    cta_section: str  # CTA行动号召
    full_script: str  # 完整脚本
    viral_mechanism: Dict  # 传播机制分析
    estimated_duration: int  # 预估时长（秒）
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "topic": self.topic.to_dict(),
            "title": self.title,
            "openings": [
                {
                    "hook_type": o.hook_type.value,
                    "content": o.content,
                    "reasoning": o.reasoning,
                    "estimated_impact": o.estimated_impact
                }
                for o in self.openings
            ],
            "recommended_opening_idx": self.recommended_opening_idx,
            "pain_point_section": self.pain_point_section,
            "twist_section": self.twist_section,
            "cta_section": self.cta_section,
            "full_script": self.full_script,
            "viral_mechanism": self.viral_mechanism,
            "estimated_duration": self.estimated_duration,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Script":
        openings = [
            ScriptOpening(
                hook_type=HookType(o["hook_type"]),
                content=o["content"],
                reasoning=o["reasoning"],
                estimated_impact=o["estimated_impact"]
            )
            for o in data["openings"]
        ]
        return cls(
            id=data["id"],
            topic=CandidateTopic.from_dict(data["topic"]),
            title=data["title"],
            openings=openings,
            recommended_opening_idx=data["recommended_opening_idx"],
            pain_point_section=data["pain_point_section"],
            twist_section=data["twist_section"],
            cta_section=data["cta_section"],
            full_script=data["full_script"],
            viral_mechanism=data["viral_mechanism"],
            estimated_duration=data["estimated_duration"],
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class VideoPlan:
    """视频制作方案"""
    id: str
    script: Script
    storyboard: List[Dict]  # 分镜脚本
    subtitle_style: Dict  # 字幕方案
    voice_direction: str  # 配音指导
    material_suggestions: List[str]  # 素材建议
    bgm_mood: str  # 背景音乐风格
    editing_notes: str  # 剪辑要点
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "script": self.script.to_dict(),
            "storyboard": self.storyboard,
            "subtitle_style": self.subtitle_style,
            "voice_direction": self.voice_direction,
            "material_suggestions": self.material_suggestions,
            "bgm_mood": self.bgm_mood,
            "editing_notes": self.editing_notes,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "VideoPlan":
        return cls(
            id=data["id"],
            script=Script.from_dict(data["script"]),
            storyboard=data["storyboard"],
            subtitle_style=data["subtitle_style"],
            voice_direction=data["voice_direction"],
            material_suggestions=data["material_suggestions"],
            bgm_mood=data["bgm_mood"],
            editing_notes=data["editing_notes"],
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class PerformanceData:
    """视频表现数据"""
    video_id: str
    video_title: str
    publish_time: datetime
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    follows: int = 0  # 涨粉数
    completions: int = 0  # 完播数
    avg_watch_time: float = 0.0  # 平均观看时长（秒）
    recorded_at: datetime = field(default_factory=datetime.now)
    
    @property
    def like_rate(self) -> float:
        """点赞率"""
        return self.likes / self.views if self.views > 0 else 0.0
    
    @property
    def share_rate(self) -> float:
        """分享率"""
        return self.shares / self.views if self.views > 0 else 0.0
    
    @property
    def comment_rate(self) -> float:
        """评论率"""
        return self.comments / self.views if self.views > 0 else 0.0
    
    @property
    def follow_rate(self) -> float:
        """涨粉率"""
        return self.follows / self.views if self.views > 0 else 0.0
    
    @property
    def completion_rate(self) -> float:
        """完播率"""
        return self.completions / self.views if self.views > 0 else 0.0
    
    def to_dict(self) -> Dict:
        return {
            "video_id": self.video_id,
            "video_title": self.video_title,
            "publish_time": self.publish_time.isoformat(),
            "views": self.views,
            "likes": self.likes,
            "shares": self.shares,
            "comments": self.comments,
            "follows": self.follows,
            "completions": self.completions,
            "avg_watch_time": self.avg_watch_time,
            "recorded_at": self.recorded_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PerformanceData":
        return cls(
            video_id=data["video_id"],
            video_title=data["video_title"],
            publish_time=datetime.fromisoformat(data["publish_time"]),
            views=data.get("views", 0),
            likes=data.get("likes", 0),
            shares=data.get("shares", 0),
            comments=data.get("comments", 0),
            follows=data.get("follows", 0),
            completions=data.get("completions", 0),
            avg_watch_time=data.get("avg_watch_time", 0.0),
            recorded_at=datetime.fromisoformat(data["recorded_at"])
        )


@dataclass
class DiagnosisReport:
    """诊断报告"""
    video_id: str
    performance: PerformanceData
    diagnosis: str  # 诊断结论
    problem_dimension: str  # 问题维度
    severity: Literal["高", "中", "低"]  # 严重程度
    suggestions: List[str]  # 优化建议
    benchmark_comparison: Dict  # 与基线对比
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "video_id": self.video_id,
            "performance": self.performance.to_dict(),
            "diagnosis": self.diagnosis,
            "problem_dimension": self.problem_dimension,
            "severity": self.severity,
            "suggestions": self.suggestions,
            "benchmark_comparison": self.benchmark_comparison,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DiagnosisReport":
        return cls(
            video_id=data["video_id"],
            performance=PerformanceData.from_dict(data["performance"]),
            diagnosis=data["diagnosis"],
            problem_dimension=data["problem_dimension"],
            severity=data["severity"],
            suggestions=data["suggestions"],
            benchmark_comparison=data["benchmark_comparison"],
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class ViralScoreDimension:
    """爆款评分维度"""
    name: str
    weight: float  # 权重
    score: int  # 分数 1-10
    reasoning: str  # 评分理由
    improvement_suggestions: List[str]  # 改进建议


@dataclass
class ViralScore:
    """爆款潜力评分"""
    content_id: str
    content_type: Literal["topic", "script", "video_plan"]
    dimensions: List[ViralScoreDimension]
    total_score: float  # 总分 0-100
    grade: ViralGrade  # 评级
    summary: str  # 总结
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "content_id": self.content_id,
            "content_type": self.content_type,
            "dimensions": [
                {
                    "name": d.name,
                    "weight": d.weight,
                    "score": d.score,
                    "reasoning": d.reasoning,
                    "improvement_suggestions": d.improvement_suggestions
                }
                for d in self.dimensions
            ],
            "total_score": self.total_score,
            "grade": self.grade.value,
            "summary": self.summary,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ViralScore":
        dimensions = [
            ViralScoreDimension(
                name=d["name"],
                weight=d["weight"],
                score=d["score"],
                reasoning=d["reasoning"],
                improvement_suggestions=d["improvement_suggestions"]
            )
            for d in data["dimensions"]
        ]
        return cls(
            content_id=data["content_id"],
            content_type=data["content_type"],
            dimensions=dimensions,
            total_score=data["total_score"],
            grade=ViralGrade(data["grade"]),
            summary=data["summary"],
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class ExperimentRecord:
    """实验记录"""
    id: str
    experiment_name: str
    hypothesis: str  # 假设
    test_variable: str  # 测试变量
    variant_a: Dict  # 方案A
    variant_b: Dict  # 方案B
    metric: str  # 评估指标
    result: Optional[Dict] = None  # 实验结果
    conclusion: Optional[str] = None  # 结论
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "experiment_name": self.experiment_name,
            "hypothesis": self.hypothesis,
            "test_variable": self.test_variable,
            "variant_a": self.variant_a,
            "variant_b": self.variant_b,
            "metric": self.metric,
            "result": self.result,
            "conclusion": self.conclusion,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ExperimentRecord":
        return cls(
            id=data["id"],
            experiment_name=data["experiment_name"],
            hypothesis=data["hypothesis"],
            test_variable=data["test_variable"],
            variant_a=data["variant_a"],
            variant_b=data["variant_b"],
            metric=data["metric"],
            result=data.get("result"),
            conclusion=data.get("conclusion"),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )


@dataclass
class AccountProfile:
    """账号画像"""
    account_name: str
    niche: str  # 领域
    target_audience: str  # 目标受众
    content_style: str  # 内容风格
    brand_voice: str  # 品牌调性
    conversion_goal: str  # 转化目标
    competitors: List[str] = field(default_factory=list)  # 竞品账号
    baseline_metrics: Dict = field(default_factory=dict)  # 基线指标
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "account_name": self.account_name,
            "niche": self.niche,
            "target_audience": self.target_audience,
            "content_style": self.content_style,
            "brand_voice": self.brand_voice,
            "conversion_goal": self.conversion_goal,
            "competitors": self.competitors,
            "baseline_metrics": self.baseline_metrics,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AccountProfile":
        return cls(
            account_name=data["account_name"],
            niche=data["niche"],
            target_audience=data["target_audience"],
            content_style=data["content_style"],
            brand_voice=data["brand_voice"],
            conversion_goal=data["conversion_goal"],
            competitors=data.get("competitors", []),
            baseline_metrics=data.get("baseline_metrics", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


@dataclass
class KnowledgeEntry:
    """知识库条目"""
    id: str
    entry_type: Literal["case", "template", "pattern", "experiment"]
    title: str
    content: Dict  # 具体内容
    tags: List[str] = field(default_factory=list)
    success_rate: Optional[float] = None  # 成功率
    usage_count: int = 0  # 使用次数
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "entry_type": self.entry_type,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "KnowledgeEntry":
        return cls(
            id=data["id"],
            entry_type=data["entry_type"],
            title=data["title"],
            content=data["content"],
            tags=data.get("tags", []),
            success_rate=data.get("success_rate"),
            usage_count=data.get("usage_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


if __name__ == "__main__":
    # 示例：创建数据模型
    print("=== 数据模型示例 ===\n")
    
    # 创建热点话题
    hot_topic = HotTopic(
        id="hot_001",
        title="人形机器人进入家庭",
        hot_value=9500000,
        category="科技",
        trend=TrendDirection.RISING,
        source="抖音热榜",
        keywords=["机器人", "AI", "智能家居"],
        description="人形机器人开始进入普通家庭，改变生活方式"
    )
    print(f"热点话题: {hot_topic.title}")
    print(f"热度: {hot_topic.hot_value}, 趋势: {hot_topic.trend.value}\n")
    
    # 创建候选选题
    candidate = CandidateTopic(
        id="topic_001",
        title="机器人管家真的能替代保姆吗？",
        source_hot_topic=hot_topic,
        emotion=EmotionType.CURIOSITY,
        conflict_point="技术理想vs现实局限",
        viral_score=85.5,
        target_audience="科技爱好者、家庭主妇",
        content_angle="实测体验+深度分析",
        reasoning="结合热点，有冲突点，能引发好奇和讨论"
    )
    print(f"候选选题: {candidate.title}")
    print(f"情绪: {candidate.emotion.value}, 评分: {candidate.viral_score}\n")
    
    # 创建表现数据
    perf = PerformanceData(
        video_id="video_001",
        video_title="机器人管家实测",
        publish_time=datetime.now(),
        views=100000,
        likes=8000,
        shares=1200,
        comments=500,
        follows=300,
        completions=45000
    )
    print(f"视频表现:")
    print(f"播放: {perf.views}, 点赞率: {perf.like_rate:.2%}")
    print(f"分享率: {perf.share_rate:.2%}, 完播率: {perf.completion_rate:.2%}\n")
    
    print("✅ 数据模型测试通过")
