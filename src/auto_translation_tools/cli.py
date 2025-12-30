"""
命令行入口
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    """CLI 主入口"""
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="自动化翻译工具 - 专名提取与翻译"
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="要处理的文本（或使用 --file 指定文件）"
    )
    parser.add_argument(
        "-f", "--file",
        type=Path,
        help="输入文件路径"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("translations.tsv"),
        help="输出 TSV 文件路径 (默认: translations.tsv)"
    )
    parser.add_argument(
        "-l", "--language",
        choices=["en", "es"],
        default="en",
        help="源语言 (默认: en)"
    )
    parser.add_argument(
        "--use-gemini",
        action="store_true",
        help="对词典未找到的项使用 Gemini 翻译"
    )
    
    args = parser.parse_args()
    
    # 获取输入文本
    if args.file:
        if not args.file.exists():
            print(f"错误: 文件不存在 - {args.file}")
            sys.exit(1)
        text = args.file.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        # 从 stdin 读取
        print("请输入文本 (Ctrl+D 结束):")
        text = sys.stdin.read()
    
    if not text.strip():
        print("错误: 未提供输入文本")
        sys.exit(1)
    
    # 处理
    from auto_translation_tools import NameExtractor, GeminiCaller
    from auto_translation_tools.base import TranslationResult
    
    print(f"正在处理... (语言: {args.language})")
    
    with NameExtractor() as extractor:
        result = extractor.extract_and_translate(text, args.language)
    
    # Gemini 备选翻译
    if args.use_gemini and result.not_found:
        print(f"使用 Gemini 翻译 {len(result.not_found)} 个未找到的项...")
        try:
            gemini = GeminiCaller()
            gemini_results = gemini.translate_not_found(result.not_found)
            result.found.extend(gemini_results)
            result.not_found = []
        except Exception as e:
            print(f"Gemini 翻译失败: {e}")
    
    # 输出结果
    result.to_tsv(str(args.output))
    print(f"\n✓ 译名表已保存到: {args.output}")
    print(f"  - 已翻译: {len(result.found)}")
    print(f"  - 未翻译: {len(result.not_found)}")


if __name__ == "__main__":
    main()
