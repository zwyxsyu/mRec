# Gemini API 智能雕刻耗材识别系统

## 概述

本项目集成了Google Gemini Pro Vision API，用于智能识别激光雕刻和切割材料。系统能够分析材料图片并提供详细的材料属性、切割参数建议和安全注意事项。

## 功能特性

### 🎯 智能材料识别
- **材料类型识别**：自动识别木材、亚克力、金属、织物等材料类型
- **具体材料名称**：提供精确的材料名称（如红橡木、黑色亚克力等）
- **置信度评估**：提供识别结果的置信度评分

### 🔧 切割参数建议
- **激光功率**：根据材料特性建议合适的激光功率
- **切割速度**：推荐最佳切割速度
- **频率设置**：建议激光频率参数
- **切割次数**：推荐切割遍数

### 🛡️ 安全指导
- **安全注意事项**：提供材料处理的安全提示
- **危险材料警告**：识别可能产生有害气体的材料
- **防护建议**：推荐适当的个人防护设备

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取Gemini API密钥

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 登录您的Google账户
3. 创建新的API密钥
4. 复制API密钥（格式类似：AIzaSyC...）

### 3. 配置API密钥

#### 方法一：使用配置脚本（推荐）

```bash
python setup_gemini.py
```

按照提示输入您的API密钥，脚本会自动：
- 保存配置到`config.json`
- 设置环境变量
- 测试API连接

#### 方法二：手动配置

1. 编辑`config.json`文件：
```json
{
  "gemini_api_key": "your_api_key_here",
  "gemini_model": "gemini-pro-vision"
}
```

2. 或者设置环境变量：
```bash
export GEMINI_API_KEY="your_api_key_here"
```

### 4. 测试配置

```bash
python gemini_recognizer.py
```

如果看到"Gemini API连接成功"，说明配置正确。

## 使用方法

### 启动Web应用

```bash
python app.py
```

访问 http://localhost:5001 打开Web界面。

### Web界面操作

1. **测试Gemini连接**：点击"测试Gemini"按钮验证API配置
2. **选择图片**：在"Gemini分析图片文件名"输入框中指定要分析的图片
3. **开始识别**：点击"开始识别"按钮进行材料分析
4. **查看结果**：在"Gemini识别结果"区域查看详细分析结果

### 程序化使用

```python
import gemini_recognizer

# 分析单个图片
results = gemini_recognizer.run_gemini_model('./materials', 'test_wood.jpg')

# 分析目录中所有图片
results = gemini_recognizer.run_gemini_model('./materials')

# 查看详细结果
for result in results:
    print(f"文件名: {result['filename']}")
    print(f"显示结果: {result['result']}")
    print(f"详细结果: {result['detailed_result']}")
```

## 分析结果格式

### 标准输出格式

```json
{
    "material_type": "木材",
    "material_name": "红橡木",
    "confidence": 0.85,
    "properties": {
        "color": "红棕色",
        "texture": "木纹清晰",
        "hardness": "硬",
        "thickness": "3mm"
    },
    "cutting_parameters": {
        "power": "40W",
        "speed": "15mm/s",
        "frequency": "1000Hz",
        "passes": "1"
    },
    "safety_notes": "切割时会产生木屑，建议使用抽风设备",
    "description": "红橡木是一种硬木，具有美丽的木纹..."
}
```

### 显示格式

```
材料类型: 木材
材料名称: 红橡木
置信度: 0.85
颜色: 红棕色
纹理: 木纹清晰
硬度: 硬
建议功率: 40W
建议速度: 15mm/s
安全提示: 切割时会产生木屑，建议使用抽风设备
```

## 支持的材料类型

系统能够识别以下主要材料类别：

### 木材类
- 红橡木、枫木、桦木、竹子等
- 胶合板、MDF、贴面板等

### 塑料类
- 亚克力（透明、彩色、磨砂）
- ABS、PETG、PVC等
- 聚碳酸酯（Lexan）

### 金属类
- 碳钢、不锈钢
- 铝、铜等

### 织物类
- 羊毛毡、皮革、绒面革
- 卡纸、纸板等

### 其他
- 软木、碳纤维
- 泡沫板、硅胶等

## 注意事项

### API限制
- Gemini API有调用频率限制
- 建议合理控制并发请求数量
- 图片大小建议不超过4MB

### 识别准确性
- 识别结果仅供参考，实际使用时需要人工确认
- 切割参数建议需要根据具体设备调整
- 对于复合材料，系统会识别主要成分

### 安全提醒
- 激光切割操作需要专业培训和防护
- 某些材料切割时可能产生有害气体
- 请严格遵守安全操作规程

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查API密钥是否正确
   - 确认API密钥是否有效
   - 重新运行`setup_gemini.py`

2. **网络连接问题**
   - 检查网络连接
   - 确认防火墙设置
   - 尝试使用VPN

3. **图片格式不支持**
   - 支持格式：JPG、JPEG、PNG、BMP
   - 建议图片尺寸：800x800像素
   - 文件大小：不超过4MB

4. **识别结果不准确**
   - 确保图片清晰度足够
   - 检查光照条件
   - 尝试不同角度的图片

### 日志查看

系统会记录详细的日志信息，可以通过以下方式查看：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 开发说明

### 自定义提示词

可以修改`gemini_recognizer.py`中的`MATERIAL_ANALYSIS_PROMPT`来自定义分析提示词。

### 扩展材料类型

在提示词中添加新的材料类型和属性描述。

### 集成其他模型

可以轻松替换为其他AI模型，只需修改`analyze_material_with_gemini`函数。

## 许可证

本项目遵循MIT许可证。

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 联系方式

如有问题，请通过GitHub Issues联系。 