import os
import sys
import time
from picamera2 import Picamera2
from datetime import datetime

HOME_DIR = '/home/zhaoxiongzhou/sensicut_project'
SAVE_DIR = f'{HOME_DIR}/speckle'
os.makedirs(SAVE_DIR, exist_ok=True)

def get_filename():
    if len(sys.argv) > 1:
        return sys.argv[1]
    else:
        return f'speckle_{int(time.time())}.jpg'

def main():
    filename = get_filename()
    save_path = os.path.join(SAVE_DIR, filename)
    try:
        picam2 = Picamera2()
        config = picam2.create_still_configuration(main={'size': (800, 800)})
        picam2.configure(config)
        picam2.start()
        time.sleep(2)  # 预热
        picam2.capture_file(save_path)
        picam2.close()
        print(f'拍照成功，图片保存于: {save_path}')
    except Exception as e:
        print(f'拍照失败: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main() 