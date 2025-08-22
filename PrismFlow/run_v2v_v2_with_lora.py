# 文件名: run_v2v_v2_with_lora.py
# 版本: v2 - 在v1基础上集成LoRA功能，现已集成optical flow稳定化
# 描述: 保持前后端分离架构，扩展process_video_entrypoint函数支持LoRA和optical flow

import os
import torch
import cv2
from PIL import Image
from tqdm import tqdm
import numpy as np
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, UniPCMultistepScheduler
from controlnet_aux import LineartAnimeDetector
import shutil
import time
import gradio as gr

# 从我们创建的库中导入CycleGAN处理器
from cyclegan_lib.cyclegan_processor import CycleGANProcessor

# 【新增】导入optical flow工具
import sys
sys.path.append('optical_flow/scripts')
try:
    from core.local_flow_utils import RAFT_estimate_flow, compute_diff_map, RAFT_clear_memory
    OPTICAL_FLOW_AVAILABLE = True
    print("✅ Optical Flow模块加载成功")
except ImportError as e:
    print(f"⚠️ Optical Flow模块加载失败: {e}")
    print("⚠️ 将使用传统处理方式")
    OPTICAL_FLOW_AVAILABLE = False

# 导入视频工具模块
try:
    from video_utils import create_browser_compatible_video, check_video_compatibility
    VIDEO_UTILS_AVAILABLE = True
    print("✅ 视频工具模块加载成功")
except ImportError as e:
    print(f"⚠️ 视频工具模块加载失败: {e}")
    VIDEO_UTILS_AVAILABLE = False

def setup_directories(output_folder):
    """创建并清理工作目录"""
    input_frames_folder = os.path.join(output_folder, "input_frames")
    output_frames_folder = os.path.join(output_folder, "output_frames")
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(input_frames_folder, exist_ok=True)
    os.makedirs(output_frames_folder, exist_ok=True)
    return input_frames_folder, output_frames_folder

