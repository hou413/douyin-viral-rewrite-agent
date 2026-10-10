"""
内容提取模块
从抖音视频中提取字幕、评论、元数据等信息
"""

import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import requests

from ..collectors.douyin_collector import VideoInfo

logger = logging.getLogger(__name__)


@dataclass
class VideoContent:
    """视频内容数据类"""
    video_id: str
    title: str
    subtitle: str = ""
    comments: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContentExtractor:
    """视频内容提取器"""

    COMMENT_URL = "https://www.douyin.com/aweme/v1/web/comment/list/"
    SUBTITLE_URL = "https://www.douyin.com/aweme/v1/web/aweme/detail/"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
    }

    def __init__(self, config: Dict[str, Any], cookie: str = ""):
        """
        初始化提取器
        :param config: 提取配置
        :param cookie: 抖音Cookie
        """
        self.extract_subtitles: bool = config.get("extract_subtitles", True)
        self.extract_comments: bool = config.get("extract_comments", True)
        self.max_comments: int = config.get("max_comments", 50)

        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        if cookie:
            self.session.headers["Cookie"] = cookie

        logger.info("内容提取器初始化完成")

    def extract(self, video_info: VideoInfo) -> VideoContent:
        """
        提取视频的完整内容
        :param video_info: 视频基本信息
        :return: 完整视频内容
        """
        logger.info(f"开始提取视频内容: {video_info.video_id}")

        subtitle = ""
        if self.extract_subtitles:
            try:
                subtitle = self._extract_subtitle(video_info.url)
            except Exception as e:
                logger.warning(f"字幕提取失败 [{video_info.video_id}]: {e}")

        comments: List[Dict[str, Any]] = []
        if self.extract_comments:
            try:
                comments = self._extract_comments(video_info.url, self.max_comments)
            except Exception as e:
                logger.warning(f"评论提取失败 [{video_info.video_id}]: {e}")

        metadata = self._extract_metadata(video_info)

        content = VideoContent(
            video_id=video_info.video_id,
            title=video_info.title,
            subtitle=subtitle,
            comments=comments,
            tags=video_info.tags,
            metadata=metadata,
        )

        logger.info(
            f"提取完成: 字幕={len(subtitle)}字, "
            f"评论={len(comments)}条, 标签={len(content.tags)}个"
        )
        return content

    def _extract_subtitle(self, video_url: str) -> str:
        """
        提取视频字幕（通过视频详情页获取ASR字幕）
        :param video_url: 视频URL
        :return: 字幕文本
        """
        video_id = self._extract_video_id(video_url)
        if not video_id:
            logger.warning(f"无法从URL提取video_id: {video_url}")
            return ""

        params = {
            "device_platform": "webapp",
            "aid": "6383",
            "aweme_id": video_id,
        }

        try:
            resp = self.session.get(
                self.SUBTITLE_URL, params=params, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            aweme = data.get("aweme_detail", {})
            if not aweme:
                return ""

            # 尝试从 video 字段获取字幕
            video_data = aweme.get("video", {})

            # 方式1: 从 caption 获取
            caption = aweme.get("caption", "")
            if caption:
                return caption

            # 方式2: 从字幕URL获取
            subtitle_infos = video_data.get("subtitle_infos", [])
            if subtitle_infos:
                subtitle_url = subtitle_infos[0].get("url", "")
                if subtitle_url:
                    return self._fetch_subtitle_text(subtitle_url)

            # 方式3: 从 desc 获取（视频描述通常包含关键内容）
            desc = aweme.get("desc", "")
            if desc:
                return desc

            return ""

        except requests.RequestException as e:
            logger.error(f"请求字幕数据失败: {e}")
            return ""

    def _fetch_subtitle_text(self, subtitle_url: str) -> str:
        """
        从字幕URL获取字幕文本
        :param subtitle_url: 字幕文件URL
        :return: 字幕文本
        """
        try:
            resp = self.session.get(subtitle_url, timeout=15)
            resp.raise_for_status()

            # 字幕文件可能是JSON格式（SRT JSON）
            try:
                data = resp.json()
                lines = []
                if isinstance(data, list):
                    for item in data:
                        text = item.get("text", "")
                        if text:
                            lines.append(text)
                elif isinstance(data, dict):
                    for item in data.get("utterances", []):
                        text = item.get("text", "")
                        if text:
                            lines.append(text)
                return "\n".join(lines)
            except (json.JSONDecodeError, ValueError):
                # 纯文本格式
                return resp.text

        except requests.RequestException as e:
            logger.error(f"获取字幕文本失败: {e}")
            return ""

    def _extract_comments(
        self, video_url: str, max_comments: int
    ) -> List[Dict[str, Any]]:
        """
        提取视频评论
        :param video_url: 视频URL
        :param max_comments: 最大评论数
        :return: 评论列表
        """
        video_id = self._extract_video_id(video_url)
        if not video_id:
            return []

        comments: List[Dict[str, Any]] = []
        cursor = 0
        page_size = 20

        while len(comments) < max_comments:
            params = {
                "device_platform": "webapp",
                "aid": "6383",
                "aweme_id": video_id,
                "cursor": cursor,
                "count": page_size,
                "item_type": 0,
            }

            try:
                resp = self.session.get(
                    self.COMMENT_URL, params=params, timeout=15
                )
                resp.raise_for_status()
                data = resp.json()

                items = data.get("comments", [])
                if not items:
                    break

                for item in items:
                    comment = {
                        "text": item.get("text", ""),
                        "likes": item.get("digg_count", 0),
                        "author": item.get("user", {}).get("nickname", ""),
                        "create_time": item.get("create_time", 0),
                        "reply_count": item.get("reply_comment_total", 0),
                    }
                    comments.append(comment)

                cursor += page_size
                has_more = data.get("has_more", 0)
                if not has_more:
                    break

            except requests.RequestException as e:
                logger.error(f"请求评论失败: {e}")
                break

        return comments[:max_comments]

    def _extract_metadata(self, video_info: VideoInfo) -> Dict[str, Any]:
        """
        提取视频元数据
        :param video_info: 视频基本信息
        :return: 元数据字典
        """
        return {
            "author": video_info.author,
            "play_count": video_info.play_count,
            "like_count": video_info.like_count,
            "comment_count": video_info.comment_count,
            "share_count": video_info.share_count,
            "create_time": video_info.create_time,
            "engagement_score": video_info.engagement_score,
            "url": video_info.url,
        }

    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        """
        从URL中提取视频ID
        :param url: 视频URL
        :return: 视频ID
        """
        if not url:
            return None

        # 匹配 /video/xxxxx 格式
        match = re.search(r"/video/(\d+)", url)
        if match:
            return match.group(1)

        # 匹配 /note/xxxxx 格式
        match = re.search(r"/note/(\d+)", url)
        if match:
            return match.group(1)

        # 如果URL本身就是数字ID
        if url.isdigit():
            return url

        return None
