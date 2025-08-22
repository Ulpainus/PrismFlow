import express from 'express';
import cors from 'cors';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const port = 3001;

// 创建uploads目录
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir);
}

// 启用CORS
app.use(cors());
app.use(express.json());

// 配置multer用于文件上传
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadsDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
  }
});

const upload = multer({ 
  storage: storage,
  fileFilter: (req, file, cb) => {
    // 只允许视频文件
    if (file.mimetype.startsWith('video/')) {
      cb(null, true);
    } else {
      cb(new Error('只允许上传视频文件'));
    }
  },
  limits: {
    fileSize: 500 * 1024 * 1024 // 限制500MB
  }
});

// 存储处理任务的状态
const processingTasks = new Map();

// 存储上传的文件信息
const uploadedFiles = new Map();

// 生成唯一任务ID
function generateTaskId() {
  return 'task_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// 文件上传接口
app.post('/api/upload-video', upload.single('video'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: '没有上传文件' });
    }

    const fileInfo = {
      id: generateTaskId(),
      originalName: req.file.originalname,
      filename: req.file.filename,
      path: req.file.path,
      size: req.file.size,
      mimetype: req.file.mimetype,
      uploadTime: new Date().toISOString()
    };

    // 保存文件信息
    uploadedFiles.set(fileInfo.id, fileInfo);

    console.log('📁 文件上传成功:', fileInfo);

    res.json({
      success: true,
      fileId: fileInfo.id,
      originalName: fileInfo.originalName,
      size: fileInfo.size,
      message: '文件上传成功'
    });
  } catch (error) {
    console.error('文件上传失败:', error);
    res.status(500).json({ error: '文件上传失败' });
  }
});

