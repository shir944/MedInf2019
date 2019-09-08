# -*- coding: utf-8 -*-
"""
Created on Sat Sep 07 16:53:34 2019

@author: slavie
"""

from PyQt5 import QtWebEngineWidgets, QtCore, QtGui, QtWidgets
from OpenGL.GL import *

import sys
import os
import numpy as np
import traceback

from gui6_arch_video import VideoFile, Results, IMGProcess
from gui6_arch_analysis import Datendiagramm, AnalysisWidget

class GLWidget(QtWidgets.QOpenGLWidget):

    def __init__(self, **kwargs):
        super(GLWidget, self).__init__(**kwargs)
        self.xRot = 0.0
        self.bigimage = np.uint8(np.random.rand(1024,1024)*255)
        self.indices = np.array([0,1,2,3], 'I')
        self.init_gl(np.uint8(np.random.rand(32,64)*255))
        
    def init_gl(self, image):
        self.image = image
        if self.image.shape[0]>self.bigimage.shape[0] | self.image.shape[1]>self.bigimage.shape[1]:
            raise ValueError('Image size greater than texture buffer')
            return
        xr = self.image.shape[1]/self.bigimage.shape[1]
        yr = self.image.shape[0]/self.bigimage.shape[0]
        self.xyr = self.image.shape[0]/self.image.shape[1]
        self.points = np.array([
                [ 0, yr,  -1, -1, 0], # 0
                [ 0,  0,  -1,  1, 0], # 1
                [xr,  0,   1,  1, 0], # 2
                [xr, yr,   1, -1, 0], # 3
                ], 'f')


    def minimumSizeHint(self):
        return QtCore.QSize(50, 32)

    def sizeHint(self):
        return QtCore.QSize(400, 255)

    def initializeGL(self):
        try:
            glClearColor(0, 0, 0, 1)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexImage2D(GL_TEXTURE_2D, 0, 3,
                         self.bigimage.shape[1], self.bigimage.shape[0],
                         0, GL_LUMINANCE, GL_UNSIGNED_BYTE,
                         self.bigimage)
            glEnable(GL_TEXTURE_2D)
        except:
            traceback.print_exc()

    def resizeGL(self, width, height):
        try:
            glViewport(0, 0, width, height)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glOrtho(-1, 1, -1, 1, -1, 1)
            #h = float(height) / float(width);
            #glFrustum(-1.0, 1.0, -h, h, 5.0, 60.0)
            glMatrixMode(GL_MODELVIEW)
        except:
            traceback.print_exc()


    def paintGL(self):
        try:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            glRotated(self.xRot, 0.0, 0.0, 1.0)
            glTexSubImage2D(GL_TEXTURE_2D,0,0,0,
                            self.image.shape[1], self.image.shape[0],
                            GL_LUMINANCE, GL_UNSIGNED_BYTE,
                            self.image)
            glInterleavedArrays(GL_T2F_V3F, 20, self.points)
            glDrawElementsui(GL_QUADS, self.indices)
        except:
            traceback.print_exc()
        finally:
            return

    def setXRotation(self, angle):
        self.xRot = angle
        self.update()

