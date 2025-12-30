"""
工具二：Gemini API Caller

专门与 Gemini 2.5-flash 模型沟通，用于：
- 词典未收录专名的备选翻译
- 上下文感知的专业术语翻译
"""

import os
from typing import Optional

from ..base import BaseTool, ToolRegistry


class GeminiCaller(BaseTool):
    """Gemini API 调用器
    
    使用 Gemini 2.5-flash 模型翻译专有名词。
    作为词典服务的备选方案，处理词典未收录的专名。
    
    Example:
        gemini = GeminiCaller()
        translation = gemini.translate_name("Eiffel Tower", "LOCATION")
        # "埃菲尔铁塔"
        
        # 批量翻译
        results = gemini.batch_translate([
            {"name": "John Doe", "type": "PERSON"},
            {"name": "Silicon Valley", "type": "LOCATION"}
        ])
    """
    
    name = "gemini_caller"
    description = "使用 Gemini 2.5-flash 翻译词典未收录的专有名词"
    
    # 默认模型
    DEFAULT_MODEL = "gemini-2.5-flash"
    
    # Prompt 模板
    TRANSLATE_PROMPT = """你是一名专业翻译。请将以下英文{entity_type}翻译为中文：

名称：{name}
{context_section}
要求：
1. 使用权威译名或通用译法
2. 人名音译遵循《世界人名翻译大辞典》规范
3. 地名遵循中国地名委员会标准

请只返回中文译名，不要解释。"""

    BATCH_PROMPT = """你是一名专业翻译。请将以下英文专有名词翻译为中文：

{names_list}

要求：
1. 使用权威译名或通用译法
2. 人名音译遵循《世界人名翻译大辞典》规范
3. 地名遵循中国地名委员会标准

请按原顺序返回译名，每行一个，不要编号或解释。"""
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None
    ):
        """初始化
        
        Args:
            api_key: Gemini API Key，默认从 GEMINI_API_KEY 读取
            model: 模型名称，默认 gemini-2.5-flash
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        self._client = None
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
    
    def _get_client(self):
        """懒加载 Gemini 客户端"""
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client
    
    def translate_name(
        self, 
        name: str, 
        entity_type: str = "专有名词",
        context: str = ""
    ) -> str:
        """翻译单个专有名词
        
        Args:
            name: 要翻译的名称
            entity_type: 实体类型描述 (PERSON -> "人名", LOCATION -> "地名")
            context: 上下文（可选）
            
        Returns:
            中文译名
        """
        # 转换实体类型为中文
        type_map = {
            "PERSON": "人名",
            "LOCATION": "地名",
            "GPE": "地名",
            "ORGANIZATION": "组织名",
        }
        type_cn = type_map.get(entity_type, entity_type)
        
        # 构造上下文部分
        context_section = f"上下文：{context}\n" if context else ""
        
        prompt = self.TRANSLATE_PROMPT.format(
            entity_type=type_cn,
            name=name,
            context_section=context_section
        )
        
        client = self._get_client()
        response = client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        return response.text.strip()
    
    def batch_translate(self, names: list[dict]) -> list[dict]:
        """批量翻译专有名词
        
        Args:
            names: [{"name": str, "type": str}, ...]
            
        Returns:
            [{"name": str, "type": str, "translation": str}, ...]
        """
        if not names:
            return []
        
        # 构造名称列表
        names_list = "\n".join([
            f"- {item['name']} ({item.get('type', '专有名词')})"
            for item in names
        ])
        
        prompt = self.BATCH_PROMPT.format(names_list=names_list)
        
        client = self._get_client()
        response = client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        # 解析返回结果
        translations = response.text.strip().split("\n")
        
        results = []
        for i, item in enumerate(names):
            translation = translations[i].strip() if i < len(translations) else ""
            results.append({
                "name": item["name"],
                "type": item.get("type", ""),
                "translation": translation,
                "source": "Gemini"
            })
        
        return results
    
    def translate_not_found(self, not_found_items: list[dict]) -> list[dict]:
        """翻译词典未找到的实体
        
        接收 NameExtractor.extract_and_translate() 返回的 not_found 列表，
        使用 Gemini 翻译。
        
        Args:
            not_found_items: [{"text": str, "type": str}, ...]
            
        Returns:
            [{"text": str, "type": str, "translation": str, "source": "Gemini"}, ...]
        """
        if not not_found_items:
            return []
        
        # 转换格式
        names = [{"name": item["text"], "type": item["type"]} for item in not_found_items]
        
        results = self.batch_translate(names)
        
        # 还原字段名
        return [{
            "text": r["name"],
            "type": r["type"],
            "translation": r["translation"],
            "source": "Gemini"
        } for r in results]
    
    def run(self, input_data: dict) -> dict:
        """BaseTool 接口实现
        
        Args:
            input_data: 
                单个: {"name": str, "type": str, "context": str}
                批量: {"names": [{"name": str, "type": str}, ...]}
            
        Returns:
            单个: {"translation": str}
            批量: {"translations": [...]}
        """
        if "names" in input_data:
            # 批量模式
            results = self.batch_translate(input_data["names"])
            return {"translations": results}
        else:
            # 单个模式
            translation = self.translate_name(
                input_data.get("name", ""),
                input_data.get("type", "专有名词"),
                input_data.get("context", "")
            )
            return {"translation": translation}


# 延迟注册（因为需要 API Key）
# ToolRegistry.register(GeminiCaller())
