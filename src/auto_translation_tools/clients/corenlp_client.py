"""
CoreNLP 客户端

封装 Stanford CoreNLP 服务的 NER（命名实体识别）功能
"""

import os
import httpx
from dataclasses import dataclass


@dataclass
class Entity:
    """命名实体"""
    text: str      # 实体文本
    type: str      # 实体类型 (PERSON, LOCATION, ORGANIZATION, etc.)
    

class CoreNLPClient:
    """CoreNLP NER 客户端
    
    使用 Stanford CoreNLP 服务提取文本中的命名实体。
    
    Example:
        client = CoreNLPClient("https://corenlp-production.up.railway.app")
        entities = client.extract_entities("John Smith visited Paris.")
        # [Entity(text="John Smith", type="PERSON"), Entity(text="Paris", type="LOCATION")]
    """
    
    DEFAULT_URL = "https://corenlp-production-e3ae.up.railway.app"
    DEFAULT_TIMEOUT = 30.0
    
    def __init__(
        self, 
        url: str | None = None, 
        timeout: float | None = None
    ):
        """初始化客户端
        
        Args:
            url: CoreNLP 服务地址，默认从环境变量 CORENLP_URL 读取
            timeout: 请求超时时间（秒）
        """
        self.url = url or os.getenv("CORENLP_URL", self.DEFAULT_URL)
        self.timeout = timeout or float(os.getenv("CORENLP_TIMEOUT", self.DEFAULT_TIMEOUT))
        self._client = httpx.Client(timeout=self.timeout)
    
    def extract_entities(
        self, 
        text: str, 
        language: str = "en",
        entity_types: list[str] | None = None
    ) -> list[Entity]:
        """提取命名实体
        
        Args:
            text: 要分析的文本
            language: 语言代码 ("en" 或 "es")
            entity_types: 要过滤的实体类型，None 表示全部
            
        Returns:
            Entity 列表
        """
        properties = {
            "annotators": "tokenize,ssplit,ner",
            "outputFormat": "json"
        }
        
        if language == "es":
            properties["pipelineLanguage"] = "es"
        
        url = f"{self.url}/?properties={httpx.QueryParams({'properties': str(properties)}).get('properties')}"
        
        # 直接构造正确的 URL
        import json
        props_json = json.dumps(properties)
        url = f"{self.url}/?properties={httpx.URL(props_json)}"
        
        try:
            response = self._client.post(
                self.url,
                params={"properties": json.dumps(properties)},
                content=text.encode("utf-8"),
                headers={"Content-Type": "text/plain; charset=utf-8"}
            )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            raise ConnectionError(f"CoreNLP request failed: {e}")
        
        # 解析 NER 结果，合并连续相同类型的实体
        entities = self._parse_ner(result)
        
        # 过滤实体类型
        if entity_types:
            entities = [e for e in entities if e.type in entity_types]
        
        return entities
    
    def _parse_ner(self, result: dict) -> list[Entity]:
        """解析 CoreNLP NER 结果，合并连续相同类型的 token"""
        entities = []
        
        if not result.get("sentences"):
            return entities
        
        for sentence in result["sentences"]:
            current_entity = None
            
            for token in sentence.get("tokens", []):
                ner_tag = token.get("ner", "O")
                word = token.get("word", "")
                
                if ner_tag != "O":
                    if current_entity and current_entity.type == ner_tag:
                        # 合并连续相同类型
                        current_entity.text += " " + word
                    else:
                        # 保存上一个实体，开始新实体
                        if current_entity:
                            entities.append(current_entity)
                        current_entity = Entity(text=word, type=ner_tag)
                else:
                    # 非实体，保存当前实体
                    if current_entity:
                        entities.append(current_entity)
                        current_entity = None
            
            # 句末检查
            if current_entity:
                entities.append(current_entity)
        
        return entities
    
    def extract_persons_and_locations(self, text: str, language: str = "en") -> list[Entity]:
        """只提取人名和地名
        
        Args:
            text: 要分析的文本
            language: 语言代码
            
        Returns:
            PERSON 和 LOCATION 类型的 Entity 列表
        """
        return self.extract_entities(
            text, 
            language, 
            entity_types=["PERSON", "LOCATION"]
        )
    
    def close(self):
        """关闭客户端"""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