def extract_frames(video_path, output_folder):
    """将视频拆分为帧图片"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"无法打开视频文件: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    frames_list = []  # 【新增】保存帧列表用于optical flow
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # 【新增】转换BGR到RGB并保存到列表
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames_list.append(frame_rgb)
        cv2.imwrite(os.path.join(output_folder, f"{frame_count:05d}.png"), frame)
        frame_count += 1
    cap.release()
    return fps, frame_count, frames_list  # 【新增】返回帧列表

def create_video(frames_folder, output_path, fps):
    """将文件夹中的图片帧合成为视频 - 使用浏览器兼容的编码格式"""
    # 如果视频工具模块可用，使用新的兼容性函数
    if VIDEO_UTILS_AVAILABLE:
        result = create_browser_compatible_video(frames_folder, output_path, fps)
        if result:
            # 检查生成的视频兼容性
            is_compatible, message = check_video_compatibility(result)
            if is_compatible:
                print(f"✅ 视频兼容性检查通过: {message}")
            else:
                print(f"⚠️ 视频兼容性警告: {message}")
            return result
        else:
            print("❌ 浏览器兼容视频创建失败，回退到原始方法")
    
    # 回退到原始方法
    frames = sorted([f for f in os.listdir(frames_folder) if f.endswith('.png')])
    if not frames:
        return None
    
    first_frame_path = os.path.join(frames_folder, frames[0])
    first_frame_img = cv2.imread(first_frame_path)
    height, width, _ = first_frame_img.shape

    # 尝试使用H.264编码器（浏览器兼容）
    try:
        # 方法1: 尝试使用H.264编码器
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            raise Exception("H264编码器不可用")
            
        print(f"🎬 使用H.264编码器创建视频: {width}x{height} @ {fps}fps")
        
    except Exception as e:
        print(f"⚠️ H.264编码器不可用: {e}")
        try:
            # 方法2: 尝试使用XVID编码器
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            output_path_avi = output_path.replace('.mp4', '.avi')
            out = cv2.VideoWriter(output_path_avi, fourcc, fps, (width, height))
            
            if not out.isOpened():
                raise Exception("XVID编码器不可用")
                
            print(f"🎬 使用XVID编码器创建AVI视频: {width}x{height} @ {fps}fps")
            
        except Exception as e2:
            print(f"⚠️ XVID编码器也不可用: {e2}")
            # 方法3: 回退到原始mp4v编码器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            print(f"🎬 使用mp4v编码器创建视频: {width}x{height} @ {fps}fps")

    # 写入帧
    for frame_name in frames:
        frame_path = os.path.join(frames_folder, frame_name)
        img = cv2.imread(frame_path)
        if img is not None:
            out.write(img)
    
    out.release()
    
    # 如果使用了AVI格式，尝试转换为MP4
    if output_path.endswith('.avi') and os.path.exists(output_path_avi):
        try:
            # 使用ffmpeg转换为MP4
            import subprocess
            cmd = [
                'ffmpeg', '-i', output_path_avi, 
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-y', output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ 成功转换为MP4: {output_path}")
                # 删除临时AVI文件
                os.remove(output_path_avi)
            else:
                print(f"⚠️ ffmpeg转换失败: {result.stderr}")
                # 保留AVI文件作为备选
                output_path = output_path_avi
                
        except Exception as e:
            print(f"⚠️ ffmpeg不可用: {e}")
            output_path = output_path_avi
    
    return output_path

# --- 【新增】LoRA加载和管理函数 ---
def load_lora_into_pipeline(pipe, lora_model_name, lora_weight):
    """
    安全地将LoRA模型加载到Stable Diffusion pipeline中
    """
    try:
        if lora_model_name and lora_model_name != "无 (None)":
            lora_path = os.path.join("models/Lora", lora_model_name)
            
            if os.path.exists(lora_path):
                print(f"🎨 正在加载LoRA: {lora_model_name} (权重: {lora_weight})")
                
                # 使用diffusers的LoRA加载方法
                pipe.load_lora_weights(lora_path)
                
                # 设置LoRA权重
                if hasattr(pipe, 'set_lora_scale'):
                    pipe.set_lora_scale(lora_weight)
                
                print(f"✅ LoRA加载成功: {lora_model_name}")
                return True
            else:
                print(f"⚠️ LoRA文件未找到: {lora_path}")
                return False
        else:
            print("ℹ️ 未选择LoRA模型，使用基础模型")
            return True
            
    except Exception as e:
        print(f"❌ LoRA加载失败: {e}")
        print("⚠️ 将继续使用基础模型")
        return False

def unload_lora_from_pipeline(pipe):
    """
    从pipeline中卸载LoRA模型
    """
    try:
        if hasattr(pipe, 'unload_lora_weights'):
            pipe.unload_lora_weights()
            print("🔄 LoRA已卸载")
    except Exception as e:
        print(f"⚠️ LoRA卸载时出错: {e}")

# 【新增】optical flow处理函数
def process_frame_with_optical_flow(
    curr_frame, prev_frame, prev_frame_styled, 
    pipe, preprocessor, prompt, config, 
    device, generator
):
    """
    使用optical flow处理单帧
    """
    if not OPTICAL_FLOW_AVAILABLE or prev_frame_styled is None:
        # 如果optical flow不可用或是第一帧，使用常规处理
        curr_frame_pil = Image.fromarray(curr_frame)
        processed_init_image = curr_frame_pil.resize((config["width"], config["height"]))
        control_image = preprocessor(processed_init_image)
        return pipe(
            prompt=prompt,
            negative_prompt=config["negative_prompt"],
            image=processed_init_image,
            control_image=control_image,
            num_inference_steps=config["steps"],
            strength=config["strength"],
            guidance_scale=config["cfg_scale"],
            generator=generator
        ).images[0]
    
    try:
        # 估计optical flow
        next_flow, prev_flow, occlusion_mask = RAFT_estimate_flow(
            prev_frame, curr_frame, device=device
        )
        
        if next_flow is not None:
            # 创建optical flow参数字典
            flow_args = {
                'occlusion_mask_flow_multiplier': 5.0,  # 光流遮罩倍数
                'occlusion_mask_difo_multiplier': 2.0,   # 原始差异倍数  
                'occlusion_mask_difs_multiplier': 0.0,   # 风格化差异倍数
                'occlusion_mask_blur': 3.0               # 遮罩模糊强度
            }
            
            alpha_mask, warped_styled_frame = compute_diff_map(
                next_flow, prev_flow, prev_frame, curr_frame, 
                prev_frame_styled, flow_args
            )
            
            # 修复扭曲的风格化帧
            warped_styled_frame = (curr_frame.astype(float) * alpha_mask + 
                                 warped_styled_frame.astype(float) * (1 - alpha_mask))
            
            # 使用扭曲帧作为初始图像
            init_image = Image.fromarray(warped_styled_frame.astype(np.uint8))
            mask_coverage = np.mean(alpha_mask)
            print(f"🌊 使用optical flow处理，遮罩覆盖率: {mask_coverage:.3f}")
            
            # 根据遮罩覆盖率选择处理模式
            if mask_coverage > 0.1:  # 如果有足够的变化区域，使用inpainting
                mask_image = Image.fromarray(np.clip(alpha_mask * 255, 0, 255).astype(np.uint8))
                processed_init_image = init_image.resize((config["width"], config["height"]))
                mask_resized = mask_image.resize((config["width"], config["height"]))
                control_image = preprocessor(processed_init_image)
                
                return pipe(
                    prompt=prompt,
                    negative_prompt=config["negative_prompt"],
                    image=processed_init_image,
                    mask_image=mask_resized,
                    control_image=control_image,
                    num_inference_steps=config["steps"],
                    strength=0.85,  # inpainting使用较高强度
                    guidance_scale=config["cfg_scale"],
                    generator=generator
                ).images[0]
            else:
                # 变化较小，使用常规img2img
                processed_init_image = init_image.resize((config["width"], config["height"]))
                control_image = preprocessor(processed_init_image)
                return pipe(
                    prompt=prompt,
                    negative_prompt=config["negative_prompt"],
                    image=processed_init_image,
                    control_image=control_image,
                    num_inference_steps=config["steps"],
                    strength=config["strength"],
                    guidance_scale=config["cfg_scale"],
                    generator=generator
                ).images[0]
        else:
            print("⚠️ Optical flow估计失败，使用常规处理")
            
    except Exception as e:
        print(f"⚠️ Optical flow处理出错: {e}")
    
    # 回退到常规处理
    curr_frame_pil = Image.fromarray(curr_frame)
    processed_init_image = curr_frame_pil.resize((config["width"], config["height"]))
    control_image = preprocessor(processed_init_image)
    return pipe(
        prompt=prompt,
        negative_prompt=config["negative_prompt"],
        image=processed_init_image,
        control_image=control_image,
        num_inference_steps=config["steps"],
        strength=config["strength"],
        guidance_scale=config["cfg_scale"],
        generator=generator
    ).images[0]

def process_video_entrypoint(
    input_video_path,
    prompt,
    strength,
    seed,
    processing_mode,
    lora_model_name,  
    lora_weight,      
    progress=gr.Progress(track_tqdm=True)
):
    """
    v2版本：接收UI参数并执行完整的视频处理流程，支持LoRA功能和optical flow稳定化。
    
    参数说明:
    - input_video_path (str): 输入视频路径
    - prompt (str): 提示词
    - strength (float): 风格化强度
    - seed (int): 随机种子
    - processing_mode (str): 处理模式，可选值为 "Stable Diffusion Only", "CycleGAN Only", "CycleGAN + Stable Diffusion"
    - lora_model_name (str): LoRA模型文件名，"无 (None)" 表示不使用LoRA
    - lora_weight (float): LoRA权重，范围0.0-2.0
    - progress: Gradio进度条对象
    """
    print(f"🎯 v2版本开始处理: 模式={processing_mode}")
    print(f"🎨 LoRA设置: 模型={lora_model_name}, 权重={lora_weight}")
    print(f"🌊 Optical Flow: {'启用' if OPTICAL_FLOW_AVAILABLE and 'Stable Diffusion' in processing_mode else '禁用'}")
    
    if input_video_path is None:
        raise gr.Error("请先上传一个视频！")

    # 1. 参数配置
    config = {
        "output_folder": f"outputs/debug_run_v2_{int(time.time())}",
        "base_model_path": "models/Stable-diffusion/v1-5-pruned-emaonly.safetensors",
        "controlnet_model_path": "models/ControlNet/control_v11p_sd15_lineart.pth",
        "negative_prompt": "low quality, worst quality, blurry, text, logo, watermark, signature",
        "width": 768,
        "height": 512,
        "cfg_scale": 7.5,
        "steps": 20,
        "strength": strength,  
    }

    # 2. 准备工作
    progress(0, desc="准备工作：创建目录...")
    input_frames_dir, output_frames_dir = setup_directories(config["output_folder"])
    
    progress(0.05, desc="准备工作：拆分视频帧...")
    fps, frame_total, frames_list = extract_frames(input_video_path, input_frames_dir)  # 【修改】获取帧列表
    
    # 【新增】调整帧尺寸用于optical flow
    target_size = (config["width"], config["height"])
    frames_resized = []
    for frame in frames_list:
        frame_resized = cv2.resize(frame, target_size)
        frames_resized.append(frame_resized)
    
    # 3. 根据模式，按需加载模型
    device = "cuda"
    cyclegan_processor = None
    pipe = None
    preprocessor = None
    
    # 加载CycleGAN模型
    if "CycleGAN" in processing_mode:
        progress(0.1, desc="加载CycleGAN模型...")
        cyclegan_model_name = "own_cyclegan"
        
        cyclegan_netG = 'resnet_9blocks'
        cyclegan_norm = 'instance'
        cyclegan_no_dropout = True

        cyclegan_processor = CycleGANProcessor(
            model_name=cyclegan_model_name,
            netG=cyclegan_netG,
            norm=cyclegan_norm,
            no_dropout=cyclegan_no_dropout,
            gpu_ids='0',
            generator_suffix='_A',
            preserve_resolution=True
        )
        
    # 加载Stable Diffusion模型
    if "Stable Diffusion" in processing_mode:
        progress(0.2, desc="加载Stable Diffusion和ControlNet模型...")
        controlnet = ControlNetModel.from_single_file(config["controlnet_model_path"], torch_dtype=torch.float16)
        pipe = StableDiffusionControlNetPipeline.from_single_file(
            config["base_model_path"], controlnet=controlnet, torch_dtype=torch.float16, use_safetensors=True
        ).to(device)
        pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
        preprocessor = LineartAnimeDetector.from_pretrained("lllyasviel/Annotators").to(device)
        
        progress(0.25, desc="加载LoRA模型...")
        lora_success = load_lora_into_pipeline(pipe, lora_model_name, lora_weight)
        if not lora_success:
            print("⚠️ LoRA加载失败，将使用基础模型继续处理")

    # 4. 核心处理循环
    generator = torch.Generator(device=device).manual_seed(int(seed)) if seed != -1 else None
    prev_frame_styled = None  # 【新增】用于optical flow的前一帧风格化结果

    with torch.no_grad():
        for i, curr_frame in enumerate(progress.tqdm(frames_resized, desc=f"正在按模式 [{processing_mode}] 处理每一帧")):
            prev_frame = frames_resized[i-1] if i > 0 else None  # 【新增】前一帧
            result_image = None

            if processing_mode == "CycleGAN Only":
                curr_frame_pil = Image.fromarray(curr_frame)
                stylized_image = cyclegan_processor.process_frame(curr_frame_pil)
                
                if i == 0:
                    try:
                        diag_input_path = os.path.join(config["output_folder"], "z_diagnostic_input.png")
                        diag_output_path = os.path.join(config["output_folder"], "z_diagnostic_output.png")
                        curr_frame_pil.save(diag_input_path)
                        stylized_image.save(diag_output_path)
                        print(f"诊断图像已保存: {diag_input_path} 和 {diag_output_path}")
                        print(f"输入尺寸: {curr_frame_pil.size}, 输出尺寸: {stylized_image.size}")
                    except Exception as e:
                        print(f"保存诊断图像时出错: {e}")

                result_image = stylized_image
            
            elif processing_mode == "Stable Diffusion Only":
                # 【新增】使用optical flow增强的Stable Diffusion处理
                result_image = process_frame_with_optical_flow(
                    curr_frame, prev_frame, prev_frame_styled,
                    pipe, preprocessor, prompt, config,
                    device, generator
                )

            elif processing_mode == "CycleGAN + Stable Diffusion":
                curr_frame_pil = Image.fromarray(curr_frame)
                cyclegan_output_image = cyclegan_processor.process_frame(curr_frame_pil)
                cyclegan_output_array = np.array(cyclegan_output_image)
                
                result_image = process_frame_with_optical_flow(
                    cyclegan_output_array, prev_frame, prev_frame_styled,
                    pipe, preprocessor, prompt, config,
                    device, generator
                )
            
            if result_image:
                filename = f"{i:05d}.png"
                result_image.save(os.path.join(output_frames_dir, filename))
                
                # 【新增】更新prev_frame_styled用于下一帧的optical flow
                if "Stable Diffusion" in processing_mode:
                    prev_frame_styled = np.array(result_image)

    # 【新增】清理optical flow模型内存
    if OPTICAL_FLOW_AVAILABLE and "Stable Diffusion" in processing_mode:
        RAFT_clear_memory()

    if pipe and "Stable Diffusion" in processing_mode:
        unload_lora_from_pipeline(pipe)

    # 5. 视频合成
    progress(0.95, desc="正在合成为最终视频...")
    final_video_path = os.path.join(config["output_folder"], "final_video_v2.mp4")
    create_video(output_frames_dir, final_video_path, fps)

    print(f"v2任务完成！输出视频已保存至: {final_video_path}")
    return final_video_path

if __name__ == "__main__":
    print("这是v2版本的模块化视频处理脚本，支持LoRA功能和optical flow稳定化。")
    print("请通过 'debug_ui_v2.py' 来运行带界面的调试。") 