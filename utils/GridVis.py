import pygame
import sys
import numpy as np
class GridVisualizerPyGame:
    def __init__(self, n, cell_size=60, spacing=15):
        """
        高效实时二维网格可视化
        :param n: 网格数量
        :param cell_size: 单个格子尺寸(像素)
        :param spacing: 网格间距(像素)
        """
        self.n = n
        self.data = np.zeros((n, 8), dtype=int)
        
        # PyGame 初始化
        pygame.init()
        
        # 计算窗口尺寸
        grid_width = 3 * cell_size
        total_width = n * (grid_width + spacing) - spacing
        self.window_size = (total_width + 2*spacing, 3 * cell_size + 2*spacing)
        
        self.screen = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption("Real-time Grid Visualization")
        
        # 颜色定义 (RGB格式)
        self.colors = {
            'background': (240, 240, 240),
            'grid_border': (200, 200, 200),
            'text': (50, 50, 50)
        }
        
        # 预定义位置布局 (相对单个网格内的坐标)
        self.positions = [
            (0, 0),  # 左上
            (2, 0),  # 右上
            (0, 1),  # 左中
            (1, 1),  # 中心
            (2, 1),  # 右中
            (0, 2),  # 左下
            (1, 2),  # 中下
            (2, 2)   # 右下
        ]
        
        # 字体
        self.font = pygame.font.SysFont(None, 24)
        self.title_font = pygame.font.SysFont(None, 28)
        
        # 网格位置计算
        self.grid_rects = []
        for i in range(n):
            x = spacing + i * (grid_width + spacing)
            y = spacing
            self.grid_rects.append(pygame.Rect(x, y, grid_width, grid_width))
    
    def value_to_color(self, value):
        """将数值转换为渐变的绿色"""
        if value == 0:
            return (255, 255, 255)  # 白色
        
        # 数值归一化 (0-200 -> 0-1)
        ratio = min(value / 200.0, 1.0)
        
        if ratio < 10:
            # 浅绿 (0-100)
            intensity = int(128 + 127 * ratio * 2)
            return (128, intensity, 128)
        else:
            # 深绿 (100-200)
            intensity = int(255 * (1 - (ratio - 0.5) * 2))
            return (0, intensity, 0)
    
    def update_grids(self, new_data):
        """更新网格数据并重绘"""
        self.data = new_data
        
        # 处理事件（防止窗口无响应）
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        # 清屏
        self.screen.fill(self.colors['background'])
        
        # 绘制所有网格
        for grid_idx in range(self.n):
            grid_rect = self.grid_rects[grid_idx]
            
            # 绘制网格标题
            title = self.title_font.render(f'Grid-{grid_idx+1}', True, self.colors['text'])
            self.screen.blit(title, (grid_rect.centerx - title.get_width()//2, 
                                     grid_rect.top - 30))
            
            # 绘制网格背景
            pygame.draw.rect(self.screen, 
                            self.colors['grid_border'], 
                            grid_rect, 
                            2)  # 边框
            
            # 计算单个单元格尺寸
            cell_w = grid_rect.width // 3
            cell_h = grid_rect.height // 3
            
            # 绘制所有位置的值
            for pos_idx, (grid_x, grid_y) in enumerate(self.positions):
                # 计算像素坐标
                pixel_x = grid_rect.left + grid_x * cell_w + cell_w // 2
                pixel_y = grid_rect.top + grid_y * cell_h + cell_h // 2
                
                # 计算值并获取颜色
                value = self.data[grid_idx, pos_idx]
                color = self.value_to_color(value)
                
                # 绘制圆点
                radius = min(cell_w, cell_h) // 3
                pygame.draw.circle(self.screen, color, (pixel_x, pixel_y), radius)
                
                # 绘制数值文本
                # if value > 0:  # 只为非零值显示数字
                #     text = self.font.render(str(value), True, (0, 0, 0))
                #     text_rect = text.get_rect(center=(pixel_x, pixel_y))
                #     self.screen.blit(text, text_rect)
        
        # 立即刷新显示
        pygame.display.flip()
    
    def run(self):
        """主循环（保持窗口打开）"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            # 使用一个while循环来避免频繁调用
            pygame.time.wait(10)
        
        pygame.quit()

    def close(self):
        """关闭可视化"""
        pygame.quit()
        sys.exit()
