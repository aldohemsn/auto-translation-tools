#!/usr/bin/env python3
"""
Auto Translation Tools 使用示例

演示如何使用专名提取翻译器和 Gemini API Caller
"""

import os
import sys
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


def demo_name_extractor():
    """演示专名提取翻译器"""
    from auto_translation_tools import NameExtractor
    
    print("=" * 60)
    print("工具一：专名提取翻译器 (Name Extractor)")
    print("=" * 60)
    
    # 测试文本
    test_text = """
    John Smith is a renowned scientist from Cambridge. He collaborated with 
    Marie Curie on groundbreaking research in Paris. Later, he moved to 
    Washington D.C. to work with Dr. Robert Johnson at the Smithsonian Institution.
    """
    
    print(f"\n输入文本:\n{test_text.strip()}\n")
    
    try:
        with NameExtractor() as extractor:
            result = extractor.extract_and_translate(test_text)
            
            print("已找到译名:")
            print("-" * 40)
            for item in result.found:
                print(f"  {item['text']:20} -> {item['translation']} ({item['type']})")
            
            print("\n未找到译名:")
            print("-" * 40)
            for item in result.not_found:
                print(f"  {item['text']:20} ({item['type']})")
            
            # 生成 TSV 文件
            output_path = Path("translations.tsv")
            result.to_tsv(str(output_path))
            print(f"\n✓ TSV 文件已生成: {output_path.absolute()}")
            
            return result
            
    except ConnectionError as e:
        print(f"✗ 服务连接失败: {e}")
        return None


def demo_gemini_caller(not_found_items: list = None):
    """演示 Gemini API Caller"""
    from auto_translation_tools import GeminiCaller
    
    print("\n" + "=" * 60)
    print("工具二：Gemini API Caller")
    print("=" * 60)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("✗ 请先设置 GEMINI_API_KEY 环境变量")
        return
    
    try:
        gemini = GeminiCaller()
        
        # 单个翻译示例
        print("\n单个翻译:")
        print("-" * 40)
        name = "Eiffel Tower"
        translation = gemini.translate_name(name, "LOCATION", "A famous landmark in Paris")
        print(f"  {name} -> {translation}")
        
        # 翻译词典未找到的项
        if not_found_items:
            print("\n翻译词典未收录项:")
            print("-" * 40)
            results = gemini.translate_not_found(not_found_items)
            for item in results:
                print(f"  {item['text']:20} -> {item['translation']} ({item['type']})")
        else:
            # 批量翻译示例
            print("\n批量翻译:")
            print("-" * 40)
            names = [
                {"name": "Silicon Valley", "type": "LOCATION"},
                {"name": "Albert Einstein", "type": "PERSON"},
            ]
            results = gemini.batch_translate(names)
            for item in results:
                print(f"  {item['name']:20} -> {item['translation']}")
                
    except ValueError as e:
        print(f"✗ 配置错误: {e}")
    except Exception as e:
        print(f"✗ API 调用失败: {e}")


def main():
    """主函数"""
    print("\n🔧 Auto Translation Tools 演示\n")
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 使用命令行提供的文本
        text = " ".join(sys.argv[1:])
        print(f"处理文本: {text}\n")
        
        from auto_translation_tools import NameExtractor
        with NameExtractor() as extractor:
            result = extractor.extract_and_translate(text)
            result.to_tsv("translations.tsv")
            print("✓ 译名表已保存到 translations.tsv")
    else:
        # 运行演示
        result = demo_name_extractor()
        
        # 如果有未找到的项，尝试用 Gemini 翻译
        if result and result.not_found:
            demo_gemini_caller(result.not_found)
        else:
            demo_gemini_caller()


if __name__ == "__main__":
    main()
