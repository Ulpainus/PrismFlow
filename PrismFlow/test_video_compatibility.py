#!/usr/bin/env python3
"""
视频兼容性测试脚本
用于检查系统环境和视频编码能力
"""

import os
import sys
import subprocess
import cv2
import numpy as np
from video_utils import check_video_compatibility, create_browser_compatible_video

def test_opencv_codecs():
    """测试OpenCV可用的编码器"""
    print("🔍 测试OpenCV编码器...")
    
    codecs_to_test = [
        ('H264', 'H.264编码器'),
        ('XVID', 'XVID编码器'),
        ('mp4v', 'MP4V编码器'),
        ('MJPG', 'Motion JPEG编码器'),
        ('X264', 'X264编码器')
    ]
    
    available_codecs = []
    
    for codec, description in codecs_to_test:
        try:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            # 创建临时视频写入器来测试
            temp_path = f"test_{codec.lower()}.mp4"
            out = cv2.VideoWriter(temp_path, fourcc, 30, (640, 480))
            
            if out.isOpened():
                print(f"✅ {codec}: {description} - 可用")
                available_codecs.append(codec)
                out.release()
                # 清理测试文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            else:
                print(f"❌ {codec}: {description} - 不可用")
                
        except Exception as e:
            print(f"❌ {codec}: {description} - 错误: {e}")
    
    return available_codecs

def test_ffmpeg():
    """测试ffmpeg是否可用"""
    print("\n🔍 测试ffmpeg...")
    
    try:
        # 测试ffmpeg版本
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ ffmpeg可用: {version_line}")
            
            # 测试ffprobe
            result2 = subprocess.run(['ffprobe', '-version'], 
                                   capture_output=True, text=True, timeout=10)
            if result2.returncode == 0:
                print("✅ ffprobe可用")
                return True
            else:
                print("❌ ffprobe不可用")
                return False
        else:
            print("❌ ffmpeg不可用")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ ffmpeg测试超时")
        return False
    except FileNotFoundError:
        print("❌ ffmpeg未安装")
        return False
    except Exception as e:
        print(f"❌ ffmpeg测试失败: {e}")
        return False

def create_test_frames():
    """创建测试帧"""
    print("\n🎨 创建测试帧...")
    
    test_dir = "test_frames"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建简单的测试帧
    for i in range(30):  # 30帧
        # 创建渐变图像
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 添加渐变效果
        for y in range(480):
            for x in range(640):
                frame[y, x] = [
                    int(255 * x / 640),  # 红色渐变
                    int(255 * y / 480),  # 绿色渐变
                    int(255 * i / 30)    # 蓝色随时间变化
                ]
        
        # 添加帧号
        cv2.putText(frame, f"Frame {i:02d}", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # 保存帧
        frame_path = os.path.join(test_dir, f"{i:05d}.png")
        cv2.imwrite(frame_path, frame)
    
    print(f"✅ 创建了30个测试帧在 {test_dir}/")
    return test_dir

def test_video_creation():
    """测试视频创建功能"""
    print("\n🎬 测试视频创建...")
    
    # 创建测试帧
    test_dir = create_test_frames()
    
    # 测试不同的输出格式
    test_outputs = [
        "test_output_h264.mp4",
        "test_output_xvid.mp4", 
        "test_output_mp4v.mp4"
    ]
    
    results = {}
    
    for output_path in test_outputs:
        print(f"\n📹 测试创建: {output_path}")
        
        try:
            result = create_browser_compatible_video(test_dir, output_path, 30.0)
            
            if result and os.path.exists(result):
                file_size = os.path.getsize(result)
                print(f"✅ 视频创建成功: {result} ({file_size} bytes)")
                
                # 检查兼容性
                is_compatible, message = check_video_compatibility(result)
                print(f"🔍 兼容性: {message}")
                
                results[output_path] = {
                    'success': True,
                    'path': result,
                    'size': file_size,
                    'compatible': is_compatible,
                    'message': message
                }
            else:
                print(f"❌ 视频创建失败: {output_path}")
                results[output_path] = {'success': False}
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            results[output_path] = {'success': False, 'error': str(e)}
    
    return results

def cleanup_test_files():
    """清理测试文件"""
    print("\n🧹 清理测试文件...")
    
    files_to_remove = [
        "test_frames",
        "test_output_h264.mp4",
        "test_output_xvid.mp4", 
        "test_output_mp4v.mp4",
        "test_temp.avi"
    ]
    
    for item in files_to_remove:
        if os.path.exists(item):
            if os.path.isdir(item):
                import shutil
                shutil.rmtree(item)
            else:
                os.remove(item)
            print(f"🗑️ 删除: {item}")

def main():
    """主测试函数"""
    print("🚀 PrismFlow 视频兼容性测试")
    print("=" * 50)
    
    # 测试OpenCV编码器
    available_codecs = test_opencv_codecs()
    
    # 测试ffmpeg
    ffmpeg_available = test_ffmpeg()
    
    # 测试视频创建
    results = test_video_creation()
    
    # 输出总结
    print("\n" + "=" * 50)
    print("📊 测试总结")
    print("=" * 50)
    
    print(f"🎬 可用编码器: {', '.join(available_codecs) if available_codecs else '无'}")
    print(f"🔄 ffmpeg可用: {'是' if ffmpeg_available else '否'}")
    
    print("\n📹 视频创建结果:")
    for output_path, result in results.items():
        if result.get('success'):
            status = "✅ 成功" if result.get('compatible') else "⚠️ 成功但可能不兼容"
            print(f"  {output_path}: {status} - {result.get('message', '')}")
        else:
            print(f"  {output_path}: ❌ 失败")
    
    # 浏览器兼容性建议
    print("\n💡 浏览器兼容性建议:")
    if any(r.get('compatible') for r in results.values()):
        print("✅ 系统可以创建浏览器兼容的视频")
    elif ffmpeg_available:
        print("⚠️ 建议安装ffmpeg以获得最佳浏览器兼容性")
    else:
        print("❌ 建议安装ffmpeg以支持H.264编码")
    
    # 清理测试文件
    cleanup_test_files()
    
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    main() 