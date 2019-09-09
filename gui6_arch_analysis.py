from PyQt5 import QtCore,  QtWidgets

import traceback
import sys
import numpy as np
import abc

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as QtCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib as plt

class MPLFigure(QtCore.QObject, Figure):

    """
    Die Klasse erzeugt eine Figur mithilfe von Matplotlib
    Damit kann man die Funktionen von Qt benutzen
    """

    def __init__(self):
        super(MPLFigure, self).__init__()

    @abc.abstractmethod
    def init_plots(self):
        """
        plot initialisieren
        """
        pass

    @abc.abstractmethod
    def plot_data(self, data):
        """
        :param data: Data zum plotten
        """
        pass


class Figure1(MPLFigure):

    """
    Figur Klasse
    """

    def __init__(self):
        super(Figure1, self).__init__()

        # Figur auf Canvas speichernAssign the figure a canvas
        # Zum Speichern und zum Qt addieren
        self.canvas = QtCanvas(self)

        # Subplots erzeugen
        self.ax1 = self.add_subplot(311)
        self.ax2 = self.add_subplot(312, sharex=self.ax1)
        self.ax3 = self.add_subplot(313, sharex=self.ax1)


        self.init_plots()

    def init_plots(self):
        # Erste Diagramm: Pupilenposition
        self.ax1.cla()
        self.ax1.grid()
        self.ax1.set_title(self.tr('Analysis Report'))
        self.ax1.set_ylabel(self.tr('Pupil Position') + ' [px]')

        # Zweite Diagramm: Pupilengeschwindigkeit
        self.ax2.cla()
        self.ax2.grid()
        self.ax2.set_xlabel(self.tr('Time') + '[s]')
        self.ax2.set_ylabel(self.tr('Pupil Velocity') + ' [px/s]')

        # Dritte Diagramm: absolute Geschwindigkeit
        self.ax3.cla()
        self.ax3.grid()
        self.ax3.set_xlabel(self.tr('Time') + '[s]')
        self.ax3.set_ylabel(self.tr('Absolute Velocity') + ' [px/s]')
        
    def plot_data(self, data):
        self.init_plots()
        self.ax1.plot(data.loc[:, 'Time'], data.loc[:, ('Hor','Ver')])
        self.ax1.legend(['Hor', 'Ver'], loc='upper right')
        self.ax1.autoscale(enable=True, axis='x', tight=True)

        self.ax2.plot(data.loc[:, 'Time'], data.loc[:, ('vHor','vVer')])
        self.ax2.legend(['Hor', 'Ver'], loc='upper right')
        self.ax2.autoscale(enable=True, axis='both', tight=True)
        
        self.ax3.plot(data.loc[:, 'Time'], data.loc[:, ('vAbs', 'vFilt', 'vConv', 'vFFT')])
        self.ax3.legend(['vAbs', 'vFilt', 'vConv', 'vFFT'], loc='upper right')
        self.ax3.autoscale(enable=True, axis='both', tight=True)

        self.canvas.draw()

class AnalysisWidget(QtWidgets.QWidget):

    """
    Hauptfenster für die Analyse
    """

    output_ready = QtCore.pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super(AnalysisWidget, self).__init__(*args, **kwargs)

        self.init_ui()

    def init_ui(self):
        """
        Interface initialisieren
        """
        # Figur erzeugen
        self.fig1 = Figure1()

        # NavigationToolBar - zum Inspektion der Diagramme
        self.toolbar = NavigationToolbar(self.fig1.canvas, self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.fig1.canvas)

    def plot_data(self, data):
        self.fig1.plot_data(data)


class Datendiagramm(Figure):
    def __init__(self, *args, **kwargs):
        super(Datendiagramm, self).__init__(*args, **kwargs)
        self.canvas = QtCanvas(self)

        # Diagram für die Pupilenposition
        # Wird mit dem Video gezeigt
        self.ax = self.add_subplot(111)
        self.ax.grid()
        self.ax.set_xlabel('Frame #')
        self.ax.set_ylabel('Pupil Position [px]')
        
        self.refresh_counter = 0
        self.refresh_rate = 10
        self.lines = None
        
    def init(self, width, height, length):
        # Datendiagramm initialisieren
        self.ax.cla()
        self.ax.grid()
        self.ax.set_xlabel('Frame #')
        self.ax.set_ylabel('Pupil Position [px]')
        self.ax.set_title('Pupil Center')
        
        self.ax.set_xlim([0, length])
        self.ax.set_ylim([0, np.maximum(width, height)])
        self.lines = self.ax.plot(np.full((length, 2), np.nan), linewidth=1)
        self.ax.legend(['Hor','Ver'])
        self.canvas.draw()
        
    """ Update the plot data for given index but don't draw """
    def set_pos(self, data):
        self.lines[0].set_ydata(data[:,0])
        self.lines[1].set_ydata(data[:,1])

    """ Redraw the plot """
    def refresh(self):
        if self.refresh_counter==0:
            if self.lines:
                self.ax.draw_artist(self.lines[0])
                self.ax.draw_artist(self.lines[1])
                self.canvas.update()
        self.refresh_counter = (self.refresh_counter+1)%self.refresh_rate
    
if __name__ == '__main__':

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self, **kwargs):
            super(MainWindow, self).__init__(**kwargs)
            
            self.tabs = QtWidgets.QTabWidget()
            self.setCentralWidget(self.tabs)
            
            # Datendiagramm erzeugen
            self.plot_widget = Datendiagramm()
            self.plot_widget.init(100,100,100)
            self.tabs.addTab(self.plot_widget.canvas, self.tr('Diagramm'))

            # Analysis Tab erzeugen
            self.analysis = AnalysisWidget(parent=self)
            self.tabs.addTab(self.analysis, self.tr('Analysis'))

    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    app.references = set()
    
    win = MainWindow()
    # Program Label
    win.setWindowTitle("Pupile Analyse")
    app.references.add(win)
    win.show()
    win.raise_()
    app.exec_()
