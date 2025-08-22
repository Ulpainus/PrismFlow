#!/usr/bin/env python3
"""
视频兼容性修复脚本
用于将不兼容的视频转换为浏览器可播放的格式
"""

import os
import sys
import glob
from video_utils import check_video_compatibility, convert_to_web_compatible

def find_video_files(directory="outputs", pattern="*.mp4"):
    """查找视频文件"""
    search_pattern = os.path.join(directory, "**", pattern)
    video_files = glob.glob(search_pattern, recursive=True)
    return video_files

def analyze_video(video_path):
    """分析视频文件的兼容性"""
    print(f"\n🔍 分析视频: {video_path}")
    
    if not os.path.exists(video_path):
        print("❌ 文件不存在")
        return None
    
    file_size = os.path.getsize(video_path)
    print(f"📏 文件大小: {file_size / (1024*1024):.2f} MB")
    
    # 检查兼容性
    is_compatible, message = check_video_compatibility(video_path)
    print(f"🔍 兼容性: {message}")
    
    return {
        'path': video_path,
        'size': file_size,
        'compatible': is_compatible,
        'message': message
    }

def fix_video(video_path, backup=True):
    """修复视频兼容性"""
    print(f"\n🔧 修复视频: {video_path}")
    
    # 创建备份
    if backup:
        backup_path = video_path + ".backup"
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(video_path, backup_path)
            print(f"💾 创建备份: {backup_path}")
    
    # 创建新的兼容文件名
    name, ext = os.path.splitext(video_path)
    fixed_path = f"{name}_web_compatible{ext}"
    
    # 转换视频
    print(f"🔄 转换为: {fixed_path}")
    success = convert_to_web_compatible(video_path, fixed_path)
    
    if success:
        # 检查转换后的视频
        is_compatible, message = check_video_compatibility(fixed_path)
        if is_compatible:
            print(f"✅ 转换成功: {message}")
            
            # 替换原文件
            os.remove(video_path)
            os.rename(fixed_path, video_path)
            print(f"✅ 已替换原文件")
            return True
        else:
            print(f"⚠️ 转换完成但兼容性警告: {message}")
            return True
    else:
        print("❌ 转换失败")
        # 清理失败的文件
        if os.path.exists(fixed_path):
            os.remove(fixed_path)
        return False

def main():
    """主函数"""
    print("🚀 PrismFlow 视频兼容性修复工具")
    print("=" * 50)
    
    # 查找所有视频文件
    video_files = find_video_files()
    
    if not video_files:
        print("❌ 没有找到视频文件")
        print("💡 请确保在outputs目录下有.mp4文件")
        return
    
    print(f"📁 找到 {len(video_files)} 个视频文件")
    
    # 分析所有视频
    video_analyses = []
    for video_path in video_files:
        analysis = analyze_video(video_path)
        if analysis:
            video_analyses.append(analysis)
    
    # 统计兼容性
    compatible_count = sum(1 for v in video_analyses if v['compatible'])
    incompatible_count = len(video_analyses) - compatible_count
    
    print(f"\n📊 兼容性统计:")
    print(f"  ✅ 兼容: {compatible_count}")
    print(f"  ❌ 不兼容: {incompatible_count}")
    
    if incompatible_count == 0:
        print("\n🎉 所有视频都是浏览器兼容的!")
        return
    
    # 询问是否修复
    print(f"\n🔧 发现 {incompatible_count} 个不兼容的视频文件")
    response = input("是否要修复这些视频? (y/N): ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("❌ 取消修复")
        return
    
    # 修复不兼容的视频
    print("\n🔧 开始修复...")
    fixed_count = 0
    
    for analysis in video_analyses:
        if not analysis['compatible']:
            if fix_video(analysis['path']):
                fixed_count += 1
    
    print(f"\n✅ 修复完成! 成功修复 {fixed_count}/{incompatible_count} 个视频")
    
    # 最终检查
    print("\n🔍 最终兼容性检查...")
    final_video_files = find_video_files()
    final_compatible = 0
    
    for video_path in final_video_files:
        is_compatible, message = check_video_compatibility(video_path)
        if is_compatible:
            final_compatible += 1
        else:
            print(f"⚠️ 仍然不兼容: {video_path} - {message}")
    
    print(f"📊 最终统计: {final_compatible}/{len(final_video_files)} 个视频兼容")

if __name__ == "__main__":
    main() 