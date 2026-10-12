"""
每日工作流编排
按时间自动执行内容生产流程
"""

import json
import logging
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from src.core.models import AccountProfile
from src.core.knowledge_base import KnowledgeBase
from src.agents.director_agent import DirectorAgent

logger = logging.getLogger(__name__)


class DailyPipeline:
    """每日工作流编排器"""

    def __init__(
        self,
        account_config_path: str = "config/account_profile.json",
        knowledge_base_path: str = "data/knowledge_base",
        ai_call_func=None
    ):
        """
        初始化工作流
        
        Args:
            account_config_path: 账号配置文件路径
            knowledge_base_path: 知识库目录路径
            ai_call_func: AI调用函数
        """
        self.account = self._load_account(account_config_path)
        self.kb = KnowledgeBase(storage_path=knowledge_base_path)
        self.director = DirectorAgent(
            account=self.account,
            ai_call_func=ai_call_func,
            knowledge_base=self.kb
        )
        
        # 输出目录
        self.output_dir = Path("data/daily_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_account(self, config_path: str) -> AccountProfile:
        """加载账号配置"""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"账号配置文件不存在: {config_path}，使用默认配置")
            return AccountProfile(
                account_name="默认账号",
                niche="通用",
                target_audience="泛人群",
                content_style="专业易懂",
                brand_voice="权威实用",
                conversion_goal="品牌认知",
            )
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return AccountProfile.from_dict(data)

    def run_morning_pipeline(self, keyword: str = "", style: str = "口播") -> Dict:
        """
        执行早间流水线（09:00-14:00）
        - 09:00 情报收集
        - 10:00 选题生成+筛选
        - 11:00 脚本设计
        - 14:00 视频制作方案
        """
        logger.info("=" * 60)
        logger.info("🌅 早间流水线启动")
        logger.info("=" * 60)
        
        result = self.director.run_daily_pipeline(keyword=keyword, style=style)
        
        # 保存到文件
        output_file = self.output_dir / f"daily_plan_{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ 早间流水线完成，结果已保存到: {output_file}")
        return result

    def run_evening_pipeline(self, performance_data: list) -> Dict:
        """
        执行晚间流水线（发布后）
        - 数据追踪
        - 诊断分析
        - 迭代优化
        """
        logger.info("=" * 60)
        logger.info("🌙 晚间流水线启动")
        logger.info("=" * 60)
        
        if not performance_data:
            logger.warning("无表现数据，跳过晚间流水线")
            return {"status": "skipped", "reason": "无表现数据"}
        
        result = self.director.analyze_performance(performance_data)
        
        # 保存到文件
        output_file = self.output_dir / f"analysis_{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ 晚间流水线完成，结果已保存到: {output_file}")
        return result

    def generate_daily_summary(self) -> Dict:
        """生成每日总结"""
        today = datetime.now().strftime('%Y%m%d')
        
        # 读取今日数据
        plan_file = self.output_dir / f"daily_plan_{today}.json"
        analysis_file = self.output_dir / f"analysis_{today}.json"
        
        summary = {
            "date": today,
            "morning_plan": None,
            "evening_analysis": None,
            "overall_status": "incomplete",
        }
        
        if plan_file.exists():
            with open(plan_file, 'r', encoding='utf-8') as f:
                summary["morning_plan"] = json.load(f)
        
        if analysis_file.exists():
            with open(analysis_file, 'r', encoding='utf-8') as f:
                summary["evening_analysis"] = json.load(f)
        
        if summary["morning_plan"] and summary["evening_analysis"]:
            summary["overall_status"] = "completed"
        elif summary["morning_plan"]:
            summary["overall_status"] = "morning_completed"
        
        # 保存总结
        summary_file = self.output_dir / f"summary_{today}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建示例账号配置
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    sample_account = {
        "account_name": "示例账号",
        "niche": "机器人/具身智能",
        "target_audience": "科技爱好者、创业者、行业从业者",
        "content_style": "专业但易懂，有深度",
        "brand_voice": "权威、前瞻、实用",
        "conversion_goal": "品牌认知+产品咨询+粉丝增长",
        "baseline_metrics": {
            "avg_like_rate": 0.05,
            "avg_share_rate": 0.01,
            "avg_completion_rate": 0.4,
            "avg_follow_rate": 0.005
        }
    }
    
    config_file = config_dir / "account_profile.json"
    if not config_file.exists():
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(sample_account, f, ensure_ascii=False, indent=2)
        logger.info(f"已创建示例账号配置: {config_file}")
    
    # 运行工作流
    pipeline = DailyPipeline()
    result = pipeline.run_morning_pipeline(keyword="机器人", style="口播")
    
    print("\n" + "=" * 60)
    print("每日工作流执行结果")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
