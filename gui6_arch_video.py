# -*- coding: utf-8 -*-
"""
Created on Sat Sep 07 16:53:34 2019

@author: slavie
"""

import pgm
import numpy as np
import pandas as pd
import traceback
import unittest
from scipy import signal, ndimage

def fftfilt(B,x,nfft=128):
    X = np.fft.fft(x,n=nfft)
    Y = np.fft.ifft(X*B)
    y = np.real(Y)
    return y

class IMGProcess():
    def __init__(self, video_width, video_height, video_length, *args, **kwargs):
        self.init(video_width, video_height, video_length)

    def init(self, video_width, video_height, video_length):
        self.frame_cox = np.arange(0, video_width, 1)
        self.frame_coy = np.arange(0, video_height, 1)
        self.sum_x = np.zeros((video_width,), dtype=np.int32)
        self.sum_y = np.zeros((video_height,), dtype=np.int32)
        self.sum_n = np.zeros((1,),dtype=np.int32)
        self.sum_n = 0
        self.com = np.zeros((2,), dtype=float)
        imgshape = (video_height,video_width)
        self.pupil_idx =  np.empty(imgshape, dtype=np.bool8)
        self.filt_img = np.zeros(imgshape,dtype=np.uint8)
        
        sharp = np.array([
                [0,-1,0],
                [-1,5,-1],
                [0,-1,0],
                ], dtype=np.float32)
        blurry = np.array([
                [1,1,1],
                [1,1,1],
                [1,1,1],
                ], dtype=np.float32)
        # k = Filterkern
        self.k = sharp

    def process(self, frame):
        # Filterung der Image
        ndimage.median_filter(frame, 3, output=self.filt_img)
        ndimage.convolve(self.filt_img, self.k, output=frame)
                
        np.less(frame, 50, out=self.pupil_idx)
        pupil = self.pupil_idx.astype(np.int32)
        np.sum(pupil, axis=0, dtype=np.int32, out=self.sum_x)
        np.sum(pupil, axis=1, dtype=np.int32, out=self.sum_y)
        self.sum_n = np.sum(self.sum_x)
        sn = 1.0/np.sum(self.sum_x)
        # Skalarprodukt
        self.com[0] = sn*np.dot(self.sum_x, self.frame_cox)
        self.com[1] = sn*np.dot(self.sum_y, self.frame_coy)
        icom = np.round(self.com).astype(int)
        frame[self.pupil_idx] = 255
        frame[icom[1],:] = 200
        frame[:,icom[0]] = 200
        # com = center of Mass 
        return self.com
    
class VideoFile():
    def __init__(self, pgmfile):
        try:
            self.video = pgm.PGMReader(pgmfile)
        except:
            traceback.print_exc()
        else:
            self.pgmfile = pgmfile
            self.init_video()

    def init_video(self):
            self.video.seek_frame(0)
            self.frame_no = 0
            self.info = {'length':self.video.length,
                         'width':self.video.width,
                         'height':self.video.height,
                         'img_buffer':self.video.img_buffer}
            self.length = self.video.length
            self.width = self.video.width
            self.height = self.video.height
            self.img_buffer = self.video.img_buffer
            self.frame_no = None
            
    def process_frame(self, n):
        self.frame_no = n
        self.video.seek_frame(n)

def fftfilt(B, x):
    X = np.fft.fft(x)
    # Die Multiplikation im Faltbereich(Y)
    # ifft = inverse Furiertransformation
    Y = np.fft.ifft(X*B)
    y = np.real(Y)
    return y

