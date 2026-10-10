"""
爆款筛选模块
根据互动数据阈值筛选爆款视频，并基于标题相似度去重
"""

import logging
from typing import List, Dict, Any
from difflib import SequenceMatcher

try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

from ..collectors.douyin_collector import VideoInfo

logger = logging.getLogger(__name__)


class ViralFilter:
    """爆款视频筛选器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化筛选器
        :param config: 筛选配置
        """
        self.min_play_count: int = config.get("min_play_count", 100_000)
        self.min_like_count: int = config.get("min_like_count", 10_000)
        self.min_comment_count: int = config.get("min_comment_count", 500)
        self.dedup_threshold: float = config.get("dedup_similarity_threshold", 0.85)
        
        logger.info(
            f"筛选器初始化: 播放>={self.min_play_count}, "
            f"点赞>={self.min_like_count}, 评论>={self.min_comment_count}, "
            f"去重阈值={self.dedup_threshold}"
        )

    def filter_videos(
        self,
        videos: List[VideoInfo],
        keywords: List[str] = None
    ) -> List[VideoInfo]:
        """
        筛选爆款视频
        :param videos: 原始视频列表
        :param keywords: 关键词列表（可选，用于相关性过滤）
        :return: 筛选后的视频列表
        """
        logger.info(f"开始筛选，输入视频数: {len(videos)}")
        
        # 第一步：阈值筛选
        threshold_passed = [v for v in videos if self._check_threshold(v)]
        logger.info(f"阈值筛选通过: {len(threshold_passed)} 条")
        
        # 第二步：关键词相关性过滤（如果提供了关键词）
        if keywords:
            relevant = []
            for v in threshold_passed:
                text = f"{v.title} {' '.join(v.tags)}".lower()
                if any(kw.lower() in text for kw in keywords):
                    relevant.append(v)
            threshold_passed = relevant
            logger.info(f"关键词相关性筛选后: {len(threshold_passed)} 条")
        
        # 第三步：去重
        deduplicated = self._deduplicate(threshold_passed)
        logger.info(f"去重后: {len(deduplicated)} 条")
        
        # 按综合互动分数排序
        deduplicated.sort(key=lambda v: v.engagement_score, reverse=True)
        
        return deduplicated

    def _check_threshold(self, video: VideoInfo) -> bool:
        """
        检查视频是否达到爆款阈值
        :param video: 视频信息
        :return: 是否达标
        """
        if video.play_count < self.min_play_count:
            return False
        if video.like_count < self.min_like_count:
            return False
        if video.comment_count < self.min_comment_count:
            return False
        return True

    def _deduplicate(self, videos: List[VideoInfo]) -> List[VideoInfo]:
        """
        基于标题相似度去重
        使用SequenceMatcher计算标题相似度，超过阈值的只保留互动分数最高的
        :param videos: 视频列表
        :return: 去重后的视频列表
        """
        if not videos:
            return []
        
        unique: List[VideoInfo] = []
        
        for video in videos:
            is_dup = False
            for existing in unique:
                sim = self._title_similarity(video.title, existing.title)
                if sim >= self.dedup_threshold:
                    is_dup = True
                    # 保留互动分数更高的
                    if video.engagement_score > existing.engagement_score:
                        unique.remove(existing)
                        unique.append(video)
                    break
            
            if not is_dup:
                unique.append(video)
        
        return unique

    def _title_similarity(self, title1: str, title2: str) -> float:
        """
        计算两个标题的相似度
        如果安装了jieba，使用分词后计算；否则直接用SequenceMatcher
        :param title1: 标题1
        :param title2: 标题2
        :return: 相似度 0-1
        """
        if not title1 or not title2:
            return 0.0
        
        if HAS_JIEBA:
            tokens1 = set(jieba.cut(title1))
            tokens2 = set(jieba.cut(title2))
            # 去除停用词和空白
            tokens1 = {t.strip() for t in tokens1 if t.strip()}
            tokens2 = {t.strip() for t in tokens2 if t.strip()}
            
            if not tokens1 or not tokens2:
                return SequenceMatcher(None, title1, title2).ratio()
            
            intersection = tokens1 & tokens2
            union = tokens1 | tokens2
            return len(intersection) / len(union) if union else 0.0
        else:
            return SequenceMatcher(None, title1, title2).ratio()
