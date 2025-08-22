<template>
  <div class="w-full h-screen bg-gray-900 text-white overflow-hidden flex flex-col">
    <!-- 顶部标题栏 -->
    <header class="bg-gray-800 px-6 py-4 border-b border-gray-700">
      <div class="flex items-center space-x-3">
        <div class="w-8 h-8 bg-purple-600 rounded flex items-center justify-center">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
            <path d="M12 2L2 7L12 12L22 7L12 2Z"/>
            <path d="M2 17L12 22L22 17"/>
            <path d="M2 12L12 17L22 12"/>
          </svg>
        </div>
        <div>
          <h1 class="text-xl font-bold text-white">PrismFlow v2 视频处理工具</h1>
          <p class="text-sm text-gray-400">v2版本新增：LoRA模型深度支持！上传视频，选择处理模式，配置LoRA设置，开始处理！</p>
        </div>
      </div>
    </header>

    <!-- 主要内容区域 -->
    <div class="flex-1 flex overflow-hidden">
      <!-- 左侧视频上传和播放区域 -->
      <div class="flex-1 flex flex-col p-4">
                 <!-- 上传视频文件按钮 -->
         <div class="mb-4">
           <button 
             @click="$refs.fileInput.click()"
             :disabled="isUploading"
             :class="[
               'flex items-center space-x-2 px-4 py-2 rounded-lg border transition-colors',
               isUploading 
                 ? 'bg-gray-600 border-gray-500 cursor-not-allowed' 
                 : 'bg-gray-700 hover:bg-gray-600 border-gray-600'
             ]">
             <span class="text-gray-300 text-lg">{{ isUploading ? '⏳' : '📁' }}</span>
             <span class="text-gray-300">{{ isUploading ? '上传中...' : '上传视频文件' }}</span>
           </button>
          <input 
            ref="fileInput" 
            type="file" 
            accept="video/*" 
            class="hidden" 
            @change="handleFileSelect">
        </div>

        <!-- 视频播放区域 -->
        <div class="flex-1 bg-black rounded-lg overflow-hidden relative">
          <video 
            v-if="videoUrl" 
            ref="videoPlayer"
            class="w-full h-full object-contain" 
            controls 
            :src="videoUrl"
            @loadedmetadata="onVideoLoaded"
            @timeupdate="onTimeUpdate"
            @play="onVideoPlay"
            @pause="onVideoPause">
          </video>
                     <div v-else class="w-full h-full flex items-center justify-center text-gray-500">
             <div class="text-center">
               <div class="text-6xl mb-3">📹</div>
               <p>请选择视频文件</p>
             </div>
           </div>
          
                     <!-- 视频信息显示 -->
           <div v-if="videoUrl" class="absolute top-4 left-4 bg-black bg-opacity-50 px-3 py-1 rounded text-sm">
             {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
           </div>
           
           <!-- 播放状态指示器 -->
           <div v-if="videoUrl && showPlayIndicator" class="absolute inset-0 flex items-center justify-center pointer-events-none">
             <div class="bg-black bg-opacity-60 p-4 rounded-full">
               <span class="text-white text-4xl">{{ isPlaying ? '⏸️' : '▶️' }}</span>
             </div>
           </div>
           
           <!-- 下载按钮 -->
           <div v-if="videoUrl && isProcessingCompleted" class="absolute top-4 right-16">
             <button @click="downloadVideo" class="bg-blue-500 hover:bg-blue-600 p-2 rounded transition-colors flex items-center space-x-2">
               <span class="text-white text-lg">⬇️</span>
               <span class="text-white text-sm">下载</span>
             </button>
      </div>
           
           <!-- 全屏按钮 -->
           <div v-if="videoUrl" class="absolute top-4 right-4">
             <button @click="toggleFullscreen" class="bg-black bg-opacity-50 p-2 rounded hover:bg-opacity-70 transition-colors">
               <span class="text-white text-lg">{{ isFullscreen ? '⏹️' : '⛶' }}</span>
             </button>
           </div>
        </div>

        <!-- 底部参数控制区域 -->
        <div class="mt-4 grid grid-cols-2 gap-4">
          <!-- 处理模式 -->
          <div class="bg-gray-800 rounded-lg p-4">
            <h3 class="text-sm font-medium text-gray-300 mb-2">处理模式</h3>
                         <select v-model="processingMode" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white">
               <option value="anime-style">快速风格转换 (动漫风)</option>
               <option value="creative-ai">创意AI重绘 (自定义)</option>
               <option value="advanced-combo">高级组合模式 (效果最佳)</option>
             </select>
          </div>

                     <!-- 提示词 -->
           <div v-if="processingMode === 'creative-ai'" class="bg-gray-800 rounded-lg p-4">
             <h3 class="text-sm font-medium text-gray-300 mb-2">提示词 (自定义风格描述)</h3>
             <textarea 
               v-model="prompt"
               rows="3"
               class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white resize-none"
               placeholder="a beautiful sketch, line art, clean lines">
             </textarea>
          </div>
        </div>
      </div>

            <!-- 右侧参数面板和状态区域 -->
      <div class="w-80 bg-gray-800 border-l border-gray-700 flex flex-col h-full">
        <!-- 进度信息 - 固定在顶部 -->
        <div class="p-4 border-b border-gray-700 flex-shrink-0">
          <div class="text-right text-sm text-gray-400">
            主步骤: {{ progressInfo.current }}/{{ progressInfo.total }} | 子步骤: {{ progressInfo.substeps }}/{{ progressInfo.totalSubsteps }} | 耗时: {{ progressInfo.time }}s
          </div>
          <div class="mt-2">
            <div class="text-sm text-gray-300 mb-1">正在执行模式: [{{ currentMode }}] - 进度: {{ progressPercent.toFixed(1) }}%</div>
            <div class="w-full bg-gray-700 rounded-full h-2">
              <div class="bg-blue-500 h-2 rounded-full transition-all duration-300" :style="`width: ${progressPercent}%`"></div>
            </div>
            <!-- 调试信息 -->
            <div class="mt-2 text-xs text-gray-500">
              <div>文件ID: {{ uploadedFileId || '无' }}</div>
              <div>任务ID: {{ currentTaskId || '无' }}</div>
              <div>状态: {{ statusMessage }}</div>
              <div>API连接: {{ API_BASE_URL }}</div>
            </div>
          </div>
        </div>

        <!-- 可滚动的参数配置区域 -->
        <div class="flex-1 overflow-y-auto">
          <!-- 参数显示面板 -->
          <div class="p-4">
            <!-- 本地参数显示 -->
            <div v-if="isProcessing" class="mb-3 p-3 bg-gray-800 rounded text-xs">
              <div class="text-blue-400 font-medium mb-2">📋 当前参数配置:</div>
              <div class="space-y-1 text-gray-300">
                <div>处理模式: {{ processingMode }}</div>
                <template v-if="processingMode === 'creative-ai'">
                  <div v-if="prompt">提示词: {{ prompt }}</div>
                  <div>LoRA模型: {{ loraModel }}</div>
                  <div>LoRA权重: {{ loraWeight }}</div>
                  <div>风格强度: {{ styleStrength }}</div>
                  <div>随机种子: {{ randomSeed }}</div>
                </template>
              </div>
            </div>
            
            <!-- 服务器参数显示 -->
            <div v-if="serverParams" class="mb-3 p-3 bg-green-900 bg-opacity-50 rounded text-xs">
              <div class="text-green-400 font-medium mb-2">✅ 服务器确认参数:</div>
              <div class="space-y-1 text-gray-300">
                <div>处理模式: {{ serverParams.processingMode }}</div>
                <template v-if="serverParams.processingMode === 'creative-ai'">
                  <div v-if="serverParams.prompt">提示词: {{ serverParams.prompt }}</div>
                  <div>LoRA模型: {{ serverParams.loraModel }}</div>
                  <div>LoRA权重: {{ serverParams.loraWeight }}</div>
                  <div>风格强度: {{ serverParams.styleStrength }}</div>
                  <div>随机种子: {{ serverParams.randomSeed }}</div>
                </template>
        </div>
      </div>

            <!-- 文件信息显示 -->
            <div v-if="serverFileInfo" class="mb-3 p-3 bg-gray-800 rounded text-xs">
              <div class="text-green-400 font-medium mb-2">📁 文件信息:</div>
              <div class="space-y-1 text-gray-300">
                <div>文件名: {{ serverFileInfo.originalName }}</div>
                <div>文件大小: {{ (serverFileInfo.size / 1024 / 1024).toFixed(2) }} MB</div>
                <div>上传时间: {{ new Date(serverFileInfo.uploadTime).toLocaleString() }}</div>
              </div>
            </div>
          </div>

          <!-- LoRA 模型配置 -->
          <div v-if="processingMode === 'creative-ai'" class="p-4 border-t border-gray-700">
            <div class="flex items-center space-x-2 mb-4">
              <div class="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
                <span class="text-white text-xs font-bold">L</span>
              </div>
              <h3 class="text-lg font-semibold text-white">LoRA 模型配置</h3>
            </div>

            <!-- LoRA 模型选择 -->
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-300 mb-2">LoRA 模型</label>
              <p class="text-xs text-gray-500 mb-2">选择要应用的LoRA模型 (仅在创意AI重绘模式下生效)</p>
              <select v-model="loraModel" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white">
                <option value="none">无 (None)</option>
                <option value="anime">Anime Style LoRA</option>
                <option value="realistic">Realistic LoRA</option>
                <option value="sketch">Sketch LoRA</option>
              </select>
            </div>

            <!-- LoRA 权重 -->
            <div class="mb-4">
              <div class="flex justify-between items-center mb-2">
                <label class="text-sm font-medium text-gray-300">LoRA 权重</label>
                <span class="text-white text-sm">{{ loraWeight }}</span>
              </div>
              <p class="text-xs text-gray-500 mb-2">调整LoRA效果强度，0.0=不使用，1.0=标准强度，2.0=最大强度</p>
              <input 
                type="range" 
                v-model="loraWeight" 
                min="0" 
                max="2" 
                step="0.1" 
                class="w-full slider">
            </div>
          </div>

          <!-- 高级参数 -->
          <div v-if="processingMode === 'creative-ai'" class="p-4 border-t border-gray-700">
            <div class="flex items-center space-x-2 mb-4">
              <span class="text-gray-400 text-xl">⚙️</span>
              <h3 class="text-lg font-semibold text-white">高级参数</h3>
            </div>

            <!-- 风格化强度 -->
            <div class="mb-4">
              <div class="flex justify-between items-center mb-2">
                <label class="text-sm font-medium text-gray-300">风格化强度</label>
                <span class="text-white text-sm">{{ styleStrength }}</span>
              </div>
              <input 
                type="range" 
                v-model="styleStrength" 
                min="0" 
                max="1" 
                step="0.05" 
                class="w-full slider mb-2">
            </div>

            <!-- 随机种子 -->
            <div class="mb-4">
              <div class="flex justify-between items-center mb-2">
                <label class="text-sm font-medium text-gray-300">随机种子</label>
              </div>
              <p class="text-xs text-gray-500 mb-2">-1 为随机种子</p>
              <input 
                type="number" 
                v-model="randomSeed" 
                class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                placeholder="-1">
            </div>
          </div>
        </div>

        <!-- 开始处理按钮 - 固定在底部 -->
        <div class="p-4 border-t border-gray-700 flex-shrink-0 bg-gray-800">
          <button 
            @click="startProcessing"
            :disabled="!uploadedFileId || isProcessing || isUploading"
            :class="[
              'w-full py-3 px-4 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2',
              uploadedFileId && !isProcessing && !isUploading
                ? 'bg-blue-500 hover:bg-blue-600 text-white' 
                : 'bg-gray-600 text-gray-400 cursor-not-allowed'
            ]">
            <span class="text-xl">🚀</span>
            <span>{{ isProcessing ? '处理中...' : '开始处理' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// 视频相关
const videoUrl = ref('')
const isProcessing = ref(false)
const isProcessingCompleted = ref(false)
const currentTaskId = ref(null)
const progressTimer = ref(null)
const uploadedFileId = ref(null)
const isUploading = ref(false)

// 视频播放控制
const currentTime = ref(0)
const duration = ref(0)
const isPlaying = ref(false)
const isFullscreen = ref(false)
const showPlayIndicator = ref(false)

// 参数配置
const processingMode = ref('anime-style')
const prompt = ref('a beautiful sketch, line art, clean lines')
const loraModel = ref('none')
const loraWeight = ref(0.8)
const styleStrength = ref(0.75)
const randomSeed = ref(-1)

// 进度信息
const progressInfo = ref({
  current: 0,
  total: 0,
  substeps: 0,
  totalSubsteps: 0,
  time: 0
})

const progressPercent = ref(0)
const totalPercent = ref(100.0)
const currentMode = ref('快速风格转换 (动漫风)')

// 状态信息
const statusMessage = ref('等待开始处理...')

// 服务器返回的参数信息
const serverParams = ref(null)
const serverFileInfo = ref(null)

// API配置
const API_BASE_URL = 'http://localhost:3001/api'

// API函数
const startProcessingAPI = async (params) => {
  try {
    console.log('🌐 发送API请求到:', `${API_BASE_URL}/start-processing`);
    const response = await fetch(`${API_BASE_URL}/start-processing`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params)
    });
    
    console.log('📡 API响应状态:', response.status, response.statusText);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('✅ API响应数据:', result);
    return result;
  } catch (error) {
    console.error('❌ 启动处理API失败:', error);
    throw error;
  }
};

