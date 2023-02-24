import os
import re
import json
import math
import csv

from NexFileData import *
import NexFileReaders

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showinfo, showerror

def color_decode(s):
    reobj = re.search(r'^#(?P<R>.{2})(?P<G>.{2})(?P<B>.{2})$', s)
    if reobj:
        d = reobj.groupdict()
        return (int(d['R'],16),int(d['G'],16),int(d['B'],16))
    else:
        print('color decode error: %s'%(s))
        exit(1)

def color_encode(r, g, b):
    return "#%x" %((r*256+g)*256+b)


def get_ch(cfg):
    reader = NexFileReaders.NexFileReader()
    fd = reader.ReadNexFile(cfg['data_path'])
    cfg['db'] = os.path.dirname(cfg['data_path']) 
    cfg['data_len'] = math.ceil(fd.EndTimeSeconds)

    plot_obj = {}
    plot_obj['m_filt_obj'] = []
    plot_obj['s_unit_obj'] = []
    plot_obj['raster_obj'] = [[] for _ in range(len(cfg['raster_ch']))]
    plot_obj['firing_rate_obj'] = []
    plot_obj['s_con_obj'] = []
    plot_obj['s_con_obj_pre'] = []

    for c in fd.Continuous:
        if c.Ch_num in cfg['m_filt_ch']:
            plot_obj['m_filt_obj'].append(c)
        if c.Ch_num in cfg['s_con_ch']:
            plot_obj['s_con_obj'].append(c)

    for w in fd.Waveforms:
        if w.Ch_num in cfg['s_unit_ch']:
            plot_obj['s_unit_obj'].append(w)
        for i in range(len(cfg['raster_ch'])):
            if w.Ch_num in cfg['raster_ch'][i]:
                plot_obj['raster_obj'][i].append(w)
        if w.Ch_num in cfg['firing_rate_ch']:
            plot_obj['firing_rate_obj'].append(w)

    plot_obj['m_filt_obj'].sort(reverse=True, key=lambda c: cfg['m_filt_ch'].index(c.Ch_num))
    for i in range(len(cfg['raster_ch'])):
        plot_obj['raster_obj'][i].sort(reverse=True, key=lambda w: cfg['raster_ch'][i].index(w.Ch_num))
    plot_obj['firing_rate_obj'].sort(key=lambda w: cfg['firing_rate_ch'].index(w.Ch_num))

    if cfg['s_con_en']:
        reader_pre = NexFileReaders.NexFileReader()
        fd_pre = reader_pre.ReadNexFile(cfg['pre_data_path'])
        for c in fd_pre.Continuous:
            if c.Ch_num in cfg['s_con_ch']:
                plot_obj['s_con_obj_pre'].append(c)

    return plot_obj

def m_filt_plt_win(con_obj: List[Continuous], win, path):
    win_l = win[1]-win[0]
    ch_n = len(con_obj)
    sample_rate = int(con_obj[0].SamplingRate)
    fig = plt.figure(figsize=(1.5*win_l,ch_n))
    ax = plt.axes()
    ax.yaxis.set_major_locator(ticker.FixedLocator(np.linspace(0, 0.25*(ch_n-1), ch_n)))
    ax.yaxis.set_major_formatter(ticker.FixedFormatter([c.Name for c in con_obj]))
    ax.set_xticks([])
    plt.tick_params(left=False)
    for i in ['top', 'right', 'bottom', 'left']:
        ax.spines[i].set_visible(False)
    for i in range(ch_n):
        y = con_obj[i].Values[win[0]*sample_rate:win[1]*sample_rate]+i*0.25
        x = np.linspace(0, len(y)/sample_rate, len(y))
        plt.plot(x, y, lw = 0.5, c='black')
    plt.plot([win_l+0.2 for _ in range(2)], [-0.1,0], lw=5, c='black')
    plt.text(win_l+0.3, -0.05, '100μV', verticalalignment='center')
    plt.plot([win_l-0.3, win_l+0.2], [-0.15,-0.15], lw=5, c='black')
    plt.text(win_l-0.05, -0.22, '500ms', horizontalalignment='center')
    plt.xlim(0, win_l+1)
    plt.ylim(-0.25, 0.25*len(con_obj))
    plt.title("%d-%dseconds"%(win[0], win[1]))
    plt.savefig(path)
    plt.close(fig)

