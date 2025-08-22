# 视频浏览器兼容性修复指南

## 问题描述

你遇到的视频预览URL无法播放的问题是由于**视频编码格式不兼容**导致的。具体原因：

1. **原始编码器**: `mp4v` - 生成未压缩的原始视频流
2. **浏览器要求**: H.264编码的MP4文件
3. **兼容性**: `mp4v`格式无法在浏览器中直接播放

## 解决方案

### 方案1: 自动修复（推荐）

运行修复脚本来自动转换现有视频：

```bash
cd PrismFlow
python fix_video_compatibility.py
```

这个脚本会：
- ✅ 扫描所有输出视频
- ✅ 检查兼容性
- ✅ 自动转换为H.264格式
- ✅ 替换原文件

### 方案2: 测试环境兼容性

运行测试脚本检查系统环境：

```bash
cd PrismFlow
python test_video_compatibility.py
```

这个脚本会：
- ✅ 测试OpenCV编码器
- ✅ 检查ffmpeg可用性
- ✅ 创建测试视频
- ✅ 验证兼容性

### 方案3: 手动转换

如果自动修复失败，可以手动转换：

```bash
# 使用ffmpeg转换单个文件
ffmpeg -i input.mp4 -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p -movflags +faststart output.mp4
```

## 技术细节

### 编码器优先级

1. **H.264** - 最佳浏览器兼容性
2. **XVID + ffmpeg转换** - 备选方案
3. **mp4v** - 回退方案（不兼容浏览器）

### 关键参数

```bash
ffmpeg参数说明:
-c:v libx264      # H.264编码器
-preset fast      # 编码速度
-crf 23           # 质量设置（0-51，越低越好）
-pix_fmt yuv420p  # 像素格式（浏览器兼容）
-movflags +faststart  # 优化网络播放
```

### 浏览器兼容性要求

- **编码格式**: H.264/AVC
- **容器格式**: MP4
- **像素格式**: yuv420p
- **元数据**: 需要faststart标志

## 文件说明

### 新增文件

- `video_utils.py` - 视频处理工具模块
- `test_video_compatibility.py` - 兼容性测试脚本
- `fix_video_compatibility.py` - 自动修复脚本

### 修改文件

- `run_v2v_v2_with_lora.py` - 更新视频创建函数
- `run_v2v_v1.py` - 更新视频创建函数
- `run_save.py` - 更新视频创建函数

## 使用步骤

### 1. 立即修复现有视频

```bash
cd PrismFlow
python fix_video_compatibility.py
```

### 2. 重新处理视频

修复后，新生成的视频将自动使用兼容格式：

```bash
python debug_ui_v2.py
```

### 3. 验证修复结果

在浏览器中测试视频预览功能，应该可以正常播放。

## 故障排除

### 问题1: ffmpeg未安装

**症状**: 转换失败，提示"ffmpeg不可用"

**解决方案**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# Windows
# 下载并安装ffmpeg: https://ffmpeg.org/download.html
```

### 问题2: 编码器不可用

**症状**: 提示"H.264编码器不可用"

**解决方案**:
- 确保OpenCV版本支持H.264
- 安装额外的编解码器包
- 使用ffmpeg作为备选方案

### 问题3: 文件权限问题

**症状**: 无法写入输出文件

**解决方案**:
```bash
# 检查目录权限
ls -la outputs/

# 修复权限
chmod 755 outputs/
```

## 性能优化

### 编码速度优化

```bash
# 快速编码（质量稍低）
ffmpeg -preset ultrafast

# 平衡编码（推荐）
ffmpeg -preset fast

# 高质量编码（速度较慢）
ffmpeg -preset slow
```

### 文件大小优化

```bash
# 高质量小文件
ffmpeg -crf 18

# 平衡质量大小
ffmpeg -crf 23

# 小文件优先
ffmpeg -crf 28
```

## 验证结果

修复成功后，你应该看到：

1. ✅ 视频可以在浏览器中正常播放
2. ✅ 预览功能正常工作
3. ✅ 下载的视频文件兼容性良好
4. ✅ 文件大小合理

## 技术支持

如果问题仍然存在，请：

1. 运行测试脚本并分享结果
2. 检查ffmpeg是否正确安装
3. 确认OpenCV版本支持H.264
4. 查看错误日志获取详细信息

---

**注意**: 此修复方案向后兼容，不会影响现有的处理流程，只是改进了输出视频的兼容性。 