const getProgressAPI = async (taskId) => {
  try {
    const url = `${API_BASE_URL}/progress/${taskId}`;
    console.log('🔍 获取进度API:', url);
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    return result;
  } catch (error) {
    console.error('❌ 获取进度API失败:', error);
    throw error;
  }
};

const downloadVideoAPI = async (taskId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/download/${taskId}`);
    return response; // 直接返回响应对象，因为现在是文件下载
  } catch (error) {
    console.error('下载失败:', error);
    throw error;
  }
};

// 文件上传API
const uploadVideoAPI = async (file) => {
  try {
    console.log('📤 开始上传文件:', file.name);
    
    const formData = new FormData();
    formData.append('video', file);
    
    const response = await fetch(`${API_BASE_URL}/upload-video`, {
      method: 'POST',
      body: formData
    });
    
    console.log('📡 上传响应状态:', response.status, response.statusText);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('✅ 文件上传成功:', result);
    return result;
  } catch (error) {
    console.error('❌ 文件上传失败:', error);
    throw error;
  }
};

// 进度轮询函数
const startProgressPolling = (taskId) => {
  console.log('🔁 启动进度轮询，任务ID:', taskId);
  
  const poll = async () => {
    try {
      console.log('📊 轮询进度中...');
      const progress = await getProgressAPI(taskId);
      
      console.log('📈 收到进度更新:', progress);
      
      // 更新进度信息
      progressInfo.value.current = progress.currentStep;
      progressInfo.value.total = progress.totalSteps;
      progressInfo.value.substeps = progress.currentSubstep;
      progressInfo.value.totalSubsteps = progress.totalSubsteps;
      progressInfo.value.time = progress.timeElapsed;
      progressPercent.value = progress.progress;
      statusMessage.value = progress.message;
      
      // 更新服务器参数信息
      if (progress.parameters) {
        serverParams.value = progress.parameters;
      }
      if (progress.fileInfo) {
        serverFileInfo.value = progress.fileInfo;
      }
      
      console.log('🎯 进度条更新:', progress.progress + '%');
      console.log('📋 服务器参数:', progress.parameters);
      
      // 更新模式名称
      const modeNames = {
        'anime-style': '快速风格转换 (动漫风)',
        'creative-ai': '创意AI重绘 (自定义)',
        'advanced-combo': '高级组合模式 (效果最佳)'
      };
      currentMode.value = modeNames[progress.mode] || progress.mode;
      
      // 检查是否完成
      if (progress.completed) {
        console.log('✅ 处理完成！');
        isProcessing.value = false;
        isProcessingCompleted.value = true;
        clearInterval(progressTimer.value);
        progressTimer.value = null;
      }
    } catch (error) {
      console.error('❌ 轮询进度失败:', error);
      statusMessage.value = `获取进度失败: ${error.message}`;
    }
  };
  
  // 立即执行一次
  poll();
  
  // 每500ms轮询一次
  progressTimer.value = setInterval(poll, 500);
};

// 停止进度轮询
const stopProgressPolling = () => {
  if (progressTimer.value) {
    clearInterval(progressTimer.value);
    progressTimer.value = null;
  }
};

// 文件上传处理
const handleFileSelect = async (event) => {
  const file = event.target.files[0]
  if (file) {
    try {
      isUploading.value = true
      statusMessage.value = '正在上传文件...'
      
      // 先在前端显示预览
      videoUrl.value = URL.createObjectURL(file)
      
      // 重置视频播放状态
      currentTime.value = 0
      duration.value = 0
      isPlaying.value = false
      isFullscreen.value = false
      showPlayIndicator.value = false
      
      // 上传到后端
      const uploadResult = await uploadVideoAPI(file)
      
      // 保存文件ID
      uploadedFileId.value = uploadResult.fileId
      statusMessage.value = `文件上传成功: ${file.name}`
      
      // 重置状态
      isProcessingCompleted.value = false
      currentTaskId.value = null
      stopProgressPolling()
      
      console.log('✅ 文件处理完成，文件ID:', uploadResult.fileId)
      
    } catch (error) {
      console.error('❌ 文件上传失败:', error)
      statusMessage.value = `文件上传失败: ${error.message}`
      videoUrl.value = ''
      uploadedFileId.value = null
      // 重置视频状态
      currentTime.value = 0
      duration.value = 0
      isPlaying.value = false
      isFullscreen.value = false
      showPlayIndicator.value = false
    } finally {
      isUploading.value = false
    }
  }
}

// 下载视频
const downloadVideo = async () => {
  if (currentTaskId.value) {
    try {
      console.log('📥 开始下载视频，任务ID:', currentTaskId.value);
      
      const response = await downloadVideoAPI(currentTaskId.value);
      
      if (!response.ok) {
        throw new Error(`下载失败: ${response.status} ${response.statusText}`);
      }
      
      // 获取文件名（从响应头中）
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'video.mp4';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // 获取文件blob
      const blob = await response.blob();
      
      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // 清理URL对象
      window.URL.revokeObjectURL(url);
      
      statusMessage.value = `下载完成: ${filename}`;
      console.log('✅ 下载完成:', filename);
      
    } catch (error) {
      console.error('❌ 下载失败:', error);
      statusMessage.value = `下载失败: ${error.message}`;
    }
  }
}

// 开始处理
const startProcessing = async () => {
  if (!uploadedFileId.value || isProcessing.value) {
    statusMessage.value = '请先上传视频文件'
    return
  }
  
  try {
    isProcessing.value = true
    isProcessingCompleted.value = false
    statusMessage.value = '正在启动处理任务...'
    
    console.log('🚀 开始处理视频...')
    
    // 重置进度和服务器信息
    progressPercent.value = 0
    progressInfo.value.current = 0
    progressInfo.value.total = 0
    progressInfo.value.substeps = 0
    progressInfo.value.totalSubsteps = 0
    progressInfo.value.time = 0
    serverParams.value = null
    serverFileInfo.value = null
    
    // 构建请求参数 - 只有creative-ai模式才发送详细参数
    const params = {
      processingMode: processingMode.value,
      fileId: uploadedFileId.value // 包含文件ID
    }
    
    // 只有creative-ai模式才添加详细参数
    if (processingMode.value === 'creative-ai') {
      params.prompt = prompt.value
      params.loraModel = loraModel.value
      params.loraWeight = parseFloat(loraWeight.value)
      params.styleStrength = parseFloat(styleStrength.value)
      params.randomSeed = parseInt(randomSeed.value)
    }
    
    console.log('📤 发送处理请求:')
    console.log('   参数详情:', params)
    
    // 启动后端处理
    const result = await startProcessingAPI(params)
    
    console.log('📥 收到服务器响应:', result)
    console.log('✅ 参数传输成功，任务ID:', result.taskId)
    
    if (result.taskId) {
      currentTaskId.value = result.taskId
      statusMessage.value = '✅ 参数传输成功，处理任务已启动，正在获取进度...'
      
      console.log('🔄 开始轮询进度，任务ID:', result.taskId)
      
      // 开始轮询进度
      startProgressPolling(result.taskId)
    } else {
      throw new Error('未能获取任务ID')
    }
  } catch (error) {
    console.error('❌ 启动处理失败:', error)
    isProcessing.value = false
    statusMessage.value = `启动处理失败: ${error.message}`
  }
}

// 视频播放控制函数
const onVideoLoaded = () => {
  const video = document.querySelector('video')
  if (video) {
    duration.value = video.duration
    console.log('视频加载完成，时长:', formatTime(video.duration))
  }
}

const onTimeUpdate = () => {
  const video = document.querySelector('video')
  if (video) {
    currentTime.value = video.currentTime
  }
}

const onVideoPlay = () => {
  isPlaying.value = true
  showPlayIndicator.value = true
  setTimeout(() => {
    showPlayIndicator.value = false
  }, 1000)
}

const onVideoPause = () => {
  isPlaying.value = false
  showPlayIndicator.value = true
  setTimeout(() => {
    showPlayIndicator.value = false
  }, 1000)
}

const formatTime = (seconds) => {
  if (!seconds || isNaN(seconds)) return '0:00'
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = Math.floor(seconds % 60)
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
  } else {
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }
}

const toggleFullscreen = async () => {
  const video = document.querySelector('video')
  if (!video) return
  
  try {
    if (!document.fullscreenElement) {
      // 进入全屏
      if (video.requestFullscreen) {
        await video.requestFullscreen()
      } else if (video.webkitRequestFullscreen) {
        await video.webkitRequestFullscreen()
      } else if (video.msRequestFullscreen) {
        await video.msRequestFullscreen()
      }
      isFullscreen.value = true
      console.log('进入全屏模式')
    } else {
      // 退出全屏
      if (document.exitFullscreen) {
        await document.exitFullscreen()
      } else if (document.webkitExitFullscreen) {
        await document.webkitExitFullscreen()
      } else if (document.msExitFullscreen) {
        await document.msExitFullscreen()
      }
      isFullscreen.value = false
      console.log('退出全屏模式')
    }
  } catch (error) {
    console.error('全屏切换失败:', error)
  }
}

// 监听全屏状态变化
const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

// 在组件挂载时添加全屏事件监听
if (typeof window !== 'undefined') {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
  document.addEventListener('msfullscreenchange', handleFullscreenChange)
}
</script>

<style scoped>
/* 滑块样式 */
.slider {
  height: 6px;
  border-radius: 3px;
  background: #374151;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3B82F6;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  transition: all 0.2s;
}

.slider::-webkit-slider-thumb:hover {
  background: #2563EB;
  transform: scale(1.1);
}

.slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3B82F6;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  transition: all 0.2s;
}

.slider::-moz-range-thumb:hover {
  background: #2563EB;
  transform: scale(1.1);
}

/* 选择框样式 */
select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: #374151;
}

::-webkit-scrollbar-thumb {
  background: #6B7280;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #9CA3AF;
}

/* 文本区域样式 */
textarea {
  resize: none;
}

/* 输入框和选择框焦点样式 */
input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: #3B82F6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

/* 视频全屏样式 */
video:fullscreen {
  object-fit: contain;
  background: black;
}

video:-webkit-full-screen {
  object-fit: contain;
  background: black;
}

video:-moz-full-screen {
  object-fit: contain;
  background: black;
}

/* 播放指示器动画 */
.play-indicator-enter-active,
.play-indicator-leave-active {
  transition: opacity 0.3s ease;
}

.play-indicator-enter-from,
.play-indicator-leave-to {
  opacity: 0;
}

/* 视频控制按钮悬停效果 */
button:hover {
  transform: scale(1.05);
  transition: transform 0.2s ease;
}

/* 视频容器悬停时显示控制按钮 */
.video-container:hover .video-controls {
  opacity: 1;
  transition: opacity 0.3s ease;
}

.video-controls {
  opacity: 0.8;
  transition: opacity 0.3s ease;
}
</style>