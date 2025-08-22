from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
import threading
import time
from datetime import datetime
import shutil
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import traceback
import json

# 导入真实的视频处理函数
try:
    from run_v2v_v2_with_lora import process_video_entrypoint
    PROCESSING_AVAILABLE = True
    print("✅ 视频处理模块加载成功")
except ImportError as e:
    print(f"❌ 视频处理模块加载失败: {e}")
    PROCESSING_AVAILABLE = False

app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 配置
UPLOAD_FOLDER = 'outputs'
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 全局变量
processing_tasks = {}  # 存储任务状态
uploaded_files = {}   # 存储上传的文件信息

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_task_id():
    """生成唯一任务ID"""
    return f"task_{int(time.time())}_{str(uuid.uuid4())[:8]}"

def get_lora_files():
    """扫描LoRA模型目录，返回可用的LoRA模型列表"""
    lora_dir = "models/Lora"
    try:
        if os.path.exists(lora_dir):
            lora_files = [f for f in os.listdir(lora_dir) if f.endswith('.safetensors')]
            return ["none"] + lora_files if lora_files else ["none"]
        else:
            print(f"⚠️ LoRA目录未找到: {lora_dir}")
            return ["none"]
    except Exception as e:
        print(f"❌ 扫描LoRA目录时出错: {e}")
        return ["none"]

class ProcessingProgress:
    """处理进度跟踪类"""
    def __init__(self, task_id):
        self.task_id = task_id
        self.current_step = 0
        self.total_steps = 100
        self.current_substep = 0
        self.total_substeps = 20
        self.progress = 0.0
        self.message = "正在初始化..."
        self.completed = False
        self.error = None
        self.start_time = time.time()
    
    def update(self, current, total, message):
        """更新进度"""
        self.current_step = current
        self.total_steps = total
        self.progress = (current / total) * 100 if total > 0 else 0
        self.message = message
        
        # 更新任务状态
        if self.task_id in processing_tasks:
            processing_tasks[self.task_id]['progress_obj'] = self
    
    def complete(self, output_path):
        """标记完成"""
        self.completed = True
        self.progress = 100.0
        self.current_step = self.total_steps
        self.message = "处理完成"
        if self.task_id in processing_tasks:
            processing_tasks[self.task_id]['output_path'] = output_path
            processing_tasks[self.task_id]['completed'] = True
    
    def set_error(self, error_msg):
        """设置错误状态"""
        self.error = error_msg
        self.completed = True
        self.message = f"处理失败: {error_msg}"

def process_video_async(task_id, input_path, params):
    """异步处理视频的函数"""
    try:
        print(f"🚀 开始异步处理任务: {task_id}")
        print(f"📋 处理参数: {params}")
        
        # 创建进度追踪器
        progress_tracker = ProcessingProgress(task_id)
        processing_tasks[task_id]['progress_obj'] = progress_tracker
        
        # 更新初始状态
        progress_tracker.update(0, 100, "正在初始化处理流程...")
        
        # 准备处理参数
        processing_mode = params.get('processingMode', 'anime-style')
        prompt = params.get('prompt', 'a beautiful sketch, line art, clean lines')
        lora_model = params.get('loraModel', 'none')
        lora_weight = float(params.get('loraWeight', 0.8))
        style_strength = float(params.get('styleStrength', 0.75))
        random_seed = int(params.get('randomSeed', -1))
        
        # 映射处理模式到内部格式
        mode_mapping = {
            'anime-style': 'CycleGAN Only',
            'creative-ai': 'Stable Diffusion Only', 
            'advanced-combo': 'CycleGAN + Stable Diffusion'
        }
        internal_mode = mode_mapping.get(processing_mode, 'CycleGAN Only')
        
        print(f"🎯 内部处理模式: {internal_mode}")
        print(f"🎨 LoRA配置: 模型={lora_model}, 权重={lora_weight}")
        
        # 创建模拟的Gradio进度对象
        class MockGradioProgress:
            def __init__(self, progress_tracker):
                self.progress_tracker = progress_tracker
                self.total_steps = 100
                
            def __call__(self, progress, desc="处理中"):
                current_step = int(progress * self.total_steps)
                self.progress_tracker.update(current_step, self.total_steps, desc)
                print(f"📊 进度更新: {current_step}/{self.total_steps} - {desc}")
                
            def tqdm(self, iterable, desc="处理中"):
                for i, item in enumerate(iterable):
                    progress = (i + 1) / len(iterable)
                    self(progress, desc)
                    yield item
        
        mock_progress = MockGradioProgress(progress_tracker)
        
        # 调用真实的处理函数
        output_path = process_video_entrypoint(
            input_video_path=input_path,
            prompt=prompt,
            strength=style_strength,
            seed=random_seed,
            processing_mode=internal_mode,
            lora_model_name=lora_model,
            lora_weight=lora_weight,
            progress=mock_progress
        )
        
        if output_path and os.path.exists(output_path):
            progress_tracker.complete(output_path)
            print(f"✅ 任务 {task_id} 处理完成: {output_path}")
        else:
            raise Exception("处理完成但未生成输出文件")
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 任务 {task_id} 处理失败: {error_msg}")
        print(f"🔍 错误详情: {traceback.format_exc()}")
        if task_id in processing_tasks:
            processing_tasks[task_id]['progress_obj'].set_error(error_msg)

