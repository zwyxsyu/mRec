import os
from sensicut.predict import SensiCutPredictor

def run_speckle_model(image_path):
    # 散斑AI模型推理
    try:
        predictor = SensiCutPredictor(model_path='sensicut/speckle_resnet50_fastai.pkl')
        if os.path.exists(image_path):
            result = predictor.predict_single_image(image_path, show_image=False, top_k=1)
            if result:
                return {
                    'filename': os.path.basename(image_path),
                    'result': f"类别: {result['predicted_class']}",
                    'confidence': float(result['confidence']),
                }
            else:
                return {'filename': os.path.basename(image_path), 'result': '未识别到类别', 'confidence': 0.0}
        else:
            return {'filename': os.path.basename(image_path), 'result': '图片不存在', 'confidence': 0.0}
    except Exception as e:
        return {'filename': os.path.basename(image_path), 'result': f'模型异常: {e}', 'confidence': 0.0} 