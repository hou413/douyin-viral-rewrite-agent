"""
热点情报Agent
负责：监控抖音热榜、分析热点趋势、竞品监控
输出：每日热点报告
"""

import json
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import requests

from src.core.models import HotTopic, TrendDirection

logger = logging.getLogger(__name__)


class HotIntelAgent:
    """热点情报Agent"""

    HOT_API = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.douyin.com/",
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self._init_cookies()
        # 历史热点用于趋势对比
        self._history: Dict[str, List[Dict]] = {}

    def _init_cookies(self):
        """获取基础cookies"""
        try:
            self.session.get("https://www.douyin.com/", headers={**self.DEFAULT_HEADERS, "Accept": "text/html"}, timeout=15)
            self.session.post(
                "https://ttwid.bytedance.com/ttwid/union/register/",
                json={"region": "cn", "aid": 1768, "needFid": False, "service": "www.douyin.com",
                      "migrate_info": {"ticket": "", "source": "node"}, "cbUrlProtocol": "https", "union": True},
                headers={**self.DEFAULT_HEADERS, "Content-Type": "application/json"},
                timeout=10,
            )
        except Exception as e:
            logger.warning(f"Cookie初始化失败: {e}")

    def fetch_hot_list(self) -> List[HotTopic]:
        """获取抖音实时热榜"""
        logger.info("开始获取抖音热榜...")
        try:
            resp = self.session.get(self.HOT_API, headers=self.DEFAULT_HEADERS, timeout=15)
            data = resp.json()
            word_list = data.get("data", {}).get("word_list", [])
            trending_list = data.get("data", {}).get("trending_list", [])

            topics = []
            seen_ids = set()
            for item in word_list + trending_list:
                gid = item.get("group_id", "")
                if gid and gid not in seen_ids:
                    seen_ids.add(gid)
                    topic = self._parse_hot_item(item)
                    if topic:
                        topics.append(topic)

            logger.info(f"获取到 {len(topics)} 条热搜")
            return topics
        except Exception as e:
            logger.error(f"获取热榜失败: {e}")
            return []

    def _parse_hot_item(self, item: Dict) -> Optional[HotTopic]:
        """解析单条热搜"""
        try:
            word = item.get("word", "")
            if not word:
                return None
            return HotTopic(
                id=str(item.get("group_id", "")),
                title=word,
                hot_value=item.get("hot_value", 0),
                category=self._infer_category(word),
                trend=self._analyze_trend(word, item.get("hot_value", 0)),
                source="抖音热榜",
                keywords=[word],
                description=word,
            )
        except Exception as e:
            logger.warning(f"解析热搜失败: {e}")
            return None

    def _infer_category(self, title: str) -> str:
        """推断热点分类"""
        category_keywords = {
            "科技": ["AI", "机器人", "芯片", "手机", "互联网", "科技", "智能", "数据"],
            "娱乐": ["明星", "电影", "综艺", "音乐", "八卦", "八卦"],
            "体育": ["比赛", "冠军", "奥运", "足球", "篮球", "NBA"],
            "社会": ["事故", "政策", "法律", "教育", "医疗"],
            "生活": ["美食", "旅行", "穿搭", "家居", "健身"],
        }
        for cat, kws in category_keywords.items():
            if any(kw in title for kw in kws):
                return cat
        return "综合"

    def _analyze_trend(self, title: str, hot_value: int) -> TrendDirection:
        """分析趋势（对比历史数据）"""
        if title in self._history:
            prev_values = [h["hot_value"] for h in self._history[title]]
            if prev_values:
                avg_prev = sum(prev_values) / len(prev_values)
                if hot_value > avg_prev * 1.1:
                    return TrendDirection.RISING
                elif hot_value < avg_prev * 0.9:
                    return TrendDirection.FALLING
        # 记录当前值
        if title not in self._history:
            self._history[title] = []
        self._history[title].append({"hot_value": hot_value, "time": datetime.now().isoformat()})
        # 保留最近10条
        self._history[title] = self._history[title][-10:]
        return TrendDirection.STABLE

    def filter_by_keyword(self, topics: List[HotTopic], keyword: str) -> List[HotTopic]:
        """按关键词过滤"""
        if not keyword:
            return topics
        kw = keyword.lower()
        return [t for t in topics if kw in t.title.lower()]

    def generate_daily_report(self, topics: List[HotTopic], keyword: str = "") -> Dict:
        """生成每日热点报告"""
        if keyword:
            topics = self.filter_by_keyword(topics, keyword)

        topics.sort(key=lambda t: t.hot_value, reverse=True)

        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "keyword_filter": keyword,
            "total_count": len(topics),
            "top10": [t.to_dict() for t in topics[:10]],
            "by_category": {},
            "rising_topics": [t.to_dict() for t in topics if t.trend == TrendDirection.RISING],
            "generated_at": datetime.now().isoformat(),
        }

        # 按分类统计
        for t in topics:
            cat = t.category
            if cat not in report["by_category"]:
                report["by_category"][cat] = []
            report["by_category"][cat].append(t.to_dict())

        return report

    def run(self, keyword: str = "") -> Dict:
        """执行热点情报收集"""
        logger.info(f"热点情报Agent启动，关键词: {keyword or '全部'}")
        topics = self.fetch_hot_list()
        report = self.generate_daily_report(topics, keyword)
        logger.info(f"热点报告生成完成: {report['total_count']}条热点")
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = HotIntelAgent()
    report = agent.run(keyword="机器人")
    print(json.dumps(report, ensure_ascii=False, indent=2))
