import serial
import numpy as np
from collections import deque
from datetime import datetime, timedelta
import os
import pickle
SENSOR_PORTS = ['/dev/ttyACM0', ]
# 需要写一个频率控制的算法
class SerialDataHandler:
    def __init__(self, port="", baud_rate=115200, num_sensors=8, 
                 sensor_id=0, store_path=None, calibration_frames=100,
                 simulate=False, sim_max_value=10000):
        '''
        openteach单进程特制的串口读取程序
        
        Parameters:
            simulate: bool, 是否使用仿真模式
            sim_max_value: float, 仿真模式下数据的最大值
        '''
        self.sensor_id = sensor_id
        self.serial_port = port
        self.baud_rate = baud_rate
        self.num_sensors = num_sensors
        self.store_path = store_path
        self.calibration_frames = calibration_frames
        self.simulate = simulate
        self.sim_max_value = sim_max_value
        
        # 数据存储
        self.latest_data = np.zeros(num_sensors)  # 最新有效数据
        self.data_buffer = deque()  # 改为队列提高性能
        self.raw_buffer = bytearray()  # 原始字节缓冲区
        
        # 校准相关
        self.calibration_values = []  # 校准数据存储
        self.baseline = np.zeros(num_sensors)  # 校准基准值
        self.calibration_done = False  # 校准完成标志
        
        if not self.simulate:
            # 连接真实串口
            self.ser = serial.Serial(port, baud_rate, timeout=0)  # 非阻塞模式
            print(f"Connected to {port} at {baud_rate} baud")
            self.perform_calibration()
        else:
            # 仿真模式不需要实际串口连接
            self.ser = None
            print(f"Running in simulation mode with {num_sensors} sensors, max value {sim_max_value}")
        
        # 执行校准
        
    
    def perform_calibration(self):
        """执行传感器校准"""
        print(f"Starting calibration for sensor {self.sensor_id}...")
        collected_frames = 0
        
        while collected_frames < self.calibration_frames:
            # 读取并处理数据
            self._read_and_process()
            
            # 检查缓冲区是否有新数据
            if self.data_buffer:
                _, raw_values = self.data_buffer.pop()
                self.calibration_values.append(raw_values)
                collected_frames += 1
            
                # 更新进度
                if collected_frames % 10 == 0:
                    print(f"Calibration progress: {collected_frames}/{self.calibration_frames}")
        
        # 计算基准值
        if self.calibration_values:
            self.baseline = np.mean(self.calibration_values, axis=0)
            print(f"Calibration completed for sensor {self.sensor_id}. Baseline: {self.baseline.tolist()}")
        else:
            print(f"Warning: No calibration data collected for sensor {self.sensor_id}")
        
        self.calibration_done = True
        self.calibration_values = []  # 释放内存
        self.data_buffer.clear()  # 清空临时缓冲区

    def _generate_simulated_data(self):
        """生成模拟数据"""
        # 生成随机数据，范围在0到sim_max_value之间
        simulated_values = np.random.uniform(0, self.sim_max_value, self.num_sensors)
        # 将数据格式化为字符串，模拟真实串口输出
        data_str = ' '.join([f"{val:.2f}" for val in simulated_values]) + '\n'
        return data_str.encode('utf-8')

    def _read_and_process(self):
        """内部方法：读取并处理串口数据"""
        # 1. 读取数据（真实或模拟）
        if self.simulate:
            # 生成模拟数据
            data = self._generate_simulated_data()
        else:
            # 非阻塞读取所有可用字节
            data = self.ser.read(self.ser.in_waiting or 1)
        
        if data:
            self.raw_buffer.extend(data)
        
        # 2. 分割完整数据帧
        while b'\n' in self.raw_buffer:
            idx = self.raw_buffer.index(b'\n')
            line_bytes = self.raw_buffer[:idx]
            del self.raw_buffer[:idx+1]  # 移除已处理部分
            
            # 3. 高效解析（跳过空行）
            if line_bytes:
                try:
                    line = line_bytes.decode().strip()
                    values = [float(val) for val in line.split()]
                    if len(values) == self.num_sensors:
                        timestamp = datetime.now()
                        raw_values = np.array(values)
                        
                        # 添加到数据缓冲区
                        self.data_buffer.append((timestamp, raw_values))
                        
                        # 更新最新数据
                        if self.calibration_done:
                            self.latest_data = raw_values - self.baseline
                        else:
                            self.latest_data = raw_values
                except (UnicodeDecodeError, ValueError):
                    pass
    
    def read_latest(self):
        """获取最新数据帧（无阻塞）"""
        # 处理新数据
        self._read_and_process()
        return self.latest_data.copy()  # 返回副本
    
    def save_data(self):
        """
        保存当前缓冲区中的数据到文件
        :param file_path: 可选，指定保存路径
        """
        if not self.data_buffer:
            print(f"No data to save for sensor {self.sensor_id}")
            return False
        
        # 确定保存路径
        # path = os.path.join(self.store_path, f"{file_index}_sensor.pkl")
        path = os.path.join(self.store_path, f"FSRsensor.pkl")
        if not path:
            print("Error: No storage path specified")
            return False
        
        # 确保目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # 转换为列表便于序列化
        data_to_save = list(self.data_buffer)
        
        # 保存为pickle文件
        try:
            with open(path, 'wb') as f:
                pickle.dump(data_to_save, f)
            print(f"Saved {len(data_to_save)} records to {path}")
            self.data_buffer.clear()
            return True
        except Exception as e:
            print(f"Failed to save data: {str(e)}")
            return False
    
    def clear_buffer(self):
        """清空数据缓冲区"""
        self.data_buffer.clear()
        print(f"Buffer cleared for sensor {self.sensor_id}")
    
    def close(self, save_before_close=False):
        """关闭串口连接"""
        if save_before_close:
            self.save_data()
        
        self.ser.close()
        print(f"Closed serial connection for sensor {self.sensor_id}")