def m_filt_plt(con_obj : List[Continuous], cfg):
    fig_dir = os.path.join(cfg['db'], 'Multi_filtered_wave')
    if not os.path.exists(fig_dir):
        os.mkdir(fig_dir)
    if cfg['m_filt_win']:
        m_filt_plt_win(con_obj, cfg['m_filt_win'], os.path.join(fig_dir,'0.png'))
    else:
        fig_num = math.ceil(con_obj[0].Values.size/cfg['m_filt_timestep']/con_obj[0].SamplingRate)
        for n in range(fig_num):
            m_filt_plt_win(con_obj, [n*cfg['m_filt_timestep'],(n+1)*cfg['m_filt_timestep']], os.path.join(fig_dir, "%d.png"%(n)))


def s_con_plt_win(con_obj: List[Continuous], con_obj_pre: List[Continuous], win, path):
    win_l = win[1]-win[0]
    sample_rate = int(con_obj[0].SamplingRate)
    fig_num = len(con_obj) 
    fig, ax = plt.subplots(2,1,figsize=(15,3))
    for n in range(fig_num):
        ax[0].axis('off')
        ax[1].axis('off')
        plt.subplot(211)
        y = con_obj_pre[n].Values[win[0]*sample_rate:win[1]*sample_rate]
        x = np.linspace(win[0], win[0]+len(y)/sample_rate, len(y))
        plt.plot(x, y, lw = 0.5, c='black')
        plt.plot([win[1]+0.1, win[1]+0.1], [-0.1,0.1], lw=5, c='black')
        plt.text(win[1]+0.15, 0, '200μV', verticalalignment='center')
        plt.xlim(win[0], win[1]+0.2)
        plt.subplot(212)
        plt.plot(x, con_obj[n].Values[win[0]*sample_rate:win[1]*sample_rate],
                    lw = 0.5, c='black')
        plt.plot([win[1]-0.5, win[1]], [-0.2,-0.2], lw=5, c='black')
        plt.text(win[1]-0.25, -0.27, '500ms', horizontalalignment='center')
        plt.plot([win[1]+0.1, win[1]+0.1], [-0.05,0.05], lw=5, c='black')
        plt.text(win[1]+0.15, 0, '100μV', verticalalignment='center')
        plt.xlim(win[0], win[1]+0.2)
        plt.savefig(os.path.join(path, '%s %d-%dseconds.png'%(con_obj[n].Name,win[0],win[1])))
    plt.close(fig)

def s_con_plt(con_obj: List[Continuous], con_obj_pre: List[Continuous], cfg):
    fig_dir = os.path.join(cfg['db'], 'Single_continuous')
    if not os.path.exists(fig_dir):
        os.mkdir(fig_dir)
    
    if cfg['s_con_win']:
        s_con_plt_win(con_obj, con_obj_pre, cfg['s_con_win'], fig_dir)
    else:
        fig_num = math.ceil(con_obj[0].Values.size/cfg['s_con_timestep']/con_obj[0].SamplingRate)
        for n in range(fig_num):
            s_con_plt_win(con_obj, con_obj_pre, [n*cfg['s_con_timestep'],(n+1)*cfg['s_con_timestep']], fig_dir)


def s_unit_plt(wave_obj: List[Waveform], cfg):
    fig_dir = os.path.join(cfg['db'], 'Single_unit')
    if not os.path.exists(fig_dir):
        os.mkdir(fig_dir)
    fig = plt.figure(figsize=(10,10))

    ax_range = cfg['ax_range']
    n = 0
    for w in wave_obj:
        x = np.linspace(0, w.NumPointsWave*1000/w.SamplingRate, w.NumPointsWave)
        for d in w.Values:
            plt.plot(x, d, lw=0.5, c='lightgrey')
        mean_w = w.Values.mean(axis=0)
        plt.plot(x, mean_w, lw = 10, c=cfg['s_unit_color'][n%len(cfg['s_unit_color'])])
        plt.xlim(ax_range[0][1], ax_range[0][1])
        plt.ylim(ax_range[1][0], ax_range[1][1])
        plt.title(w.Name)
        plt.savefig(os.path.join(fig_dir, '%s.png'%(w.Name)))
        plt.clf()
        n += 1
    plt.close(fig)


