import time
from utils.data_logger import DataRecorder
from utils.serialReader import SerialDataHandler
from config import SERIAL_PORT, CALIBRATION_FRAMES

READ_RATE_HZ = 500        
RECORD_RATE_HZ = 100      
SAVE_DIR = "data_logs"


serial_handle = SerialDataHandler(
    port=SERIAL_PORT,
    calibration_frames=CALIBRATION_FRAMES
)

rec = DataRecorder(
    record_rate_hz=RECORD_RATE_HZ,
    save_dir=SAVE_DIR
)

rec.enable_keyboard_control()

print("Press [S] to start recording")
print("Press [Q] to stop & save")

read_interval = 1.0 / READ_RATE_HZ

while True:
    value = serial_handle.read_latest()
    rec.update_value(value)
    time.sleep(read_interval)
