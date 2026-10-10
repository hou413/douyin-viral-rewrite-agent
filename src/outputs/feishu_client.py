"""
飞书API客户端模块
实现飞书开放平台API调用，支持多维表格和文档操作
"""

import time
import logging
from typing import List, Dict, Any

import requests

logger = logging.getLogger(__name__)


class FeishuClient:
    """飞书开放平台API客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"
    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

    def __init__(self, app_id: str, app_secret: str):
        """
        初始化飞书客户端
        :param app_id: 应用ID
        :param app_secret: 应用密钥
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str = ""
        self._token_expires: float = 0
        
        if not app_id or not app_secret:
            logger.warning("飞书 app_id 或 app_secret 未配置")
        
        logger.info("飞书客户端初始化完成")

    def get_tenant_access_token(self) -> str:
        """
        获取 tenant_access_token
        :return: token字符串
        """
        # 如果token未过期，直接返回
        if self._token and time.time() < self._token_expires:
            return self._token
        
        if not self.app_id or not self.app_secret:
            raise ValueError("飞书 app_id 或 app_secret 未配置")
        
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }
        
        try:
            resp = requests.post(self.TOKEN_URL, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") != 0:
                raise Exception(f"获取token失败: {data.get('msg', '未知错误')}")
            
            self._token = data["tenant_access_token"]
            # token有效期通常为2小时，提前5分钟刷新
            self._token_expires = time.time() + data.get("expire", 7200) - 300
            
            logger.info("飞书token获取成功")
            return self._token
            
        except requests.RequestException as e:
            logger.error(f"获取飞书token失败: {e}")
            raise

    def _get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        token = self.get_tenant_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def write_to_bitable(
        self,
        app_token: str,
        table_id: str,
        records: List[Dict[str, Any]]
    ) -> bool:
        """
        写入多维表格
        :param app_token: 多维表格app_token
        :param table_id: 数据表ID
        :param records: 记录列表，每条记录为字段名到值的映射
        :return: 是否成功
        """
        if not app_token or not table_id:
            logger.error("多维表格 app_token 或 table_id 未配置")
            return False
        
        url = f"{self.BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
        
        # 构建请求体
        body_records = []
        for record in records:
            fields = {}
            for key, value in record.items():
                # 飞书多维表格字段值处理
                if isinstance(value, list):
                    fields[key] = value
                elif isinstance(value, dict):
                    fields[key] = str(value)
                else:
                    fields[key] = value
            body_records.append({"fields": fields})
        
        payload = {"records": body_records}
        
        try:
            resp = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") != 0:
                logger.error(f"写入多维表格失败: {data.get('msg')}")
                return False
            
            logger.info(f"成功写入 {len(records)} 条记录到多维表格")
            return True
            
        except requests.RequestException as e:
            logger.error(f"写入多维表格失败: {e}")
            return False

    def create_document(
        self,
        folder_token: str,
        title: str,
        content: str
    ) -> str:
        """
        创建飞书文档
        :param folder_token: 文件夹token
        :param title: 文档标题
        :param content: 文档内容（Markdown格式）
        :return: 文档URL，失败返回空字符串
        """
        if not folder_token:
            logger.error("飞书文件夹token未配置")
            return ""
        
        # 第一步：创建文档
        create_url = f"{self.BASE_URL}/docx/v1/documents"
        
        payload = {
            "folder_token": folder_token,
            "title": title,
        }
        
        try:
            resp = requests.post(
                create_url,
                headers=self._get_headers(),
                json=payload,
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") != 0:
                logger.error(f"创建文档失败: {data.get('msg')}")
                return ""
            
            document_id = data.get("data", {}).get("document", {}).get("document_id", "")
            if not document_id:
                logger.error("创建文档成功但未返回document_id")
                return ""
            
            # 第二步：写入内容（将Markdown转为飞书块格式）
            if content:
                self._write_document_content(document_id, content)
            
            doc_url = f"https://open.feishu.cn/docx/{document_id}"
            logger.info(f"飞书文档创建成功: {doc_url}")
            return doc_url
            
        except requests.RequestException as e:
            logger.error(f"创建飞书文档失败: {e}")
            return ""

    def _write_document_content(self, document_id: str, content: str) -> bool:
        """
        向文档写入内容
        :param document_id: 文档ID
        :param content: Markdown内容
        :return: 是否成功
        """
        # 获取文档根block_id
        get_url = f"{self.BASE_URL}/docx/v1/documents/{document_id}"
        
        try:
            resp = requests.get(get_url, headers=self._get_headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") != 0:
                return False
            
            # 将Markdown内容转换为飞书文本块
            blocks = self._markdown_to_blocks(content)
            
            if not blocks:
                return True
            
            # 批量创建块
            batch_url = f"{self.BASE_URL}/docx/v1/documents/{document_id}/blocks/{document_id}/children"
            
            payload = {
                "children": blocks,
                "index": 0,
            }
            
            resp = requests.post(
                batch_url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            
            if result.get("code") != 0:
                logger.error(f"写入文档内容失败: {result.get('msg')}")
                return False
            
            logger.info(f"文档内容写入成功，共 {len(blocks)} 个块")
            return True
            
        except requests.RequestException as e:
            logger.error(f"写入文档内容失败: {e}")
            return False

    def _markdown_to_blocks(self, content: str) -> List[Dict[str, Any]]:
        """
        将Markdown内容转换为飞书文档块格式
        :param content: Markdown内容
        :return: 飞书块列表
        """
        blocks: List[Dict[str, Any]] = []
        lines = content.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 标题
            if line.startswith("# "):
                blocks.append({
                    "block_type": 3,  # heading1
                    "heading1": {
                        "elements": [{"text_run": {"content": line[2:]}}]
                    }
                })
            elif line.startswith("## "):
                blocks.append({
                    "block_type": 4,  # heading2
                    "heading2": {
                        "elements": [{"text_run": {"content": line[3:]}}]
                    }
                })
            elif line.startswith("### "):
                blocks.append({
                    "block_type": 5,  # heading3
                    "heading3": {
                        "elements": [{"text_run": {"content": line[4:]}}]
                    }
                })
            # 列表
            elif line.startswith("- ") or line.startswith("* "):
                blocks.append({
                    "block_type": 12,  # bullet
                    "bullet": {
                        "elements": [{"text_run": {"content": line[2:]}}]
                    }
                })
            # 有序列表
            elif len(line) > 2 and line[0].isdigit() and ". " in line[:5]:
                text = line.split(". ", 1)[1] if ". " in line else line
                blocks.append({
                    "block_type": 13,  # ordered
                    "ordered": {
                        "elements": [{"text_run": {"content": text}}]
                    }
                })
            # 普通文本
            else:
                blocks.append({
                    "block_type": 2,  # text
                    "text": {
                        "elements": [{"text_run": {"content": line}}]
                    }
                })
        
        return blocks