@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    """上传视频文件接口"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['video']
        if file.filename == '' or file.filename is None:
            return jsonify({'error': '没有选择文件'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式'}), 400
        
        # 生成文件ID和安全文件名
        file_id = generate_task_id()
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        saved_filename = f"{file_id}.{file_extension}"
        filepath = os.path.join(UPLOAD_FOLDER, saved_filename)
        
        # 保存文件
        file.save(filepath)
        
        # 保存文件信息
        file_info = {
            'id': file_id,
            'originalName': filename,
            'filename': saved_filename,
            'path': filepath,
            'size': os.path.getsize(filepath),
            'mimetype': file.content_type,
            'uploadTime': datetime.now().isoformat()
        }
        
        uploaded_files[file_id] = file_info
        
        print(f"📁 文件上传成功: {filename} -> {saved_filename}")
        
        return jsonify({
            'success': True,
            'fileId': file_id,
            'originalName': filename,
            'size': file_info['size'],
            'message': '文件上传成功'
        })
        
    except RequestEntityTooLarge:
        return jsonify({'error': '文件太大，超过500MB限制'}), 413
    except Exception as e:
        print(f"❌ 文件上传失败: {e}")
        return jsonify({'error': f'文件上传失败: {str(e)}'}), 500

@app.route('/api/start-processing', methods=['POST'])
def start_processing():
    """开始处理视频接口"""
    try:
        if not PROCESSING_AVAILABLE:
            return jsonify({'error': '视频处理模块不可用'}), 500
        
        data = request.json
        if data is None:
            return jsonify({'error': '无效的请求数据'}), 400
            
        file_id = data.get('fileId')
        
        if not file_id or file_id not in uploaded_files:
            return jsonify({'error': '无效的文件ID'}), 400
        
        file_info = uploaded_files[file_id]
        input_path = file_info['path']
        
        if not os.path.exists(input_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 参数类型转换和验证
        try:
            lora_weight = float(data.get('loraWeight', 0.8)) if data.get('loraWeight') is not None else 0.8
            style_strength = float(data.get('styleStrength', 0.75)) if data.get('styleStrength') is not None else 0.75
            random_seed = int(data.get('randomSeed', -1)) if data.get('randomSeed') is not None else -1
            
            # 参数范围验证
            if not (0.0 <= lora_weight <= 2.0):
                return jsonify({'error': 'LoRA权重必须在0.0-2.0范围内'}), 400
            if not (0.0 <= style_strength <= 1.0):
                return jsonify({'error': '风格强度必须在0.0-1.0范围内'}), 400
                
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'参数类型错误: {str(e)}'}), 400
        
        # 创建任务记录
        task_record = {
            'id': task_id,
            'status': 'processing',
            'fileId': file_id,
            'originalFile': file_info,
            'parameters': {
                'processingMode': data.get('processingMode', 'anime-style'),
                'prompt': data.get('prompt', ''),
                'loraModel': data.get('loraModel', 'none'),
                'loraWeight': lora_weight,
                'styleStrength': style_strength,
                'randomSeed': random_seed
            },
            'startTime': time.time(),
            'completed': False,
            'output_path': None,
            'progress_obj': None
        }
        
        processing_tasks[task_id] = task_record
        
        print(f"🚀 启动处理任务: {task_id}")
        print(f"📋 任务参数: {task_record['parameters']}")
        
        # 在新线程中启动处理
        thread = threading.Thread(
            target=process_video_async,
            args=(task_id, input_path, task_record['parameters'])
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'taskId': task_id,
            'status': 'started',
            'message': '处理任务已启动'
        })
        
    except Exception as e:
        print(f"❌ 启动处理失败: {e}")
        return jsonify({'error': f'启动处理失败: {str(e)}'}), 500

@app.route('/api/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """获取处理进度接口"""
    try:
        if task_id not in processing_tasks:
            return jsonify({'error': '任务不存在'}), 404
        
        task = processing_tasks[task_id]
        progress_obj = task.get('progress_obj')
        
        if not progress_obj:
            # 如果还没有进度对象，返回初始状态
            return jsonify({
                'id': task_id,
                'status': 'initializing',
                'progress': 0,
                'currentStep': 0,
                'totalSteps': 100,
                'currentSubstep': 0,
                'totalSubsteps': 20,
                'timeElapsed': int(time.time() - task['startTime']),
                'mode': task['parameters']['processingMode'],
                'message': '正在初始化...',
                'completed': False,
                'downloadUrl': None,
                'previewUrl': None,
                'parameters': task['parameters'],
                'fileInfo': {
                    'id': task['fileId'],
                    'originalName': task['originalFile']['originalName'],
                    'size': task['originalFile']['size'],
                    'uploadTime': task['originalFile']['uploadTime']
                }
            })
        
        # 计算进度百分比
        progress_percent = min(progress_obj.progress, 100)
        
        response_data = {
            'id': task_id,
            'status': 'completed' if progress_obj.completed else 'processing',
            'progress': progress_percent,
            'currentStep': progress_obj.current_step,
            'totalSteps': progress_obj.total_steps,
            'currentSubstep': progress_obj.current_substep,
            'totalSubsteps': progress_obj.total_substeps,
            'timeElapsed': int(time.time() - task['startTime']),
            'mode': task['parameters']['processingMode'],
            'message': progress_obj.message,
            'completed': progress_obj.completed,
            'downloadUrl': f'/api/download/{task_id}' if progress_obj.completed and not progress_obj.error else None,
            'previewUrl': f'/api/download/{task_id}?preview=true' if progress_obj.completed and not progress_obj.error else None,
            'parameters': task['parameters'],
            'fileInfo': {
                'id': task['fileId'],
                'originalName': task['originalFile']['originalName'],
                'size': task['originalFile']['size'],
                'uploadTime': task['originalFile']['uploadTime']
            }
        }
        
        if progress_obj.error:
            response_data['error'] = progress_obj.error
            response_data['status'] = 'error'
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ 获取进度失败: {e}")
        return jsonify({'error': f'获取进度失败: {str(e)}'}), 500

@app.route('/api/download/<task_id>', methods=['GET'])
def download_video(task_id):
    """下载/预览处理结果接口"""
    try:
        if task_id not in processing_tasks:
            return jsonify({'error': '任务不存在'}), 404
        
        task = processing_tasks[task_id]
        
        if not task.get('completed'):
            return jsonify({'error': '任务尚未完成'}), 400
        
        output_path = task.get('output_path')
        if not output_path or not os.path.exists(output_path):
            return jsonify({'error': '输出文件不存在'}), 404
        
        # 检查是否为预览模式
        preview_mode = request.args.get('preview') == 'true'
        
        # 获取原始文件名并添加处理标识
        original_name = task['originalFile']['originalName']
        name_without_ext = os.path.splitext(original_name)[0]
        ext = os.path.splitext(original_name)[1]
        processed_filename = f"{name_without_ext}_processed{ext}"
        
        if preview_mode:
            print(f"🎬 开始预览文件: {processed_filename}")
            # 预览模式：设置为inline，浏览器会直接播放
            return send_file(
                output_path,
                as_attachment=False,  # 不作为附件下载
                download_name=processed_filename,
                mimetype='video/mp4'
            )
        else:
            print(f"📥 开始下载文件: {processed_filename}")
            # 下载模式：设置为attachment，浏览器会下载
            return send_file(
                output_path,
                as_attachment=True,
                download_name=processed_filename,
                mimetype='video/mp4'
            )
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return jsonify({'error': f'操作失败: {str(e)}'}), 500

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """获取所有任务状态（调试用）"""
    tasks_info = []
    for task_id, task in processing_tasks.items():
        progress_obj = task.get('progress_obj')
        task_info = {
            'id': task_id,
            'status': 'completed' if task.get('completed') else 'processing',
            'fileId': task['fileId'],
            'startTime': task['startTime'],
            'parameters': task['parameters']
        }
        if progress_obj:
            task_info['progress'] = progress_obj.progress
            task_info['message'] = progress_obj.message
            task_info['error'] = progress_obj.error
        tasks_info.append(task_info)
    
    return jsonify({
        'tasks': tasks_info,
        'total': len(tasks_info)
    })

@app.route('/', methods=['GET'])
def root():
    """根路径信息"""
    return jsonify({
        'message': '🚀 PrismFlow v2 视频处理服务器 (真实处理版本)',
        'status': 'running',
        'processing_available': PROCESSING_AVAILABLE,
        'endpoints': {
            'POST /api/upload-video': '上传视频文件',
            'POST /api/start-processing': '开始处理任务',
            'GET /api/progress/:taskId': '获取处理进度',
            'GET /api/download/:taskId': '下载处理结果',
            'GET /api/download/:taskId?preview=true': '预览处理结果（在线播放）',
            'GET /api/tasks': '查看所有任务'
        },
        'frontend': 'http://localhost:5173',
        'version': '2.0.0-real',
        'features': {
            'video_preview': '支持生成视频的在线预览',
            'lora_models': '支持LoRA模型深度配置',
            'real_processing': '真实视频处理功能'
        }
    })

def cleanup_old_tasks():
    """定期清理旧任务"""
    current_time = time.time()
    to_remove = []
    
    for task_id, task in processing_tasks.items():
        # 清理1小时前完成的任务
        if task.get('completed') and (current_time - task['startTime']) > 3600:
            to_remove.append(task_id)
    
    for task_id in to_remove:
        del processing_tasks[task_id]
        print(f"🗑️ 清理旧任务: {task_id}")

def start_cleanup_timer():
    """启动清理定时器"""
    def cleanup_loop():
        while True:
            time.sleep(300)  # 每5分钟清理一次
            cleanup_old_tasks()
    
    cleanup_thread = threading.Thread(target=cleanup_loop)
    cleanup_thread.daemon = True
    cleanup_thread.start()

if __name__ == "__main__":
    print("🚀 启动 PrismFlow v2 真实处理服务器...")
    print(f"✨ 视频处理可用: {'是' if PROCESSING_AVAILABLE else '否'}")
    print(f"📂 上传目录: {UPLOAD_FOLDER}")
    print(f"📏 最大文件大小: {MAX_FILE_SIZE // (1024*1024)}MB")
    print(f"🎨 支持的LoRA模型: {get_lora_files()}")
    
    # 启动清理定时器
    start_cleanup_timer()
    
    # 启动Flask服务器
    app.run(
        host='0.0.0.0',  # CloudStudio环境需要监听所有接口
        port=3001,  # 使用与原server.js相同的端口
        debug=True,
        threaded=True
    ) 