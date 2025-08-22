"""
视频处理工具模块 - 专门解决浏览器兼容性问题
"""

import cv2
import os
import subprocess
import tempfile
from typing import Optional, Tuple

def create_browser_compatible_video(frames_folder: str, output_path: str, fps: float) -> Optional[str]:
    """
    创建浏览器兼容的视频文件
    
    支持的编码格式优先级：
    1. H.264 (最佳浏览器兼容性)
    2. XVID + ffmpeg转换
    3. mp4v (回退方案)
    
    Args:
        frames_folder: 包含PNG帧的文件夹路径
        output_path: 输出视频文件路径
        fps: 帧率
        
    Returns:
        成功时返回输出文件路径，失败时返回None
    """
    
    frames = sorted([f for f in os.listdir(frames_folder) if f.endswith('.png')])
    if not frames:
        print("❌ 没有找到PNG帧文件")
        return None
    
    # 获取第一帧的尺寸
    first_frame_path = os.path.join(frames_folder, frames[0])
    first_frame_img = cv2.imread(first_frame_path)
    if first_frame_img is None:
        print("❌ 无法读取第一帧")
        return None
        
    height, width, _ = first_frame_img.shape
    print(f"📐 视频尺寸: {width}x{height}, 帧率: {fps}")
    
    # 方法1: 尝试直接使用H.264编码器
    if try_h264_encoding(frames_folder, output_path, fps, width, height):
        return output_path
    
    # 方法2: 使用XVID编码器 + ffmpeg转换
    if try_xvid_with_ffmpeg(frames_folder, output_path, fps, width, height):
        return output_path
    
    # 方法3: 回退到mp4v编码器
    if try_mp4v_encoding(frames_folder, output_path, fps, width, height):
        return output_path
    
    print("❌ 所有编码方法都失败了")
    return None

def try_h264_encoding(frames_folder: str, output_path: str, fps: float, width: int, height: int) -> bool:
    """尝试使用H.264编码器"""
    try:
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            print("⚠️ H.264编码器不可用")
            return False
            
        print("🎬 使用H.264编码器创建视频...")
        
        # 写入所有帧
        for frame_name in sorted([f for f in os.listdir(frames_folder) if f.endswith('.png')]):
            frame_path = os.path.join(frames_folder, frame_name)
            img = cv2.imread(frame_path)
            if img is not None:
                out.write(img)
        
        out.release()
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"✅ H.264视频创建成功: {output_path}")
            return True
        else:
            print("❌ H.264视频文件无效")
            return False
            
    except Exception as e:
        print(f"⚠️ H.264编码失败: {e}")
        return False

def try_xvid_with_ffmpeg(frames_folder: str, output_path: str, fps: float, width: int, height: int) -> bool:
    """使用XVID编码器 + ffmpeg转换为H.264"""
    try:
        # 创建临时AVI文件
        temp_avi = output_path.replace('.mp4', '_temp.avi')
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(temp_avi, fourcc, fps, (width, height))
        
        if not out.isOpened():
            print("⚠️ XVID编码器不可用")
            return False
            
        print("🎬 使用XVID编码器创建临时AVI...")
        
        # 写入所有帧
        for frame_name in sorted([f for f in os.listdir(frames_folder) if f.endswith('.png')]):
            frame_path = os.path.join(frames_folder, frame_name)
            img = cv2.imread(frame_path)
            if img is not None:
                out.write(img)
        
        out.release()
        
        if not os.path.exists(temp_avi) or os.path.getsize(temp_avi) == 0:
            print("❌ 临时AVI文件创建失败")
            return False
        
        # 使用ffmpeg转换为H.264 MP4
        print("🔄 使用ffmpeg转换为H.264 MP4...")
        cmd = [
            'ffmpeg', '-i', temp_avi,
            '-c:v', 'libx264',           # H.264编码器
            '-preset', 'fast',           # 编码速度
            '-crf', '23',                # 质量设置
            '-pix_fmt', 'yuv420p',       # 像素格式（浏览器兼容）
            '-movflags', '+faststart',   # 优化网络播放
            '-y',                        # 覆盖输出文件
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 清理临时文件
        if os.path.exists(temp_avi):
            os.remove(temp_avi)
        
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"✅ ffmpeg转换成功: {output_path}")
            return True
        else:
            print(f"❌ ffmpeg转换失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"⚠️ XVID+ffmpeg方法失败: {e}")
        # 清理临时文件
        if 'temp_avi' in locals() and os.path.exists(temp_avi):
            os.remove(temp_avi)
        return False

def try_mp4v_encoding(frames_folder: str, output_path: str, fps: float, width: int, height: int) -> bool:
    """回退到mp4v编码器"""
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            print("⚠️ mp4v编码器不可用")
            return False
            
        print("🎬 使用mp4v编码器创建视频（浏览器可能无法播放）...")
        
        # 写入所有帧
        for frame_name in sorted([f for f in os.listdir(frames_folder) if f.endswith('.png')]):
            frame_path = os.path.join(frames_folder, frame_name)
            img = cv2.imread(frame_path)
            if img is not None:
                out.write(img)
        
        out.release()
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"⚠️ mp4v视频创建成功（但浏览器可能无法播放）: {output_path}")
            return True
        else:
            print("❌ mp4v视频文件无效")
            return False
            
    except Exception as e:
        print(f"⚠️ mp4v编码失败: {e}")
        return False

def check_video_compatibility(video_path: str) -> Tuple[bool, str]:
    """
    检查视频文件的浏览器兼容性
    
    Returns:
        (is_compatible, message)
    """
    if not os.path.exists(video_path):
        return False, "文件不存在"
    
    try:
        # 使用ffprobe检查视频信息
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"无法读取视频信息: {result.stderr}"
        
        import json
        info = json.loads(result.stdout)
        
        # 检查视频流
        video_streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'video']
        if not video_streams:
            return False, "没有找到视频流"
        
        video_stream = video_streams[0]
        codec_name = video_stream.get('codec_name', '').lower()
        
        # 检查编码格式
        if codec_name in ['h264', 'avc']:
            return True, "H.264编码 - 浏览器兼容"
        elif codec_name in ['mp4v', 'mpeg4']:
            return False, "MP4V编码 - 浏览器不兼容"
        elif codec_name in ['xvid']:
            return False, "XVID编码 - 浏览器不兼容"
        else:
            return False, f"未知编码格式: {codec_name}"
            
    except Exception as e:
        return False, f"检查失败: {str(e)}"

def convert_to_web_compatible(input_path: str, output_path: str) -> bool:
    """
    将任意视频转换为Web兼容格式
    
    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        
    Returns:
        转换是否成功
    """
    try:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264',           # H.264编码器
            '-preset', 'fast',           # 编码速度
            '-crf', '23',                # 质量设置
            '-pix_fmt', 'yuv420p',       # 像素格式（浏览器兼容）
            '-movflags', '+faststart',   # 优化网络播放
            '-y',                        # 覆盖输出文件
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"✅ 视频转换成功: {output_path}")
            return True
        else:
            print(f"❌ 视频转换失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"⚠️ 视频转换失败: {e}")
        return False 