class Results():
    df = None
    sr = 220.0 # Sampling Rate in Hz
    def __init__(self, filename, n_samples):
        self.filename = filename
        self.n_samples = n_samples
        # Excel-ähnliche Tabelle mit (6) benannten Spalten anlegen und mit nan füllen
        # s. Pandas-Dokumentation in Python4DataAnalysis.pdf z.B. S. 116
        # vAbs - die absolute Geschwindigkeit
        col = ['Time', 'Hor', 'Ver', 'vHor', 'vVer','vAbs', 'vFilt', 'vFFT', 'vConv']
        self.df = pd.DataFrame(np.full((n_samples,len(col)), np.nan), columns=col)
        # Zeiger auf Daten-Matrix für später merken
        self.data = self.df.values
        # Indizes der Positions-Spalten für später merken
        self.pos_col = self.df.columns.isin(['Hor','Ver'])
        
        # Filter initialisieren
        self.vel_k = np.array([1,0,-1],dtype=np.float64)*(self.sr/2.0)

        # Filterkern
        b = np.ones(5)
        b = b/np.sum(b)
        #b = np.array([-1,0,1], dtype=np.float32)
        self.b = b        
        # fast furier transformation
        self.B = np.fft.fft(b,n=n_samples)
        
    def store_pos(self, frame_no, pos):
        self.data[frame_no,self.pos_col] = pos
        self.data[frame_no,0] = frame_no
        
    def get_pos(self):
        return self.df.loc[:, ('Hor','Ver')].values

    def get_dataframe(self):
        # df = eingangsfaktor, Dataframes
        return self.df
    
    def analyze(self):
        # Geschwindigkeit als Ableitung der Position berechnen (mit np.gradient)
        self.df.loc[:, ('Hor','Ver')].interpolate(inplace=True)
        self.df.loc[:, ('vHor','vVer')] = np.gradient(self.df.loc[:, ('Hor','Ver')],axis=0)*self.sr
        # np.hypot - Hypothenose berechnen
        np.hypot(self.df['vHor'], self.df['vVer'], out=self.df['vAbs'].values)
        self.df['vAbs'].interpolate(inplace=True)

        # die absolut Werte mit lfilter filtrieren
        self.df['vFilt'] = signal.lfilter(self.b, 1., self.df['vAbs'].values)
        self.df['vConv'] = signal.convolve(self.df['vAbs'].values, self.b, mode='same', method='auto')
        # ***wenn der Kern groß ist: Furier-Transformation, wenn der Kern kelin: Faltung
        # die Ergebnisse von Filtern werden verschoben(an andere Stelle geschrieben) und von Convolve nicht
        
        self.df['vFFT'] = fftfilt(self.B, self.df['vAbs'].values)

        return self.df
        
    def save_result(self):
        # Report als h5, txt und py Datei speichern
        #df['Time'] = df['Time'].interpolate().round()  # Fill in missing time values
        #df['Time'].astype(np.int64)
        #self.df.set_index('Time', inplace=True)
        datastore = pd.HDFStore(self.filename+'.h5')
        datastore['pupil'] = self.df
        datastore.close()
        np.save(self.filename, self.df.values)
        np.savetxt(self.filename+'.txt', self.df.values)
        print("save")

    def load_result(self):
        datastore = pd.HDFStore(self.filename+'.h5')
        self.dataframe = datastore['pupil']
        datastore.close()
        return self.dataframe

def process_pgm (pgmfile):
    import matplotlib.pyplot as plt
    fig = plt.figure(4)
    fig.clf()
    video = VideoFile(pgmfile)
    result = np.full((video.length, 2), np.nan)
    imgproc = IMGProcess(video.width, video.height, video.length)
    for i in range(0,video.length):
        video.process_frame(i)
        result[i,:] = imgproc.process(video.img_buffer)
    plt.plot(result)
        
    
def Analyzepgm(pgmfile):
    import matplotlib.pyplot as plt
    return i

def Showpgm(pgmfile, n):
    import matplotlib.pyplot as plt
    video = VideoFile(pgmfile)
    imgproc = IMGProcess(video.width, video.height, video.length)
    
    fig = plt.figure(2)
    plt.clf()
    
    nth = np.int(np.floor(video.length/n))
    
    for i, frame_no in enumerate(range(0,video.length,nth),1):
        video.process_frame(frame_no)
        imgproc.process(video.img_buffer)
        
        ax = fig.add_subplot(n, 1, i)
        ax.imshow(video.img_buffer, cmap='gray')
        if i==1:
            plt.title("Frames=%d Width=%d Height=%d" % (video.length, video.width, video.height))
        ax.set_axis_off()
    
    plt.show()
    return i

def showpgm(pgmfile, n):
    import matplotlib.pyplot as plt
    
    video = pgm.PGMReader(pgmfile)

    fig = plt.figure(1)
    plt.clf()
    
    nth = np.int(np.floor(video.length/n))

    for i, frame_no in enumerate(range(0,video.length,nth),1):
        video.seek_frame(frame_no)
        
        ax = fig.add_subplot(n, 1, i)
        ax.imshow(video.img_buffer, cmap='gray')
        if i==1:
            plt.title("Frames=%d Width=%d Height=%d" % (video.length, video.width, video.height))
        ax.set_axis_off()
    
    plt.show()
    return i

if __name__ == '__main__':
    unittest.main()

