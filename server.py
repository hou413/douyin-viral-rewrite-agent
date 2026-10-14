#!/usr/bin/env python3
"""
本地后端服务 - 代理 AI 改写请求
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


class RewriteHandler(SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """处理改写请求"""
        if self.path == '/api/rewrite':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                request_data = json.loads(post_data.decode('utf-8'))
                original = request_data.get('original', '')
                version_count = request_data.get('versionCount', 6)
                style = request_data.get('style', '口播')
                
                # 调用 AI 改写
                rewritten_versions = self.call_ai_rewrite(original, version_count, style)
                
                # 返回结果
                response = {
                    'success': True,
                    'versions': rewritten_versions
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                error_response = {
                    'success': False,
                    'error': str(e)
                }
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def call_ai_rewrite(self, original_text, version_count, style='口播'):
        """调用 AI 模型进行改写"""
        versions = []
        
        style_descriptions = {
            '口播': '直接有力，适合真人出镜口播，语气坚定有感染力',
            '故事': '情感共鸣，用故事线叙事，有起承转合',
            '干货': '信息密集，条理清晰，适合知识分享',
            '搞笑': '轻松幽默，用段子和梗，适合泛娱乐',
            '悬念': '制造好奇，先抛问题再解答，适合引流转化'
        }
        style_desc = style_descriptions.get(style, style_descriptions['口播'])
        
        for i in range(version_count):
            prompt = f"""请改写以下抖音短视频脚本，目的是防止被抖音识别为重复内容。

改写风格要求：{style} - {style_desc}

改写要求：
1. 保留核心信息和结构
2. 替换同义词、调整句式
3. 改变开头表达方式
4. 保持{style}风格的口语化表达
5. 确保改写后仍然通顺自然
6. 至少改动5处以上
7. 符合「{style_desc}」的风格特点

原文：
{original_text}

请严格按JSON格式返回（不要包含其他内容）：
{{
    "rewritten": "<改写后的完整脚本>",
    "changes": ["改动1", "改动2", "改动3", "改动4", "改动5"]
}}"""
            
            # 调用 API
            api_url = f"{API_BASE}/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {API_KEY}'
            }
            
            payload = {
                'model': MODEL,
                'messages': [
                    {
                        'role': 'system',
                        'content': '你是抖音爆款脚本改写专家，擅长在保留核心信息的同时，通过同义词替换、句式调整等方式改写脚本，防止被识别为重复内容。'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.8,
                'max_tokens': 2000
            }
            
            try:
                req = urllib.request.Request(
                    api_url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers,
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    content = result['choices'][0]['message']['content']
                    
                    # 解析 JSON
                    ai_result = json.loads(content)
                    
                    versions.append({
                        'version': i + 1,
                        'rewritten': ai_result.get('rewritten', ''),
                        'changes': ai_result.get('changes', []),
                        'isQualified': len(ai_result.get('changes', [])) >= 3
                    })
                    
            except Exception as e:
                print(f"AI 调用失败: {e}")
                # 降级为规则改写
                versions.append({
                    'version': i + 1,
                    'rewritten': original_text,
                    'changes': ['AI 调用失败，使用原文'],
                    'isQualified': False
                })
        
        return versions


def run_server(port=8000):
    """启动服务器"""
    server = HTTPServer(('localhost', port), RewriteHandler)
    print(f"🚀 服务器已启动: http://localhost:{port}")
    print(f"📝 API 端点: /api/rewrite")
    print(f"🤖 使用模型: {MODEL}")
    print(f"按 Ctrl+C 停止服务器")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        server.server_close()


if __name__ == '__main__':
    run_server()
