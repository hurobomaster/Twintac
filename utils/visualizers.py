import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import numpy as np

pg.setConfigOptions(antialias=True)
pg.setConfigOption('background', 'k')   # 黑色背景
pg.setConfigOption('foreground', 'w')   # 白色文字

class TimeSeriesVisualizerPG:
    def __init__(self, window_sec=5, fs=500, max_value=150):
        self.fs = fs
        self.window_sec = window_sec
        self.window_size = fs * window_sec

        self.win = pg.GraphicsLayoutWidget(show=True, title="Tactile Time Series")
        self.win.resize(800, 900)

        self.plots = []
        self.curves = []
        self.history = np.zeros((8, self.window_size))

        for i in range(8):
            p = self.win.addPlot(title=f"Channel {i}")
            p.setYRange(0, max_value)
            p.showGrid(x=True, y=True)
            curve = p.plot(pen=pg.mkPen(color=pg.intColor(i, 8), width=2))
            self.plots.append(p)
            self.curves.append(curve)
            self.win.nextRow()

    def update(self, values):
        # 左移
        self.history = np.roll(self.history, -1, axis=1)
        self.history[:, -1] = values

        for i in range(8):
            self.curves[i].setData(self.history[i])

        QtWidgets.QApplication.processEvents()


class BarVisualizerPG:
    def __init__(self, max_value=150):
        self.max_value = max_value
        self.win = pg.GraphicsLayoutWidget(show=True, title="Tactile Bars")
        self.plot = self.win.addPlot()
        self.plot.setYRange(0, max_value)
        self.plot.setXRange(-0.5, 7.5)
        self.plot.showGrid(x=True, y=True)

        # initialize bars
        self.bars = []
        for i in range(8):
            bar = pg.BarGraphItem(x=[i], height=[0], width=0.8, brush=pg.intColor(i, 8))
            self.plot.addItem(bar)
            self.bars.append(bar)

    def update(self, values):
        for i in range(8):
            self.bars[i].setOpts(height=[values[i]])
        QtWidgets.QApplication.processEvents()