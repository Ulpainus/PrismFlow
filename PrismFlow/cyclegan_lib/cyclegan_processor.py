import torch
import torchvision.transforms as transforms
from PIL import Image
import os
import argparse
from .models import create_model
from .options.test_options import TestOptions
from . import util

class CycleGANProcessor:
    def __init__(self, model_name, netG='resnet_9blocks', norm='instance', no_dropout=True, gpu_ids='0', generator_suffix='_A', preserve_resolution=True):
        """
        初始化CycleGAN处理器，加载模型到内存中。
        参数:
        - model_name (str): 预训练模型的名称 (即checkpoints目录下的文件夹名).
        - netG (str): 生成器的架构, e.g., 'resnet_9blocks', 'unet_256'.
        - norm (str): 归一化层的类型, e.g., 'instance', 'batch'.
        - no_dropout (bool): 【已修复】是否使用dropout.
        - gpu_ids (str): 使用的GPU ID, '0', '1', '-1' for CPU.
        - generator_suffix (str): 要使用的生成器后缀, 如 '_A' (用于A->B) 或 '_B' (用于B->A).
        - preserve_resolution (bool): 是否保持原始分辨率，如果False则缩放到256x256
        """
        self.preserve_resolution = preserve_resolution
        opt = self._get_test_options(model_name, netG, norm, no_dropout, gpu_ids, generator_suffix)
        self.opt = opt
        self.device = torch.device('cuda:{}'.format(opt.gpu_ids[0])) if opt.gpu_ids else torch.device('cpu')
        self.model = create_model(opt)
        self.model.setup(opt)
        self.model.eval()
        self._setup_transform()
        
        print(f"CycleGAN model '{model_name}' (netG: {netG}, norm: {norm}) with generator 'G{generator_suffix}' loaded successfully.")
        print(f"分辨率保持模式: {'开启' if preserve_resolution else '关闭 (固定256x256)'}")

    def _get_test_options(self, model_name, netG, norm, no_dropout, gpu_ids, generator_suffix):
        """内部函数，用于手动构建一个options对象以加载模型"""
        parser = argparse.ArgumentParser()
        opt_parser = TestOptions().initialize(parser)
        opt = opt_parser.parse_args([])

        opt.isTrain = False
        opt.model_suffix = generator_suffix
        opt.netG = netG
        opt.norm = norm
        opt.no_dropout = no_dropout

        opt.model = 'test'
        opt.dataset_mode = 'single'
        opt.name = model_name
        
        # 【修复】使用绝对路径确保无论在什么目录下运行都能找到模型
        # 获取当前文件所在目录的绝对路径
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        opt.checkpoints_dir = os.path.join(current_file_dir, 'checkpoints')
        
        opt.gpu_ids = [int(id) for id in gpu_ids.split(',')] if gpu_ids != '-1' else []
        opt.direction = 'AtoB'
        opt.input_nc = 3
        opt.output_nc = 3
        opt.num_threads = 0
        opt.batch_size = 1
        opt.serial_batches = True
        opt.no_flip = True
        opt.display_id = -1
        return opt

    def _setup_transform(self):
        """设置从PIL Image到PyTorch Tensor的转换"""
        if self.preserve_resolution:
            self.transform_no_resize = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
            ])
        else:
            transform_list = []
            transform_list.append(transforms.Resize([256, 256], transforms.InterpolationMode.BICUBIC))
            transform_list.append(transforms.ToTensor())
            transform_list.append(transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)))
            self.transform = transforms.Compose(transform_list)
    def _pad_to_multiple_of_4(self, img):
        """将图像尺寸填充到4的倍数，确保网络兼容性"""
        width, height = img.size
        

        new_width = ((width + 3) // 4) * 4
        new_height = ((height + 3) // 4) * 4
        
        if new_width != width or new_height != height:
            new_img = Image.new('RGB', (new_width, new_height), (0, 0, 0))
            paste_x = (new_width - width) // 2
            paste_y = (new_height - height) // 2
            new_img.paste(img, (paste_x, paste_y))
            return new_img, (paste_x, paste_y, width, height)
        else:
            return img, None

    def _crop_from_padded(self, img, crop_info):
        """从填充后的图像中裁剪出原始尺寸"""
        if crop_info is None:
            return img
        
        paste_x, paste_y, orig_width, orig_height = crop_info
        return img.crop((paste_x, paste_y, paste_x + orig_width, paste_y + orig_height))

    @torch.no_grad()
    def process_frame(self, pil_image):
        """
        接收一个PIL图像，返回一个经过CycleGAN处理的PIL图像。
        """
        if self.preserve_resolution:
            # 保持原始分辨率的处理流程
            original_size = pil_image.size
            rgb_image = pil_image.convert('RGB')
            
            # 填充到4的倍数以确保网络兼容
            padded_image, crop_info = self._pad_to_multiple_of_4(rgb_image)
            
            tensor_image = self.transform_no_resize(padded_image).unsqueeze(0).to(self.device)
            
            # CycleGAN处理
            self.model.set_input({'A': tensor_image, 'A_paths': ''})
            self.model.test()
            visuals = self.model.get_current_visuals()
            result_tensor = visuals['fake']
        
            result_array = util.tensor2im(result_tensor)
            result_pil = Image.fromarray(result_array)
            
            result_pil = self._crop_from_padded(result_pil, crop_info)
            
            if result_pil.size != original_size:
                result_pil = result_pil.resize(original_size, Image.Resampling.BICUBIC)
            
            return result_pil
        else:
            tensor_image = self.transform(pil_image.convert('RGB')).unsqueeze(0).to(self.device)
            self.model.set_input({'A': tensor_image, 'A_paths': ''})
            self.model.test()
            visuals = self.model.get_current_visuals()
            result_tensor = visuals['fake']
            result_pil = util.tensor2im(result_tensor)
            return Image.fromarray(result_pil)
