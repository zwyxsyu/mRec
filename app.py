import os
import threading
import time
import paramiko
import subprocess
from flask import Flask, render_template, request, jsonify, send_file, url_for
import json
import gemini_recognizer
import speckle_recognizer
from dotenv import load_dotenv
import uuid
from threading import Thread
load_dotenv()

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
    # 使用新的Gemini识别模块
    return gemini_recognizer.run_gemini_model(image_dir)

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
        default_user=RASPBERRY_DEFAULT_USER,
        collect_url=url_for('collect_speckle_page')
    )

@app.route('/check_raspberry', methods=['POST'])
def check_raspberry():
    data = request.json
    ip = data['ip']
    username = data['username']
    password = data['password']
    ok, msg = check_raspberry_connect(ip, username, password)
    return jsonify({'success': ok, 'msg': msg})

gemini_tasks = {}

@app.route('/start_recognition', methods=['POST'])
def start_recognition():
    data = request.json
    ip = data['ip']
    username = data['username']
    password = data['password']
    speckle_filename = f'speckle_{int(time.time())}.jpg'
    status = {'gemini': None, 'speckle': None, 'msg': '', 'success': True, 'raspberry_log': ''}

    # Gemini识别（本地图片目录）
    def do_gemini_progress(task_id, gemini_dir, gemini_filename=None):
        import gemini_recognizer
        # 获取要识别的文件列表
        if gemini_filename:
            files = [gemini_filename] if os.path.exists(os.path.join(gemini_dir, gemini_filename)) else []
        else:
            # 自动选取目录下创建时间最新的图片
            all_files = [f for f in os.listdir(gemini_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
            if all_files:
                latest_file = max(all_files, key=lambda f: os.path.getctime(os.path.join(gemini_dir, f)))
                files = [latest_file]
            else:
                files = []
        total = len(files)
        results = []
        for idx, fname in enumerate(files):
            image_path = os.path.join(gemini_dir, fname)
            start_time = time.time()
            analysis_result = gemini_recognizer.analyze_material_with_gemini(gemini_recognizer.init_gemini_client(), image_path)
            elapsed = time.time() - start_time
            display_result = gemini_recognizer.format_result_for_display(analysis_result)
            result = {
                'filename': fname,
                'result': display_result,
                'detailed_result': analysis_result,
                'elapsed_ms': int(elapsed * 1000)
            }
            results.append(result)
            gemini_tasks[task_id] = {
                'progress': idx + 1,
                'total': total,
                'results': results.copy(),
                'done': False
            }
        gemini_tasks[task_id]['done'] = True

    # 生成任务ID
    task_id = str(uuid.uuid4())
    gemini_tasks[task_id] = {'progress': 0, 'total': 1, 'results': [], 'done': False}

    def do_recognition():
        ok, msg = trigger_raspberry_capture(ip, username, password, speckle_filename)
        status['raspberry_log'] = msg
        if not ok:
            status['speckle'] = {'error': msg}
            status['success'] = False
            return
        ok, local_path = scp_pull_speckle_image(ip, username, password, speckle_filename)
        if not ok:
            status['speckle'] = {'error': local_path}
            status['success'] = False
            return
        status['speckle'] = speckle_recognizer.run_speckle_model(local_path)

    # 启动Gemini识别线程
    t2 = Thread(target=do_gemini_progress, args=(task_id, GEMINI_IMAGE_DIR, data.get('gemini_filename')))
    t2.start()
    # 其余同步执行
    start_time = time.time()
    do_recognition()
    t2.join()
    total_elapsed = int((time.time() - start_time) * 1000)
    status['gemini'] = gemini_tasks[task_id]['results']
    status['gemini_task_id'] = task_id

    # TODO: 综合Gemini和散斑结果，后续实现融合逻辑
    # 目前直接返回示例HTML，便于前端调试
    status['final_result'] = '''<div class="flex items-center gap-2 mb-2">
        <span class="font-bold text-yellow-700 text-base">总耗时: 1234 ms</span>
    </div>
    <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <div><span class="font-medium text-gray-600">材料类型：</span>错误</div>
        <div><span class="font-medium text-gray-600">材料名称：</span>分析失败</div>
        <div><span class="font-medium text-gray-600">置信度：</span>0.00</div>
        <div><span class="font-medium text-gray-600">颜色：</span>-</div>
        <div><span class="font-medium text-gray-600">纹理：</span>-</div>
        <div><span class="font-medium text-gray-600">硬度：</span>-</div>
    </div>'''
    return jsonify(status)

@app.route('/gemini_progress', methods=['GET'])
def gemini_progress():
    task_id = request.args.get('task_id')
    if not task_id or task_id not in gemini_tasks:
        return jsonify({'error': '无效的任务ID'}), 404
    return jsonify(gemini_tasks[task_id])

@app.route('/upload_script', methods=['POST'])
def upload_script():
    data = request.json
    ip = data['ip']
    username = data['username']
    password = data['password']
    ok, msg = upload_script_to_raspberry(ip, username, password)
    return jsonify({'success': ok, 'msg': msg})

@app.route('/test_gemini', methods=['POST'])
def test_gemini():
    """测试Gemini API连接"""
    try:
        success, msg = gemini_recognizer.test_gemini_connection()
        return jsonify({'success': success, 'msg': msg})
    except Exception as e:
        return jsonify({'success': False, 'msg': f'测试失败: {str(e)}'})

@app.route('/collect_speckle', methods=['GET'])
def collect_speckle_page():
    return render_template('collect_speckle.html',
        default_ip=RASPBERRY_DEFAULT_IP,
        default_user=RASPBERRY_DEFAULT_USER
    )

@app.route('/collect_speckle', methods=['POST'])
def collect_speckle():
    data = request.json
    subdir = data.get('subdir', '').strip()
    if not subdir:
        return jsonify({'success': False, 'msg': '子目录名称不能为空'})
    # 1. 在PC端创建子目录
    pc_subdir = os.path.join(SPECKLE_IMAGE_DIR, subdir)
    os.makedirs(pc_subdir, exist_ok=True)
    # 2. 在树莓派端创建同名目录并采集图片
    # 这里只采集一张图片为例，可扩展为多张
    ip = RASPBERRY_DEFAULT_IP
    username = RASPBERRY_DEFAULT_USER
    password = data.get('password', '')  # 可扩展为前端输入
    remote_subdir = f'{HOME_DIR}/speckle/{subdir}'
    # 创建目录+采集
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=5)
        # 创建目录
        ssh.exec_command(f'mkdir -p {remote_subdir}')
        # 拍照
        import time
        fname = f'speckle_{int(time.time())}.jpg'
        cmd = f'cd {os.path.dirname(RASPBERRY_CAPTURE_SCRIPT)} && source venv/bin/activate && python3 {RASPBERRY_CAPTURE_SCRIPT} {subdir}/{fname}'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        ssh.close()
        # 拉取图片到本地子目录
        from scp import SCPClient
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=5)
        with SCPClient(ssh.get_transport()) as scp:
            scp.get(f'{remote_subdir}/{fname}', os.path.join(pc_subdir, fname))
        ssh.close()
        if exit_status == 0:
            return jsonify({'success': True, 'msg': f'采集完成，图片已保存到{subdir}。\n{out}'})
        else:
            return jsonify({'success': False, 'msg': f'采集失败(exit {exit_status}):\n{out}\n{err}'})
    except Exception as e:
        return jsonify({'success': False, 'msg': f'采集失败: {e}'})

if __name__ == '__main__':
    os.makedirs(GEMINI_IMAGE_DIR, exist_ok=True)
    os.makedirs(SPECKLE_IMAGE_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5001, debug=True) 