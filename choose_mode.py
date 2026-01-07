import time
from pynput import keyboard

from utils.visualizers import TimeSeriesVisualizerPG
from utils.serialReader import SerialDataHandler
from utils.RbfVis import TactileVisualizer, STLProcessor
from config import SERIAL_PORT, CALIBRATION_FRAMES

exit_flag = False
reset_flag = False

def on_press(key):
    global exit_flag, reset_flag

    if key == keyboard.Key.esc:
        print("ESC pressed → exiting all programs...")
        exit_flag = True
        return False
    if key == keyboard.KeyCode.from_char('r'):
        print("Reset (R) pressed → resetting calibration...")
        reset_flag = True


def run_open3d_mode():
    global reset_flag

    serial_handle = SerialDataHandler(port=SERIAL_PORT, calibration_frames=CALIBRATION_FRAMES)
    stl_processor = STLProcessor()

    aim_stl_data = stl_processor.load_data("model/processed_stl_data.npy")
    tac_vis = TactileVisualizer(aim_stl_data, show_axes=False)
    tac_vis.create_window()

    print("Running Open3D tactile visualization... Press ESC to exit.")

    while not exit_flag:
        if reset_flag:
            print("Resetting Serial + Calibration...")
            serial_handle.close()
            serial_handle = SerialDataHandler(port=SERIAL_PORT, calibration_frames=CALIBRATION_FRAMES)
            reset_flag = False
        value = serial_handle.read_latest()
        tac_vis.update_visualization(value)

    serial_handle.close()
    print("Open3D mode exited.")


def run_timeseries_mode():
    global reset_flag

    serial_handle = SerialDataHandler(port=SERIAL_PORT, calibration_frames=CALIBRATION_FRAMES)
    time_vis = TimeSeriesVisualizerPG(fs=50)

    print("Running TimeSeries visualizer... Press ESC to exit.")

    while not exit_flag:
        if reset_flag:
            print("Resetting Serial + Calibration...")
            serial_handle.close()
            serial_handle = SerialDataHandler(port=SERIAL_PORT, calibration_frames=CALIBRATION_FRAMES)
            reset_flag = False
        value = serial_handle.read_latest()
        time_vis.update(value)

    serial_handle.close()
    print("TimeSeries mode exited.")


def run_readonly_mode():
    global reset_flag

    serial_handle = SerialDataHandler(port=SERIAL_PORT, calibration_frames=CALIBRATION_FRAMES)
    print("Running ReadOnly mode (print serial data)... Press ESC to exit.")

    while not exit_flag:
        if reset_flag:
            print("Resetting Serial + Calibration...")
            serial_handle.close()
            serial_handle = SerialDataHandler(port=SERIAL_PORT, calibration_frames=CALIBRATION_FRAMES)
            reset_flag = False
        value = serial_handle.read_latest()
        print(value)

    serial_handle.close()
    print("ReadOnly mode exited.")


if __name__ == "__main__":

    print("请选择模式：")
    print("1 = Open3D 触觉可视化")
    print("2 = TimeSeries 时间序列图")
    print("3 = ReadOnly 只读模式 (打印串口数据)")
    mode = input("输入 1 / 2 / 3 : ").strip()

    # 开启键盘监听
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    
    if mode == "1":
        run_open3d_mode()
    elif mode == "2":
        run_timeseries_mode()
    elif mode == "3":
        run_readonly_mode()
    else:
        print("无效输入，退出程序。")

    print("All programs exited.")