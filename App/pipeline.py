# Everything about managing Projects
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import dronewq
from dronewq.utils.settings import Settings

class Pipeline:
    def __init__(self, folder_path: str):
        self.settings = Settings()
        self.settings = self.settings.load(folder_path)
        
    def water_metadata(self):
        dronewq.write_metadata_csv(self.settings.raw_water_dir, self.settings.main_dir)

    def flight_plan(self):
        if not os.path.exists(self.settings.metadata):
            raise FileNotFoundError("Metadata file not found.")

        img_metadata = pd.read_csv(self.settings.metadata)
        fig, ax = plt.subplots(1,3, figsize=(10,3), layout='tight')

        ax[0].plot(list(range(len(img_metadata))),img_metadata['Altitude'])
        ax[0].set_ylabel('Altitude (m)')

        ax[1].scatter(img_metadata['Longitude'], img_metadata['Latitude'])
        ax[1].set_ylabel('Latitude')
        ax[1].set_xlabel('Longitude')

        ax[2].plot(list(range(len(img_metadata))),img_metadata['Yaw'])
        ax[2].set_ylabel('Yaw')

        out_path = os.path.join(self.settings.main_dir, "flight_plan.png")
        fig.savefig(out_path, dpi=300, bbox_inches='tight', transparent=False)
        plt.close(fig)
    
    def run(self):
        mask_pixels = True if self.settings.mask_method else False
        dronewq.process_raw_to_rrs(
            lw_method=self.settings.lw_method,
            ed_method=self.settings.ed_method,
            mask_pixels=mask_pixels,
            pixel_masking_method=self.settings.mask_method,
            nir_threshold=0.02,
            random_n=10,
            #NOTE: Should probably ask this from user
            clean_intermediates=True,
            overwrite_lt_lw=False,
            num_workers=4,
        )
    
    def 
    
    def rrs_plot(self, count: int = 25):
        masked_rrs_imgs_hedley, img_metadata = dronewq.retrieve_imgs_and_metadata(img_dir = self.settings.masked_rrs_dir, count=count)

        fig, ax = plt.subplots(1,1, figsize=(6,3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0,1,len(masked_rrs_imgs_hedley)))

        for i in range(len(masked_rrs_imgs_hedley)):
            plt.plot(wv, np.nanmean(masked_rrs_imgs_hedley[i,0:5,:,:],axis=(1,2)), marker = 'o', color=colors[i], label="")
            plt.xlabel('Wavelength (nm)')
            plt.ylabel(r'$R_{rs}\ (sr^{-1})$')
        plt.plot(wv, np.nanmean(masked_rrs_imgs_hedley[:,0:5,:,:], axis=(0,2,3)),  marker = 'o', color='black', linewidth=5, label='Mean')

        plt.legend(frameon=False)

        out_path = os.path.join(self.settings.main_dir, "rrs_plot.png")
        fig.savefig(out_path, dpi=300, bbox_inches='tight', transparent=False)
        plt.close(fig)
    
    def lt_plot(self, count: int = 25):
        lt_imgs, img_metadata = dronewq.retrieve_imgs_and_metadata(img_dir = self.settings.lt_dir, count=count)

        fig, ax = plt.subplots(1,1, figsize=(6,3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0,1,len(lt_imgs)))

        for i in range(len(lt_imgs)):
            plt.plot(wv, np.nanmean(lt_imgs[i,0:5,:,:],axis=(1,2)), marker = 'o', color=colors[i], label="")
            plt.xlabel('Wavelength (nm)')
            plt.ylabel(r'$L_{t}\ (mW\ cm^{-2}\ nm^{-1}\ sr^{-1})$')
        plt.plot(wv, np.nanmean(lt_imgs[:,0:5,:,:], axis=(0,2,3)),  marker = 'o', color='black', linewidth=5, label='Mean')

        plt.legend(frameon=False)

        out_path = os.path.join(self.settings.main_dir, "lt_plot.png")
        fig.savefig(out_path, dpi=300, bbox_inches='tight', transparent=False)
        plt.close(fig)
            
    def ed_plot(self, count: int = 25):
        ed_imgs, img_metadata = dronewq.retrieve_imgs_and_metadata(img_dir = self.settings.ed_dir, count=count)

        fig, ax = plt.subplots(1,1, figsize=(6,3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0,1,len(ed_imgs)))

        for i in range(len(ed_imgs)):
            plt.plot(wv, np.nanmean(ed_imgs[i,0:5,:,:],axis=(1,2)), marker = 'o', color=colors[i], label="")
            plt.xlabel('Wavelength (nm)')
            plt.ylabel(r'$E_{d}\ (mW\ cm^{-2}\ nm^{-1})$')
        plt.plot(wv, np.nanmean(ed_imgs[:,0:5,:,:], axis=(0,2,3)),  marker = 'o', color='black', linewidth=5, label='Mean')

        plt.legend(frameon=False)

        out_path = os.path.join(self.settings.main_dir, "ed_plot.png")
        fig.savefig(out_path, dpi=300, bbox_inches='tight', transparent=False)
        plt.close(fig)

    def masked_rrs_plot(self, count: int = 25):
        masked_rrs_imgs_hedley, img_metadata = dronewq.retrieve_imgs_and_metadata(img_dir = self.settings.masked_rrs_dir, count=count)

        fig, ax = plt.subplots(1,1, figsize=(6,3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0,1,len(masked_rrs_imgs_hedley)))

        for i in range(len(masked_rrs_imgs_hedley)):
            plt.plot(wv, np.nanmean(masked_rrs_imgs_hedley[i,0:5,:,:],axis=(1,2)), marker = 'o', color=colors[i], label="")
            plt.xlabel('Wavelength (nm)')
            plt.ylabel(r'$R_{rs}\ (sr^{-1})$')
        plt.plot(wv, np.nanmean(masked_rrs_imgs_hedley[:,0:5,:,:], axis=(0,2,3)),  marker = 'o', color='black', linewidth=5, label='Mean')

        plt.legend(frameon=False)

        out_path = os.path.join(self.settings.main_dir, "masked_rrs_plot.png")
        fig.savefig(out_path, dpi=300, bbox_inches='tight', transparent=False)
        plt.close(fig)