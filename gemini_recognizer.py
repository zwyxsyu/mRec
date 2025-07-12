import os
import base64
import json
import google.generativeai as genai
from PIL import Image
import logging
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini API配置
API_KEYS = [
    "AIzaSyAH8vH2cFfJUMpFo14Hox0xF_zCxRaJaF4",
    "AIzaSyB767Wx05W_fuLco-0QIiduk-3IYpX9CAQ",
    "AIzaSyBdcCn7KZwKiE9tXsxVPPvJfoAwalh80fQ",
    "AIzaSyBiqxRWjy2FhUdLdY_GapW2h5VCTLz2R5w",
    "AIzaSyBw5HWst_uBgY-v1C52eTMawKP8Bvi1SrE",
    "AIzaSyBO-R7HFQthZYbs0sGTLUyNI7H3C8CYAaU",
    "AIzaSyCeJeZrXU3bIztBcKBZYmZ9EEm6cQV1aXs"
]
api_key_index = 0

def get_gemini_config():
    """从API_KEYS轮换获取Gemini配置"""
    global api_key_index
    api_key = API_KEYS[api_key_index]
    model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
    return api_key, model

GEMINI_API_KEY, GEMINI_MODEL = get_gemini_config()

# 材料识别提示词模板
MATERIAL_ANALYSIS_PROMPT = """
你是一个专业的智能雕刻耗材识别专家。请分析这张图片中的物体，并提供详细的识别结果。

请特别关注物体的**形状和类型**，例如“玻璃材质的杯子”、“金属钥匙扣”、“木质圆盘”等。

请按照以下格式返回JSON格式的结果：

{
    "material_type": "材料类型（如：木材、亚克力、金属、玻璃、织物等）",
    "material_name": "具体材料名称（如：红橡木、黑色亚克力、碳钢、玻璃等）",
    "object_shape": "物体的形状和类型描述（如：圆盘、杯子、钥匙扣、板材、棒状等）",
    "confidence": "置信度（0-1之间的数值）",
    "properties": {
        "color": "颜色描述",
        "texture": "纹理特征",
        "hardness": "硬度等级（软/中/硬）",
        "thickness": "厚度估计（毫米）"
    },
    "cutting_parameters": {
        "power": "建议激光功率（瓦特）",
        "speed": "建议切割速度（毫米/秒）",
        "frequency": "建议频率（赫兹）",
        "passes": "建议切割次数"
    },
    "safety_notes": "安全注意事项",
    "description": "详细描述"
}

注意事项：
1. 如果无法确定具体材料或形状，请提供最可能的选项和置信度
2. 切割参数仅供参考，实际使用时需要根据设备调整
3. 重点关注材料的颜色、纹理、反光特性、形状等视觉特征
4. 对于复合材料或复杂物体，请识别主要成分和主要形态
5. 形状描述要简明准确，如“玻璃杯”、“金属钥匙扣”、“木质圆盘”等
"""

def init_gemini_client():
    """初始化Gemini客户端，支持API Key轮换"""
    global api_key_index
    for _ in range(len(API_KEYS)):
        api_key, model = get_gemini_config()
        if not api_key:
            logger.error("未设置GEMINI_API_KEY环境变量")
            return None
        try:
            genai.configure(api_key=api_key)
            model_obj = genai.GenerativeModel(model)
            return model_obj
        except Exception as e:
            msg = str(e)
            if "429" in msg or "quota" in msg or "exceeded" in msg:
                logger.warning(f"API Key {api_key} 配额超限，尝试下一个Key...")
                api_key_index = (api_key_index + 1) % len(API_KEYS)
                continue
            logger.error(f"初始化Gemini客户端失败: {e}")
            return None
    logger.error("所有API Key均已超限或不可用")
    return None