// 启动视频处理任务
app.post('/api/start-processing', (req, res) => {
  const { processingMode, prompt, loraModel, loraWeight, styleStrength, randomSeed, fileId } = req.body;
  
  console.log('📋 收到处理请求，参数详情:');
  console.log('   - 处理模式:', processingMode);
  
  // 只有creative-ai模式才显示详细参数
  if (processingMode === 'creative-ai') {
    console.log('   - 提示词:', prompt);
    console.log('   - LoRA模型:', loraModel);
    console.log('   - LoRA权重:', loraWeight);
    console.log('   - 风格强度:', styleStrength);
    console.log('   - 随机种子:', randomSeed);
  }
  
  console.log('   - 文件ID:', fileId);
  
  const taskId = generateTaskId();
  
  // 随机生成总步数，让每次处理都不一样
  const randomTotalSteps = Math.floor(Math.random() * 200) + 500; // 500-700步
  const randomTotalSubsteps = Math.floor(Math.random() * 15) + 20; // 20-35子步骤
  
  // 初始化任务状态
  const task = {
    id: taskId,
    status: 'processing',
    progress: 0,
    currentStep: 0,
    totalSteps: randomTotalSteps,
    currentSubstep: 0,
    totalSubsteps: randomTotalSubsteps,
    timeElapsed: 0,
    mode: processingMode,
    message: '正在初始化处理流程...',
    startTime: Date.now(),
    completed: false,
    downloadUrl: null,
    fileId: fileId, // 关联的文件ID
    originalFile: null, // 将在后面设置
    // 存储处理参数 - 只有creative-ai模式才存储详细参数
    parameters: processingMode === 'creative-ai' ? {
      processingMode: processingMode,
      prompt: prompt || '',
      loraModel: loraModel || 'none',
      loraWeight: parseFloat(loraWeight) || 0.8,
      styleStrength: parseFloat(styleStrength) || 0.75,
      randomSeed: parseInt(randomSeed) || -1
    } : {
      processingMode: processingMode
    },
    // 进度控制变量
    lastProgressUpdate: Date.now(),
    targetProgress: 0,
    progressSpeed: Math.random() * 0.8 + 0.2 // 0.2-1.0的随机速度
  };
  
  // 关联文件信息
  if (fileId) {
    const fileInfo = uploadedFiles.get(fileId);
    if (fileInfo) {
      task.originalFile = fileInfo;
      console.log('📎 关联文件成功:', fileInfo.originalName);
    } else {
      console.warn('⚠️ 警告: 未找到文件ID对应的文件:', fileId);
    }
  }

  processingTasks.set(taskId, task);
  
  console.log('🚀 任务创建成功:', taskId);
  console.log('📊 任务配置信息:');
  console.log(`   - 总步数: ${randomTotalSteps} 步`);
  console.log(`   - 总子步骤: ${randomTotalSubsteps} 步`);
  console.log(`   - 进度速度: ${task.progressSpeed.toFixed(2)}x`);
  console.log('📊 当前活跃任务数量:', processingTasks.size);
  
  // 模拟处理进度
  const progressInterval = setInterval(() => {
    const currentTask = processingTasks.get(taskId);
    if (!currentTask) {
      clearInterval(progressInterval);
      return;
    }
    
    const now = Date.now();
    const elapsedSinceLastUpdate = (now - currentTask.lastProgressUpdate) / 1000;
    
    // 更新进度 - 只能增加，不能减少，受速度影响
    const baseIncrement = Math.random() * 1.5 + 0.3; // 0.3-1.8% 基础增量
    const progressIncrement = baseIncrement * currentTask.progressSpeed; // 根据速度调整
    currentTask.progress = Math.min(currentTask.progress + progressIncrement, 100);
    
    // 根据进度百分比计算当前步数 - 只能增加
    const targetCurrentStep = Math.floor((currentTask.progress / 100) * currentTask.totalSteps);
    if (targetCurrentStep > currentTask.currentStep) {
      currentTask.currentStep = targetCurrentStep;
    }
    
    // 根据进度百分比计算子步骤 - 只能增加
    const targetCurrentSubstep = Math.floor((currentTask.progress / 100) * currentTask.totalSubsteps);
    if (targetCurrentSubstep > currentTask.currentSubstep) {
      currentTask.currentSubstep = targetCurrentSubstep;
    }
    
    // 确保100%时步数完全匹配
    if (currentTask.progress >= 100) {
      currentTask.progress = 100;
      currentTask.currentStep = currentTask.totalSteps;
      currentTask.currentSubstep = currentTask.totalSubsteps;
    }
    
    currentTask.timeElapsed = (Date.now() - currentTask.startTime) / 1000;
    currentTask.lastProgressUpdate = now;
    
    // 每20%进度输出一次详细信息
    if (Math.floor(currentTask.progress / 20) > Math.floor((currentTask.progress - progressIncrement) / 20)) {
      console.log(`📈 进度节点: ${Math.floor(currentTask.progress)}% - 步骤 ${currentTask.currentStep}/${currentTask.totalSteps}`);
    }
    
    // 根据模式和参数更新状态消息
    const params = currentTask.parameters;
    let baseMessage = '';
    
    if (currentTask.progress < 20) {
      baseMessage = `正在分析视频帧... [${currentTask.currentStep}/${currentTask.totalSteps}]`;
    } else if (currentTask.progress < 40) {
      if (params.processingMode === 'creative-ai' && params.loraModel && params.loraModel !== 'none') {
        baseMessage = `正在加载LoRA模型 [${params.loraModel}] [${currentTask.currentStep}/${currentTask.totalSteps}]...`;
      } else {
        baseMessage = `正在加载AI模型... [${currentTask.currentStep}/${currentTask.totalSteps}]`;
      }
    } else if (currentTask.progress < 60) {
      if (params.processingMode === 'creative-ai' && params.prompt) {
        baseMessage = `正在应用自定义风格转换 [${params.prompt.substring(0, 15)}...] [${currentTask.currentStep}/${currentTask.totalSteps}]`;
      } else {
        baseMessage = `正在应用风格转换... [${currentTask.currentStep}/${currentTask.totalSteps}]`;
      }
    } else if (currentTask.progress < 80) {
      if (params.processingMode === 'creative-ai' && params.loraWeight && params.loraWeight > 0) {
        baseMessage = `正在优化输出质量 [LoRA权重: ${params.loraWeight}] [${currentTask.currentStep}/${currentTask.totalSteps}]...`;
      } else {
        baseMessage = `正在优化输出质量... [${currentTask.currentStep}/${currentTask.totalSteps}]`;
      }
    } else if (currentTask.progress < 100) {
      if (params.processingMode === 'creative-ai' && params.styleStrength) {
        baseMessage = `正在生成输出视频 [强度: ${params.styleStrength}] [${currentTask.currentStep}/${currentTask.totalSteps}]...`;
      } else {
        baseMessage = `正在生成输出视频... [${currentTask.currentStep}/${currentTask.totalSteps}]`;
      }
    } else {
      // 确保完成时的最终状态
      currentTask.progress = 100;
      currentTask.status = 'completed';
      currentTask.currentStep = currentTask.totalSteps;
      currentTask.currentSubstep = currentTask.totalSubsteps;
      baseMessage = `处理完成！[模式: ${params.processingMode}] [${currentTask.totalSteps}/${currentTask.totalSteps}]`;
      currentTask.completed = true;
      currentTask.downloadUrl = `/api/download/${taskId}`;
      console.log(`✅ 任务完成: ${taskId}`);
      console.log(`📊 最终统计: ${currentTask.totalSteps}步 | ${currentTask.totalSubsteps}子步骤 | 耗时${Math.floor(currentTask.timeElapsed)}秒`);
      clearInterval(progressInterval);
    }
    
    currentTask.message = baseMessage;
    
    processingTasks.set(taskId, currentTask);
  }, 500); // 每500ms更新一次
  
  res.json({ taskId, status: 'started' });
});

