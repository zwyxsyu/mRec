# app.py
import os
from flask import Flask, render_template, Response, jsonify, request
from PIL import Image
import google.generativeai as genai
import json
import time
import io
import threading
import random 

# Import Picamera2 for camera control
from picamera2 import Picamera2
import cv2 # OpenCV for image processing (e.g., converting to JPEG)

# Flask App Initialization
app = Flask(__name__)

# --- API Key Rotation Configuration ---
# Store your API keys in a list for rotation
API_KEYS = [
    "AIzaSyCz7zuo4zNtKGGjz8mrjrebqu_CVtJDK3w",
    "AIzaSyAH8vH2cFfJUMpFo14Hox0xF_zCxRaJaF4",
    "AIzaSyB767Wx05W_fuLco-0QIiduk-3IYpX9CAQ",
    "AIzaSyBdcCn7KZwKiE9tXsxVPPvJfoAwalh80fQ",
    "AIzaSyBiqxRWjy2FhUdLdY_GapW2h5VCTLz2R5w",
    "AIzaSyBw5HWst_uBgY-vC52eTMawKP8Bvi1SrE", 
    "AIzaSyBO-R7HFQthZYbs0sGTLUyNI7H3C8CYAaU",
    "AIzaSyCeJeZrXU3bIztBcKBZYmZ9EEm6cQV1aXs"
]

# Global index to keep track of the current API key
current_key_index = 0
# Global variable to store the currently active model instance
model = None

# --- Backend Messages for Localization ---
# These messages will be sent to the frontend based on the requested language
BACKEND_MESSAGES = {
    'zh': {
        'BUSY': '检测进行中，请稍候。',
        'STARTING': '正在启动检测...',
        'CAPTURING_AI': '正在捕获图像并调用AI模型...',
        'STARTED': '材料检测已启动...',
        'COMPLETED': '识别完成。',
        'FAILED': '综合识别失败，请重试。',
        'ERROR_OCCURRED': '检测过程中发生错误:',
        'API_BLOCKED': 'API调用失败: 内容被阻止。',
        'API_EXHAUSTED': '所有API密钥均已耗尽或失败。',
        'IMAGE_NOT_FOUND': '错误：未找到图片文件：', # Kept for consistency, less relevant with live camera
        'NO_IMAGES_FOUND': '错误：目录中未找到材料图片。', # Kept for consistency, less relevant with live camera
        'API_CALL_FAILED': 'API调用失败:',
        'IDENTIFICATION_TIME': '识别耗时：', 
        'CAMERA_INIT_FAILED': '摄像头初始化失败。', 
        'CAMERA_CAPTURE_FAILED': '摄像头捕获图像失败。', 
    },
    'en': {
        'BUSY': 'Detection in progress, please wait.',
        'STARTING': 'Starting detection...',
        'CAPTURING_AI': 'Capturing images and calling AI models...',
        'STARTED': 'Material detection started...',
        'COMPLETED': 'Identification completed.',
        'FAILED': 'Comprehensive identification failed, please retry.',
        'ERROR_OCCURRED': 'An error occurred during detection:',
        'API_BLOCKED': 'API call failed: Content blocked.',
        'API_EXHAUSTED': 'All API keys exhausted or failed.',
        'IMAGE_NOT_FOUND': 'Error: Image file not found at ',
        'NO_IMAGES_FOUND': 'Error: No material images found in the directory.',
        'API_CALL_FAILED': 'API call failed:',
        'IDENTIFICATION_TIME': 'Identification time: ',
        'CAMERA_INIT_FAILED': 'Camera initialization failed.',
        'CAMERA_CAPTURE_FAILED': 'Failed to capture image from camera.',
    }
}


def configure_gemini_model():
    """Configures the Gemini model with the current API key."""
    global model, current_key_index
    if not API_KEYS:
        print("Error: No API keys configured.")
        exit(1)

    # Cycle through keys if index goes out of bounds
    current_key_index = current_key_index % len(API_KEYS)

    genai.configure(api_key=API_KEYS[current_key_index])
    model = genai.GenerativeModel("gemini-1.5-flash")
    print(f"Gemini model configured with API key index: {current_key_index}")

# Initial configuration of the model
configure_gemini_model()

# Global variables for storing the latest identification result and detection status
current_material_info = {}
is_detecting = False
detection_thread = None 

# --- Picamera2 Initialization ---
picam2 = None
try:
    picam2 = Picamera2()
    # Configure for video streaming (main stream) and still capture (lores stream)
    # The lores stream is used for AI processing to get a smaller image quickly
    # For Pi 4B, 640x480 is a good balance for lores stream for AI input
    video_config = picam2.create_video_configuration(main={"size": (640, 480)}, lores={"size": (640, 480)}, encode="rgb")