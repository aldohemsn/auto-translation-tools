"""
可扩展工具平台的核心架构

BaseTool: 所有工具的抽象基类
ToolRegistry: 工具注册表，支持动态发现和调用
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class BaseTool(ABC):
    """所有翻译工具的抽象基类
    
    子类必须定义 name 和 description 属性，并实现 run 方法。
    
    Example:
        class MyTool(BaseTool):
            name = "my_tool"
            description = "我的自定义工具"
            
            def run(self, input_data: dict) -> dict:
                return {"result": "..."}
    """
    
    name: str = ""
    description: str = ""
    
    @abstractmethod
    def run(self, input_data: dict) -> dict:
        """执行工具
        
        Args:
            input_data: 输入数据字典
            
        Returns:
            输出结果字典
        """
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"


class ToolRegistry:
    """工具注册表
    
    支持动态注册、发现和调用工具。
    未来可扩展为自动发现 tools/ 目录下的所有工具。
    """
    
    _tools: dict[str, BaseTool] = {}
    
    @classmethod
    def register(cls, tool: BaseTool) -> None:
        """注册工具
        
        Args:
            tool: BaseTool 实例
        """
        if not tool.name:
            raise ValueError(f"Tool {tool.__class__.__name__} must have a name")
        cls._tools[tool.name] = tool
    
    @classmethod
    def get(cls, name: str) -> BaseTool | None:
        """获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            工具实例，未找到返回 None
        """
        return cls._tools.get(name)
    
    @classmethod
    def list_tools(cls) -> list[str]:
        """列出所有已注册的工具名称"""
        return list(cls._tools.keys())
    
    @classmethod
    def run_tool(cls, name: str, input_data: dict) -> dict:
        """运行指定工具
        
        Args:
            name: 工具名称
            input_data: 输入数据
            
        Returns:
            工具输出
            
        Raises:
            KeyError: 工具不存在
        """
        tool = cls.get(name)
        if not tool:
            raise KeyError(f"Tool '{name}' not found. Available: {cls.list_tools()}")
        return tool.run(input_data)


@dataclass
class TranslationResult:
    """翻译结果数据类"""
    
    found: list[dict] = field(default_factory=list)      # 已找到译名的实体
    not_found: list[dict] = field(default_factory=list)  # 未找到译名的实体
    
    def to_tsv(self, output_path: str) -> None:
        """导出为 TSV 格式
        
        格式: 原文\t类型\t译名\t来源
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("原文\t类型\t译名\t来源\n")
            for item in self.found:
                f.write(f"{item['text']}\t{item['type']}\t{item['translation']}\t{item['source']}\n")
            for item in self.not_found:
                f.write(f"{item['text']}\t{item['type']}\t\t未找到\n")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "found": self.found,
            "not_found": self.not_found,
            "total": len(self.found) + len(self.not_found),
            "found_count": len(self.found),
            "not_found_count": len(self.not_found)
        }
