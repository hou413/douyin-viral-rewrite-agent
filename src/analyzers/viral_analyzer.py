"""
AI分析模块
使用AI分析爆款视频的传播逻辑、钩子模式、痛点等
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

from openai import OpenAI

from ..extractors.content_extractor import VideoContent

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    hook_patterns: List[str] = field(default_factory=list)           # 钩子模式
    pain_points: List[str] = field(default_factory=list)             # 用户痛点
    content_structure: List[str] = field(default_factory=list)       # 内容结构
    engagement_logic: str = ""                                        # 互动逻辑
    conversion_path: str = ""                                         # 转化路径
    viral_factors: List[str] = field(default_factory=list)           # 爆款因素
    raw_analysis: str = ""                                            # 原始分析文本


class ViralAnalyzer:
    """爆款视频AI分析器"""

    def __init__(self, ai_config: Dict[str, Any]):
        """
        初始化AI分析器
        :param ai_config: AI配置
        """
        self.client = self._init_client(ai_config)
        self.model = ai_config.get("model", "qwen-plus")
        self.temperature = ai_config.get("temperature", 0.8)
        self.max_tokens = ai_config.get("max_tokens", 4096)
        
        # 加载分析提示词
        self.prompt_template = self._load_prompt()
        
        logger.info(f"AI分析器初始化完成，模型: {self.model}")

    def _init_client(self, ai_config: Dict[str, Any]) -> OpenAI:
        """初始化OpenAI兼容客户端"""
        api_key = ai_config.get("api_key", "")
        base_url = ai_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        
        if not api_key:
            raise ValueError("AI API Key未配置")
        
        return OpenAI(api_key=api_key, base_url=base_url)

    def _load_prompt(self) -> str:
        """加载分析提示词模板"""
        try:
            with open("prompts/analysis_prompt.md", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("分析提示词文件未找到，使用默认模板")
            return self._default_analysis_prompt()

    def analyze(self, video_contents: List[VideoContent]) -> AnalysisResult:
        """
        分析爆款视频内容
        :param video_contents: 视频内容列表
        :return: 分析结果
        """
        logger.info(f"开始分析 {len(video_contents)} 个视频内容")
        
        # 构建分析内容
        content_text = self._build_content_text(video_contents)
        
        # 调用AI分析
        prompt = self.prompt_template.replace("{{CONTENT}}", content_text)
        
        try:
            response = self._call_ai(prompt, content_text)
            result = self._parse_analysis(response)
            logger.info("分析完成")
            return result
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            raise

    def _call_ai(self, prompt: str, content: str) -> str:
        """
        调用AI接口
        :param prompt: 提示词
        :param content: 内容
        :return: AI响应
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的短视频内容分析师，擅长拆解爆款视频的传播逻辑。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            logger.error(f"调用AI失败: {e}")
            raise

    def _build_content_text(self, video_contents: List[VideoContent]) -> str:
        """构建分析内容文本"""
        parts = []
        for i, vc in enumerate(video_contents, 1):
            part = f"""
=== 视频 {i} ===
标题: {vc.title}
字幕/文案: {vc.subtitle[:1000] if vc.subtitle else '无'}
标签: {', '.join(vc.tags) if vc.tags else '无'}
热门评论（前5条）:
"""
            # 添加热门评论
            top_comments = sorted(vc.comments, key=lambda x: x.get("likes", 0), reverse=True)[:5]
            for j, c in enumerate(top_comments, 1):
                part += f"  {j}. {c.get('text', '')} (点赞: {c.get('likes', 0)})\n"
            
            parts.append(part)
        
        return "\n".join(parts)

    def _parse_analysis(self, response: str) -> AnalysisResult:
        """解析AI响应为结构化结果"""
        try:
            # 尝试解析JSON
            data = json.loads(response)
            return AnalysisResult(
                hook_patterns=data.get("hook_patterns", []),
                pain_points=data.get("pain_points", []),
                content_structure=data.get("content_structure", []),
                engagement_logic=data.get("engagement_logic", ""),
                conversion_path=data.get("conversion_path", ""),
                viral_factors=data.get("viral_factors", []),
                raw_analysis=response
            )
        except json.JSONDecodeError:
            # 如果不是JSON，尝试从文本中提取
            logger.warning("AI响应非JSON格式，尝试文本解析")
            return self._parse_text_analysis(response)

    def _parse_text_analysis(self, text: str) -> AnalysisResult:
        """从文本中提取分析结果"""
        result = AnalysisResult(raw_analysis=text)
        
        # 简单的关键词提取
        lines = text.split("\n")
        current_section = ""
        
        for line in lines:
            line = line.strip()
            if "钩子" in line or "hook" in line.lower():
                current_section = "hook"
            elif "痛点" in line:
                current_section = "pain"
            elif "结构" in line:
                current_section = "structure"
            elif "互动" in line:
                current_section = "engagement"
            elif "转化" in line:
                current_section = "conversion"
            elif "爆款" in line:
                current_section = "viral"
            elif line and current_section:
                if current_section == "hook":
                    result.hook_patterns.append(line)
                elif current_section == "pain":
                    result.pain_points.append(line)
                elif current_section == "structure":
                    result.content_structure.append(line)
                elif current_section == "engagement":
                    result.engagement_logic += line + "\n"
                elif current_section == "conversion":
                    result.conversion_path += line + "\n"
                elif current_section == "viral":
                    result.viral_factors.append(line)
        
        return result

    @staticmethod
    def _default_analysis_prompt() -> str:
        """默认分析提示词"""
        return """请分析以下爆款视频内容，提取关键信息：

{{CONTENT}}

请从以下维度分析并以JSON格式输出：
{
  "hook_patterns": ["开头钩子模式列表"],
  "pain_points": ["用户痛点列表"],
  "content_structure": ["内容结构步骤"],
  "engagement_logic": "互动逻辑说明",
  "conversion_path": "转化路径说明",
  "viral_factors": ["爆款因素列表"]
}
"""
