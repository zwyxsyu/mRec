import os
from sensicut.predict import SensiCutPredictor
import time

def run_speckle_model(image_path):
    # 散斑AI模型推理
    try:
        start_time = time.time()
        predictor = SensiCutPredictor(model_path='sensicut/speckle_resnet50_fastai_improved_merged_v2lr.pkl')
        if os.path.exists(image_path):
            result = predictor.predict_single_image(image_path, show_image=False, top_k=1)
            elapsed = int((time.time() - start_time) * 1000)  # 转换为毫秒
            if result:
                return {
                    'filename': os.path.basename(image_path),
                    'result': f"类别: {result['predicted_class']}",
                    'confidence': float(result['confidence']),
                    'elapsed_ms': elapsed
                }
            else:
                return {'filename': os.path.basename(image_path), 'result': '未识别到类别', 'confidence': 0.0, 'elapsed_ms': elapsed}
        else:
            return {'filename': os.path.basename(image_path), 'result': '图片不存在', 'confidence': 0.0, 'elapsed_ms': 0}
    except Exception as e:
        return {'filename': os.path.basename(image_path), 'result': f'模型异常: {e}', 'confidence': 0.0, 'elapsed_ms': 0} 