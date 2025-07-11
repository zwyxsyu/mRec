import os
import threading
import time
import paramiko
import subprocess
from flask import Flask, render_template, request, jsonify, send_file
import json
import gemini_recognizer
import speckle_recognizer

# ========== 配置 ========== #
with open('config.json', 'r') as f:
    config = json.load(f)
RASPBERRY_DEFAULT_IP = config.get('raspberry_ip', '')
RASPBERRY_DEFAULT_USER = config.get('raspberry_user', '')
HOME_DIR = config.get('home_dir', '')
GEMINI_IMAGE_DIR = os.path.abspath(config.get('gemini_image_dir', './materials'))
SPECKLE_IMAGE_DIR = os.path.abspath(config.get('speckle_image_dir', './speckle'))
RASPBERRY_IMAGE_DIR = f'{HOME_DIR}/speckle'          # 树莓派图片目录
RASPBERRY_CAPTURE_SCRIPT = f'{HOME_DIR}/capture_speckle.py'  # 拍照脚本

app = Flask(__name__)

# ========== 工具函数 ========== #
def check_raspberry_connect(ip, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=3)
        ssh.close()
        return True, '连接成功'
    except Exception as e:
        return False, f'连接失败: {e}'

def trigger_raspberry_capture(ip, username, password, filename):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=5)
        # 先cd到脚本目录，激活虚拟环境，再执行脚本
        script_dir = os.path.dirname(RASPBERRY_CAPTURE_SCRIPT)
        cmd = f'cd {script_dir} && source venv/bin/activate && python3 {RASPBERRY_CAPTURE_SCRIPT} {filename}'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        ssh.close()
        if exit_status == 0:
            return True, f'拍照完成\n{out}'
        else:
            return False, f'拍照失败(exit {exit_status}):\n{out}\n{err}'
    except Exception as e:
        return False, f'拍照失败: {e}'

def scp_pull_speckle_image(ip, username, password, filename):
    try:
        import paramiko
        from scp import SCPClient
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=5)
        with SCPClient(ssh.get_transport()) as scp:
            local_path = os.path.join(SPECKLE_IMAGE_DIR, filename)
            remote_path = os.path.join(RASPBERRY_IMAGE_DIR, filename)
            scp.get(remote_path, local_path)
        ssh.close()
        return True, local_path
    except Exception as e:
        return False, str(e)

def run_gemini_model(image_dir):
    # TODO: 替换为你的Gemini大模型API调用逻辑
    # 示例：遍历目录图片，返回分析结果
    results = []
    for fname in os.listdir(image_dir):
        if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            # 这里调用Gemini API，返回结果
            results.append({'filename': fname, 'result': f'Gemini分析结果({fname})'})
    return results

def run_speckle_model(image_path):
    # TODO: 替换为你的本地散斑模型推理逻辑
    # 示例：返回假结果
    return {'filename': os.path.basename(image_path), 'result': '散斑模型分析结果(假数据)'}

def upload_script_to_raspberry(ip, username, password, local_script='capture_speckle.py', remote_path=None):
    if remote_path is None:
        remote_path = f'{HOME_DIR}/capture_speckle.py'
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=5)
        sftp = ssh.open_sftp()
        sftp.put(local_script, remote_path)
        sftp.chmod(remote_path, 0o755)
        sftp.close()
        ssh.close()
        return True, '脚本上传成功'
    except Exception as e:
        return False, f'脚本上传失败: {e}'

# ========== 路由 ========== #
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html',
        gemini_dir=GEMINI_IMAGE_DIR,
        speckle_dir=SPECKLE_IMAGE_DIR,
        raspberry_dir=RASPBERRY_IMAGE_DIR,
        default_ip=RASPBERRY_DEFAULT_IP,
        default_user=RASPBERRY_DEFAULT_USER
    )

@app.route('/check_raspberry', methods=['POST'])
def check_raspberry():
    data = request.json
    ip = data['ip']
    username = data['username']
    password = data['password']
    ok, msg = check_raspberry_connect(ip, username, password)
    return jsonify({'success': ok, 'msg': msg})

@app.route('/start_recognition', methods=['POST'])
def start_recognition():
    data = request.json
    ip = data['ip']
    username = data['username']
    password = data['password']
    speckle_filename = f'speckle_{int(time.time())}.jpg'
    status = {'gemini': None, 'speckle': None, 'msg': '', 'success': True, 'raspberry_log': ''}

    def do_recognition():
        # 1. 触发树莓派拍照
        ok, msg = trigger_raspberry_capture(ip, username, password, speckle_filename)
        status['raspberry_log'] = msg
        if not ok:
            status['speckle'] = {'error': msg}
            status['success'] = False
            return
        # 2. 拉取图片
        ok, local_path = scp_pull_speckle_image(ip, username, password, speckle_filename)
        if not ok:
            status['speckle'] = {'error': local_path}
            status['success'] = False
            return
        # 3. 散斑模型推理
        status['speckle'] = speckle_recognizer.run_speckle_model(local_path)

    # Gemini识别（本地图片目录）
    def do_gemini():
        # 支持前端传递图片文件名
        gemini_filename = data.get('gemini_filename')
        status['gemini'] = gemini_recognizer.run_gemini_model(GEMINI_IMAGE_DIR, gemini_filename)

    t1 = threading.Thread(target=do_recognition)
    t2 = threading.Thread(target=do_gemini)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    return jsonify(status)

@app.route('/upload_script', methods=['POST'])
def upload_script():
    data = request.json
    ip = data['ip']
    username = data['username']
    password = data['password']
    ok, msg = upload_script_to_raspberry(ip, username, password)
    return jsonify({'success': ok, 'msg': msg})

if __name__ == '__main__':
    os.makedirs(GEMINI_IMAGE_DIR, exist_ok=True)
    os.makedirs(SPECKLE_IMAGE_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5001, debug=True) 