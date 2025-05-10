import json
import os
from loguru import logger
# 设置root路径跟目录为该文件的上一级目录
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger.info(f"root_path: {root_path}")
def load_json(file_path):
    # 检测文件是否存在
    file_path = os.path.join(root_path, file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件 {file_path} 不存在")
    # 读取文件
    with open(file_path, 'r') as file:
        return json.load(file)


