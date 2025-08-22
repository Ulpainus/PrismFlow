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
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imwrite(os.path.join(output_folder, f"{frame_count:05d}.png"), frame)
        frame_count += 1
    cap.release()
    return fps, frame_count

def create_video(frames_folder, output_path, fps):
    """将文件夹中的图片帧合成为视频 - 使用浏览器兼容的编码格式"""
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

def process_video_entrypoint(
    input_video_path,
    prompt,
    strength,
    seed,
    processing_mode, 
    progress=gr.Progress(track_tqdm=True)
):
    """
    接收UI参数并执行完整的视频处理流程。
    
    新增参数:
    - processing_mode (str): 处理模式，可选值为 "Stable Diffusion Only", "CycleGAN Only", "CycleGAN + Stable Diffusion"
    """
    if input_video_path is None:
        raise gr.Error("请先上传一个视频！")

    # 1. 参数配置
    config = {
        "output_folder": f"outputs/debug_run_{int(time.time())}",
        "base_model_path": "models/Stable-diffusion/v1-5-pruned-emaonly.safetensors",
        "controlnet_model_path": "models/ControlNet/control_v11p_sd15_lineart.pth",
        "negative_prompt": "low quality, worst quality, blurry, text, logo, watermark, signature",
        "width": 768,
        "height": 512,
        "cfg_scale": 7.5,
        "steps": 20,
    }

    # 2. 准备工作
    progress(0, desc="准备工作：创建目录...")
    input_frames_dir, output_frames_dir = setup_directories(config["output_folder"])
    
    progress(0.05, desc="准备工作：拆分视频帧...")
    fps, frame_total = extract_frames(input_video_path, input_frames_dir)
    
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

    # 4. 核心处理循环
    input_frame_files = sorted(os.listdir(input_frames_dir))
    generator = torch.Generator(device=device).manual_seed(int(seed)) if seed != -1 else None

    with torch.no_grad():
        for filename in progress.tqdm(input_frame_files, desc=f"正在按模式 [{processing_mode}] 处理每一帧"):
            frame_path = os.path.join(input_frames_dir, filename)
            init_image = Image.open(frame_path).convert("RGB")
            
            original_width, original_height = init_image.size
            
            result_image = None 

            if processing_mode == "CycleGAN Only":
                stylized_image = cyclegan_processor.process_frame(init_image)
                
                if filename == input_frame_files[0]:
                    try:
                        diag_input_path = os.path.join(config["output_folder"], "z_diagnostic_input.png")
                        diag_output_path = os.path.join(config["output_folder"], "z_diagnostic_output.png")
                        init_image.save(diag_input_path)
                        stylized_image.save(diag_output_path)
                        print(f"诊断图像已保存: {diag_input_path} 和 {diag_output_path}")
                        print(f"输入尺寸: {init_image.size}, 输出尺寸: {stylized_image.size}")
                    except Exception as e:
                        print(f"保存诊断图像时出错: {e}")

                result_image = stylized_image
            
            elif processing_mode == "Stable Diffusion Only":
                processed_init_image = init_image.resize((config["width"], config["height"]))
                control_image = preprocessor(processed_init_image)
                result_image = pipe(
                    prompt=prompt,
                    negative_prompt=config["negative_prompt"],
                    image=processed_init_image,
                    control_image=control_image,
                    num_inference_steps=config["steps"],
                    strength=strength,
                    guidance_scale=config["cfg_scale"],
                    generator=generator
                ).images[0]

            elif processing_mode == "CycleGAN + Stable Diffusion":
                cyclegan_output_image = cyclegan_processor.process_frame(init_image)
                processed_init_image = cyclegan_output_image.resize((config["width"], config["height"]))
                control_image = preprocessor(processed_init_image)
                result_image = pipe(
                    prompt=prompt,
                    negative_prompt=config["negative_prompt"],
                    image=processed_init_image,
                    control_image=control_image,
                    num_inference_steps=config["steps"],
                    strength=strength,
                    guidance_scale=config["cfg_scale"],
                    generator=generator
                ).images[0]
            
            if result_image:
                result_image.save(os.path.join(output_frames_dir, filename))

    # 5. 视频合成
    progress(0.95, desc="正在合成为最终视频...")
    final_video_path = os.path.join(config["output_folder"], "final_video.mp4")
    create_video(output_frames_dir, final_video_path, fps)

    print(f"任务完成！输出视频已保存至: {final_video_path}")
    return final_video_path

if __name__ == "__main__":
    print("这是一个模块化的视频处理脚本。")
    print("请通过 'debug_ui.py' 来运行带界面的调试。")
