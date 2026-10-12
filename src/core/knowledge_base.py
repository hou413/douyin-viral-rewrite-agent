"""
爆款知识库
存储爆款案例、脚本模板、实验记录、账号历史数据
使用JSON文件存储，支持CRUD操作
"""

import json
import os
import logging
from typing import List, Optional, Dict
from datetime import datetime

from src.core.models import KnowledgeEntry

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """爆款知识库 - 管理所有知识条目"""
    
    def __init__(self, base_dir: str = "data/knowledge_base"):
        self.base_dir = base_dir
        self._ensure_dirs()
        self._cache: Dict[str, List[KnowledgeEntry]] = {}
        self._load_all()
    
    def _ensure_dirs(self):
        """确保存储目录存在"""
        os.makedirs(self.base_dir, exist_ok=True)
    
    def _file_path(self, category: str) -> str:
        """获取分类对应的文件路径"""
        file_map = {
            "case": "hot_cases.json",
            "template": "script_templates.json",
            "experiment": "experiment_log.json",
            "performance": "performance_history.json"
        }
        filename = file_map.get(category, f"{category}.json")
        return os.path.join(self.base_dir, filename)
    
    def _load_all(self):
        """加载所有知识库数据"""
        for category in ["case", "template", "experiment", "performance"]:
            filepath = self._file_path(category)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._cache[category] = [
                        KnowledgeEntry.from_dict(entry) for entry in data
                    ]
                    logger.info(f"加载 {category} 知识库: {len(self._cache[category])} 条")
                except Exception as e:
                    logger.error(f"加载 {category} 知识库失败: {e}")
                    self._cache[category] = []
            else:
                self._cache[category] = []
    
    def _save(self, category: str):
        """保存指定分类到文件"""
        filepath = self._file_path(category)
        entries = self._cache.get(category, [])
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    [entry.to_dict() for entry in entries],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            logger.info(f"保存 {category} 知识库: {len(entries)} 条")
        except Exception as e:
            logger.error(f"保存 {category} 知识库失败: {e}")
    
    # ========== CRUD 操作 ==========
    
    def add(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """添加知识条目"""
        category = entry.entry_type
        if category not in self._cache:
            self._cache[category] = []
        self._cache[category].append(entry)
        self._save(category)
        logger.info(f"添加知识条目: {entry.title} (ID: {entry.id})")
        return entry
    
    def get(self, entry_id: str, entry_type: str) -> Optional[KnowledgeEntry]:
        """获取指定知识条目"""
        entries = self._cache.get(entry_type, [])
        for entry in entries:
            if entry.id == entry_id:
                return entry
        return None
    
    def list_all(self, entry_type: str, tags: Optional[List[str]] = None) -> List[KnowledgeEntry]:
        """列出指定类型的所有条目，可按标签过滤"""
        entries = self._cache.get(entry_type, [])
        if tags:
            entries = [e for e in entries if any(t in e.tags for t in tags)]
        return entries
    
    def update(self, entry_id: str, entry_type: str, updates: Dict) -> Optional[KnowledgeEntry]:
        """更新知识条目"""
        entries = self._cache.get(entry_type, [])
        for i, entry in enumerate(entries):
            if entry.id == entry_id:
                # 更新字段
                for key, value in updates.items():
                    if hasattr(entry, key):
                        setattr(entry, key, value)
                entry.updated_at = datetime.now()
                self._save(entry_type)
                logger.info(f"更新知识条目: {entry_id}")
                return entry
        return None
    
    def delete(self, entry_id: str, entry_type: str) -> bool:
        """删除知识条目"""
        entries = self._cache.get(entry_type, [])
        original_len = len(entries)
        self._cache[entry_type] = [e for e in entries if e.id != entry_id]
        if len(self._cache[entry_type]) < original_len:
            self._save(entry_type)
            logger.info(f"删除知识条目: {entry_id}")
            return True
        return False
    
    def increment_usage(self, entry_id: str, entry_type: str):
        """增加使用次数"""
        entries = self._cache.get(entry_type, [])
        for entry in entries:
            if entry.id == entry_id:
                entry.usage_count += 1
                self._save(entry_type)
                break
    
    def update_success_rate(self, entry_id: str, entry_type: str, new_rate: float, alpha: float = 0.3):
        """
        更新成功率（指数移动平均）
        alpha: 新数据的权重
        """
        entries = self._cache.get(entry_type, [])
        for entry in entries:
            if entry.id == entry_id:
                if entry.success_rate is None:
                    entry.success_rate = new_rate
                else:
                    entry.success_rate = alpha * new_rate + (1 - alpha) * entry.success_rate
                entry.updated_at = datetime.now()
                self._save(entry_type)
                logger.info(f"更新成功率: {entry_id} -> {entry.success_rate:.2f}")
                break
    
    # ========== 高级查询 ==========
    
    def search_by_tags(self, tags: List[str], entry_type: Optional[str] = None) -> List[KnowledgeEntry]:
        """按标签搜索"""
        results = []
        types_to_search = [entry_type] if entry_type else self._cache.keys()
        for t in types_to_search:
            entries = self._cache.get(t, [])
            for entry in entries:
                if any(tag in entry.tags for tag in tags):
                    results.append(entry)
        return results
    
    def get_top_performers(self, entry_type: str, min_success_rate: float = 0.7, limit: int = 10) -> List[KnowledgeEntry]:
        """获取表现最好的条目"""
        entries = self._cache.get(entry_type, [])
        filtered = [e for e in entries if e.success_rate and e.success_rate >= min_success_rate]
        return sorted(filtered, key=lambda e: e.success_rate, reverse=True)[:limit]
    
    def get_templates_for_scenario(self, scenario: str) -> List[KnowledgeEntry]:
        """获取适用于某场景的模板"""
        templates = self._cache.get("template", [])
        results = []
        for t in templates:
            content = t.content
            if "applicable_scenarios" in content:
                if scenario in content["applicable_scenarios"]:
                    results.append(t)
        return sorted(results, key=lambda e: e.success_rate or 0, reverse=True)
    
    # ========== 统计 ==========
    
    def stats(self) -> Dict:
        """知识库统计信息"""
        result = {}
        for category, entries in self._cache.items():
            result[category] = {
                "total": len(entries),
                "with_success_rate": sum(1 for e in entries if e.success_rate is not None),
                "avg_success_rate": self._avg_success_rate(entries),
                "total_usage": sum(e.usage_count for e in entries)
            }
        return result
    
    def _avg_success_rate(self, entries: List[KnowledgeEntry]) -> Optional[float]:
        """计算平均成功率"""
        rates = [e.success_rate for e in entries if e.success_rate is not None]
        return sum(rates) / len(rates) if rates else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== 知识库测试 ===\n")
    
    # 初始化知识库
    kb = KnowledgeBase(base_dir="data/knowledge_base")
    
    # 添加爆款案例
    case = KnowledgeEntry(
        id="case_001",
        entry_type="case",
        title="人形机器人进入家庭 - 爆款案例",
        content={
            "metrics": {"views": 1000000, "likes": 50000, "shares": 10000},
            "viral_mechanism": {
                "hook_type": "冲突型",
                "emotion": "好奇+焦虑",
                "conflict_point": "技术理想vs现实局限"
            },
            "script_structure": {
                "opening": "你以为机器人管家已经很厉害了？其实...",
                "pain_point": "实际使用中的各种问题",
                "twist": "但有一个功能真的改变了我的生活",
                "cta": "关注我，看更多真实测评"
            }
        },
        tags=["机器人", "科技", "智能家居"],
        success_rate=0.85,
        usage_count=5
    )
    kb.add(case)
    
    # 添加脚本模板
    template = KnowledgeEntry(
        id="template_001",
        entry_type="template",
        title="技术科普-冲突型模板",
        content={
            "structure": {
                "opening_pattern": "冲突型钩子",
                "opening_variants": [
                    "你以为XX是这样？其实...",
                    "99%的人都误解了XX",
                    "XX的真相可能让你失望"
                ],
                "middle_pattern": "痛点+解决方案",
                "ending_pattern": "CTA+悬念"
            },
            "applicable_scenarios": ["技术误解", "行业真相"]
        },
        tags=["科普", "冲突型"],
        success_rate=0.75,
        usage_count=12
    )
    kb.add(template)
    
    # 查询
    print("\n--- 按标签搜索 ---")
    results = kb.search_by_tags(["机器人"])
    for r in results:
        print(f"  找到: {r.title}")
    
    print("\n--- 获取最佳模板 ---")
    top = kb.get_top_performers("template", min_success_rate=0.7)
    for t in top:
        print(f"  模板: {t.title}, 成功率: {t.success_rate}")
    
    print("\n--- 知识库统计 ---")
    stats = kb.stats()
    for category, info in stats.items():
        print(f"  {category}: {info['total']} 条, 平均成功率: {info['avg_success_rate']}")
    
    print("\n✅ 知识库测试通过")