def raster_plt(wave_obj_list, cfg):
    fig_dir = os.path.join(cfg['db'], 'Raster')
    if not os.path.exists(fig_dir):
        os.mkdir(fig_dir)
    for i in range(len(wave_obj_list)):
        s_raster_plt(wave_obj_list[i], cfg['raster_color'][i%len(cfg['raster_color'])],
                        cfg['data_len'], os.path.join(fig_dir, '%d.png'%(i)))

def s_raster_plt(wave_obj: List[Waveform], color, data_len, path):
    fig = plt.figure(figsize=(15, 0.2*len(wave_obj)))
    c_start = color_decode(color[1])
    c_end = color_decode(color[0])
    r_list = np.linspace(c_start[0], c_end[0], len(wave_obj))
    g_list = np.linspace(c_start[1], c_end[1], len(wave_obj))
    b_list = np.linspace(c_start[2], c_end[2], len(wave_obj))
    ax = plt.axes()
    ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.set_xticks([])
    plt.tick_params(axis = 'y', width = 3, length = 5)
    def raster_ylabel(v, pos):
        return int(v*5)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(raster_ylabel))
    for i in ['top', 'right', 'bottom', 'left']:
        ax.spines[i].set_visible(False)
    for n in range(len(wave_obj)):
        plt.scatter(wave_obj[n].Timestamps, [n*0.2 for _ in range(len(wave_obj[n].Timestamps))], 
                    marker='|', c=color_encode(int(r_list[n]), int(g_list[n]), int(b_list[n])))
    plt.xlim(-1.5, data_len) 
    plt.ylim(-0.2, len(wave_obj)*0.2)
    plt.plot([data_len-10, data_len], [-0.2,-0.2], lw='5', c='black')
    plt.text(data_len-5,-0.3,'10s',horizontalalignment='center', verticalalignment='top')
    plt.savefig(path)
    plt.close(fig)


def firing_rate_plt(wave_obj: List[Waveform], cfg):
    fig_dir = os.path.join(cfg['db'], 'Firing_rate')
    if not os.path.exists(fig_dir):
        os.mkdir(fig_dir)
    
    data = []
    for w in wave_obj:
        d = [0 for _ in range(cfg['data_len']+math.floor(cfg['firing_rate_win']/2)*2)] 
        for t in w.Timestamps:
            for i in range(cfg['firing_rate_win']):
                if cfg['firing_rate_win']%2:
                    d[i+math.floor(t)] += 1
                else:
                    d[i+math.floor(t+0.5)] += 1
        rate = [0 for _ in range(cfg['data_len'])]
        for i in range(cfg['data_len']): 
            if i < math.floor(cfg['firing_rate_win']/2):
                if cfg['firing_rate_win']%2:
                    rate[i] = d[i+math.floor(cfg['firing_rate_win']/2)]/(i+math.ceil(cfg['firing_rate_win']/2))
                else:
                    rate[i] = d[i+math.floor(cfg['firing_rate_win']/2)]/(i+cfg['firing_rate_win']/2+0.5)
            elif i < cfg['data_len']-math.floor(cfg['firing_rate_win']/2):
                rate[i] = d[i+math.floor(cfg['firing_rate_win']/2)]/cfg['firing_rate_win']
            else:
                if cfg['firing_rate_win']%2:
                    rate[i] = d[i+math.floor(cfg['firing_rate_win']/2)]/((cfg['data_len']-i-1)
                                +math.ceil(cfg['firing_rate_win']/2))
                else:
                    rate[i] = d[i+math.floor(cfg['firing_rate_win']/2)]/((cfg['data_len']-i-1)
                                +cfg['firing_rate_win']/2+0.5)
        data.append(rate)
    
    if cfg['firing_rate_export']:
        name_r = ['time'] + [w.Name for w in wave_obj]
        with open (os.path.join(fig_dir, 'firing_rate.csv'), 'w', newline="") as csv_f:
            csv_w = csv.writer(csv_f)
            csv_w.writerow(name_r)
            for i in range(len(data[0])):
                d = [i+0.5] + [t[i] for t in data]
                csv_w.writerow(d)

    fig = plt.figure(figsize=(15, 0.2*len(wave_obj)))
    ax = plt.axes()
    ax.yaxis.set_major_locator(ticker.MultipleLocator(5))
    ax.set_xticks([])
    for i in ['top', 'right', 'bottom', 'left']:
        ax.spines[i].set_visible(False)
    plt.tick_params(axis = 'y', width = 3, length = 5)
    plt.imshow(data, cmap=plt.cm.jet,aspect='auto', origin='lower')  
    plt.colorbar()
    plt.plot([cfg['data_len']-10, cfg['data_len']], [-1,-1], lw='3', c='black')
    plt.text(cfg['data_len']-5,-1.5,'10s',horizontalalignment='center', verticalalignment='top')
    plt.xlim(-1,cfg['data_len'])
    plt.savefig(os.path.join(fig_dir, '1.png'))
    plt.close(fig)

