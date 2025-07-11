#!/usr/bin/env python3
"""
Gemini API 设置脚本
用于配置Gemini API密钥和环境变量
"""

import os
import json
import getpass

def setup_gemini_api():
    """设置Gemini API配置"""
    print("=== Gemini API 配置 ===")
    print("请从 https://makersuite.google.com/app/apikey 获取您的API密钥")
    
    # 获取API密钥
    api_key = getpass.getpass("请输入您的Gemini API密钥: ").strip()
    
    if not api_key:
        print("错误: API密钥不能为空")
        return False
    
    # 更新配置文件
    config_file = 'config.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    config['gemini_api_key'] = api_key
    config['gemini_model'] = 'gemini-pro-vision'
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    # 设置环境变量
    os.environ['GEMINI_API_KEY'] = api_key
    
    print("✓ Gemini API配置已保存到config.json")
    print("✓ 环境变量已设置")
    
    # 测试连接
    print("\n正在测试Gemini API连接...")
    try:
        import gemini_recognizer
        success, msg = gemini_recognizer.test_gemini_connection()
        if success:
            print(f"✓ {msg}")
            return True
        else:
            print(f"✗ {msg}")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def create_env_file():
    """创建.env文件"""
    env_content = """# Gemini API配置
GEMINI_API_KEY=your_api_key_here

# 其他环境变量
FLASK_ENV=development
FLASK_DEBUG=1
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✓ 已创建.env文件模板")
    print("请编辑.env文件，将your_api_key_here替换为您的实际API密钥")

if __name__ == "__main__":
    print("智能雕刻耗材识别系统 - Gemini API配置")
    print("=" * 50)
    
    # 创建.env文件
    create_env_file()
    
    # 设置API
    if setup_gemini_api():
        print("\n🎉 Gemini API配置完成！")
        print("现在可以运行主应用程序了:")
        print("python app.py")
    else:
        print("\n❌ Gemini API配置失败")
        print("请检查API密钥是否正确，然后重试") 