def encode_image_to_base64(image_path):
    """将图片编码为base64格式"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"图片编码失败 {image_path}: {e}")
        return None

def analyze_material_with_gemini(model, image_path):
    """使用Gemini分析材料"""
    try:
        # 加载图片
        image = Image.open(image_path)
        
        # 构建提示词
        prompt = MATERIAL_ANALYSIS_PROMPT
        
        # 调用Gemini API
        response = model.generate_content([prompt, image])
        
        # 解析响应
        response_text = response.text
        
        # 尝试提取JSON部分
        try:
            # 查找JSON格式的内容
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                result['raw_response'] = response_text
                return result
            else:
                # 如果没有找到JSON，返回原始响应
                return {
                    'material_type': '未知',
                    'material_name': '无法识别',
                    'confidence': 0.0,
                    'properties': {},
                    'cutting_parameters': {},
                    'safety_notes': '需要人工确认',
                    'description': response_text,
                    'raw_response': response_text
                }
        except json.JSONDecodeError:
            # JSON解析失败，返回原始响应
            return {
                'material_type': '未知',
                'material_name': '无法识别',
                'confidence': 0.0,
                'properties': {},
                'cutting_parameters': {},
                'safety_notes': '需要人工确认',
                'description': response_text,
                'raw_response': response_text
            }
            
    except Exception as e:
        logger.error(f"Gemini分析失败 {image_path}: {e}")
        return {
            'material_type': '错误',
            'material_name': '分析失败',
            'confidence': 0.0,
            'properties': {},
            'cutting_parameters': {},
            'safety_notes': f'分析出错: {str(e)}',
            'description': f'Gemini API调用失败: {str(e)}',
            'error': str(e)
        }

def format_result_for_display(result):
    """格式化结果用于显示"""
    if 'error' in result:
        return f"分析失败: {result['error']}"
    
    display_text = f"材料类型: {result.get('material_type', '未知')}\n"
    display_text += f"材料名称: {result.get('material_name', '未知')}\n"
    display_text += f"置信度: {result.get('confidence', 0.0):.2f}\n"
    
    if result.get('properties'):
        props = result['properties']
        display_text += f"颜色: {props.get('color', '未知')}\n"
        display_text += f"纹理: {props.get('texture', '未知')}\n"
        display_text += f"硬度: {props.get('hardness', '未知')}\n"
    
    if result.get('cutting_parameters'):
        params = result['cutting_parameters']
        display_text += f"建议功率: {params.get('power', '未知')}\n"
        display_text += f"建议速度: {params.get('speed', '未知')}\n"
    
    if result.get('safety_notes'):
        display_text += f"安全提示: {result['safety_notes']}\n"
    
    return display_text

def run_gemini_model(image_dir, filename=None):
    """主函数：运行Gemini材料识别"""
    # 初始化Gemini客户端
    model = init_gemini_client()
    if not model:
        return [{'filename': 'error', 'result': 'Gemini API未配置，请设置GEMINI_API_KEY环境变量'}]
    
    results = []
    
    # 确定要处理的文件
    if filename:
        files = [filename] if os.path.exists(os.path.join(image_dir, filename)) else []
    else:
        files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
    
    # 处理每个文件
    for fname in files:
        image_path = os.path.join(image_dir, fname)
        logger.info(f"正在分析图片: {fname}")
        start_time = time.time()
        # 使用Gemini分析材料
        analysis_result = analyze_material_with_gemini(model, image_path)
        elapsed = time.time() - start_time
        # 格式化显示结果
        display_result = format_result_for_display(analysis_result)
        # 保存详细结果
        result = {
            'filename': fname,
            'result': display_result,
            'detailed_result': analysis_result,
            'elapsed_ms': int(elapsed * 1000)
        }
        results.append(result)
        logger.info(f"图片 {fname} 分析完成, 耗时 {elapsed:.2f}s")
    
    return results

def test_gemini_connection():
    """测试Gemini API连接"""
    model = init_gemini_client()
    if not model:
        return False, "Gemini API未配置"
    
    try:
        # 创建一个简单的测试图片
        test_image = Image.new('RGB', (100, 100), color='red')
        
        # 简单测试
        response = model.generate_content(["这是一张红色图片", test_image])
        return True, "Gemini API连接成功"
    except Exception as e:
        return False, f"Gemini API连接失败: {e}"

if __name__ == "__main__":
    # 测试代码
    print("测试Gemini连接...")
    success, msg = test_gemini_connection()
    print(f"连接状态: {msg}") 