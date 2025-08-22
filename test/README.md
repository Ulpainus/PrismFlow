# PrismFlow v2 视频处理工具

一个功能强大的视频AI处理工具，支持多种处理模式和实时进度监控。

## 🚀 功能特性

- **文件管理**：
  - 安全的视频文件上传 (支持MP4、AVI、MOV等格式)
  - 后端文件存储，支持大文件 (最大500MB)
  - 原版视频文件下载功能

- **多种处理模式**：
  - 快速风格转换 (动漫风)
  - 创意AI重绘 (自定义)
  - 高级组合模式 (效果最佳)

- **高级参数配置**：
  - LoRA模型配置
  - 风格化强度调节
  - 随机种子设置

- **实时进度监控**：
  - 实时进度条更新
  - 详细处理状态显示
  - 文件和任务状态追踪
  - 参数传输确认和验证

## 📦 安装依赖

```bash
npm install
```

## 🔧 运行方式

### 方式一：同时启动前端和后端（推荐）

```bash
npm run dev:full
```

这将同时启动：
- 前端开发服务器 (http://localhost:5173)
- 后端API服务器 (http://localhost:3001)

### 方式二：分别启动

**启动后端服务器：**
```bash
npm run server
```

**启动前端开发服务器：**
```bash
npm run dev
```

## 🌐 访问地址

- **前端界面**: http://localhost:5173
- **后端API**: http://localhost:3001

## 📋 API接口

### 上传视频文件
```
POST /api/upload-video
```
- 使用 multipart/form-data 格式
- 字段名: `video`
- 支持格式: MP4, AVI, MOV等视频格式
- 文件大小限制: 500MB

### 启动处理任务
```
POST /api/start-processing
```

请求体：
```json
{
  "processingMode": "anime-style|creative-ai|advanced-combo",
  "prompt": "处理提示词",
  "loraModel": "none|anime|realistic|sketch",
  "loraWeight": 0.8,
  "styleStrength": 0.75,
  "randomSeed": -1,
  "fileId": "上传文件返回的ID"
}
```

### 获取处理进度
```
GET /api/progress/:taskId
```

### 下载原始视频
```
GET /api/download/:taskId
```
- 返回原始上传的视频文件
- 保持原文件名和格式

### 查看所有任务（调试用）
```
GET /api/tasks
```

## 🎯 使用说明

1. **上传视频**：点击"上传视频文件"按钮选择视频文件，等待上传完成
2. **选择模式**：从三种处理模式中选择一种
3. **配置参数**：根据选择的模式配置相应参数（LoRA、风格强度等）
4. **开始处理**：确认文件上传成功后，点击"开始处理"按钮启动任务
5. **参数验证**：在右侧面板可以看到本地参数和服务器确认的参数对比
6. **监控进度**：观察实时进度更新和处理状态
7. **下载原版**：处理完成后点击右上角下载按钮，下载原始上传的视频文件

## 🛠️ 技术栈

### 前端
- Vue 3
- Vite
- CSS3 (Tailwind风格)

### 后端
- Node.js
- Express.js
- Multer (文件上传处理)
- CORS支持
- 文件系统管理

## 📁 项目结构

```
.
├── src/
│   ├── App.vue          # 主要前端组件
│   ├── main.js          # 前端入口文件
│   └── assets/          # 静态资源
├── server.js            # 后端服务器
├── package.json         # 项目配置
└── README.md           # 项目说明
```

## 🔍 故障排除

### 前端无法连接后端
- 确认后端服务器已启动 (http://localhost:3001)
- 检查控制台是否有CORS错误
- 确认防火墙设置

### 进度不更新
- 检查浏览器网络标签页
- 确认API响应正常
- 检查任务ID是否正确

### 下载失败
- 确认处理已完成
- 检查后端下载接口状态
- 查看浏览器下载设置

## 📝 开发说明

### 修改API地址
如需修改后端地址，请在 `src/App.vue` 中修改：
```javascript
const API_BASE_URL = 'http://localhost:3001/api'
```

### 自定义处理逻辑
在 `server.js` 中的处理进度模拟部分可以替换为实际的AI处理逻辑。

## �� 许可证

MIT License
