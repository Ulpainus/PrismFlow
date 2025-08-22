# PrismFlow 环境配置指南

## 🚀 快速部署（基于验证环境）

### 前提条件
- Python 3.9
- CUDA 12.6+ (如果使用GPU)
- 至少16GB内存
- 至少50GB磁盘空间

### 步骤1: 创建虚拟环境
```bash
# 创建conda环境
conda create -n prismflow python=3.9 -y
conda activate prismflow

# 或使用venv
python3.9 -m venv prismflow
source prismflow/bin/activate  # Linux/Mac
# 或 prismflow\Scripts\activate  # Windows
```

### 步骤2: 安装PyTorch (CUDA版本)
```bash
# 安装PyTorch 2.7.1 + CUDA 12.6
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu126
```

### 步骤3: 安装PrismFlow依赖
```bash
# 克隆项目
git clone <your-prismflow-repo>
cd PrismFlow

# 安装精确版本依赖
pip install -r requirements.txt
```

### 步骤4: 验证安装
```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA可用: {torch.cuda.is_available()}')"
python -c "import gradio; print(f'Gradio: {gradio.__version__}')"
```

## 🌐 云端服务器运行

### 启动界面
```bash
cd PrismFlow
python debug_ui_v2.py
```

### 云端访问配置
- 脚本会自动检测云端环境
- 启用Gradio分享链接 (`share=True`)
- 生成公共访问URL (格式: `https://xxxxx.gradio.live`)

### 防火墙配置（如需要）
```bash
# Ubuntu/Debian
sudo ufw allow 7860

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=7860/tcp
sudo firewall-cmd --reload
```

## 📦 模型文件配置

### 目录结构
```
PrismFlow/
├── models/
│   ├── Stable-diffusion/
│   │   └── v1-5-pruned-emaonly.safetensors
│   ├── ControlNet/
│   │   └── control_v11p_sd15_lineart.pth
│   ├── Lora/
│   │   └── (可选LoRA模型.safetensors)
│   └── RAFT/
│       └── raft-sintel.pth
└── cyclegan_lib/
    └── checkpoints/
        └── own_cyclegan/
```

### 模型下载链接
- **Stable Diffusion v1.5**: https://huggingface.co/runwayml/stable-diffusion-v1-5
- **ControlNet LineArt**: https://huggingface.co/lllyasviel/ControlNet-v1-1
- **RAFT模型**: https://drive.google.com/uc?id=1MqDajR89k-xLV0HIrmJ0k-n8ZpG6_suM

## 🔧 故障排除

### 常见问题

#### 1. Gradio版本冲突
```bash
# 如果遇到pydantic兼容性问题
pip install gradio==3.50.2 pydantic==1.10.22
```

#### 2. CUDA内存不足
```bash
# 设置环境变量限制内存使用
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

#### 3. 模型下载失败
```bash
# 手动创建模型目录
mkdir -p models/{Stable-diffusion,ControlNet,Lora,RAFT}
mkdir -p cyclegan_lib/checkpoints/own_cyclegan
```

#### 4. 云端访问问题
- 确保使用 `share=True` 启动
- 检查防火墙设置
- 确认服务器网络策略

## 🎯 性能优化

### GPU内存优化
```python
# 在运行前设置
import torch
torch.backends.cudnn.benchmark = True
torch.backends.cuda.matmul.allow_tf32 = True
```

### CPU优化
```bash
# 设置OpenMP线程数
export OMP_NUM_THREADS=4
```

## 📝 版本信息

**验证环境配置**:
- Python: 3.9
- PyTorch: 2.7.1
- CUDA: 12.6
- Gradio: 3.50.2
- GPU: Tesla V100-SXM2-32GB

**成功测试平台**:
- ✅ Ubuntu Server (云端)
- ✅ Windows 10/11 (本地)
- ✅ Linux 服务器

## 🆘 技术支持

如果遇到问题，请提供：
1. 操作系统版本
2. Python版本 (`python --version`)
3. PyTorch版本和CUDA可用性
4. 错误日志完整信息
5. 显卡型号和显存大小

---

**最后更新**: 基于成功运行的云端服务器环境验证 