# Auto Translation Tools

自动化翻译工具平台 - 可扩展的翻译辅助工具集

## 功能

### 🔧 工具一：专名提取翻译器 (Name Extractor)
- 使用 CoreNLP NER 自动提取人名、地名
- 通过词典服务查询权威中文译名
- 生成 TSV 格式译名表

### 🤖 工具二：Gemini API Caller
- 调用 Gemini 2.5-flash 模型
- 作为词典未收录专名的备选翻译方案
- 支持上下文感知翻译

## 安装

```bash
pip install -e .
```

## 配置

复制环境变量模板并填写：

```bash
cp .env.example .env
```

配置项：
- `DICT_READER_URL`: 词典服务地址
- `CORENLP_URL`: CoreNLP 服务地址  
- `MCP_API_KEY`: 词典服务认证密钥（可选）
- `GEMINI_API_KEY`: Google Gemini API 密钥

## 使用示例

```python
from auto_translation_tools import NameExtractor, GeminiCaller

# 专名提取翻译
extractor = NameExtractor()
result = extractor.extract_and_translate("John Smith visited Paris.")
result.to_tsv("translations.tsv")

# Gemini 备选翻译
gemini = GeminiCaller()
translation = gemini.translate_name("Eiffel Tower", "LOCATION")
```

## 扩展开发

新工具只需继承 `BaseTool` 并注册：

```python
from auto_translation_tools.base import BaseTool, ToolRegistry

class MyTool(BaseTool):
    name = "my_tool"
    description = "我的自定义工具"
    
    def run(self, input_data: dict) -> dict:
        # 实现逻辑
        return {"result": "..."}

ToolRegistry.register(MyTool())
```

## 服务依赖

| 服务 | 地址 | 说明 |
|------|------|------|
| Dict Reader | dict-reader-production.up.railway.app | 词典查询服务 |
| CoreNLP | corenlp-production-e3ae.up.railway.app | NLP分析服务 |

## License

MIT
