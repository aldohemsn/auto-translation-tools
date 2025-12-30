"""
工具一：专名提取翻译器

使用 CoreNLP NER 提取人名和地名，通过词典服务查询中文译名，
生成 TSV 格式译名表。
"""

import os
from typing import Optional

from ..base import BaseTool, ToolRegistry, TranslationResult
from ..clients.corenlp_client import CoreNLPClient
from ..clients.dict_client import DictClient


class NameExtractor(BaseTool):
    """专名提取翻译器
    
    工作流程：
    1. 调用 CoreNLP 提取 PERSON 和 LOCATION 实体
    2. 对每个实体调用词典服务查询中文译名
    3. 记录未找到译名的实体（可后续使用 GeminiCaller 翻译）
    4. 生成 TSV 格式译名表
    
    Example:
        extractor = NameExtractor()
        result = extractor.extract_and_translate("John Smith visited Paris.")
        result.to_tsv("translations.tsv")
        
        # 查看未找到的实体
        print(result.not_found)
    """
    
    name = "name_extractor"
    description = "使用 NER 提取人名和地名，通过词典服务查询译名"
    
    def __init__(
        self,
        corenlp_url: str | None = None,
        dict_url: str | None = None,
        api_key: str | None = None
    ):
        """初始化
        
        Args:
            corenlp_url: CoreNLP 服务地址
            dict_url: 词典服务地址
            api_key: 词典服务 API Key
        """
        self.corenlp = CoreNLPClient(url=corenlp_url)
        self.dict_client = DictClient(url=dict_url, api_key=api_key)
    
    def extract_and_translate(
        self, 
        text: str, 
        language: str = "en"
    ) -> TranslationResult:
        """提取并翻译专有名词
        
        Args:
            text: 要处理的文本
            language: 语言代码 ("en" 或 "es")
            
        Returns:
            TranslationResult 包含已翻译和未翻译的实体
        """
        result = TranslationResult()
        
        # 1. 提取人名和地名
        entities = self.corenlp.extract_persons_and_locations(text, language)
        
        # 2. 去重（保留第一次出现）
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity.text.lower(), entity.type)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        # 3. 查询词典
        for entity in unique_entities:
            translation = self._lookup_with_fallback(entity.text, entity.type)
            
            if translation:
                result.found.append({
                    "text": entity.text,
                    "type": entity.type,
                    "translation": translation,
                    "source": "词典"
                })
            else:
                result.not_found.append({
                    "text": entity.text,
                    "type": entity.type
                })
        
        return result
    
    def _lookup_with_fallback(self, text: str, entity_type: str) -> str | None:
        """查询词典，支持回退策略
        
        对于人名：先查全名，找不到则查姓氏
        """
        # 标准化实体类型（CITY -> LOCATION 等）
        normalized_type = self._normalize_entity_type(entity_type)
        
        # 直接查询
        translation = self.dict_client.lookup_by_entity_type(text, normalized_type)
        if translation:
            return self._clean_translation(translation)
        
        # 人名回退：尝试查询姓氏（假设最后一个词是姓）
        if normalized_type == "PERSON" and " " in text:
            parts = text.split()
            last_name = parts[-1]  # 姓氏通常在最后
            translation = self.dict_client.lookup_person(last_name)
            if translation:
                return self._clean_translation(translation)
        
        return None
    
    def _normalize_entity_type(self, entity_type: str) -> str:
        """标准化实体类型"""
        # 地名相关类型都映射为 LOCATION
        location_types = {"CITY", "COUNTRY", "STATE_OR_PROVINCE", "GPE", "LOCATION"}
        if entity_type in location_types:
            return "LOCATION"
        return entity_type
    
    def _clean_translation(self, raw_html: str) -> str:
        """清理词典返回的 HTML 格式译名
        
        词典返回可能包含 HTML 标签，需要提取纯文本译名
        格式示例：
        - 人名：Smith斯米特[法、英]；史密斯[英]
        - 地名：Paris 【国家】法 【译名】巴黎
        """
        import re
        
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', raw_html)
        text = text.strip()
        
        # 尝试提取【译名】后的内容（地名格式）
        if '【译名】' in text:
            match = re.search(r'【译名】\s*(\S+)', text)
            if match:
                return match.group(1).strip()
        
        # 尝试提取中文译名（人名格式：Name译名[语言]）
        # 匹配连续的中文字符
        chinese_match = re.search(r'[\u4e00-\u9fff·]+', text)
        if chinese_match:
            translation = chinese_match.group()
            # 移除可能的前缀英文
            return translation
        
        # 回退：返回清理后的第一行
        lines = text.split('\n')
        if lines:
            first_line = lines[0].strip()
            # 取第一个分号前的内容
            for sep in ['；', ';', '，', ',']:
                if sep in first_line:
                    first_line = first_line.split(sep)[0].strip()
                    break
            return first_line
        
        return text
    
    def run(self, input_data: dict) -> dict:
        """BaseTool 接口实现
        
        Args:
            input_data: {"text": str, "language": str (optional)}
            
        Returns:
            TranslationResult.to_dict()
        """
        text = input_data.get("text", "")
        language = input_data.get("language", "en")
        result = self.extract_and_translate(text, language)
        return result.to_dict()
    
    def close(self):
        """关闭客户端连接"""
        self.corenlp.close()
        self.dict_client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# 注册工具
ToolRegistry.register(NameExtractor())
