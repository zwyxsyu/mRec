#!/usr/bin/env python3
"""
Gemini API 功能测试脚本
用于测试材料识别功能
"""

import os
import sys
import json
from pathlib import Path

def test_gemini_connection():
    """测试Gemini API连接"""
    print("🔍 测试Gemini API连接...")
    try:
        import gemini_recognizer
        success, msg = gemini_recognizer.test_gemini_connection()
        if success:
            print(f"✅ {msg}")
            return True
        else:
            print(f"❌ {msg}")
            return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

def test_material_analysis():
    """测试材料分析功能"""
    print("\n🔍 测试材料分析功能...")
    
    # 检查materials目录
    materials_dir = Path("./materials")
    if not materials_dir.exists():
        print("❌ materials目录不存在")
        return False
    
    # 查找测试图片
    image_files = list(materials_dir.glob("*.jpg")) + list(materials_dir.glob("*.png"))
    if not image_files:
        print("❌ materials目录中没有找到图片文件")
        return False
    
    # 选择第一张图片进行测试
    test_image = image_files[0]
    print(f"📸 使用测试图片: {test_image.name}")
    
    try:
        import gemini_recognizer
        
        # 分析单张图片
        results = gemini_recognizer.run_gemini_model(str(materials_dir), test_image.name)
        
        if results and len(results) > 0:
            result = results[0]
            print(f"✅ 分析完成")
            print(f"📄 文件名: {result['filename']}")
            print(f"📊 分析结果:")
            print(result['result'])
            
            # 显示详细结果
            if 'detailed_result' in result:
                detailed = result['detailed_result']
                print(f"\n🔍 详细结果:")
                print(json.dumps(detailed, indent=2, ensure_ascii=False))
            
            return True
        else:
            print("❌ 分析失败，没有返回结果")
            return False
            
    except Exception as e:
        print(f"❌ 分析测试失败: {e}")
        return False

def test_configuration():
    """测试配置"""
    print("🔍 检查配置...")
    
    # 检查配置文件
    config_file = Path("config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            api_key = config.get('gemini_api_key', '')
            if api_key:
                print(f"✅ 配置文件存在，API密钥已配置")
                return True
            else:
                print("⚠️ 配置文件存在，但API密钥未配置")
                return False
        except Exception as e:
            print(f"❌ 配置文件读取失败: {e}")
            return False
    else:
        print("❌ 配置文件不存在")
        return False

def main():
    """主测试函数"""
    print("🚀 Gemini API 功能测试")
    print("=" * 50)
    
    # 测试配置
    if not test_configuration():
        print("\n💡 请先运行 setup_gemini.py 配置API密钥")
        return
    
    # 测试连接
    if not test_gemini_connection():
        print("\n💡 请检查API密钥和网络连接")
        return
    
    # 测试材料分析
    if test_material_analysis():
        print("\n🎉 所有测试通过！Gemini API功能正常")
    else:
        print("\n❌ 材料分析测试失败")

if __name__ == "__main__":
    main() 