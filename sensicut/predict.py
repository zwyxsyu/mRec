import torch
from fastai.vision.all import *
import json
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from pathlib import Path
import os
import argparse
import glob

class SensiCutPredictor:
    def __init__(self, model_path='sensicut_resnet50_fastai.pkl', class_names_path='class_names_fastai.json'):
        """
        初始化预测器

        Args:
            model_path: 导出的fast.ai模型路径
            class_names_path: 类别名称文件路径
        """
        self.model_path = model_path
        self.class_names_path = class_names_path
        self.learner = None
        self.class_names = None

        # 加载模型和类别名称
        self.load_model()
        self.load_class_names()

    def load_model(self):
        """加载fast.ai模型"""
        try:
            self.learner = load_learner(self.model_path)
            print(f"模型加载成功: {self.model_path}")
        except Exception as e:
            print(f"模型加载失败: {e}")
            raise

    def load_class_names(self):
        """加载类别名称"""
        try:
            with open(self.class_names_path, 'r', encoding='utf-8') as f:
                self.class_names = json.load(f)
            print(f"类别名称加载成功: {len(self.class_names)} 个类别")
        except Exception as e:
            print(f"类别名称加载失败: {e}")
            # 如果加载失败，使用模型中的词汇表
            if self.learner:
                self.class_names = self.learner.dls.vocab
                print(f"使用模型词汇表: {len(self.class_names)} 个类别")

    def predict_single_image(self, image_path, show_image=True, top_k=3):
        """
        预测单张图片

        Args:
            image_path: 图片路径
            show_image: 是否显示图片
            top_k: 返回前k个预测结果

        Returns:
            dict: 预测结果
        """
        try:
            # 加载图片
            image = Image.open(image_path).convert('RGB')

            # 使用模型预测
            pred, pred_idx, probs = self.learner.predict(image_path)

            # 获取前k个预测结果
            top_k_indices = torch.topk(probs, top_k).indices
            top_k_probs = torch.topk(probs, top_k).values

            results = {
                'predicted_class': str(pred),
                'confidence': float(probs[pred_idx]),
                'top_k_predictions': []
            }

            for i in range(top_k):
                idx = top_k_indices[i]
                prob = top_k_probs[i]
                class_name = self.learner.dls.vocab[idx]
                results['top_k_predictions'].append({
                    'class': class_name,
                    'confidence': float(prob)
                })

            # 显示图片和预测结果
            if show_image:
                plt.figure(figsize=(10, 6))
                plt.subplot(1, 2, 1)
                plt.imshow(image)
                plt.title(f'输入图片\n{Path(image_path).name}')
                plt.axis('off')

                plt.subplot(1, 2, 2)
                classes = [item['class'] for item in results['top_k_predictions']]
                confidences = [item['confidence'] for item in results['top_k_predictions']]

                bars = plt.barh(range(len(classes)), confidences)
                plt.yticks(range(len(classes)), classes)
                plt.xlabel('置信度')
                plt.title(f'前{top_k}个预测结果')

                # 为每个条形添加数值标签
                for i, (bar, conf) in enumerate(zip(bars, confidences)):
                    plt.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2, 
                            f'{conf:.3f}', ha='left', va='center')

                plt.tight_layout()
                plt.show()

            return results

        except Exception as e:
            print(f"预测失败: {e}")
            return None

    def predict_batch(self, image_paths, show_results=True):
        """
        批量预测多张图片

        Args:
            image_paths: 图片路径列表
            show_results: 是否显示结果

        Returns:
            list: 预测结果列表
        """
        results = []

        for image_path in image_paths:
            result = self.predict_single_image(image_path, show_image=False)
            if result:
                result['image_path'] = image_path
                results.append(result)

        if show_results and results:
            self.show_batch_results(results)

        return results

    def show_batch_results(self, results, max_images=9):
        """显示批量预测结果"""
        n_images = min(len(results), max_images)
        cols = 3
        rows = (n_images + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(15, 5*rows))
        if rows == 1:
            axes = [axes]
        axes = np.array(axes).flatten()

        for i in range(n_images):
            result = results[i]
            image_path = result['image_path']

            # 加载并显示图片
            image = Image.open(image_path).convert('RGB')
            axes[i].imshow(image)

            # 设置标题
            title = f"{Path(image_path).name}\n"
            title += f"预测: {result['predicted_class']}\n"
            title += f"置信度: {result['confidence']:.3f}"

            axes[i].set_title(title, fontsize=10)
            axes[i].axis('off')

        # 隐藏多余的子图
        for i in range(n_images, len(axes)):
            axes[i].axis('off')

        plt.tight_layout()
        plt.show()

    def evaluate_test_folder(self, test_folder, show_summary=True, show_accuracy=True):
        """
        评估测试文件夹中的所有图片

        Args:
            test_folder: 测试文件夹路径
            show_summary: 是否显示结果摘要
            show_accuracy: 是否显示准确率分析

        Returns:
            dict: 评估结果
        """
        # 获取所有图片文件
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        image_paths = []

        for ext in image_extensions:
            image_paths.extend(glob.glob(os.path.join(test_folder, ext)))

        if not image_paths:
            print(f"在 {test_folder} 中没有找到图片文件")
            return None

        print(f"找到 {len(image_paths)} 张图片")

        # 批量预测
        results = self.predict_batch(image_paths, show_results=False)

        # 计算准确率
        accuracy_stats = self.calculate_accuracy(results)

        # 统计结果
        class_counts = {}
        total_confidence = 0

        for result in results:
            predicted_class = result['predicted_class']
            confidence = result['confidence']

            if predicted_class not in class_counts:
                class_counts[predicted_class] = []
            class_counts[predicted_class].append(confidence)
            total_confidence += confidence

        # 计算统计信息
        stats = {
            'total_images': len(results),
            'average_confidence': total_confidence / len(results),
            'class_distribution': {}
        }

        for class_name, confidences in class_counts.items():
            stats['class_distribution'][class_name] = {
                'count': len(confidences),
                'percentage': len(confidences) / len(results) * 100,
                'avg_confidence': np.mean(confidences),
                'min_confidence': np.min(confidences),
                'max_confidence': np.max(confidences)
            }

        if show_summary:
            self.show_evaluation_summary(stats)

        if show_accuracy:
            self.show_accuracy_summary(accuracy_stats)

        return {
            'stats': stats,
            'accuracy_stats': accuracy_stats,
            'detailed_results': results
        }

    def show_evaluation_summary(self, stats):
        """显示评估摘要"""
        print("\n=== 评估结果摘要 ===")
        print(f"总图片数: {stats['total_images']}")
        print(f"平均置信度: {stats['average_confidence']:.3f}")
        print(f"\n各类别分布:")
        print(f"{'类别':<20} {'数量':<8} {'百分比':<10} {'平均置信度':<12} {'最低置信度':<12} {'最高置信度'}")
        print("-" * 80)

        for class_name, info in stats['class_distribution'].items():
            print(f"{class_name:<20} {info['count']:<8} {info['percentage']:<10.1f}% "
                  f"{info['avg_confidence']:<12.3f} {info['min_confidence']:<12.3f} {info['max_confidence']:<12.3f}")

    def extract_true_label_from_filename(self, filename):
        """
        从文件名中提取真实标签

        Args:
            filename: 文件名

        Returns:
            str: 真实标签
        """
        # 从文件名中提取材料名称（文件名格式：MaterialName-其他参数）
        basename = os.path.basename(filename)
        true_label = basename.split('-')[0]
        return true_label

    def calculate_accuracy(self, results):
        """
        计算预测准确率

        Args:
            results: 预测结果列表

        Returns:
            dict: 准确率统计信息
        """
        correct_predictions = 0
        total_predictions = len(results)

        # 按类别统计准确率
        class_accuracy = {}

        for result in results:
            true_label = self.extract_true_label_from_filename(result['image_path'])
            predicted_label = result['predicted_class']

            # 初始化类别统计
            if true_label not in class_accuracy:
                class_accuracy[true_label] = {'correct': 0, 'total': 0}

            class_accuracy[true_label]['total'] += 1

            # 检查预测是否正确
            if predicted_label == true_label:
                correct_predictions += 1
                class_accuracy[true_label]['correct'] += 1

        # 计算每个类别的准确率
        for class_name in class_accuracy:
            correct = class_accuracy[class_name]['correct']
            total = class_accuracy[class_name]['total']
            class_accuracy[class_name]['accuracy'] = correct / total if total > 0 else 0

        overall_accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0

        return {
            'overall_accuracy': overall_accuracy,
            'correct_predictions': correct_predictions,
            'total_predictions': total_predictions,
            'class_accuracy': class_accuracy
        }

    def show_accuracy_summary(self, accuracy_stats):
        """显示准确率摘要"""
        print("\n=== 测试集准确率分析 ===")
        print(f"总体准确率: {accuracy_stats['overall_accuracy']:.3f} ({accuracy_stats['overall_accuracy']*100:.1f}%)")
        print(f"正确预测: {accuracy_stats['correct_predictions']}/{accuracy_stats['total_predictions']}")

        print(f"\n各类别准确率:")
        print(f"{'类别':<20} {'正确数':<8} {'总数':<8} {'准确率':<10}")
        print("-" * 50)

        # 按准确率排序
        sorted_classes = sorted(accuracy_stats['class_accuracy'].items(), 
                              key=lambda x: x[1]['accuracy'], reverse=True)

        for class_name, stats in sorted_classes:
            accuracy = stats['accuracy']
            correct = stats['correct']
            total = stats['total']
            print(f"{class_name:<20} {correct:<8} {total:<8} {accuracy:<10.3f} ({accuracy*100:.1f}%)")

        # 找出表现最好和最差的类别
        best_class = max(accuracy_stats['class_accuracy'].items(), key=lambda x: x[1]['accuracy'])
        worst_class = min(accuracy_stats['class_accuracy'].items(), key=lambda x: x[1]['accuracy'])

        print(f"\n表现最好的类别: {best_class[0]} (准确率: {best_class[1]['accuracy']:.3f})")
        print(f"表现最差的类别: {worst_class[0]} (准确率: {worst_class[1]['accuracy']:.3f})")

