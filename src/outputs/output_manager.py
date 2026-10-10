"""
输出管理模块
支持本地JSON/Markdown输出和飞书输出
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from .feishu_client import FeishuClient
from ..evaluators.quality_evaluator import ScoredScript
from ..analyzers.viral_analyzer import AnalysisResult

logger = logging.getLogger(__name__)


class OutputManager:
    """输出管理器"""

    def __init__(self, output_config: Dict[str, Any]):
        """
        初始化输出管理器
        :param output_config: 输出配置
        """
        self.mode = output_config.get("mode", "local")
        self.local_path = output_config.get("local_path", "./data/output")
        
        # 飞书客户端（按需初始化）
        self.feishu_client: FeishuClient = None
        feishu_config = output_config.get("feishu", {})
        if self.mode in ("feishu", "both"):
            app_id = feishu_config.get("app_id", "")
            app_secret = feishu_config.get("app_secret", "")
            if app_id and app_secret:
                self.feishu_client = FeishuClient(app_id, app_secret)
                self.bitable_app_token = feishu_config.get("bitable_app_token", "")
                self.folder_token = feishu_config.get("folder_token", "")
                self.table_id = feishu_config.get("table_id", "")
            else:
                logger.warning("飞书配置不完整，飞书输出将被跳过")
        
        logger.info(f"输出管理器初始化完成，模式: {self.mode}")

    def save_results(
        self,
        scored_scripts: List[ScoredScript],
        analysis_report: AnalysisResult
    ) -> Dict[str, Any]:
        """
        保存结果
        :param scored_scripts: 带评分的文案列表
        :param analysis_report: 分析报告
        :return: 输出结果摘要
        """
        logger.info(f"开始保存结果，共 {len(scored_scripts)} 条文案")
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_scripts": len(scored_scripts),
            "outputs": {}
        }
        
        if self.mode in ("local", "both"):
            try:
                local_path = self._save_local(scored_scripts, analysis_report)
                result["outputs"]["local"] = local_path
                logger.info(f"本地输出完成: {local_path}")
            except Exception as e:
                logger.error(f"本地输出失败: {e}")
                result["outputs"]["local_error"] = str(e)
        
        if self.mode in ("feishu", "both"):
            try:
                success = self._save_feishu(scored_scripts, analysis_report)
                result["outputs"]["feishu"] = success
            except Exception as e:
                logger.error(f"飞书输出失败: {e}")
                result["outputs"]["feishu_error"] = str(e)
        
        return result

    def _save_local(
        self,
        scripts: List[ScoredScript],
        report: AnalysisResult
    ) -> str:
        """
        保存到本地文件
        :param scripts: 文案列表
        :param report: 分析报告
        :return: 输出目录路径
        """
        # 创建输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(self.local_path, timestamp)
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存JSON数据
        json_data = {
            "generated_at": datetime.now().isoformat(),
            "analysis": {
                "hook_patterns": report.hook_patterns,
                "pain_points": report.pain_points,
                "content_structure": report.content_structure,
                "engagement_logic": report.engagement_logic,
                "conversion_path": report.conversion_path,
                "viral_factors": report.viral_factors,
            },
            "scripts": []
        }
        
        for scored in scripts:
            script_data = {
                "title": scored.script.title,
                "script_text": scored.script.script_text,
                "hashtags": scored.script.hashtags,
                "style": scored.script.style,
                "estimated_duration": scored.script.estimated_duration,
                "scores": {
                    "attraction": scored.score_result.attraction_score,
                    "relevance": scored.score_result.relevance_score,
                    "originality": scored.score_result.originality_score,
                    "total": scored.score_result.total_score,
                },
                "suggestions": scored.score_result.suggestions,
            }
            json_data["scripts"].append(script_data)
        
        json_path = os.path.join(output_dir, "results.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 保存Markdown报告
        md_content = self._generate_markdown_report(scripts, report)
        md_path = os.path.join(output_dir, "report.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        # 保存每条文案为单独文件
        scripts_dir = os.path.join(output_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        
        for i, scored in enumerate(scripts, 1):
            script_md = self._format_script_markdown(scored, i)
            filename = f"{i:02d}_{scored.script.style}_{scored.script.title[:20]}.md"
            # 清理文件名中的非法字符
            filename = "".join(c for c in filename if c not in r'\/:*?"<>|')
            script_path = os.path.join(scripts_dir, filename)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_md)
        
        logger.info(f"本地保存完成: {output_dir}")
        return output_dir

    def _save_feishu(
        self,
        scripts: List[ScoredScript],
        report: AnalysisResult
    ) -> bool:
        """
        保存到飞书
        :param scripts: 文案列表
        :param report: 分析报告
        :return: 是否成功
        """
        if not self.feishu_client:
            logger.warning("飞书客户端未初始化")
            return False
        
        success = True
        
        # 写入多维表格
        if self.bitable_app_token and self.table_id:
            records = []
            for scored in scripts:
                record = {
                    "标题": scored.script.title,
                    "风格": scored.script.style,
                    "文案内容": scored.script.script_text[:2000],  # 限制长度
                    "标签": ", ".join(scored.script.hashtags),
                    "预估时长(秒)": scored.script.estimated_duration,
                    "吸引力分数": round(scored.score_result.attraction_score, 1),
                    "相关性分数": round(scored.score_result.relevance_score, 1),
                    "原创度分数": round(scored.score_result.originality_score, 1),
                    "总分": round(scored.score_result.total_score, 1),
                    "改进建议": "; ".join(scored.score_result.suggestions),
                }
                records.append(record)
            
            if records:
                ok = self.feishu_client.write_to_bitable(
                    self.bitable_app_token, self.table_id, records
                )
                if not ok:
                    success = False
        else:
            logger.info("多维表格未配置，跳过写入")
        
        # 创建飞书文档报告
        if self.folder_token:
            md_report = self._generate_markdown_report(scripts, report)
            title = f"爆款改写报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            doc_url = self.feishu_client.create_document(
                self.folder_token, title, md_report
            )
            if not doc_url:
                success = False
            else:
                logger.info(f"飞书文档已创建: {doc_url}")
        
        return success

    def _generate_markdown_report(
        self,
        scripts: List[ScoredScript],
        report: AnalysisResult
    ) -> str:
        """生成Markdown格式的分析报告"""
        lines = [
            "# 抖音爆款改写报告",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 一、爆款分析摘要",
            "",
            "### 1.1 钩子模式",
        ]
        for hp in report.hook_patterns:
            lines.append(f"- {hp}")
        
        lines.extend([
            "",
            "### 1.2 用户痛点",
        ])
        for pp in report.pain_points:
            lines.append(f"- {pp}")
        
        lines.extend([
            "",
            "### 1.3 内容结构",
        ])
        for cs in report.content_structure:
            lines.append(f"- {cs}")
        
        lines.extend([
            "",
            f"### 1.4 互动逻辑",
            "",
            report.engagement_logic,
            "",
            "### 1.5 转化路径",
            "",
            report.conversion_path,
            "",
            "### 1.6 爆款因素",
        ])
        for vf in report.viral_factors:
            lines.append(f"- {vf}")
        
        lines.extend([
            "",
            "## 二、生成文案",
            "",
        ])
        
        for i, scored in enumerate(scripts, 1):
            lines.extend([
                f"### 文案 {i}: {scored.script.title}",
                "",
                f"**风格**: {scored.script.style} | "
                f"**预估时长**: {scored.script.estimated_duration}秒 | "
                f"**总分**: {scored.score_result.total_score:.1f}",
                "",
                f"**评分明细**: 吸引力 {scored.score_result.attraction_score:.1f} | "
                f"相关性 {scored.score_result.relevance_score:.1f} | "
                f"原创度 {scored.score_result.originality_score:.1f}",
                "",
                "#### 文案内容",
                "",
                scored.script.script_text,
                "",
                f"**标签**: {' '.join('#' + t for t in scored.script.hashtags)}",
                "",
            ])
            
            if scored.score_result.suggestions:
                lines.append("**改进建议**:")
                for s in scored.score_result.suggestions:
                    lines.append(f"- {s}")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)

    def _format_script_markdown(self, scored: ScoredScript, index: int) -> str:
        """格式化单条文案为Markdown"""
        lines = [
            f"# {scored.script.title}",
            "",
            f"- **风格**: {scored.script.style}",
            f"- **预估时长**: {scored.script.estimated_duration}秒",
            f"- **总分**: {scored.score_result.total_score:.1f}",
            "",
            "## 文案内容",
            "",
            scored.script.script_text,
            "",
            "## 标签",
            "",
            " ".join("#" + t for t in scored.script.hashtags),
            "",
        ]
        
        if scored.score_result.suggestions:
            lines.extend([
                "## 改进建议",
                "",
            ])
            for s in scored.score_result.suggestions:
                lines.append(f"- {s}")
        
        return "\n".join(lines)
