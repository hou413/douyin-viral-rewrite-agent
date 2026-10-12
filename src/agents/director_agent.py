"""
总导演Agent
负责：编排所有子Agent、管理账号定位、最终决策和审核
输出：每日内容计划
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.core.models import (
    HotTopic, CandidateTopic, Script, VideoPlan, 
    PerformanceData, DiagnosisReport, AccountProfile
)
from src.core.knowledge_base import KnowledgeBase
from src.core.viral_scorer import ViralScorer
from src.agents.hot_intel_agent import HotIntelAgent
from src.agents.topic_agent import TopicAgent
from src.agents.script_agent import ScriptAgent
from src.agents.video_agent import VideoAgent
from src.agents.data_agent import DataAgent
from src.agents.iterate_agent import IterateAgent

logger = logging.getLogger(__name__)


class DirectorAgent:
    """总导演Agent - 内容增长系统总指挥"""

    def __init__(
        self,
        account: AccountProfile,
        ai_call_func=None,
        knowledge_base: Optional[KnowledgeBase] = None
    ):
        self.account = account
        self._call_ai = ai_call_func
        self.kb = knowledge_base or KnowledgeBase()
        self.scorer = ViralScorer(ai_call_func=ai_call_func)
        
        # 初始化6个子Agent
        self.hot_intel = HotIntelAgent()
        self.topic_agent = TopicAgent(ai_call_func=ai_call_func, account=account)
        self.script_agent = ScriptAgent(ai_call_func=ai_call_func, account=account)
        self.video_agent = VideoAgent(ai_call_func=ai_call_func)
        self.data_agent = DataAgent(baseline_metrics=account.baseline_metrics)
        self.iterate_agent = IterateAgent(knowledge_base=self.kb, ai_call_func=ai_call_func)

    def run_daily_pipeline(self, keyword: str = "", style: str = "口播") -> Dict:
        """
        执行每日内容生产流水线
        返回完整的每日内容计划
        """
        logger.info(f"=== 每日内容流水线启动 ===")
        logger.info(f"账号: {self.account.account_name}")
        logger.info(f"领域: {self.account.niche}")
        logger.info(f"关键词: {keyword or '全部'}")

        pipeline_result = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "account": self.account.account_name,
            "stages": {},
        }

        # Stage 1: 热点情报收集
        logger.info("\n[Stage 1] 热点情报收集...")
        hot_report = self.hot_intel.run(keyword=keyword)
        hot_topics = [HotTopic.from_dict(t) for t in hot_report.get("top10", [])]
        pipeline_result["stages"]["hot_intel"] = {
            "count": len(hot_topics),
            "top3": [t.title for t in hot_topics[:3]],
        }

        if not hot_topics:
            logger.warning("未获取到热点，流水线终止")
            return pipeline_result

        # Stage 2: 选题生成与筛选
        logger.info("\n[Stage 2] 选题生成与筛选...")
        candidates = self.topic_agent.generate_topics(hot_topics, max_topics=20)
        top_candidates = self.topic_agent.filter_top_topics(candidates, top_n=5, min_score=60)
        pipeline_result["stages"]["topic_generation"] = {
            "total": len(candidates),
            "selected": len(top_candidates),
            "topics": [{"title": t.title, "score": t.viral_score} for t in top_candidates],
        }

        if not top_candidates:
            logger.warning("未筛选出合格选题，流水线终止")
            return pipeline_result

        # Stage 3: 脚本创作
        logger.info("\n[Stage 3] 脚本创作...")
        scripts = self.script_agent.create_scripts(top_candidates, style=style)
        pipeline_result["stages"]["script_creation"] = {
            "count": len(scripts),
            "scripts": [{"title": s.title, "duration": s.estimated_duration} for s in scripts],
        }

        if not scripts:
            logger.warning("脚本创作失败，流水线终止")
            return pipeline_result

        # Stage 4: 爆款潜力评估
        logger.info("\n[Stage 4] 爆款潜力评估...")
        scored_scripts = []
        for script in scripts:
            score = self.scorer.score_script(script, self.account)
            scored_scripts.append({
                "script": script,
                "score": score,
            })
            logger.info(f"  {script.title}: {score.total_score}分 ({score.grade.value})")

        pipeline_result["stages"]["viral_scoring"] = {
            "scripts": [
                {
                    "title": s["script"].title,
                    "score": s["score"].total_score,
                    "grade": s["score"].grade.value,
                }
                for s in scored_scripts
            ]
        }

        # Stage 5: 视频制作方案
        logger.info("\n[Stage 5] 视频制作方案...")
        # 只为评分>=70的脚本生成制作方案
        high_score_scripts = [s["script"] for s in scored_scripts if s["score"].total_score >= 70]
        if not high_score_scripts:
            high_score_scripts = [scored_scripts[0]["script"]]  # 至少选一个
        
        video_plans = self.video_agent.create_video_plans(high_score_scripts)
        pipeline_result["stages"]["video_planning"] = {
            "count": len(video_plans),
            "plans": [
                {
                    "title": p.script.title,
                    "storyboard_count": len(p.storyboard),
                    "bgm_mood": p.bgm_mood,
                }
                for p in video_plans
            ]
        }

        # 汇总输出
        pipeline_result["summary"] = {
            "hot_topics_found": len(hot_topics),
            "topics_generated": len(candidates),
            "topics_selected": len(top_candidates),
            "scripts_created": len(scripts),
            "video_plans_ready": len(video_plans),
            "top_script": scored_scripts[0]["script"].title if scored_scripts else None,
            "top_score": scored_scripts[0]["score"].total_score if scored_scripts else 0,
        }

        logger.info(f"\n=== 每日流水线完成 ===")
        logger.info(f"热点: {len(hot_topics)} → 选题: {len(candidates)} → 脚本: {len(scripts)} → 制作方案: {len(video_plans)}")

        return pipeline_result

    def analyze_performance(self, performance_data: List[PerformanceData]) -> Dict:
        """
        分析视频表现数据（发布后调用）
        """
        logger.info(f"\n=== 数据分析阶段 ===")
        
        # 诊断每条视频
        reports = self.data_agent.batch_diagnose(performance_data)
        
        # 生成汇总
        summary = self.data_agent.generate_summary(reports)
        
        # 迭代优化
        iteration_result = self.iterate_agent.analyze_and_iterate(reports, self.account.account_name)
        
        return {
            "diagnosis": summary,
            "iteration": iteration_result,
        }

    def review_and_approve(self, script: Script) -> Dict:
        """
        最终审核脚本
        返回审核结果和建议
        """
        score = self.scorer.score_script(script, self.account)
        
        approval = {
            "approved": score.total_score >= 70,
            "score": score.total_score,
            "grade": score.grade.value,
            "summary": score.summary,
            "dimensions": [
                {
                    "name": d.name,
                    "score": d.score,
                    "reasoning": d.reasoning,
                    "suggestions": d.improvement_suggestions,
                }
                for d in score.dimensions
            ],
        }

        if not approval["approved"]:
            approval["feedback"] = f"评分{score.total_score}分，低于70分门槛。建议优化后重新提交。"
        else:
            approval["feedback"] = f"评分{score.total_score}分，可以执行。"

        return approval


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建账号配置
    account = AccountProfile(
        account_name="测试账号",
        niche="机器人/具身智能",
        target_audience="科技爱好者、创业者",
        content_style="专业但易懂",
        brand_voice="权威、前瞻、实用",
        conversion_goal="品牌认知+产品咨询",
        baseline_metrics={
            "avg_like_rate": 0.05,
            "avg_share_rate": 0.01,
            "avg_completion_rate": 0.4,
            "avg_follow_rate": 0.005,
        }
    )
    
    # 创建总导演
    director = DirectorAgent(account=account)
    
    # 执行每日流水线
    result = director.run_daily_pipeline(keyword="机器人", style="口播")
    
    print("\n" + "="*60)
    print("每日内容计划")
    print("="*60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