def main():
    """主函数 - 示例用法"""
    print("SensiCut Fast.ai 预测器")
    print("=" * 50)

    # 初始化预测器
    try:
        predictor = SensiCutPredictor()
    except Exception as e:
        print(f"初始化预测器失败: {e}")
        print("请确保已经训练了模型并生成了 sensicut_resnet50_fastai.pkl 文件")
        return

    # 示例1: 预测单张图片
    print("\n1. 单张图片预测示例")
    print("-" * 30)

    parser = argparse.ArgumentParser(description='SensiCut材料分类预测')
    parser.add_argument('--image', type=str, required=True, help='要预测的图像路径')
    parser.add_argument('--top_k', type=int, default=5, help='显示前k个预测结果')

    args = parser.parse_args()
    # 这里需要替换为实际的图片路径
    sample_image = args.image  # 替换为实际的图片路径

    if os.path.exists(sample_image):
        result = predictor.predict_single_image(sample_image, show_image=True, top_k=args.top_k)
        if result:
            print(f"预测结果: {result['predicted_class']}")
            print(f"置信度: {result['confidence']:.3f}")
    else:
        print(f"示例图片 {sample_image} 不存在")

    # 示例2: 批量预测和准确率评估
    print("\n2. 批量预测和准确率评估示例")
    print("-" * 30)

    # 如果有测试文件夹，可以进行批量预测
    test_folder = "testData/augmented"  # 替换为实际的测试文件夹路径

    if os.path.exists(test_folder):
        evaluation_result = predictor.evaluate_test_folder(test_folder, show_summary=True, show_accuracy=True)

        if evaluation_result:
            print(f"\n=== 测试结果总结 ===")
            accuracy_stats = evaluation_result['accuracy_stats']
            print(f"测试集总体准确率: {accuracy_stats['overall_accuracy']:.3f} ({accuracy_stats['overall_accuracy']*100:.1f}%)")
            print(f"正确预测数量: {accuracy_stats['correct_predictions']}/{accuracy_stats['total_predictions']}")
            print("\n详细预测结果已保存到 evaluation_result 变量中")
    else:
        print(f"测试文件夹 {test_folder} 不存在")

    print("\n预测完成!")

if __name__ == "__main__":
    main()