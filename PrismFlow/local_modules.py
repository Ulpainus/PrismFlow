# local_modules.py
# 为PrismFlow项目提供路径配置

import os

class paths:
    """路径配置类"""
    # 项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # 模型存储路径
    models_path = os.path.join(project_root, "models")
    
    # 确保目录存在
    os.makedirs(models_path, exist_ok=True)
    os.makedirs(os.path.join(models_path, "RAFT"), exist_ok=True)

# 兼容性别名
models_path = paths.models_path 