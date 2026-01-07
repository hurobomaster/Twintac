import open3d as o3d
import numpy as np
import time
import math
from scipy.interpolate import Rbf
from collections import defaultdict

real_sensor_coords = np.array([[-10, 0, 6], [-10, 0, 0], [-10, 0, -6], [0, 0, 6], [0, 0, 0], [0, 0, -6], [15, 0, 3], [15, 0, -3], ])

# == 加载stl文件并存储用于可视化的信息 == #
class STLProcessor:
    def __init__(self):
        self.mesh = None # 模型mesh文件，此处的mesh包含了stl文件中所有的信息
        self.points = None
        self.normals = None
        self.sensor_points = None # sensor points 的xz坐标

    # def _random_sensor_points(self):
    #     xz_coords = self.mesh.vertices[:, [0, 2]]
    #     self.x_min, self.z_min = np.min(xz_coords, axis=0)
    #     self.x_max, self.z_max = np.max(xz_coords, axis=0)

    def load_and_process(self, stl_path):
        self.mesh = o3d.io.read_triangle_mesh(stl_path)
        if not self.mesh.has_vertices():
            raise ValueError("STL file error")

        # 获取顶点和法线
        self.points = np.asarray(self.mesh.vertices)
        self.normals = np.asarray(self.mesh.vertex_normals)

        # 正式获取传感器坐标点请使用这个函数
        self.select_sensor_points(real_sensor_coords)

        return {
            'points': self.points,
            'normals': self.normals,
            'triangles': np.asarray(self.mesh.triangles),
            'sensor_points': self.sensor_points,
        }
    
    def select_sensor_points(self, sensor_coords, num_sensors=8):    
        # indices = random.sample(range(len(self.points)), num_sensors)
        # self.sensor_points = self.points[indices]
        self.sensor_points = sensor_coords
        return self.sensor_points

    def save_data(self, save_path):
        """保存处理后的数据"""
        data = {
            'points': self.points,
            'normals': self.normals,
            'triangles': np.asarray(self.mesh.triangles),
            'sensor_points': self.sensor_points,
        }
        np.save(save_path, data)

    @staticmethod
    def load_data(load_path):
        return np.load(load_path, allow_pickle=True).item()
    


