from typing import Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import os
import logging
import numpy as np
from pathlib import Path
from .base_processor import BaseImageProcessor

# 配置日志
logger = logging.getLogger(__name__)

class ProductInfoProcessor(BaseImageProcessor):
    """产品信息模板处理器"""
    def __init__(self, product_info: dict, canvas_size: Tuple[int, int] = (1240, 1500)):
        """
        初始化产品信息处理器
        Args:
            product_info: 包含产品信息的字典，例如：
                {
                    'title': '产品名称',
                    'pcs': 200,  # 整数
                    'height_cm': 13.8,  # 浮点数，单位cm
                    'length_cm': 14.3,  # 浮点数，单位cm
                    'product_image_path': 'path/to/product.png'  # 产品图片路径
                }
        """
        super().__init__(canvas_size)
        self.product_info = product_info
        
        # 设置字体目录
        self.fonts_dir = Path(__file__).parent.parent / 'assets' / 'fonts'
        self.title_font_path = self.fonts_dir / 'Poppins-Bold.ttf'
        self.regular_font_path = self.fonts_dir / 'Poppins-Regular.ttf'
        
        # 加载字体
        self._load_fonts()
        
        # 定义产品放置的box区域
        self.product_box = {
            'x': 624,      # 左上角x坐标
            'y': 831,      # 左上角y坐标
            'width': 420,  # box宽度
            'height': 505  # box高度
        }
        
        # 参考尺寸设置
        self.reference_height_cm = 13.8  # 参考高度13.8cm
        
        # 文本颜色
        self.gray_color = "#737373"
        
        # 文本位置
        self.text_positions = {
            'title': (127, 295),
            'pcs': (1014, 513),
            'length': (714, 1400),
            'height': (1100, 945)
        }

    def _load_fonts(self):
        """加载字体文件"""
        try:
            self.title_font = ImageFont.truetype(str(self.title_font_path), 45)
            self.info_font = ImageFont.truetype(str(self.regular_font_path), 35)
            self.dimension_font = ImageFont.truetype(str(self.regular_font_path), 28)
        except Exception as e:
            logger.warning(f"无法加载Poppins字体: {str(e)}")
            logger.warning(f"请确保字体文件存在于路径: {self.fonts_dir}")
            self.title_font = ImageFont.load_default()
            self.info_font = ImageFont.load_default()
            self.dimension_font = ImageFont.load_default()

    @staticmethod
    def format_dimension(value_cm: float) -> str:
        """将厘米数值转换为显示格式"""
        inch_value = value_cm / 2.54
        return f"{value_cm:.1f} cm / {inch_value:.2f} inch"

    def scale_product_by_real_size(self, image: Image.Image, real_height_cm: float) -> Image.Image:
        """根据真实尺寸缩放产品图片"""
        size_ratio = real_height_cm / self.reference_height_cm
        target_height_px = int(self.product_box['height'] * size_ratio)
        aspect_ratio = image.width / image.height
        target_width_px = int(target_height_px * aspect_ratio)
        return image.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)

    def process_image(self, image: Optional[Image.Image] = None) -> Image.Image:
        """
        处理产品信息模板图片
        Args:
            image: 可选的基础图片，如果不提供则使用默认模板
        Returns:
            处理后的图片
        """
        # 加载基础模板
        if image is None:
            template_path = Path(__file__).parent.parent / 'assets' / 'templates' / 'InfoBasic.png'
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")
            image = Image.open(template_path)
        
        # 创建绘图对象
        draw = ImageDraw.Draw(image)
        
        # 处理产品图片
        if 'product_image_path' in self.product_info:
            try:
                product_image = Image.open(self.product_info['product_image_path'])
                bounds = self._detect_product_bounds(product_image)
                if bounds:
                    # 将边界框格式从 (x, y, width, height) 转换为 (left, top, right, bottom)
                    x, y, w, h = bounds
                    product_image = product_image.crop((x, y, x + w, y + h))
                    product_image = self.scale_product_by_real_size(
                        product_image, 
                        self.product_info['height_cm']
                    )
                    
                    # 确保图片不会超出box的范围
                    if product_image.width > self.product_box['width']:
                        scale_ratio = self.product_box['width'] / product_image.width
                        new_width = self.product_box['width']
                        new_height = int(product_image.height * scale_ratio)
                        product_image = product_image.resize(
                            (new_width, new_height), 
                            Image.Resampling.LANCZOS
                        )
                    
                    # 计算放置位置
                    center_x = self.product_box['x'] + (self.product_box['width'] - product_image.width) // 2
                    bottom_y = self.product_box['y'] + self.product_box['height'] - product_image.height
                    
                    # 粘贴产品图片
                    image.paste(product_image, (center_x, bottom_y), product_image)
            except Exception as e:
                logger.error(f"处理产品图片时出错: {str(e)}")
                raise  # 添加 raise 以便更好地追踪错误
        
        # 添加文本信息
        draw.text(self.text_positions['title'], self.product_info['title'], 
                 fill='black', font=self.title_font)
        draw.text(self.text_positions['pcs'], f"{self.product_info['pcs']}pcs", 
                 fill='black', font=self.info_font)
        
        # 添加尺寸信息
        length_text = self.format_dimension(self.product_info['length_cm'])
        height_text = self.format_dimension(self.product_info['height_cm'])
        
        # 添加length文本
        draw.text(self.text_positions['length'], length_text, 
                 fill=self.gray_color, font=self.dimension_font)
        
        # 处理height旋转文本
        text_bbox = draw.textbbox((0, 0), height_text, font=self.dimension_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        txt = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))
        d = ImageDraw.Draw(txt)
        d.text((0, 0), height_text, font=self.dimension_font, fill=self.gray_color)
        txt_rotated = txt.rotate(90, expand=True)
        
        image.paste(txt_rotated, self.text_positions['height'], txt_rotated)
        
        return image

