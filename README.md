# Auto Translation Tools

自动化翻译工具平台（Auto Translation Tools）是一个基于 Python 的翻译辅助工具集。它采用**混合架构**，结合了传统的规则/词典匹配与现代 LLM（Gemini）能力，旨在提供高准确度、可追溯且低成本的专有名词翻译方案。

## 🌟 核心特性

- **混合翻译引擎**：
  - **规则优先**：优先使用权威词典（世界人名/地名翻译大辞典、英汉大词典）。
  - **LLM 兜底**：使用 Gemini 2.5-flash 处理词典未收录的新词或复杂上下文。
- **三级查询策略**：实现精细化的查词逻辑（专项词典 > 通用词典 > 姓氏回退）。
- **来源可追溯**：输出结果包含具体的词典来源（如“世界地名翻译大辞典”），便于审校。
- **插件式架构**：基于 `BaseTool` 和 `ToolRegistry`，轻松扩展新工具。

---

## 🚀 快速开始

### 1. 环境准备

需要 Python 3.10+。

```bash
# 克隆仓库
git clone https://github.com/aldohemsn/auto-translation-tools.git
cd auto-translation-tools

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖 (开发模式)
pip install -e .
```

### 2. 配置环境

复制并配置环境变量：

```bash
cp .env.example .env
```

| 变量名 | 说明 | 默认值/示例 |
|--------|------|-------------|
| `DICT_READER_URL` | 词典服务地址 | `https://dict-reader-production.up.railway.app` |
| `CORENLP_URL` | CoreNLP 服务地址 | `https://corenlp-production-e3ae.up.railway.app` |
| `GEMINI_API_KEY` | Google AI Studio Key | `AIzaSy...` (使用 Gemini 功能必填) |
| `MCP_API_KEY` | 词典服务 API Key | (可选) |

### 3. 命令行使用

**基础提取与翻译**：
```bash
# 从文本提取
name-extractor "John Smith visited Paris"

# 从文件提取并保存为 TSV
name-extractor -f input.txt -o output.tsv
```

**启用 Gemini 增强**：
当词典查不到时，自动请求 Gemini 进行翻译：
```bash
name-extractor -f input.txt --use-gemini
```

---

## 🛠️ 开发指南

### 项目结构

```
src/auto_translation_tools/
├── base.py                 # 🔧 核心架构 (BaseTool, ToolRegistry)
├── cli.py                  # 命令行入口
├── tools/                  # 🔌 具体工具实现
│   ├── name_extractor.py   # 专名提取翻译器 (核心逻辑)
│   └── gemini_caller.py    # Gemini API 封装
└── clients/                # 📡 外部服务客户端
    ├── corenlp_client.py   # NER 提取
    └── dict_client.py      # 词典查询 (封装了多级查询)
```

### 核心逻辑：专名提取翻译器 (`NameExtractor`)

该工具 (`tools/name_extractor.py`) 的工作流程如下：

1.  **NER 识别**：调用 `CoreNLP` 识别文本中的 `PERSON`, `LOCATION`, `CITY`, `COUNTRY` 等实体。
2.  **实体标准化**：将各类地名标签统一映射为查询用的类型。
3.  **多级优先级查询** (`_lookup_with_priority`)：
    *   **Level 1 - 专项词典**：查询《世界人名翻译大辞典》或《世界地名翻译大辞典》。准确度最高。
    *   **Level 2 - 通用词典**：查询《英汉大词典》。用于补充常用词汇（如 "Japan", "Kyoto"）。
    *   **Level 3 - 姓氏回退**：如果是人名且未找到，尝试仅查询姓氏。
4.  **结果清理**：去除词典数据中的 HTML 标签和导航噪音（如“回到顶部”）。
5.  **Gemini 补充**（可选）：对上述步骤均为找到的实体，调用 LLM 生成翻译。

### 扩展新工具

只需继承 `BaseTool` 并注册即可：

```python
from auto_translation_tools.base import BaseTool, ToolRegistry

class MyNewTool(BaseTool):
    name = "my_tool"
    description = "工具描述"
    
    def run(self, input_data: dict) -> dict:
        # 实现逻辑
        return {"result": "success"}

# 注册 (通常在 tools/__init__.py 或文件末尾)
ToolRegistry.register(MyNewTool())
```

### 客户端 API

**DictClient**:

```python
from auto_translation_tools.clients import DictClient

client = DictClient()
# 返回 LookupResult 对象，包含 translation, source, database_id
result = client.lookup_general("Hello") 
print(f"{result.translation} (来源: {result.source})")
```

**CoreNLPClient**:

```python
from auto_translation_tools.clients import CoreNLPClient

client = CoreNLPClient()
entities = client.extract_entities("John Smith")
# [Entity(text='John Smith', type='PERSON')]
```

---

## 🔗 服务依赖

本项目依赖以下后台服务：

1.  **Dict Reader Service**: 提供 MDX 词典查询 (人名、地名、英汉大词典)。
2.  **CoreNLP Service**: 提供斯坦福 CoreNLP 的 NER 能力。

---

## License

MIT
