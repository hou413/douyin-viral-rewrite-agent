"""
抖音爆款采集模块
支持3种采集方式：API、网页爬虫、控屏（预留）
"""

import time
import logging
import hashlib
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """视频信息数据类"""
    video_id: str
    title: str
    author: str
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    url: str = ""
    create_time: str = ""
    tags: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def engagement_score(self) -> float:
        """计算综合互动分数"""
        return self.like_count * 1.0 + self.comment_count * 3.0 + self.share_count * 5.0


class DouyinCollector:
    """抖音视频采集器"""

    # 抖音网页端API
    SEARCH_URL = "https://www.douyin.com/aweme/v1/web/search/item/"
    DETAIL_URL = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Accept": "application/json, text/plain, */*",
    }

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器
        :param config: 采集配置字典
        """
        self.method = config.get("method", "scraper")
        self.cookie = config.get("douyin_cookie", "")
        self.api_key = config.get("api_key", "")
        self.api_secret = config.get("api_secret", "")
        self.max_videos = config.get("max_videos_per_run", 50)
        self.request_interval = config.get("request_interval", 2)
        
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        if self.cookie:
            self.session.headers["Cookie"] = self.cookie
        
        logger.info(f"采集器初始化完成，采集方式: {self.method}")

    def search_by_keyword(
        self,
        keyword: str,
        time_range_days: int = 7,
        max_count: int = 50
    ) -> List[VideoInfo]:
        """
        根据关键词搜索视频
        :param keyword: 搜索关键词
        :param time_range_days: 时间范围（天）
        :param max_count: 最大采集数量
        :return: 视频信息列表
        """
        logger.info(f"开始采集: keyword={keyword}, days={time_range_days}, max={max_count}")
        
        effective_max = min(max_count, self.max_videos)
        
        if self.method == "api":
            videos = self._search_via_api(keyword, effective_max)
        elif self.method == "scraper":
            videos = self._search_via_scraper(keyword, effective_max)
        elif self.method == "control_screen":
            videos = self._search_via_control_screen(keyword, effective_max)
        else:
            raise ValueError(f"不支持的采集方式: {self.method}")
        
        # 按时间过滤
        cutoff = datetime.now() - timedelta(days=time_range_days)
        filtered = []
        for v in videos:
            if v.create_time:
                try:
                    ct = datetime.fromisoformat(v.create_time)
                    if ct >= cutoff:
                        filtered.append(v)
                except (ValueError, TypeError):
                    filtered.append(v)
            else:
                filtered.append(v)
        
        logger.info(f"采集完成: 共获取 {len(filtered)} 条视频")
        return filtered

    def _search_via_api(self, keyword: str, max_count: int) -> List[VideoInfo]:
        """通过抖音开放平台API采集"""
        if not self.api_key:
            logger.warning("API Key未配置，降级为scraper模式")
            return self._search_via_scraper(keyword, max_count)
        
        videos: List[VideoInfo] = []
        cursor = 0
        page_size = 20
        
        while len(videos) < max_count:
            params = {
                "keyword": keyword,
                "search_channel": "aweme_general",
                "sort_type": 2,  # 按热度排序
                "publish_time": 1,  # 最近发布
                "count": page_size,
                "cursor": cursor,
            }
            
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                resp = self.session.get(
                    "https://open.douyin.com/api/search/video/",
                    params=params,
                    headers=headers,
                    timeout=15
                )
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("data", {}).get("error_code", -1) != 0:
                    logger.error(f"API返回错误: {data}")
                    break
                
                items = data.get("data", {}).get("data", [])
                if not items:
                    break
                
                for item in items:
                    vi = self._parse_api_item(item)
                    if vi:
                        videos.append(vi)
                
                cursor += page_size
                time.sleep(self.request_interval)
                
            except requests.RequestException as e:
                logger.error(f"API请求失败: {e}")
                break
        
        return videos[:max_count]

    def _search_via_scraper(self, keyword: str, max_count: int) -> List[VideoInfo]:
        """通过网页爬虫采集"""
        videos: List[VideoInfo] = []
        offset = 0
        page_size = 24
        
        while len(videos) < max_count:
            params = {
                "device_platform": "webapp",
                "aid": "6383",
                "channel": "channel_pc_web",
                "search_channel": "aweme_general",
                "keyword": keyword,
                "search_source": "normal_search",
                "query_correct_type": "1",
                "is_filter_search": "0",
                "from_group_id": "",
                "offset": offset,
                "count": page_size,
                "sort_type": "2",
                "publish_time": "1",
            }
            
            try:
                resp = self.session.get(
                    self.SEARCH_URL,
                    params=params,
                    timeout=15
                )
                resp.raise_for_status()
                data = resp.json()
                
                items = data.get("data", [])
                if not items:
                    logger.info("没有更多数据")
                    break
                
                for item in items:
                    vi = self._parse_scraper_item(item)
                    if vi:
                        videos.append(vi)
                
                offset += page_size
                has_more = data.get("has_more", 0)
                if not has_more:
                    break
                
                # 随机延迟，避免被封
                delay = self.request_interval + random.uniform(0.5, 1.5)
                time.sleep(delay)
                
            except requests.RequestException as e:
                logger.error(f"爬虫请求失败: {e}")
                break
            except Exception as e:
                logger.error(f"解析数据失败: {e}")
                break
        
        logger.info(f"爬虫采集完成: {len(videos)} 条")
        return videos[:max_count]

    def _search_via_control_screen(self, keyword: str, max_count: int) -> List[VideoInfo]:
        """控屏方式采集（预留接口）"""
        logger.warning("控屏采集方式尚未实现，请接入自动化框架")
        return []

    def _parse_api_item(self, item: Dict[str, Any]) -> Optional[VideoInfo]:
        """解析API返回的视频数据"""
        try:
            aweme = item.get("aweme_info", item)
            stats = aweme.get("statistics", {})
            
            # 提取标签
            tags = []
            text_extra = aweme.get("text_extra", [])
            for te in text_extra:
                if te.get("hashtag_name"):
                    tags.append(te["hashtag_name"])
            
            create_ts = aweme.get("create_time", 0)
            create_time = datetime.fromtimestamp(create_ts).isoformat() if create_ts else ""
            
            return VideoInfo(
                video_id=str(aweme.get("aweme_id", "")),
                title=aweme.get("desc", ""),
                author=aweme.get("author", {}).get("nickname", ""),
                play_count=stats.get("play_count", 0),
                like_count=stats.get("digg_count", 0),
                comment_count=stats.get("comment_count", 0),
                share_count=stats.get("share_count", 0),
                url=f"https://www.douyin.com/video/{aweme.get('aweme_id', '')}",
                create_time=create_time,
                tags=tags,
                raw_data=item
            )
        except Exception as e:
            logger.warning(f"解析API数据失败: {e}")
            return None

    def _parse_scraper_item(self, item: Dict[str, Any]) -> Optional[VideoInfo]:
        """解析爬虫返回的视频数据"""
        try:
            aweme = item.get("aweme_info", {})
            if not aweme:
                return None
            
            stats = aweme.get("statistics", {})
            
            # 提取标签
            tags = []
            for te in aweme.get("text_extra", []):
                hn = te.get("hashtag_name", "")
                if hn:
                    tags.append(hn)
            
            create_ts = aweme.get("create_time", 0)
            create_time = datetime.fromtimestamp(create_ts).isoformat() if create_ts else ""
            
            video_id = str(aweme.get("aweme_id", ""))
            
            return VideoInfo(
                video_id=video_id,
                title=aweme.get("desc", ""),
                author=aweme.get("author", {}).get("nickname", "未知"),
                play_count=stats.get("play_count", 0),
                like_count=stats.get("digg_count", 0),
                comment_count=stats.get("comment_count", 0),
                share_count=stats.get("share_count", 0),
                url=f"https://www.douyin.com/video/{video_id}",
                create_time=create_time,
                tags=tags,
                raw_data=item
            )
        except Exception as e:
            logger.warning(f"解析爬虫数据失败: {e}")
            return None
