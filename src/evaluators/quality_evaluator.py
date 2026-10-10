"""
质量评估模块
使用AI对生成的文案进行多维度评分和筛选
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

from openai import OpenAI

from ..creators.content_creator import Script
from ..analyzers.viral_analyzer import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class ScoreResult:
    """评分结果数据类"""
    script: Script
    attraction_score: float = 0.0      # 吸引力分数 0-100
    relevance_score: float = 0.0       # 相关性分数 0-100
    originality_score: float = 0.0     # 原创度分数 0-100
    total_score: float = 0.0           # 综合分数 0-100
    suggestions: List[str] = field(default_factory=list)  # 改进建议


@dataclass
class ScoredScript:
    """带评分的文案"""
    script: Script
    score_result: ScoreResult


class QualityEvaluator:
    """文案质量评估器"""

    def __init__(self, ai_config: Dict[str, Any], eval_config: Dict[str, Any]):
        """
        初始化评估器
        :param ai_config: AI配置
        :param eval_config: 评估配置
        """
        self.client = self._init_client(ai_config)
        self.model = ai_config.get("model", "qwen-plus")
        self.temperature = ai_config.get("temperature", 0.3)  # 评估用低温度
        self.max_tokens = ai_config.get("max_tokens", 2048)
        
        self.min_score = eval_config.get("min_score", 70)
        weights = eval_config.get("weights", {})
        self.w_attraction = weights.get("attraction", 0.35)
        self.w_relevance = weights.get("relevance", 0.30)
        self.w_originality = weights.get("originality", 0.35)
        
        # 加载评估提示词
        self.prompt_template = self._load_prompt()
        
        logger.info(f"评估器初始化完成，最低通过分数: {self.min_score}")

    def _init_client(self, ai_config: Dict[str, Any]) -> OpenAI:
        """初始化OpenAI兼容客户端"""
        api_key = ai_config.get("api_key", "")
        base_url = ai_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        
        if not api_key:
            raise ValueError("AI API Key未配置")
        
        return OpenAI(api_key=api_key, base_url=base_url)

    def _load_prompt(self) -> str:
        """加载评估提示词模板"""
        try:
            with open("prompts/evaluation_prompt.md", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("评估提示词文件未找到，使用默认模板")
            return self._default_eval_prompt()

    def evaluate(
        self,
        scripts: List[Script],
        analysis: AnalysisResult
    ) -> List[ScoredScript]:
        """
        评估文案质量
        :param scripts: 待评估文案列表
        :param analysis: 爆款分析结果（作为评估参考）
        :return: 带评分的文案列表，按分数降序排列
        """
        logger.info(f"开始评估 {len(scripts)} 条文案")
        
        scored_scripts: List[ScoredScript] = []
        
        for script in scripts:
            try:
                score_result = self._score_single(script, analysis)
                scored = ScoredScript(script=script, score_result=score_result)
                scored_scripts.append(scored)
                
                logger.info(
                    f"评估完成: [{script.style}] "
                    f"吸引力={score_result.attraction_score:.1f}, "
                    f"相关性={score_result.relevance_score:.1f}, "
                    f"原创度={score_result.originality_score:.1f}, "
                    f"总分={score_result.total_score:.1f}"
                )
            except Exception as e:
                logger.error(f"评估失败 [{script.style}]: {e}")
        
        # 按总分降序排列
        scored_scripts.sort(key=lambda x: x.score_result.total_score, reverse=True)
        
        # 过滤低于最低分数的
        passed = [s for s in scored_scripts if s.score_result.total_score >= self.min_score]
        logger.info(f"评估完成: {len(passed)}/{len(scored_scripts)} 条通过（分数>={self.min_score}）")
        
        return passed

    def _score_single(self, script: Script, analysis: AnalysisResult) -> ScoreResult:
        """
        评估单条文案
        :param script: 待评估文案
        :param analysis: 爆款分析结果
        :return: 评分结果
        """
        prompt = self.prompt_template.replace("{{SCRIPT_TITLE}}", script.title)
        prompt = prompt.replace("{{SCRIPT_TEXT}}", script.script_text)
        prompt = prompt.replace("{{SCRIPT_STYLE}}", script.style)
        prompt = prompt.replace("{{HOOK_PATTERNS}}", json.dumps(analysis.hook_patterns, ensure_ascii=False))
        prompt = prompt.replace("{{PAIN_POINTS}}", json.dumps(analysis.pain_points, ensure_ascii=False))
        prompt = prompt.replace("{{VIRAL_FACTORS}}", json.dumps(analysis.viral_factors, ensure_ascii=False))
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的短视频内容评审专家，请客观评估文案质量。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            content = response.choices[0].message.content or ""
            return self._parse_score(content, script)
            
        except Exception as e:
            logger.error(f"AI评估调用失败: {e}")
            raise

    def _parse_score(self, content: str, script: Script) -> ScoreResult:
        """解析评分结果"""
        try:
            data = json.loads(content)
            attraction = float(data.get("attraction_score", 0))
            relevance = float(data.get("relevance_score", 0))
            originality = float(data.get("originality_score", 0))
            
            # 计算加权总分
            total = (
                attraction * self.w_attraction +
                relevance * self.w_relevance +
                originality * self.w_originality
            )
            
            suggestions = data.get("suggestions", [])
            if isinstance(suggestions, str):
                suggestions = [suggestions]
            
            return ScoreResult(
                script=script,
                attraction_score=min(100, max(0, attraction)),
                relevance_score=min(100, max(0, relevance)),
                originality_score=min(100, max(0, originality)),
                total_score=min(100, max(0, total)),
                suggestions=suggestions
            )
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"解析评分失败: {e}，使用默认分数")
            return ScoreResult(
                script=script,
                attraction_score=50,
                relevance_score=50,
                originality_score=50,
                total_score=50,
                suggestions=["评分解析失败，建议人工复核"]
            )

    @staticmethod
    def _default_eval_prompt() -> str:
        """默认评估提示词"""
        return """请评估以下抖音短视频文案的质量：

标题：{{SCRIPT_TITLE}}
风格：{{SCRIPT_STYLE}}
文案内容：
{{SCRIPT_TEXT}}

参考爆款特征：
- 钩子模式：{{HOOK_PATTERNS}}
- 用户痛点：{{PAIN_POINTS}}
- 爆款因素：{{VIRAL_FACTORS}}

请从以下维度评分（0-100）：
1. 吸引力（attraction_score）：开头是否能抓住注意力
2. 相关性（relevance_score）：与目标受众和痛点的匹配度
3. 原创度（originality_score）：是否有创新，非简单模仿

请以JSON格式输出：
{
  "attraction_score": 85,
  "relevance_score": 80,
  "originality_score": 75,
  "suggestions": ["改进建议1", "改进建议2"]
}
"""