class ProductShotsProcessor(BaseImageProcessor):
    """产品多角度展示处理器"""
    def __init__(self, product_images: list, canvas_size: Tuple[int, int] = (790, 1196)):
        """
        初始化产品多角度展示处理器
        Args:
            product_images: 包含三张产品图片路径的列表，例如：
                [
                    'path/to/product1.png',
                    'path/to/product2.png',
                    'path/to/product3.png'
                ]
        """
        super().__init__(canvas_size)
        if len(product_images) != 3:
            raise ValueError("必须提供3张产品图片")
        self.product_images = product_images
        
        # 定义三个可绘制区域
        self.draw_boxes = [
            {
                'x': 200,
                'y': 280,
                'width': 400,
                'height': 400
            },
            {
                'x': 0,
                'y': 772,
                'width': 380,
                'height': 380
            },
            {
                'x': 410,
                'y': 772,
                'width': 380,
                'height': 380
            }
        ]

    def scale_and_center_image(self, image: Image.Image, target_box: dict) -> Image.Image:
        """缩放并居中图片到目标区域"""
        # 获取非透明区域边界
        bounds = self._detect_product_bounds(image)
        if not bounds:
            return image
            
        # 裁剪非透明区域
        x, y, w, h = bounds
        cropped_image = image.crop((x, y, x + w, y + h))
        
        # 计算缩放比例
        width_ratio = target_box['width'] / cropped_image.width
        height_ratio = target_box['height'] / cropped_image.height
        scale_ratio = min(width_ratio, height_ratio)
        
        # 计算缩放后的尺寸
        new_width = int(cropped_image.width * scale_ratio)
        new_height = int(cropped_image.height * scale_ratio)
        
        # 缩放图片
        scaled_image = cropped_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return scaled_image

    def process_image(self, image: Optional[Image.Image] = None) -> Image.Image:
        """
        处理产品多角度展示模板图片
        Args:
            image: 可选的基础图片，如果不提供则使用默认模板
        Returns:
            处理后的图片
        """
        # 加载基础模板
        if image is None:
            template_path = Path(__file__).parent.parent / 'assets' / 'templates' / 'ShotsBasic.png'
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")
            image = Image.open(template_path)
        
        # 处理三张产品图片
        for i, (product_image_path, box) in enumerate(zip(self.product_images, self.draw_boxes)):
            try:
                # 打开产品图片
                product_image = Image.open(product_image_path)
                
                # 缩放并居中图片
                scaled_image = self.scale_and_center_image(product_image, box)
                
                # 计算居中位置
                center_x = box['x'] + (box['width'] - scaled_image.width) // 2
                center_y = box['y'] + (box['height'] - scaled_image.height) // 2
                
                # 粘贴产品图片
                image.paste(scaled_image, (center_x, center_y), scaled_image)
                
            except Exception as e:
                logger.error(f"处理第{i+1}张产品图片时出错: {str(e)}")
        
        return image 