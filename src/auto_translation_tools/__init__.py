"""
Auto Translation Tools - 可扩展的翻译工具平台
"""

from .base import BaseTool, ToolRegistry
from .tools.name_extractor import NameExtractor
from .tools.gemini_caller import GeminiCaller

__version__ = "0.1.0"
__all__ = ["BaseTool", "ToolRegistry", "NameExtractor", "GeminiCaller"]
