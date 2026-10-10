"""
流程编排模块 - 串联所有模块完成完整的爆款改写流程
"""
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml

from src.collectors.douyin_collector import DouyinCollector, VideoInfo
from src.filters.viral_filter import ViralFilter
from src.extractors.content_extractor import ContentExtractor, VideoContent
from src.analyzers.viral_analyzer import ViralAnalyzer, AnalysisResult
from src.creators.content_creator import ContentCreator, Script
from src.evaluators.quality_evaluator import QualityEvaluator, ScoredScript
from src.outputs.output_manager import OutputManager

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """流程执行结果"""
    success: bool
    keywords: List[str]
    collected_count: int = 0
    filtered_count: int = 0
    extracted_count: int = 0
    created_count: int = 0
    passed_count: int = 0
    output_paths: dict = field(default_factory=dict)
    error: Optional[str] = None
    duration_seconds: float = 0


class Pipeline:
    """爆款改写Agent主流程编排"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._init_modules()

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _setup_logging(self):
        """配置日志"""
        log_cfg = self.config.get("logging", {})
        level = getattr(logging, log_cfg.get("level", "INFO"))
        log_file = log_cfg.get("file", "./logs/agent.log")

        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )

    def _init_modules(self):
        """初始化各模块"""
        logger.info("初始化各模块...")
        self.collector = DouyinCollector(self.config.get("collector", {}))
        self.filter = ViralFilter(self.config.get("filter", {}))
        self.extractor = ContentExtractor(self.config.get("extractor", {}))
        self.analyzer = ViralAnalyzer(self.config.get("ai", {}))
        self.creator = ContentCreator(
            self.config.get("ai", {}),
            self.config.get("creator", {}),
        )
        self.evaluator = QualityEvaluator(
            self.config.get("ai", {}),
            self.config.get("evaluator", {}),
        )
        self.output_manager = OutputManager(self.config.get("output", {}))
        logger.info("所有模块初始化完成")

    def run(
        self,
        keywords: List[str],
        target_audience: str,
        product_info: str,
    ) -> PipelineResult:
        """执行完整流程"""
        start_time = time.time()
        result = PipelineResult(success=False, keywords=keywords)

        try:
            # ========== 第1步：爆款采集 ==========
            logger.info(f"📥 第1步：爆款采集 | 关键词: {keywords}")
            all_videos: List[VideoInfo] = []
            filter_cfg = self.config.get("filter", {})
            time_range = filter_cfg.get("time_range_days", 7)
            max_videos = self.config.get("collector", {}).get("max_videos_per_run", 50)

            for keyword in keywords:
                videos = self.collector.search_by_keyword(
                    keyword=keyword,
                    time_range_days=time_range,
                    max_count=max_videos,
                )
                logger.info(f"  关键词「{keyword}」采集到 {len(videos)} 个视频")
                all_videos.extend(videos)

            result.collected_count = len(all_videos)
            logger.info(f"  共采集 {len(all_videos)} 个视频")

            if not all_videos:
                result.error = "未采集到任何视频，请检查关键词或采集配置"
                logger.warning(result.error)
                result.duration_seconds = time.time() - start_time
                return result

            # ========== 第2步：爆款筛选 ==========
            logger.info("🔍 第2步：爆款筛选")
            filtered_videos = self.filter.filter_videos(all_videos, keywords)
            result.filtered_count = len(filtered_videos)
            logger.info(f"  筛选后剩余 {len(filtered_videos)} 个爆款视频")

            if not filtered_videos:
                result.error = "筛选后无视频，请降低筛选阈值"
                logger.warning(result.error)
                result.duration_seconds = time.time() - start_time
                return result

            # ========== 第3步：文案提取 ==========
            logger.info("📝 第3步：文案提取")
            contents: List[VideoContent] = []
            for video in filtered_videos:
                try:
                    content = self.extractor.extract(video)
                    contents.append(content)
                except Exception as e:
                    logger.warning(f"  提取视频 {video.video_id} 失败: {e}")

            result.extracted_count = len(contents)
            logger.info(f"  成功提取 {len(contents)} 个视频内容")

            if not contents:
                result.error = "未能提取任何视频内容"
                logger.warning(result.error)
                result.duration_seconds = time.time() - start_time
                return result

            # ========== 第4步：AI分析 ==========
            logger.info("🧠 第4步：AI爆款分析")
            analysis: AnalysisResult = self.analyzer.analyze(contents)
            logger.info(f"  分析完成 | 爆款因子: {len(analysis.viral_factors)} 个")

            # ========== 第5步：AI创作 ==========
            logger.info("✍️ 第5步：AI文案创作")
            scripts: List[Script] = self.creator.create(
                analysis_result=analysis,
                target_audience=target_audience,
                product_info=product_info,
            )
            result.created_count = len(scripts)
            logger.info(f"  生成 {len(scripts)} 版文案")

            # ========== 第6步：质量评估 ==========
            logger.info("⭐ 第6步：质量评估")
            scored_scripts: List[ScoredScript] = self.evaluator.evaluate(
                scripts=scripts,
                analysis=analysis,
            )

            # 按总分排序
            scored_scripts.sort(key=lambda x: x.total_score, reverse=True)
            result.passed_count = sum(
                1 for s in scored_scripts if s.total_score >= self.config.get("evaluator", {}).get("min_score", 70)
            )
            logger.info(f"  通过评估: {result.passed_count}/{len(scored_scripts)}")

            # ========== 第7步：结果输出 ==========
            logger.info("📤 第7步：结果输出")
            report = self._generate_report(result, analysis, scored_scripts)
            output_result = self.output_manager.save_results(scored_scripts, report)
            result.output_paths = output_result
            logger.info(f"  输出完成: {output_result}")

            result.success = True
            result.duration_seconds = time.time() - start_time
            logger.info(f"✅ 流程完成 | 耗时: {result.duration_seconds:.1f}s")

        except Exception as e:
            logger.error(f"❌ 流程执行异常: {e}", exc_info=True)
            result.error = str(e)
            result.duration_seconds = time.time() - start_time

        return result

    def _generate_report(
        self,
        result: PipelineResult,
        analysis: AnalysisResult,
        scored_scripts: List[ScoredScript],
    ) -> str:
        """生成Markdown格式的分析报告"""
        lines = [
            "# 每日爆款分析与创作报告",
            f"\n**执行时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**关键词**: {', '.join(result.keywords)}",
            f"**耗时**: {result.duration_seconds:.1f}秒",
            "",
            "## 📊 执行摘要",
            f"| 阶段 | 数量 |",
            f"|------|------|",
            f"| 采集视频 | {result.collected_count} |",
            f"| 筛选爆款 | {result.filtered_count} |",
            f"| 提取内容 | {result.extracted_count} |",
            f"| 创作文案 | {result.created_count} |",
            f"| 通过评估 | {result.passed_count} |",
            "",
            "## 🔥 爆款因子分析",
        ]

        for i, factor in enumerate(analysis.viral_factors, 1):
            lines.append(f"{i}. {factor}")

        lines.extend([
            "",
            "## 🎯 钩子模式",
        ])
        for hook in analysis.hook_patterns:
            lines.append(f"- {hook}")

        lines.extend([
            "",
            "## 😣 用户痛点",
        ])
        for pain in analysis.pain_points:
            lines.append(f"- {pain}")

        lines.extend([
            "",
            "## ✍️ 创作文案（按评分排序）",
        ])

        for i, scored in enumerate(scored_scripts, 1):
            s = scored.script
            lines.extend([
                f"### 文案{i}（总分: {scored.total_score:.0f}）",
                f"**标题**: {s.title}",
                f"**风格**: {s.style} | **预计时长**: {s.estimated_duration}s",
                f"**标签**: {' '.join(s.hashtags)}",
                "",
                f"```",
                s.script_text,
                f"```",
                "",
                f"**评估建议**: {scored.suggestions}",
                "",
            ])

        return "\n".join(lines)