def run():
    cur_path = os.getcwd()
    with open(os.path.join(cur_path, 'plot_cfg.json'),'r') as cfg_f:
        cfg = json.load(cfg_f)

    cfg['data_path'] = data_path.get() 
    cfg['pre_data_path'] = pre_data_path.get()
    if not cfg['data_path']:
        showerror(title = "Error", message = "Do not select \"Post Data\"")
        return
    if not cfg['pre_data_path']:
        if cfg['s_con_en']:
            showerror(title = "Error", message = "Do not select \"Pre Data\" when s_con_en=1")
            return

    plot_obj = get_ch(cfg)
    if cfg['m_filt_en'] and plot_obj['m_filt_obj']:
        m_filt_plt(plot_obj['m_filt_obj'], cfg)
    if cfg['s_unit_en'] and plot_obj['s_unit_obj']:
        s_unit_plt(plot_obj['s_unit_obj'], cfg)
    if cfg['raster_en'] and plot_obj['raster_obj'][0]:
        raster_plt(plot_obj['raster_obj'], cfg)
    if cfg['firing_rate_en'] and plot_obj['firing_rate_obj']:
        firing_rate_plt(plot_obj['firing_rate_obj'], cfg)
    if cfg['s_con_en'] and plot_obj['s_con_obj']:
        s_con_plt(plot_obj['s_con_obj'], plot_obj['s_con_obj_pre'], cfg)

    showinfo(title = "", message = "Complete") 

def data_select():
    data_path.set('')
    s = askopenfilename(filetypes=[('NEX', '*.nex')])
    if s:
        data_path.set(s.replace('/','\\'))
def pre_data_select():
    pre_data_path.set('')
    s = askopenfilename(filetypes=[('NEX', '*.nex')])
    if s:
        pre_data_path.set(s.replace('/','\\'))

if __name__ == "__main__":
    root = tk.Tk()
    root.title('OfflineSorter Data Drawer V1')
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw-390) / 2
    y = (sh-100) / 2
    root.geometry('390x100+%d+%d'%(x,y))
    root.resizable(False, False)

    data_path = tk.StringVar()
    tk.Entry(root, textvariable=data_path, width=40).grid(row=0, column=0, sticky='w', padx=5)
    tk.Button(root, text='Post Data', width=10, font=('微软雅黑', 10), command=data_select).grid(row=0, column=1, sticky='w')

    pre_data_path = tk.StringVar()
    tk.Entry(root, textvariable=pre_data_path, width=40).grid(row=1, column=0, sticky='w', padx=5)
    tk.Button(root, text='Pre Data', width=10, font=('微软雅黑', 10), command=pre_data_select).grid(row=1, column=1, sticky='w')

    tk.Button(root, text='Start', pady=0, font=('微软雅黑', 10), command=run).grid(row=2, columnspan=2)
    root.mainloop()

