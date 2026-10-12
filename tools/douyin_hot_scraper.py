#!/usr/bin/env python3
"""
抖音热榜爆款抓取工具
用法: python3 douyin_hot_scraper.py [关键词] [--top 50] [--json]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests


def get_session():
    """创建带基础cookies的session"""
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.douyin.com/",
    }
    
    # 获取基础cookies
    try:
        session.get("https://www.douyin.com/", headers={**headers, "Accept": "text/html"}, timeout=15)
    except Exception:
        pass
    
    # 获取ttwid
    try:
        session.post(
            "https://ttwid.bytedance.com/ttwid/union/register/",
            json={
                "region": "cn",
                "aid": 1768,
                "needFid": False,
                "service": "www.douyin.com",
                "migrate_info": {"ticket": "", "source": "node"},
                "cbUrlProtocol": "https",
                "union": True,
            },
            headers={**headers, "Content-Type": "application/json"},
            timeout=10,
        )
    except Exception:
        pass
    
    return session, headers


def fetch_hot_list(session, headers) -> list[dict]:
    """获取抖音热榜"""
    try:
        resp = session.get(
            "https://www.douyin.com/aweme/v1/web/hot/search/list/",
            headers=headers,
            timeout=15,
        )
        data = resp.json()
        
        word_list = data.get("data", {}).get("word_list", [])
        trending_list = data.get("data", {}).get("trending_list", [])
        
        # 合并去重
        all_items = []
        seen_ids = set()
        
        for item in word_list + trending_list:
            group_id = item.get("group_id", "")
            if group_id and group_id not in seen_ids:
                seen_ids.add(group_id)
                all_items.append(item)
        
        return all_items
    except Exception as e:
        print(f"[ERROR] 获取热榜失败: {e}", file=sys.stderr)
        return []


def filter_by_keyword(items: list[dict], keyword: str) -> list[dict]:
    """按关键词过滤热榜"""
    if not keyword:
        return items
    
    keyword_lower = keyword.lower()
    filtered = []
    
    for item in items:
        word = item.get("word", "").lower()
        if keyword_lower in word or word in keyword_lower:
            filtered.append(item)
    
    return filtered


def format_hot_value(value: int) -> str:
    """格式化热度值"""
    if value >= 10000000:
        return f"{value / 10000000:.1f}千万"
    elif value >= 10000:
        return f"{value / 10000:.1f}万"
    else:
        return str(value)


def format_output(items: list[dict], keyword: str, top_n: int) -> str:
    """格式化为可读报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        "# 🔥 抖音热榜爆款报告",
        "",
        f"**关键词**: {keyword if keyword else '全部热榜'}",
        f"**抓取时间**: {now}",
        f"**结果数**: {len(items)} 条",
        "",
        "---",
        "",
    ]
    
    for idx, item in enumerate(items[:top_n], 1):
        word = item.get("word", "未知话题")
        hot_value = item.get("hot_value", 0)
        position = item.get("position", idx)
        label = item.get("label", 0)
        video_count = item.get("video_count", 0)
        group_id = item.get("group_id", "")
        
        # 标签
        label_map = {1: "🔥 热", 2: "🆕 新", 3: "🏆 推荐"}
        label_str = label_map.get(label, "")
        
        # 热度
        hot_str = format_hot_value(hot_value)
        
        # 链接
        if group_id:
            url = f"https://www.douyin.com/hot/{group_id}"
        else:
            url = "N/A"
        
        lines.extend([
            f"### #{position} {word} {label_str}",
            f"- 🔥 热度: {hot_str}",
            f"- 🎬 相关视频: {video_count} 个",
            f"- 🔗 链接: {url}",
            "",
        ])
    
    # 总结
    lines.extend([
        "---",
        "",
        "## 💡 使用建议",
        "",
        "1. **蹭热点**: 选择与你的领域相关的热搜话题创作内容",
        "2. **看趋势**: 关注热度上升快的话题，提前布局",
        "3. **避竞争**: 避开头部大V已经占据的话题，找细分角度",
        "",
    ])
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="抖音热榜爆款抓取")
    parser.add_argument("keyword", nargs="?", default="", help="过滤关键词 (可选)")
    parser.add_argument("--top", type=int, default=50, help="显示前N条 (默认50)")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--output", "-o", help="输出文件路径")
    args = parser.parse_args()
    
    print("[INFO] 正在获取抖音热榜...", file=sys.stderr)
    session, headers = get_session()
    items = fetch_hot_list(session, headers)
    
    if not items:
        print("[ERROR] 未获取到热榜数据", file=sys.stderr)
        sys.exit(1)
    
    print(f"[INFO] 获取到 {len(items)} 条热搜", file=sys.stderr)
    
    # 关键词过滤
    if args.keyword:
        items = filter_by_keyword(items, args.keyword)
        print(f"[INFO] 关键词 '{args.keyword}' 匹配 {len(items)} 条", file=sys.stderr)
    
    # 按热度排序
    items.sort(key=lambda x: x.get("hot_value", 0), reverse=True)
    
    # 输出
    if args.json:
        output = json.dumps(items[:args.top], ensure_ascii=False, indent=2)
    else:
        output = format_output(items, args.keyword, args.top)
    
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"[INFO] 结果已保存到 {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
