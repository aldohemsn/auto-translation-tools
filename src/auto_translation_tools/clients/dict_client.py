"""
词典服务客户端

封装 Dict Reader 服务的查询功能
"""

import os
import httpx
from dataclasses import dataclass
from typing import Optional


@dataclass
class LookupResult:
    """词典查询结果"""
    translation: str      # 译名
    source: str           # 来源词典名称
    database_id: str      # 词典ID
    raw_definition: str   # 原始定义（包含HTML）


class DictClient:
    """词典服务客户端
    
    调用 Dict Reader 服务查询人名、地名等专有名词的翻译。
    
    Example:
        client = DictClient("https://dict-reader-production.up.railway.app")
        result = client.lookup_person("Smith")
        # "史密斯"
    """
    
    DEFAULT_URL = "https://dict-reader-production.up.railway.app"
    DEFAULT_TIMEOUT = 10.0
    
    # 实体类型到词典名称的映射
    ENTITY_TO_DICT = {
        "PERSON": "person",
        "LOCATION": "place",
        "GPE": "place",       # Geo-Political Entity
        "CITY": "place",      # CoreNLP常见类型
        "COUNTRY": "place",
        "STATE_OR_PROVINCE": "place",
    }
    
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None
    ):
        """初始化客户端
        
        Args:
            url: 词典服务地址，默认从 DICT_READER_URL 读取
            api_key: API 认证密钥，默认从 MCP_API_KEY 读取
            timeout: 请求超时时间（秒）
        """
        self.url = url or os.getenv("DICT_READER_URL", self.DEFAULT_URL)
        self.api_key = api_key or os.getenv("MCP_API_KEY", "")
        self.timeout = timeout or float(os.getenv("DICT_READER_TIMEOUT", self.DEFAULT_TIMEOUT))
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        self._client = httpx.Client(timeout=self.timeout, headers=headers)
    
    def lookup(self, word: str, database: str = "*") -> Optional[LookupResult]:
        """查询词条，返回完整结果
        
        Args:
            word: 要查询的词
            database: 词典名称 (person, place, ec_dict, *, etc.)
            
        Returns:
            LookupResult 包含译名和来源，未找到返回 None
        """
        try:
            response = self._client.post(
                f"{self.url}/define",
                json={"word": word, "database": database}
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("found") and result.get("definitions"):
                first_def = result["definitions"][0]
                return LookupResult(
                    translation=first_def.get("definition", ""),
                    source=first_def.get("database_name", first_def.get("database", database)),
                    database_id=first_def.get("database", database),
                    raw_definition=first_def.get("definition", "")
                )
            return None
            
        except httpx.HTTPError as e:
            raise ConnectionError(f"Dict Reader request failed: {e}")
    
    def lookup_person(self, name: str) -> Optional[LookupResult]:
        """查询人名（世界人名翻译大辞典）"""
        return self.lookup(name, "person")
    
    def lookup_place(self, name: str) -> Optional[LookupResult]:
        """查询地名（世界地名翻译大辞典）"""
        return self.lookup(name, "place")
    
    def lookup_general(self, word: str) -> Optional[LookupResult]:
        """查询通用词典（英汉大词典）
        
        用于专项词典未找到时的备选查询
        """
        return self.lookup(word, "ec_dict")
    
    def lookup_by_entity_type(self, name: str, entity_type: str) -> Optional[LookupResult]:
        """根据实体类型查询专项词典
        
        Args:
            name: 名称
            entity_type: NER 实体类型 (PERSON, LOCATION, etc.)
            
        Returns:
            LookupResult，未找到返回 None
        """
        database = self.ENTITY_TO_DICT.get(entity_type, "*")
        return self.lookup(name, database)
    
    def match(self, pattern: str, database: str = "*", strategy: str = "prefix") -> list[dict]:
        """前缀匹配查询
        
        Args:
            pattern: 匹配模式
            database: 词典名称
            strategy: 匹配策略 (prefix, suffix, exact)
            
        Returns:
            匹配结果列表
        """
        try:
            response = self._client.post(
                f"{self.url}/match",
                json={"pattern": pattern, "database": database, "strategy": strategy}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("matches", [])
            
        except httpx.HTTPError as e:
            raise ConnectionError(f"Dict Reader match failed: {e}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = self._client.get(f"{self.url}/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
    
    def close(self):
        """关闭客户端"""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