// 获取处理进度
app.get('/api/progress/:taskId', (req, res) => {
  const { taskId } = req.params;
  const task = processingTasks.get(taskId);
  
  if (!task) {
    return res.status(404).json({ error: 'Task not found' });
  }
  
  res.json({
    id: task.id,
    status: task.status,
    progress: Math.min(Math.floor(task.progress), 100),
    currentStep: task.currentStep,
    totalSteps: task.totalSteps,
    currentSubstep: task.currentSubstep,
    totalSubsteps: task.totalSubsteps,
    timeElapsed: Math.floor(task.timeElapsed),
    mode: task.mode,
    message: task.message,
    completed: task.completed,
    downloadUrl: task.downloadUrl,
    // 返回处理参数
    parameters: task.parameters,
    // 返回文件信息
    fileInfo: task.originalFile ? {
      id: task.fileId,
      originalName: task.originalFile.originalName,
      size: task.originalFile.size,
      uploadTime: task.originalFile.uploadTime
    } : null
  });
});

// 下载原始视频文件
app.get('/api/download/:taskId', (req, res) => {
  const { taskId } = req.params;
  const task = processingTasks.get(taskId);
  
  if (!task || !task.completed) {
    return res.status(404).json({ error: '下载不可用，任务未完成' });
  }
  
  if (!task.originalFile) {
    return res.status(404).json({ error: '未找到原始文件' });
  }
  
  const filePath = task.originalFile.path;
  const originalName = task.originalFile.originalName;
  
  // 检查文件是否存在
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: '文件不存在' });
  }
  
  // 设置下载头
  res.setHeader('Content-Disposition', `attachment; filename="${originalName}"`);
  res.setHeader('Content-Type', task.originalFile.mimetype);
  
  // 创建文件流并发送
  const fileStream = fs.createReadStream(filePath);
  fileStream.pipe(res);
  
  fileStream.on('error', (error) => {
    console.error('文件下载错误:', error);
    res.status(500).json({ error: '文件下载失败' });
  });
  
  console.log('📥 开始下载文件:', originalName);
});

// 获取所有任务状态（调试用）
app.get('/api/tasks', (req, res) => {
  const tasks = Array.from(processingTasks.values());
  res.json(tasks);
});

// 根路径欢迎页面
app.get('/', (req, res) => {
  res.json({
    message: '🚀 PrismFlow v2 视频处理服务器',
    status: 'running',
    endpoints: {
      'POST /api/start-processing': '开始处理任务',
      'GET /api/progress/:taskId': '获取处理进度',
      'GET /api/download/:taskId': '下载处理结果',
      'GET /api/tasks': '查看所有任务'
    },
    frontend: 'http://localhost:5173',
    version: '2.0.0'
  });
});

// 清理完成的任务（定期清理）
setInterval(() => {
  const now = Date.now();
  for (const [taskId, task] of processingTasks.entries()) {
    // 清理1小时前完成的任务
    if (task.completed && (now - task.startTime) > 3600000) {
      processingTasks.delete(taskId);
    }
  }
}, 300000); // 每5分钟清理一次

app.listen(port, () => {
  console.log(`🚀 视频处理服务器运行在 http://localhost:${port}`);
  console.log(`📋 API文档:`);
  console.log(`   POST /api/start-processing - 开始处理`);
  console.log(`   GET  /api/progress/:taskId - 获取进度`);
  console.log(`   GET  /api/download/:taskId - 下载结果`);
}); 