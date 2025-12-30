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
        
        查询优先级:
        1. 专项词典（世界人名/地名翻译大辞典）
        2. 通用词典（英汉大词典）
        3. 人名姓氏回退查询
        
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
        
        # 3. 多级查询词典
        for entity in unique_entities:
            lookup_result = self._lookup_with_priority(entity.text, entity.type)
            
            if lookup_result:
                result.found.append({
                    "text": entity.text,
                    "type": entity.type,
                    "translation": lookup_result["translation"],
                    "source": lookup_result["source"]
                })
            else:
                result.not_found.append({
                    "text": entity.text,
                    "type": entity.type
                })
        
        return result
    
    def _lookup_with_priority(self, text: str, entity_type: str) -> dict | None:
        """多级优先级查询
        
        优先级:
        1. 专项词典（人名翻译大辞典/地名翻译大辞典）
        2. 通用词典（英汉大词典）
        3. 人名姓氏回退
        
        Returns:
            {"translation": str, "source": str} 或 None
        """
        normalized_type = self._normalize_entity_type(entity_type)
        
        # 第一优先级：专项词典
        lookup_result = self.dict_client.lookup_by_entity_type(text, normalized_type)
        if lookup_result:
            translation = self._clean_translation(lookup_result.raw_definition)
            if translation:  # 只有有效译名才返回
                return {
                    "translation": translation,
                    "source": lookup_result.source
                }
        
        # 第二优先级：通用词典（英汉大词典）
        lookup_result = self.dict_client.lookup_general(text)
        if lookup_result:
            translation = self._clean_translation(lookup_result.raw_definition)
            if translation:  # 只有有效译名才返回
                return {
                    "translation": translation,
                    "source": lookup_result.source
                }
        
        # 第三优先级：人名姓氏回退
        if normalized_type == "PERSON" and " " in text:
            parts = text.split()
            last_name = parts[-1]  # 姓氏通常在最后
            lookup_result = self.dict_client.lookup_person(last_name)
            if lookup_result:
                translation = self._clean_translation(lookup_result.raw_definition)
                if translation:
                    return {
                        "translation": translation,
                        "source": f"{lookup_result.source}（姓氏）"
                    }
        
        return None
    
    def _normalize_entity_type(self, entity_type: str) -> str:
        """标准化实体类型"""
        # 地名相关类型都映射为 LOCATION
        location_types = {"CITY", "COUNTRY", "STATE_OR_PROVINCE", "GPE", "LOCATION"}
        if entity_type in location_types:
            return "LOCATION"
        return entity_type
    
    def _clean_translation(self, raw_html: str) -> str | None:
        """清理词典返回的 HTML 格式译名
        
        词典返回可能包含 HTML 标签和导航元素，需要提取纯文本译名
        格式示例：
        - 人名词典：Smith斯米特[法、英]；史密斯[英]
        - 地名词典：Paris 【国家】法 【译名】巴黎
        - 英汉大词典：回到顶部HonshuHon·shuˈhɒnʃuː本州(岛)...
        
        Returns:
            清理后的译名，如果是无效内容返回 None
        """
        import re
        
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', raw_html)
        text = text.strip()
        
        # 移除开头的导航噪音文本
        noise_patterns = [
            r'^回到顶部',
            r'^返回顶部',
            r'^查看更多',
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text)
        text = text.strip()
        
        # 尝试提取【译名】后的内容（地名词典格式）
        if '【译名】' in text:
            match = re.search(r'【译名】\s*(\S+)', text)
            if match:
                return match.group(1).strip()
        
        # 尝试提取带括号的中文译名（英汉大词典格式：本州(岛)）
        # 匹配：连续中文字符 + 可选的括号内容
        chinese_with_paren = re.search(r'([\u4e00-\u9fff·]+(?:\([^)]+\))?)', text)
        if chinese_with_paren:
            translation = chinese_with_paren.group(1)
            # 过滤掉过短或无意义的结果
            if len(translation) >= 2:
                return translation
        
        # 回退：提取连续的中文字符
        chinese_match = re.search(r'[\u4e00-\u9fff·]{2,}', text)
        if chinese_match:
            return chinese_match.group()
        
        return None
    
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
