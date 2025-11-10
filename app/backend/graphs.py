#creating graphs for app
from flask import Blueprint, request, jsonify, Response
from dronewq.utils.settings import Settings
from dronewq.utils.images import retrieve_imgs_and_metadata
import os
import io
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

plt.rcParams['mathtext.default'] = 'regular'

bp = Blueprint("graphs", __name__)

@bp.route('/plot_lt', methods=["GET"])
def plot_lt():
    fig, axs = plt.subplots(2,2, figsize=(10,5))

    axs = axs.ravel()

    wv = [475, 560, 668, 717, 842]
    colors = plt.cm.viridis(np.linspace(0,1,len(lt_imgs)))

    #lt
    for i in range(len(lt_imgs)):
        axs[0].plot(wv, np.nanmean(lt_imgs[i,0:5,:,:],axis=(1,2)),  marker = 'o', color=colors[i], label="")
        axs[0].set_xlabel('Wavelength (nm)')
        axs[0].set_ylabel('$L_t\ (mW\ m^2\ sr^{-1}\ nm^{-1}$)')   
    axs[0].plot(wv, np.nanmean(lt_imgs[:,0:5,:,:], axis=(0,2,3)),  marker = 'o', color='black', linewidth=5, label='Mean')
    axs[0].legend(frameon=False)
    plt.savefig('lt_plot.png')

@bp.route('/plot_dls_ed', methods=["GET"])
def plot_dls_ed():
    fig = Figure()
    canvas = FigureCanvas(fig)
    ax = fig.add_subplot(111)
    ax.plot(wv, ed.iloc[:,1:6].mean(axis=0),  marker = 'o', color='black', linewidth=5, label='Mean')
    FigureCanvas(fig).print_png(response)
    return response 

@bp.route('/plot_masked_rrs_hedley', methods=["GET"])
def plot_masked_rrs_hedley():
    fig = Figure()
    canvas = FigureCanvas(fig)
    ax = fig.add_subplot(111)
    ax.plot([1, 2, 3, 4, 5])
    canvas.print_png(response)
    return response 