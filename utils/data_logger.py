import time
import csv
import threading
from pynput import keyboard
from pathlib import Path
from datetime import datetime



class DataRecorder:
    def __init__(self, record_rate_hz=100, save_dir="records"):
        self.record_interval = 1.0 / record_rate_hz
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.record_data = []
        self.latest_value = None
        self.lock = threading.Lock()

        self.record_flag = False
        self.exit_flag = False
        self.start_time = None
        self.record_thread = None

    def update_value(self, value):
        if value is None:
            return
        with self.lock:
            self.latest_value = value.copy()

    def _record_loop(self):
        print("[Recorder] Recording started...")
        self.start_time = time.time()

        while self.record_flag:
            with self.lock:
                if self.latest_value is not None:
                    t = time.time() - self.start_time
                    self.record_data.append([t] + list(self.latest_value))
            time.sleep(self.record_interval)

        print("[Recorder] Recording thread exited.")

    # 开始录制
    def start_recording(self):
        if self.record_flag:
            print("[Recorder] Already recording.")
            return

        self.record_data = []
        self.record_flag = True

        self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.record_thread.start()

    # 停止录制并保存
    def stop_and_save(self, filename=None):
        if not self.record_flag:
            print("[Recorder] Not recording.")
            return

        self.record_flag = False
        self.record_thread.join()

        if len(self.record_data) == 0:
            print("[Recorder] No data to save.")
            return

        if filename is None:
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{now}.csv"

        save_path = self.save_dir / filename

        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            header = ["timestamp"] + [f"value_{i}" for i in range(len(self.record_data[0]) - 1)]
            writer.writerow(header)
            writer.writerows(self.record_data)

        print(f"[Recorder] Saved → {save_path}")

    def enable_keyboard_control(self):
        def on_press(key):
            try:
                if key.char == 's':
                    print("[Key] S → start recording")
                    self.start_recording()

                elif key.char == 'q':
                    print("[Key] Q → stop & save")
                    self.stop_and_save()
            except AttributeError:
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()
