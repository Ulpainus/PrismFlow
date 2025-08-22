import gradio as gr
import time
import os 

from run_v2v_v1 import process_video_entrypoint 

print("--- 正在运行最新版本的 debug_ui.py (诊断ID: 752024, 已集成LoRA功能) ---")

# --- 新增一个辅助函数，用于获取所有LoRA模型文件名 ---
def get_lora_files(lora_dir="models/Lora"):
    """
    扫描指定目录，返回所有.safetensors文件的列表。
    如果目录不存在，则返回一个包含'无 (None)'的列表。
    """
    if not os.path.exists(lora_dir):
        print(f"警告: LoRA目录未找到: {lora_dir}")
        return ["无 (None)"]
    try:
        files = [f for f in os.listdir(lora_dir) if f.endswith(".safetensors")]
        if not files:
            return ["无 (None)"]
        return ["无 (None)"] + files
    except Exception as e:
        print(f"错误: 扫描LoRA目录时出错: {e}")
        return ["无 (None)"]

# --- Gradio UI 定义 ---
def create_debug_ui():
    """创建并配置Gradio用户界面"""
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="indigo"), title="PrismFlow - AI调试台") as app:
        gr.Markdown("# 棱镜流调试台")     
        with gr.Row():
            with gr.Column(scale=1):
                input_video = gr.Video(label="上传测试视频", sources=["upload"])
                
                processing_mode = gr.Radio(
                    ["Stable Diffusion Only", "CycleGAN Only", "CycleGAN + Stable Diffusion"],
                    label="选择处理模式",
                    value="Stable Diffusion Only"
                )
                
                prompt = gr.Textbox(label="Prompt提示词", value="ghibli studio style, anime, masterpiece")

                # --- LoRA 功能区 ---
                gr.Markdown("--- LoRA 配置 (仅对SD模式生效) ---")
                lora_model = gr.Dropdown(
                    choices=get_lora_files(),
                    label="选择LoRA模型", 
                    value="无 (None)"
                )
                lora_weight = gr.Slider(
                    minimum=0.0, maximum=2.0, value=0.8, step=0.05,
                    label="LoRA权重"
                )
                # --- LoRA 功能区结束 ---
                
                strength = gr.Slider(minimum=0.1, maximum=1.0, value=0.7, label="风格化强度 (主要影响SD)")
                seed = gr.Number(label="随机种子", value=42, precision=0)
                
                run_button = gr.Button("开始处理", variant="primary")

            with gr.Column(scale=2):
                # --- 输出组件 ---
                output_video = gr.Video(label="处理结果预览")

        run_button.click(
            fn=process_video_entrypoint, 
            # 【重要】确保inputs列表的顺序与函数参数的顺序完全一致！
            inputs=[
                input_video, 
                prompt, 
                strength, 
                seed,
                processing_mode,
                lora_model,    
                lora_weight     
            ], 
            outputs=output_video
        )

    return app

if __name__ == "__main__":
    my_debug_app = create_debug_ui()
    my_debug_app.launch()