class MatrixSerialHandler(SerialDataHandler):
    def __init__(self, rows=3, cols=4, data_type='int', *args, **kwargs):
        """
        矩阵串口数据处理程序
        
        Parameters:
            rows (int): 矩阵行数
            cols (int): 矩阵列数
            data_type (str): 数据类型，'int'或'float'，默认为'int'
        """
        # 保存矩阵参数
        self.rows = rows
        self.cols = cols
        self.data_type = data_type.lower()  # 确保小写

        # 矩阵相关存储
        self.line_counter = 0  # 当前接收的行计数器
        self.row_buffer = []   # 存储已接收的行数据
        # 计算传感器总数 = 行数 × 列数
        kwargs['num_sensors'] = rows * cols  # 通过kwargs传递num_sensors


        # 调用父类初始化
        super().__init__(*args, **kwargs)  # 不再显式传递num_sensors
         # 如果数据是整数类型，修改基线和校准值类型为int
        if self.data_type == 'int':
            self.baseline = self.baseline.astype(int)
            self.latest_data = self.latest_data.astype(int)       
        # 最新矩阵数据
        self.latest_matrix = np.zeros((rows, cols))  # 二维矩阵格式
    
    def _generate_simulated_data(self):
        """生成模拟矩阵数据 (覆盖父类方法)"""
        # 生成完整矩阵 (rows x cols)
        # print(self.data_type)
        if self.data_type == 'int':
            simulated_matrix = np.random.randint(0, self.sim_max_value, (self.rows, self.cols))
        else:
            simulated_matrix = np.random.uniform(0, self.sim_max_value, (self.rows, self.cols))
        
        # 生成完整矩阵数据的字符串表示
        matrix_lines = []
        for row in simulated_matrix:
            if self.data_type == 'int':
                line_str = ' '.join(f"{val}" for val in row)
            else:
                line_str = ' '.join(f"{val:.2f}" for val in row)
            matrix_lines.append(line_str)
        
        # 返回所有行数据 + 换行符
        return '\n'.join(matrix_lines).encode('utf-8')
    
    def _read_and_process(self):
        """内部方法：读取并处理串口数据为矩阵格式 (覆盖父类方法)"""
        # 1. 读取数据（真实或模拟）
        if self.simulate:
            data = self._generate_simulated_data()
        else:
            data = self.ser.read(self.ser.in_waiting or 1)
        
        if data:
            self.raw_buffer.extend(data)
        
        # 2. 分割完整数据行
        while b'\n' in self.raw_buffer:
            idx = self.raw_buffer.index(b'\n')
            line_bytes = self.raw_buffer[:idx]
            del self.raw_buffer[:idx+1]  # 移除已处理部分
            
            # 3. 解析单行数据
            if line_bytes:
                try:
                    line = line_bytes.decode().strip()
                    values = line.split()
                    
                    # 只处理包含正确列数的行
                    if len(values) == self.cols:
                        # 根据类型转换数据
                        if self.data_type == 'int':
                            row_data = [int(val) for val in values]
                        else:
                            row_data = [float(val) for val in values]
                        
                        self.row_buffer.append(row_data)
                        self.line_counter += 1
                        
                        # 4. 当收集到完整矩阵时处理
                        if self.line_counter >= self.rows:
                            # 处理完整矩阵
                            self._process_full_matrix()
                            
                except (UnicodeDecodeError, ValueError) as e:
                    # 调试信息：打印错误和导致错误的数据
                    print(f"Error processing data: {e}, Data: {line_bytes}")
                    pass
    
    def _process_full_matrix(self):
        """处理完整的矩阵数据"""
        if len(self.row_buffer) < self.rows:
            return  # 确保有足够的行
        
        # 1. 创建二维矩阵
        matrix_data = np.array(self.row_buffer[:self.rows])
        
        # 2. 平展为一维数组（与父类兼容）
        flat_data = matrix_data.flatten()
        timestamp = datetime.now()
        
        # 3. 更新数据缓冲区和最新数据
        self.data_buffer.append((timestamp, flat_data))
        
        # 4. 更新最新矩阵（校准后/原始）
        if self.calibration_done:
            # 更新二维矩阵数据
            calibrated_matrix = matrix_data - self.baseline.reshape(self.rows, self.cols)
            self.latest_matrix = calibrated_matrix
            
            # 更新父类的一维数据（兼容）
            self.latest_data = flat_data - self.baseline
        else:
            self.latest_matrix = matrix_data
            self.latest_data = flat_data
        
        # 5. 重置缓冲区和计数器
        self.row_buffer = self.row_buffer[self.rows:]  # 保留多余的数据
        self.line_counter = len(self.row_buffer)  # 更新行计数器
    
    def read_latest_matrix(self):
        """获取最新的二维矩阵数据（无阻塞）"""
        self._read_and_process()  # 确保处理最新数据
        return_row_array = self.latest_matrix.copy()
        return_row_array.reshape([self.rows, self.cols])
        return return_row_array

def testSimulateReader():
    # 使用真实串口
    # handler = SerialDataHandler(port="/dev/ttyUSB0", baud_rate=115200)

    # 使用仿真模式，模拟8个传感器，数据范围0-1000
    sim_handler = SerialDataHandler(num_sensors=4, simulate=True, sim_max_value=255, calibration_frames=0)
    while True:
        print(sim_handler.read_latest())

def testMatrixSerialReader():
    matrix_handler = MatrixSerialHandler(
        port='/dev/ttyUSB1',
        rows=3, 
        cols=4, 
        data_type='int',  # 浮点数数据
        simulate=False,       # 仿真模式
        sim_max_value=255,  # 最大浮点数
        num_sensors=12       # 自动计算: 3×4=12
    )
    while True:
        print(matrix_handler.read_latest_matrix())

if __name__ =='__main__':
    # testSimulateReader()
    testMatrixSerialReader()