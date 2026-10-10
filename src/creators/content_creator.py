"""
AI创作模块
基于爆款分析结果，生成多风格的短视频文案
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

from openai import OpenAI

from ..analyzers.viral_analyzer import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class Script:
    """文案脚本数据类"""
    title: str
    script_text: str
    hashtags: List[str] = field(default_factory=list)
    style: str = ""
    estimated_duration: int = 30  # 预估时长（秒）


class ContentCreator:
    """AI内容创作者"""

    def __init__(self, ai_config: Dict[str, Any], creator_config: Dict[str, Any]):
        """
        初始化创作者
        :param ai_config: AI配置
        :param creator_config: 创作配置
        """
        self.client = self._init_client(ai_config)
        self.model = ai_config.get("model", "qwen-plus")
        self.temperature = ai_config.get("temperature", 0.8)
        self.max_tokens = ai_config.get("max_tokens", 4096)
        
        self.num_variants = creator_config.get("num_variants", 3)
        self.styles = creator_config.get("styles", ["口播", "故事", "干货"])
        
        # 加载创作提示词
        self.prompt_template = self._load_prompt()
        
        logger.info(f"创作者初始化完成，模型: {self.model}, 风格: {self.styles}")

    def _init_client(self, ai_config: Dict[str, Any]) -> OpenAI:
        """初始化OpenAI兼容客户端"""
        api_key = ai_config.get("api_key", "")
        base_url = ai_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        
        if not api_key:
            raise ValueError("AI API Key未配置")
        
        return OpenAI(api_key=api_key, base_url=base_url)

    def _load_prompt(self) -> str:
        """加载创作提示词模板"""
        try:
            with open("prompts/creation_prompt.md", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("创作提示词文件未找到，使用默认模板")
            return self._default_creation_prompt()

    def create(
        self,
        analysis_result: AnalysisResult,
        target_audience: str,
        product_info: str
    ) -> List[Script]:
        """
        基于分析结果创作文案
        :param analysis_result: 爆款分析结果
        :param target_audience: 目标受众描述
        :param product_info: 产品/服务信息
        :return: 文案列表
        """
        logger.info(f"开始创作文案，目标受众: {target_audience}")
        
        scripts: List[Script] = []
        
        for style in self.styles[:self.num_variants]:
            try:
                script = self._generate_variant(
                    analysis_result, target_audience, product_info, style
                )
                scripts.append(script)
                logger.info(f"生成 {style} 风格文案完成")
            except Exception as e:
                logger.error(f"生成 {style} 风格文案失败: {e}")
        
        logger.info(f"文案创作完成，共 {len(scripts)} 条")
        return scripts

    def _generate_variant(
        self,
        analysis: AnalysisResult,
        audience: str,
        product: str,
        style: str
    ) -> Script:
        """
        生成单个文案变体
        :param analysis: 分析结果
        :param audience: 目标受众
        :param product: 产品信息
        :param style: 文案风格
        :return: 文案脚本
        """
        # 构建提示词
        prompt = self.prompt_template.replace("{{STYLE}}", style)
        prompt = prompt.replace("{{TARGET_AUDIENCE}}", audience)
        prompt = prompt.replace("{{PRODUCT_INFO}}", product)
        prompt = prompt.replace("{{HOOK_PATTERNS}}", json.dumps(analysis.hook_patterns, ensure_ascii=False))
        prompt = prompt.replace("{{PAIN_POINTS}}", json.dumps(analysis.pain_points, ensure_ascii=False))
        prompt = prompt.replace("{{CONTENT_STRUCTURE}}", json.dumps(analysis.content_structure, ensure_ascii=False))
        prompt = prompt.replace("{{ENGAGEMENT_LOGIC}}", analysis.engagement_logic)
        prompt = prompt.replace("{{CONVERSION_PATH}}", analysis.conversion_path)
        prompt = prompt.replace("{{VIRAL_FACTORS}}", json.dumps(analysis.viral_factors, ensure_ascii=False))
        
        # 调用AI
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个专业的抖音短视频文案创作者，擅长{style}风格。你需要基于爆款分析结果，创作原创、有吸引力的文案。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            content = response.choices[0].message.content or ""
            return self._parse_script(content, style)
            
        except Exception as e:
            logger.error(f"AI调用失败: {e}")
            raise

    def _parse_script(self, content: str, style: str) -> Script:
        """解析AI响应为Script对象"""
        try:
            data = json.loads(content)
            return Script(
                title=data.get("title", ""),
                script_text=data.get("script_text", ""),
                hashtags=data.get("hashtags", []),
                style=style,
                estimated_duration=data.get("estimated_duration", 30)
            )
        except json.JSONDecodeError:
            # 尝试从文本中提取
            return self._parse_text_script(content, style)

    def _parse_text_script(self, content: str, style: str) -> Script:
        """从文本中解析文案"""
        lines = content.strip().split("\n")
        title = ""
        script_lines = []
        hashtags = []
        
        for line in lines:
            line = line.strip()
            if not title and (line.startswith("#") or "标题" in line):
                title = line.lstrip("#").replace("标题：", "").replace("标题:", "").strip()
            elif line.startswith("#") or line.startswith("＃"):
                tag = line.lstrip("#").lstrip("＃").strip()
                if tag:
                    hashtags.append(tag)
            else:
                script_lines.append(line)
        
        script_text = "\n".join(script_lines).strip()
        
        # 估算时长（按每秒4个字估算）
        char_count = len(script_text)
        estimated_duration = max(15, min(180, char_count // 4))
        
        return Script(
            title=title or f"{style}风格文案",
            script_text=script_text or content,
            hashtags=hashtags,
            style=style,
            estimated_duration=estimated_duration
        )

    @staticmethod
    def _default_creation_prompt() -> str:
        """默认创作提示词"""
        return """基于以下爆款分析结果，以{{STYLE}}风格创作一条抖音短视频文案。

目标受众：{{TARGET_AUDIENCE}}
产品信息：{{PRODUCT_INFO}}

爆款分析：
- 钩子模式：{{HOOK_PATTERNS}}
- 用户痛点：{{PAIN_POINTS}}
- 内容结构：{{CONTENT_STRUCTURE}}
- 互动逻辑：{{ENGAGEMENT_LOGIC}}
- 转化路径：{{CONVERSION_PATH}}
- 爆款因素：{{VIRAL_FACTORS}}

要求：
1. 开头3秒必须有强力钩子
2. 内容要有节奏感，适合口播
3. 自然融入产品信息，不要硬广
4. 结尾有互动引导
5. 原创度要高，不能照搬原文

请以JSON格式输出：
{
  "title": "视频标题",
  "script_text": "完整文案内容",
  "hashtags": ["标签1", "标签2"],
  "estimated_duration": 30
}
"""
