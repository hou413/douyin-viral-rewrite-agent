#!/usr/bin/env python3
"""
K12小学英语爆款内容工具 - 后端服务
运行: python3 server.py
访问: http://localhost:8000
"""

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.error

# API 配置
API_KEY = os.getenv("OPENAI_API_KEY", "sk-sp-9b83a216b0f2452d8f1949ff5bbf3dd2")
API_BASE = "https://coding.dashscope.aliyuncs.com/v1"
MODEL = "qwen3.7-plus"

# 抖音热榜 API（公开接口）
DOUYIN_HOT_API = "https://www.douyin.com/aweme/v1/web/hot/search/list/"


def call_ai(messages, temperature=0.8, max_tokens=2000):
    """通用 AI 调用"""
    api_url = f"{API_BASE}/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    payload = {
        'model': MODEL,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens
    }
    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode('utf-8'))
        return result['choices'][0]['message']['content']


def fetch_douyin_hot():
    """抓取抖音热榜"""
    try:
        # 方案1：尝试抖音官方热榜 API
        req = urllib.request.Request(
            DOUYIN_HOT_API,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.douyin.com/',
                'Accept': 'application/json'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            word_list = data.get('data', {}).get('word_list', [])
            if word_list:
                return [{
                    'word': item.get('word', ''),
                    'hot_value': item.get('hot_value', 0),
                    'event_time': item.get('event_time', ''),
                    'label': item.get('label', 0)
                } for item in word_list[:50]]
    except Exception as e:
        print(f"抖音热榜API失败: {e}")

    # 方案2：降级到第三方热榜聚合 API
    try:
        req = urllib.request.Request(
            "https://api.vvhan.com/api/hotlist/douyinHot",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('success'):
                return [{
                    'word': item.get('title', ''),
                    'hot_value': item.get('hot', 0),
                    'url': item.get('url', '')
                } for item in data.get('data', [])[:50]]
    except Exception as e:
        print(f"第三方热榜API也失败: {e}")

    # 方案3：再试一个备用
    try:
        req = urllib.request.Request(
            "https://api.pearktrue.cn/api/dailyhot/?type=douyin&num=50",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('code') == 200:
                return [{
                    'word': item.get('title', ''),
                    'hot_value': item.get('hot', 0),
                } for item in data.get('data', [])[:50]]
    except Exception as e:
        print(f"备用热榜API也失败: {e}")

    return []


def ai_select_topics(hot_list):
    """AI 从热榜中筛选 K12 小学英语相关选题"""
    hot_text = "\n".join([f"{i+1}. {item['word']}（热度：{item.get('hot_value', '未知')}）" for i, item in enumerate(hot_list)])

    prompt = f"""你是一个K12小学英语赛道的抖音内容策划专家。

以下是当前抖音热榜（{len(hot_list)}条）：
{hot_text}

请从热榜中筛选出与以下领域相关的选题：
- 小学教育（1-6年级）
- 英语学习（少儿英语、英语启蒙、自然拼读、绘本阅读等）
- 亲子教育（家长关心的教育话题）
- 儿童成长（学习方法、习惯养成等）
- 教育热点（政策变化、考试动态等）

即使热榜中没有直接相关的，也要找到能「蹭热点」关联到K12英语的角度。比如：
- 热门话题 + 英语元素（如热门电影+英语配音）
- 教育焦虑 + 解决方案
- 亲子互动 + 英语启蒙

请选出5个最有爆款潜力的选题，严格按JSON格式返回：
{{
    "topics": [
        {{
            "title": "选题标题（结合热点+K12英语）",
            "score": 85,
            "hotValue": "热度值",
            "category": "分类（教育/亲子/热点关联）",
            "angle": "具体的内容切入角度，50字以内",
            "audience": "目标受众描述",
            "suggestedTitles": ["参考标题1", "参考标题2", "参考标题3"]
        }}
    ]
}}

注意：score 范围 60-95，综合考虑热度、相关性、传播潜力。"""

    messages = [
        {
            'role': 'system',
            'content': '你是K12小学英语赛道的抖音内容策划专家，擅长从热点中发现与教育相关的爆款选题。'
        },
        {'role': 'user', 'content': prompt}
    ]

    content = call_ai(messages, temperature=0.7, max_tokens=3000)
    result = json.loads(content)
    return result.get('topics', [])


class RewriteHandler(SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """静态文件服务"""
        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            request_data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except:
            request_data = {}

        if self.path == '/api/rewrite':
            self.handle_rewrite(request_data)
        elif self.path == '/api/topics':
            self.handle_topics(request_data)
        else:
            self.send_response(404)
            self.end_headers()

    def handle_rewrite(self, request_data):
        """处理改写请求"""
        original = request_data.get('original', '')
        version_count = request_data.get('versionCount', 6)

        rewritten_versions = self.call_ai_rewrite(original, version_count)

        response = {'success': True, 'versions': rewritten_versions}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

    def handle_topics(self, request_data):
        """处理选题请求"""
        count = request_data.get('count', 5)

        try:
            # 1. 抓取热榜
            print("📡 正在抓取抖音热榜...")
            hot_list = fetch_douyin_hot()

            if not hot_list:
                response = {
                    'success': True,
                    'topics': self.get_fallback_topics()
                }
            else:
                print(f"✅ 获取到 {len(hot_list)} 条热榜")
                # 2. AI 筛选
                print("🤖 AI 正在筛选K12英语相关选题...")
                topics = ai_select_topics(hot_list)
                response = {'success': True, 'topics': topics[:count]}

        except Exception as e:
            print(f"❌ 选题失败: {e}")
            response = {
                'success': True,
                'topics': self.get_fallback_topics()
            }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

    def get_fallback_topics(self):
        """降级：AI 直接生成 K12 英语选题（不依赖热榜）"""
        try:
            prompt = """你是K12小学英语赛道的抖音内容策划专家。

请结合当前教育热点和抖音传播规律，直接生成5个今日K12小学英语赛道的爆款选题。

要求：
- 覆盖不同受众（家长、老师、学生）
- 包含实用干货、情感共鸣、热点关联等不同类型
- 每个选题要有具体的切入角度和参考标题

严格按JSON格式返回：
{
    "topics": [
        {
            "title": "选题标题",
            "score": 85,
            "hotValue": "预估热度",
            "category": "分类",
            "angle": "内容切入角度，50字以内",
            "audience": "目标受众",
            "suggestedTitles": ["参考标题1", "参考标题2", "参考标题3"]
        }
    ]
}"""
            messages = [
                {'role': 'system', 'content': '你是K12小学英语赛道的抖音内容策划专家。'},
                {'role': 'user', 'content': prompt}
            ]
            content = call_ai(messages, temperature=0.8, max_tokens=3000)
            result = json.loads(content)
            return result.get('topics', [])
        except:
            return []

    def call_ai_rewrite(self, original_text, version_count):
        """K12 小学英语赛道改写"""
        versions = []

        for i in range(version_count):
            prompt = f"""请改写以下K12小学英语赛道的抖音短视频脚本，目的是防止被抖音识别为重复内容。

改写要求：
1. 保留核心教育信息和结构
2. 替换同义词、调整句式
3. 改变开头表达方式
4. 保持面向家长/学生的口语化风格
5. 确保改写后仍然通顺自然
6. 至少改动5处以上
7. 注意教育赛道合规，不使用焦虑营销和虚假承诺用语

原文：
{original_text}

请严格按JSON格式返回（不要包含其他内容）：
{{
    "rewritten": "<改写后的完整脚本>",
    "changes": ["改动1", "改动2", "改动3", "改动4", "改动5"]
}}"""

            try:
                content = call_ai([
                    {
                        'role': 'system',
                        'content': '你是K12小学英语赛道的抖音爆款脚本改写专家，擅长在保留核心教育价值的同时，通过同义词替换、句式调整等方式改写脚本，防止被识别为重复内容。熟悉教育赛道合规要求。'
                    },
                    {'role': 'user', 'content': prompt}
                ], temperature=0.8)

                ai_result = json.loads(content)
                versions.append({
                    'version': i + 1,
                    'rewritten': ai_result.get('rewritten', ''),
                    'changes': ai_result.get('changes', []),
                    'isQualified': len(ai_result.get('changes', [])) >= 3
                })
            except Exception as e:
                print(f"AI 调用失败: {e}")
                versions.append({
                    'version': i + 1,
                    'rewritten': original_text,
                    'changes': ['AI 调用失败，使用原文'],
                    'isQualified': False
                })

        return versions


def run_server(port=8000):
    server = HTTPServer(('localhost', port), RewriteHandler)
    print(f"🚀 K12小学英语内容工具已启动: http://localhost:{port}")
    print(f"📝 API 端点:")
    print(f"   - /api/rewrite  爆款改写")
    print(f"   - /api/topics   全网选题")
    print(f"🤖 使用模型: {MODEL}")
    print(f"按 Ctrl+C 停止服务器")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        server.server_close()


if __name__ == '__main__':
    run_server()