class VideoWindow(QtWidgets.QWidget):
    
    playback = False
    file = None
    improc = None
    results = None
    databuf = None
    frame_no = 0
    call_stop = None
    
    def __init__(self, **kwargs):
        super(VideoWindow, self).__init__(**kwargs)
        self.init_ui()
        
    def init_ui(self):
        self.display = GLWidget(parent=self)
        
        self.plot_widget = Datendiagramm()
        self.plot_widget.init(100,75,200)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setTickInterval(1)
        self.slider.setValue(0)
        self.slider.setRange(0, 359)
        self.slider.valueChanged.connect(self.display.setXRotation)
        
        # Pushbutton erzeugen und definieren
        self.btn_play = QtWidgets.QPushButton(self.tr('&Play'))
        self.btn_play.setCheckable(True)
        # Slot-Funktion play_start übergeben
        # Diese Funktion wird aus der GUI-Eventschleife
        # beim Anklicken des Pushbuttons aufgerufen
        self.btn_play.clicked.connect(self.play_start)

        self.btn_stop = QtWidgets.QPushButton(self.tr('Stop'))
        self.btn_stop.setCheckable(True)
        self.btn_stop.clicked.connect(self.play_stop)

        self.btn_next = QtWidgets.QPushButton(self.tr('Next'))
        self.btn_next.clicked.connect(self.play_next)
        self.btn_prev = QtWidgets.QPushButton(self.tr('Previous'))
        self.btn_prev.clicked.connect(self.play_prev)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)
        self.buttonBox.addButton(self.btn_play, QtWidgets.QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.btn_stop, QtWidgets.QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.btn_prev, QtWidgets.QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.btn_next, QtWidgets.QDialogButtonBox.ActionRole)

        # Timer erzeugen und definieren
        self.playback_timer = QtCore.QTimer(self)
        self.playback_timer.setTimerType(QtCore.Qt.PreciseTimer)
        # Slot-Funktion timerfun übergeben
        # Diese Funktion wird aus der GUI-Eventschleife
        # immer dann aufgerufen, wenn nichts anderes passiert
        self.playback_timer.timeout.connect(self.timerfun)
        self.play_stop()

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.display,1,0,1,1)
        layout.addWidget(self.plot_widget.canvas,1,1,1,2)
        layout.addWidget(self.slider,2,0,1,3)
        layout.addWidget(self.buttonBox,3,0,1,3)
        self.setLayout(layout)

    def refresh(self):
        try:
            self.display.image = np.uint8(np.random.rand(
                                self.display.image.shape[0],
                                self.display.image.shape[1])*255)
            self.display.update()
        except:
            traceback.print_exc()
            
    def open_video(self, file):
        self.file = VideoFile(file)
        self.results = Results(file, self.file.length)
        self.imgproc = IMGProcess(self.file.width, self.file.height, self.file.length)
        self.plot_widget.init(self.file.width, self.file.height, self.file.length)

        self.frame_no = 0
        self.slider.setValue(self.frame_no)
        self.slider.setRange(0, self.file.info['length']-1)
        self.slider.valueChanged.disconnect()
        self.slider.valueChanged.connect(self.show_frame)
        self.play_stop()
        self.display.init_gl(self.file.info['img_buffer'])
        self.display.update()
            
    def show_frame(self, n):
        try:
            self.file.process_frame(n)
            pos = self.imgproc.process(self.file.img_buffer)
            self.results.store_pos(n, pos)
            self.plot_widget.set_pos(self.results.get_pos())
            self.plot_widget.refresh()
            self.frame_no = n
            self.slider.setValue(n)
            self.display.update()
        except:
            traceback.print_exc()

    def play_start(self):
        if not self.playback:
            self.playback = True
            self.playback_timer.start(0)
            self.btn_stop.setChecked(False)
    def play_stop(self):
        if self.playback:
            self.playback = False
            self.playback_timer.stop()
            self.btn_play.setChecked(False)
            if self.call_stop:
                self.call_stop()
    def play_next(self):
        self.frame_no += 1
        if self.playback or self.frame_no>=self.file.info['length']-1:
            self.frame_no = self.file.info['length']-1
        self.show_frame(self.frame_no)        
    def play_prev(self):
        self.frame_no -= 1
        if self.playback or self.frame_no<=0:
            self.frame_no = 0
        self.show_frame(self.frame_no)

    def connect_stop(self, fun):
        self.call_stop = fun        

    def timerfun(self):
        try:
            if self.frame_no>=self.file.info['length']-1:
                self.play_stop()
            else:
                self.show_frame(self.frame_no)
                self.frame_no += 1
        except EOFError:
            self.play_stop()
        # Catch any remaining exceptions
        except:
            traceback.print_exc()
            self.play_stop()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        menu_file = self.menuBar().addMenu(self.tr('File'))
        menu_file.addAction(self.tr('Open') + '...', self.open_file)
        menu_file.addSeparator()
        menu_file.addAction(self.tr('Exit'), self.close)


        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        self.video = VideoWindow(parent=self)
        self.tabs.addTab(self.video, self.tr('Video'))

        self.analysis = AnalysisWidget(parent=self)
        self.tabs.addTab(self.analysis, self.tr('Analysis'))
        self.tabs.setTabEnabled(self.tabs.indexOf(self.analysis), False)
        self.video.connect_stop(self.call_stop)

        self.tabs.currentChanged.connect(self.tab_changed)

    def tab_changed(self, index):
        try:
            tab = self.tabs.widget(index)
            if tab == self.analysis:
                if self.video.results != None:
                    self.analysis.plot_data(self.video.results.analyze())
        except:
            traceback.print_exc()

    def call_stop(self):
        self.tabs.setTabEnabled(self.tabs.indexOf(self.analysis), True)
        self.tabs.setCurrentWidget(self.analysis)
        
    def open_file(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(caption=self.tr('Choose video file'),
                                                        filter=self.tr('pgm Video File') + ' *.pgm')
        if file:
            self.tabs.setTabEnabled(self.tabs.indexOf(self.analysis), False)
            self.tabs.setTabEnabled(self.tabs.indexOf(self.video), True)
            self.tabs.setCurrentWidget(self.video)
            try:
                self.video.open_video(file)
            except:
                traceback.print_exc()

    def open_cda(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(caption=self.tr('Choose CDA file'),
                                                        filter=self.tr('CDA File') + ' *.xml')
        if file:
            self.tabs.setTabEnabled(self.tabs.indexOf(self.report), True)
            self.tabs.setCurrentWidget(self.report)
            try:
                self.report.load_file(file)
            except:
                traceback.print_exc()

if __name__ == '__main__':
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    app.references = set()
    
    win = MainWindow()
    app.references.add(win)
    win.setWindowTitle("Pupile Analyse")
    win.show()
    win.raise_()
    app.exec_()