class TactileVisualizer:
    def __init__(self, stl_data, scale_factor=1.0, grid_size=50, show_axes=True, calibration_num=10):
        self.scale_factor = scale_factor
        self.stl_data = stl_data
        self.vis = o3d.visualization.Visualizer()

        self.mesh = None
        self.sensor_points = None # 传感器点
        self.running = False
        self.view_control = None

        self.original_points = None  # 存储原始顶点

        self.show_axes = show_axes
        self.coord_frame = None  # 坐标轴对象

        # 传感器点信息
        self.sensor_points_coords = stl_data['sensor_points'] # 传感器在stl中的坐标
        # self._init_distance_coefficients()
        # 新增校准相关属性
        self.calibration_num = calibration_num  # 校准帧数
        self.calibration_count = 0  # 当前已接收的校准帧数
        self.calibration_values = []  # 存储校准期间的传感器数据
        self.baseline_values = None  # 校准后的基准值
        self.calibrated = False  # 是否已完成校准


    def _init_distance_coefficients(self):
        """计算每个顶点到Y=0平面的距离系数(归一化到[0,1])"""
        y_coords = np.abs(self.original_points[:, 1])  # 取Y坐标绝对值
        self.distance_coeffs = (y_coords - 0.0) / (np.max(y_coords) - np.min(y_coords))
        # 可选：对系数做非线性变换（例如平方增强差异）
        self.distance_coeffs = self.distance_coeffs ** 2     

    def create_window(self):
        self.vis.create_window()
        self.view_control = self.vis.get_view_control()
        
        # 设置背景为纯黑色
        render_opt = self.vis.get_render_option()
        render_opt.background_color = np.array([0.0, 0.0, 0.0])  # RGB黑色
        
        # 旧版兼容方案（0.11及更早）
        if self.show_axes:
            self.coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=50, origin=[0,0,0])
            
            # 修改顶点颜色实现透明
            colors = np.array(self.coord_frame.vertex_colors) * 0.7  # 降低颜色饱和度
            self.coord_frame.vertex_colors = o3d.utility.Vector3dVector(colors)
            
            self.vis.add_geometry(self.coord_frame)
        # 旧版兼容方案（0.11及更早）
        if self.show_axes:
            self.coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=50, origin=[0,0,0])
            
            # 修改顶点颜色实现透明
            colors = np.array(self.coord_frame.vertex_colors) * 0.7  # 降低颜色饱和度
            self.coord_frame.vertex_colors = o3d.utility.Vector3dVector(colors)
            
            self.vis.add_geometry(self.coord_frame)

        # 创建STL网格
        self.mesh = o3d.geometry.TriangleMesh()
        self.mesh.vertices = o3d.utility.Vector3dVector(self.stl_data['points'])
        self.mesh.triangles = o3d.utility.Vector3iVector(self.stl_data['triangles'])
        self.mesh.compute_vertex_normals()
        self.mesh.paint_uniform_color([0.7, 0.7, 0.7])

        # 存储原始顶点位置
        self.original_points = np.copy(self.stl_data['points'])
        # 初始化形变系数(点初始化时距离y轴的距离，距离y轴0点越远(越高)形变越大)
        self._init_distance_coefficients()

        # 添加传感器点可视化 (红色显示)
        self.sensor_points = o3d.geometry.PointCloud()
        self.sensor_points.points = o3d.utility.Vector3dVector(self.sensor_points_coords)
        self.sensor_points.paint_uniform_color([1, 0, 0])

        # 添加到可视化
        self.vis.add_geometry(self.mesh)
        self.vis.add_geometry(self.sensor_points)

        # 设置初始视角
        self.view_control.set_front([0, 0, -1])
        self.view_control.set_up([0, 1, 0])

        self.running = True

    def update_visualization(self, sensor_values):
        if not self.running:
            return
        # 校准阶段处理
        if not self.calibrated:
            self.calibration_values.append(sensor_values.copy())
            self.calibration_count += 1

            if self.calibration_count >= self.calibration_num:
                # 计算每个通道的基准值（取平均值）
                self.baseline_values = np.mean(self.calibration_values, axis=0)
                self.calibrated = True
                print("Calibration success! Baseline values:", self.baseline_values)
            return  # 校准期间不更新可视化

        # 校准完成后，减去基准值
        calibrated_values = sensor_values - self.baseline_values
        # print(calibrated_values)

        new_points = np.copy(self.original_points)

        # RBF插值计算形变量（保持原有逻辑）
        rbf = Rbf(self.sensor_points_coords[:, 0], 
                self.sensor_points_coords[:, 2],
                calibrated_values,  # 使用校准后的值
                function='gaussian')
        y_offsets = np.maximum(rbf(new_points[:, 0], new_points[:, 2]), 0)
        deformation = 0.4 * y_offsets * self.distance_coeffs * self.scale_factor
        new_points[:, 1] -= deformation

        # 初始化颜色数组
        colors = np.ones((len(new_points), 3)) * 0.9  # 默认浅灰色

        # 优化的颜色映射
        for i, def_val in enumerate(deformation):
            if def_val <= 1:
                # 0-2: 浅灰色 (0.9,0.9,0.9)
                colors[i] = [0.9, 0.9, 0.9]
            elif def_val <= 6:
                # 2-8: 浅绿到中绿 (0.6,1,0.6) -> (0.2,0.8,0.2)
                ratio = (def_val - 2) / 5
                colors[i] = [0.6 - 0.4*ratio, 1 - 0.2*ratio, 0.6 - 0.4*ratio]
            elif def_val <= 10:
                # 8-12: 绿色到红色过渡 (0.2,0.8,0.2) -> (0.8,0.2,0.2)
                ratio = (def_val - 8) / 4
                colors[i] = [0.2 + 0.6*ratio, 0.8 - 0.6*ratio, 0.2]
            else:
                # 12+: 红色到深红 (0.8,0.2,0.2) -> (0.4,0,0)
                ratio = min((def_val - 12) / 42, 1)  # 限制在50达到最深
                colors[i] = [0.8 - 0.4*ratio, max(0.2 - 0.2*ratio, 0), 0.2 - 0.2*ratio]

        # 更新网格
        self.mesh.vertices = o3d.utility.Vector3dVector(new_points)
        self.mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
        self.mesh.compute_vertex_normals()

        # 刷新可视化
        self.vis.update_geometry(self.mesh)
        self.vis.poll_events()
        self.vis.update_renderer()

    def close_window(self):
        if self.running:
            self.vis.destroy_window()
            self.running = False
