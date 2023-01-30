import multiprocessing, glob, shutil, os, datetime, subprocess, math

import geopandas as gpd
import pandas as pd

import numpy as np
import matplotlib.pyplot as plt

import cv2
import exiftool
import rasterio
# from GPSPhoto import gpsphoto
import scipy.ndimage as ndimage
from skimage.transform import resize
from pathlib import Path


from ipywidgets import FloatProgress, Layout
from IPython.display import display

from micasense import imageset as imageset
from micasense import capture as capture
import micasense.imageutils as imageutils
import micasense.plotutils as plotutils
from micasense import panel 
from micasense import image as image

import random
import cameratransform as ct
from rasterio.merge import merge


def write_metadata_csv(img_set, csv_output_path):
    """
    This function grabs the EXIF metadata from img_set and writes it to outputPath/metadata.csv. Other metadata could be added based on what is needed in your workflow.
    
    Inputs: 
    img_set: An ImageSet is a container for a group of Captures that are processed together. It is defined by running the ImageSet.from_directory() function found in Micasense's imageset.py 
    csv_output_path: A string containing the filepath to store metadata.csv containing image EXIF metadata 
    
    Output: A .csv of metadata for each image capture. 
    
    """
    header = "SourceFile,GPSDateStamp,GPSTimeStamp,GPSLatitude,GPSLatitudeRef,GPSLongitude,GPSLongitudeRef,GPSAltitude,FocalLength,ImageWidth,ImageHeight,GPSImgDirection,GPSPitch,GPSRoll\n"
    
    lines = [header]
    for i,capture in enumerate(img_set.captures):
        #get lat,lon,alt,time
        outputFilename = 'capture_' + str(i+1)+'.tif'
        fullOutputPath = os.path.join(csv_output_path, outputFilename)
        lat,lon,alt = capture.location()
        
        imagesize  = capture.images[0].meta.image_size()
        
        yaw, pitch, roll = capture.dls_pose()
        yaw, pitch, roll = np.array([yaw, pitch, roll]) * 180/math.pi

        linestr = '"{}",'.format(fullOutputPath)
        linestr += capture.utc_time().strftime("%Y:%m:%d,")
        linestr += capture.utc_time().strftime("%H:%M:%S,")
        linestr += '{},'.format(capture.location()[0])
        if capture.location()[0] > 0:
            linestr += 'N,'
        else:
            linestr += 'S,'
        linestr += '{},'.format(capture.location()[1])
        if capture.location()[1] > 0:
            linestr += 'E,'
        else:
            linestr += 'W,'
        linestr += '{},'.format(capture.location()[2])
        linestr += '{},'.format(capture.images[0].focal_length)
        linestr += '{},{},'.format(imagesize[0],imagesize[1])
        linestr += '{},{},{}'.format(yaw, pitch, roll)
        linestr += '\n' # when writing in text mode, the write command will convert to os.linesep
        lines.append(linestr)
        

    fullCsvPath = os.path.join(csv_output_path,'metadata.csv')
    with open(fullCsvPath, 'w') as csvfile: #create CSV
        csvfile.writelines(lines)
    
    # let's convert the timestamp to a proper Datetime object and make the filenames the index
    df = pd.read_csv(fullCsvPath)
    df['filename'] = df['SourceFile'].str.split('/').str[-1]
    df = df.set_index('filename')
    df['UTC-Time'] = pd.to_datetime(df['GPSDateStamp'] +' '+ df['GPSTimeStamp'],format="%Y:%m:%d %H:%M:%S")    
    df.to_csv(fullCsvPath)
    
    return(fullCsvPath)

def load_images(img_list):
    """
    This function loads all images in a directory as a multidimensional numpy array. 
    
    Inputs: 
    img_list: A list of .tif files, usually called by using glob.glob(filepath) 
    
    Output: A multidimensional numpy array of all image captures in a directory 
    
    """
    all_imgs = []
    for im in img_list:
        with rasterio.open(im, 'r') as src:
            all_imgs.append(src.read())
    return(np.array(all_imgs))

def load_img_fn_and_meta(csv_path, count=10000, start=0):
    """
    This function returns a pandas dataframe of captures and associated metadata with the options of how many to list and what number of image to start on.  
    
    Inputs: 
    csv_path: A string containing the filepath 
    count: The amount of images to load. Default is 10000
    start: The image to start loading from. Default is 0 (first image the .csv). 
    
    Output: Pandas dataframe of image metadata
    
    """    
    df = pd.read_csv(csv_path)
    df = df.set_index('filename')
    df['UTC-Time'] = pd.to_datetime(df['UTC-Time'])    
    # cut off if necessary
    df = df.iloc[start:start+count]

    return(df)

def retrieve_imgs_and_metadata(img_dir, count=10000, start=0, altitude_cutoff = 0, sky=False):
    """
    This function is the main interface we expect the user to use when grabbing a subset of imagery from any stage in processing. This returns the images as a numpy array and metadata as a pandas dataframe. 
    
    Inputs:
    img_dir: A string containing the directory filepath of images to be retrieved
    count: The amount of images you want to list. Default is 10000
    start: The number of image to start on. Default is 0 (first image in img_dir). 
    
    Outputs: A multidimensional numpy array of all image captures in a directory and a Pandas dataframe of image metadata. 
    
    """
    if sky:
        csv_path = img_dir + '/metadata.csv'
    else:
        csv_path = os.path.dirname(img_dir) + '/metadata.csv'
        
    df = load_img_fn_and_meta(csv_path, count=count, start=start)
    
    # apply altitiude threshold and set IDs as the indez
    df = df[df['GPSAltitude'] > altitude_cutoff]
    
    # this grabs the filenames from the subset of the dataframe we've selected, then preprends the image_dir that we want.
    # the filename is the index
    all_imgs = load_images([os.path.join(img_dir,fn) for fn in df.index.values])
  
    return(all_imgs, df)


def get_warp_matrix(img_capture, max_alignment_iterations = 50):
    """
    This function uses the MicaSense imageutils.align_capture() function to determine an alignment (warp) matrix of a single capture that can be applied to all images. From MicaSense: "For best alignment results it's recommended to select a capture which has features which visible in all bands. Man-made objects such as cars, roads, and buildings tend to work very well, while captures of only repeating crop rows tend to work poorly. Remember, once a good transformation has been found for flight, it can be generally be applied across all of the images." Ref: https://github.com/micasense/imageprocessing/blob/master/Alignment.ipynb
        
    Inputs: 
    img_capture: A capture is a set of images taken by one MicaSense camera which share the same unique capture identifier (capture_id). These images share the same filename prefix, such as IMG_0000_*.tif. It is defined by running ImageSet.from_directory().captures. 
    max_alignment_iterations: The maximum number of solver iterations. 
    
    ****AW_question: Why are we only changing some of the default inputs? Want to discuss this function.  
    
    Output: A numpy.ndarray of the warp matrix from a single image capture. 
    """
    
    ## Alignment settings
    match_index = 0 # Index of the band 
    warp_mode = cv2.MOTION_HOMOGRAPHY # MOTION_HOMOGRAPHY or MOTION_AFFINE. For Altum images only use HOMOGRAPHY
    pyramid_levels = 1 # for images with RigRelatives, setting this to 0 or 1 may improve alignment
    print("Aligning images. Depending on settings this can take from a few seconds to many minutes")
    # Can potentially increase max_iterations for better results, but longer runtimes
    warp_matrices, alignment_pairs = imageutils.align_capture(img_capture,
                                                              ref_index = match_index,
                                                              max_iterations = max_alignment_iterations,
                                                              warp_mode = warp_mode,
                                                              pyramid_levels = pyramid_levels)

    return(warp_matrices)


def save_images(img_set, img_output_path, thumbnailPath, warp_img_capture, generateThumbnails=True, overwrite=False):
    """
    This function processes each capture in an imageset to apply a warp matrix and save new .tifs with units of radiance (W/sr/nm) and optional RGB .jpgs.
    
    Inputs: 
    img_set: An ImageSet is a container for a group of Captures that are processed together. It is defined by running the ImageSet.from_directory() function found in Micasense's imageset.py 
    img_output_path: A string containing the filepath to store a new folder of radiance .tifs
    thumbnailPath: A string containing the filepath to store a new folder of RGB thumnail .jpgs
    warp_img_capture: A Capture chosen to align all images. Can be created by using Micasense's ImageSet-from_directory().captures function
    generateThumbnails: Option to create RGB .jpgs of all the images. Default is True
    overwrite: Option to overwrite files that have been written previously. Default is False
    
    Output: New .tif files for each capture in img_set with units of radiance (W/sr/nm) and optional new RGB thumbnail .jpg files for each capture.
    """

    warp_matrices = get_warp_matrix(warp_img_capture)

    if not os.path.exists(img_output_path):
        os.makedirs(img_output_path)
    if generateThumbnails and not os.path.exists(thumbnailPath):
        os.makedirs(thumbnailPath)

    start = datetime.datetime.now()
    for i,capture in enumerate(img_set.captures):
        outputFilename = 'capture_' + str(i+1) + '.tif'
        thumbnailFilename = 'capture_' + str(i+1) + '.jpg'
        fullOutputPath = os.path.join(img_output_path, outputFilename)
        fullThumbnailPath= os.path.join(thumbnailPath, thumbnailFilename)
        if (not os.path.exists(fullOutputPath)) or overwrite:
            if(len(capture.images) == len(img_set.captures[0].images)):
               
                capture.dls_irradiance = None
                capture.compute_undistorted_radiance()
                capture.create_aligned_capture(irradiance_list=None, img_type= 'radiance', warp_matrices=warp_matrices)
                capture.save_capture_as_stack(fullOutputPath, sort_by_wavelength=True)
                if generateThumbnails:
                    capture.save_capture_as_rgb(fullThumbnailPath)
        capture.clear_image_data()
    end = datetime.datetime.now()

    print("Saving time: {}".format(end-start))
    print("Alignment+Saving rate: {:.2f} images per second".format(float(len(img_set.captures))/float((end-start).total_seconds())))
    return(True)


def process_micasense_images(project_dir, warp_img_dir=None, overwrite=False, sky=False):
    """
    This function is wrapper function for the save_images() function to read in an image directory and produce new .tifs with units of radiance (W/sr/nm).  
    
    Inputs: 
    project_dir: a string containing the filepath of the raw .tifs
    warp_img_dir: a string containing the filepath of the capture to use to create the warp matrix
    overwrite: Option to overwrite files that have been written previously. Default is False
    sky: Option to run raw sky captures to collected Lsky. If True, the save_images() is run on raw .tif files and saves new .tifs in sky_lt directories. If False, save_images() is run on raw .tif files and saves new .tifs in lt directories. 
    
    Output: New .tif files for each capture in image directory with units of radiance (W/sr/nm) and optional new RGB thumbnail .jpg files for each capture.
        
    """
    
    if sky:
        img_dir = project_dir+'/raw_sky_imgs'
    else:
        img_dir = project_dir+'/raw_water_imgs'

    imgset = imageset.ImageSet.from_directory(img_dir)
    
    if warp_img_dir:
        warp_img_capture = imageset.ImageSet.from_directory(warp_img_dir).captures[0]
        print('used warp dir', warp_img_dir)
    else:
        warp_img_capture = imgset.captures[0]
    
    # just have the sky images go into a different dir and the water imgs go into a default 'lt_imgs' dir 
    if sky:
        outputPath = os.path.join(project_dir,'sky_lt_imgs')
        output_csv_path = outputPath
        thumbnailPath = os.path.join(project_dir, 'sky_lt_thumbnails')
    else:
        outputPath = os.path.join(project_dir,'lt_imgs')
        output_csv_path = project_dir
        thumbnailPath = os.path.join(project_dir, 'lt_thumbnails')
    
    if save_images(imgset, outputPath, thumbnailPath, warp_img_capture, overwrite=overwrite) == True:
        print("Finished saving images.")
        fullCsvPath = write_metadata_csv(imgset, output_csv_path)
        print("Finished saving image metadata.")
            
    return(outputPath)


######## workflow functions ########

def mobley_rho_method(sky_lt_dir, lt_dir, lw_dir, rho = 0.028): 
    """
    This function calculates water leaving radiance (Lw) by multiplying a single (or small set of) sky radiance (Lsky) images by a single rho value. The default is rho = 0.028, which is based off recommendations described in Mobley, 1999. This approach should only be used if sky conditions are not changing substantially during the flight and winds are less than 5 m/s. 
    
    Inputs: 
    sky_lt_dir: A string containing the directory filepath of sky_lt images
    lt_dir: A string containing the directory filepath of lt images 
    lw_dir: A string containing the directory filepath of new lw images
    rho = The effective sea-surface reflectance of a wave facet. The default 0.028
    
    Outputs: New Lw .tifs with units of W/sr/nm
    """

    # grab the first ten of these images, average them, then delete this from memory
    sky_imgs, sky_img_metadata = retrieve_imgs_and_metadata(sky_lt_dir, count=10, start=0, altitude_cutoff=0, sky=True)
    lsky_median = np.median(sky_imgs,axis=(0,2,3)) # here we want the median of each band
    del sky_imgs # free up the memory

    # go through each Lt image in the dir and subtract out rho*lsky to account for sky reflection
    for im in glob.glob(lt_dir + "/*.tif"):
        with rasterio.open(im, 'r') as Lt_src:
            profile = Lt_src.profile
            profile['count']=5
            lw_all = []
            for i in range(1,6):
                # todo this is probably faster if we read them all and divide by the vector
                lt = Lt_src.read(i)
                lw = lt - (rho*lsky_median[i-1])
                lw_all.append(lw) #append each band
            stacked_lw = np.stack(lw_all) #stack into np.array

            #write new stacked lw tifs
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(lw_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_lw)
                
    return(True)


def blackpixel_method(sky_lt_dir, lt_dir, lw_dir):
    """
    This function calculates water leaving radiance (Lw) by applying the black pixel assumption which assumes Lw in the NIR is negligable due to strong absorption of water. Therefore, total radiance (Lt) in the NIR is considered to be solely surface reflected light (Lsr) , which allows rho to be calculated if sky radiance (Lsky) is known. This method should only be used for waters where there is little to none NIR signal (i.e. Case 1 waters). The assumption tends to fail in more turbid waters where high concentrations of particles enhance backscattering and Lw in the NIR (i.e. Case 2 waters). 
        
    Inputs: 
    sky_lt_dir: A string containing the directory filepath of sky_lt images
    lt_dir: A string containing the directory filepath of lt images 
    lw_dir: A string containing the directory filepath of new lw images
    
    Outputs: New Lw .tifs with units of W/sr/nm
        
    """
    # grab the first ten of these images, average them, then delete this from memory
    sky_imgs, sky_img_metadata = retrieve_imgs_and_metadata(sky_lt_dir, count=10, start=0, altitude_cutoff=0, sky=True)
    lsky_median = np.median(sky_imgs,axis=(0,2,3)) # here we want the median of each band
    del sky_imgs

    for im in glob.glob(lt_dir + "/*.tif"):
        with rasterio.open(im, 'r') as Lt_src:
            profile = Lt_src.profile
            profile['count']=5
           
            Lt = Lt_src.read(4)
            rho = Lt/lsky_median[4-1]
            lw_all = []
            for i in range(1,6):
                # todo this is probably faster if we read them all and divide by the vector
                lt = Lt_src.read(i)
                lw = lt - (rho*lsky_median[i-1]) 
                lw_all.append(lw) #append each band
            stacked_lw = np.stack(lw_all) #stack into np.array

            #write new stacked lw tifs
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(lw_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_lw)
                
    return(True)


def hedley_method(lt_dir, lw_dir, random_n=10):
    """
   This function calculates water leaving radiance (Lw) by modelling a constant 'ambient' NIR brightness level which is removed from all pixels across all bands. An ambient NIR level is calculated by averaging the minimum 10% of Lt(NIR) across a random subset images. This value represents the NIR brightness of a pixel with no sun glint. A linear relationship between Lt(NIR) amd the visible bands (Lt) is established, and for each pixel, the slope of this line is multiplied by the difference between the pixel NIR value and the ambient NIR level. 
   
   Inputs: 
   lt_dir: A string containing the directory filepath of lt images 
   lw_dir: A string containing the directory filepath of new lw images
   random_n: The amount of random images to calculate ambient NIR level. Default is 10. 
   
   Outputs: New Lw .tifs with units of W/sr/nm
   
   """
    lt_all = []
    rand = random.sample(glob.glob(lt_dir + "/*.tif"), random_n) #open random n files. n is selected by user in process_raw_
    for im in rand:
        with rasterio.open(im, 'r') as lt_src:
            profile = lt_src.profile
            lt = lt_src.read()
            lt_all.append(lt)

    stacked_lt = np.stack(lt_all)
    stacked_lt_reshape = stacked_lt.reshape(*stacked_lt.shape[:-2], -1) #flatten last two dims

    #apply linear regression between NIR and visible bands 
    min_lt_NIR = []
    for i in range(len(rand)):
        min_lt_NIR.append(np.percentile(stacked_lt_reshape[i,4,:], .1)) #calculate minimum 10% of Lt(NIR)
    mean_min_lt_NIR = np.mean(min_lt_NIR) #take mean of minimum 10% of random Lt(NIR)

    all_slopes = []
    for i in range(len(glob.glob(lt_dir + "/*.tif"))):
        im = glob.glob(lt_dir + "/*.tif")[i]
        im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
        with rasterio.open(im, 'r') as lt_src:
            profile = lt_src.profile
            lt = lt_src.read()
            lt_reshape = lt.reshape(*lt.shape[:-2], -1) #flatten last two dims

        lw_all = []
        for j in range(0,5):
            slopes = np.polyfit(lt_reshape[4,:], lt_reshape[j,:], 1)[0] #calculate slope between NIR and all bands of random files
            all_slopes.append(slopes)

            #calculate Lw (Lt - b(Lt(NIR)-min(Lt(NIR))))
            lw = lt[j,:,:] - all_slopes[j]*(lt[4,:,:]-mean_min_lt_NIR)
            lw_all.append(lw)

        stacked_lw = np.stack(lw_all) #stack into np.array
        profile['count']=5

        #write new stacked Rrs tif w/ reflectance units
        with rasterio.open(os.path.join(lw_dir, im_name), 'w', **profile) as dst:
            dst.write(stacked_lw)
    return(True)


def panel_ed(panel_dir, lw_dir, rrs_dir, output_csv_path):
    """
    This function calculates remote sensing reflectance (Rrs) by dividing downwelling irradiance (Ed) from the water leaving radiance (Lw) .tifs. Ed is calculated from the calibrated reflectance panel. This method does not perform well when light is variable such as partly cloudy days. It is recommended to use in the case of a clear, sunny day. 
    
    Inputs:
    panel_dir: A string containing the directory filepath of the panel image captures
    lw_dir: A string containing the directory filepath of lw images
    rrs_dir: A string containing the directory filepath of new rrs images
    output_csv_path: A string containing the filepath to save Ed measurements (mW/m2/nm) calculated from the panel
    
    Outputs:
    New Rrs .tifs with units of sr^-1 
    New .csv file with average Ed measurements (mW/m2/nm) calculated from image cpatures of the calibrated reflectance panel
    
    """
    panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures
    panels = np.array(panel_imgset)  
    
    ed_data = []
    ed_columns = ['image', 'ed_475', 'ed_560', 'ed_668', 'ed_717', 'ed_842']
    
    for i in range(len(panels)):         
        #calculate panel Ed from every panel capture
        ed = np.array(panels[i].panel_irradiance()) # this function automatically finds the panel albedo and uses that to calcuate Ed, otherwise raises an error
        ed[3], ed[4] = ed[4], ed[3] #flip last two bands
        ed_row = ['capture_'+str(i+1)]+[np.mean(ed[0])]+[np.mean(ed[1])]+[np.mean(ed[2])]+[np.mean(ed[3])]+[np.mean(ed[4])]
        ed_data.append(ed_row)
        
    ed_data = pd.DataFrame.from_records(ed_data, index='image', columns = ed_columns)
    ed_data.to_csv(output_csv_path+'/panel_ed.csv')

    # now divide the lw_imagery by Ed to get rrs
    # go through each Lt image in the dir and divide it by the lsky
    for im in glob.glob(lw_dir + "/*.tif"):
        with rasterio.open(im, 'r') as Lw_src:
            profile = Lw_src.profile
            profile['count']=5
            rrs_all = []
            # could vectorize this for speed
            for i in range(1,6):
                lw = Lw_src.read(i)
                
                rrs = lw/ed[i-1]
                rrs_all.append(rrs) #append each band
            stacked_rrs = np.stack(rrs_all) #stack into np.array
            
            #write new stacked Rrs tifs w/ Rrs units
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(rrs_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_rrs)
    return(True)


def dls_ed(raw_water_dir, lw_dir, rrs_dir, output_csv_path, panel_dir=None, dls_corr=False):

    """
    This function calculates remote sensing reflectance (Rrs) by dividing downwelling irradiance (Ed) from the water leaving radiance (Lw) .tifs. Ed is derived from the downwelling light sensor (DLS), which is collected at every image capture. This method does not perform well when light is variable such as partly cloudy days. It is recommended to use in overcast, completely cloudy conditions. A DLS correction can be optionally applied to tie together DLS and panel Ed measurements. In this case, a compensation factor derived from the calibration reflectance panel is applied to DLS Ed measurements.The defualt is False. 
    

    Inputs:
    raw_water_dir: A string containing the directory filepath of the raw water images
    lw_dir: A string containing the directory filepath of lw images
    rrs_dir: A string containing the directory filepath of new rrs images
    output_csv_path: A string containing the filepath to save Ed measurements (mW/m2/nm) derived from the DLS
    panel_dir: A string containing the filepath of panel images. Only need if dls_corr=True. 
    dls_corr: Option to apply compensation factor from calibration reflectance panel to DLS Ed measurements. Default is False. 
    
    Outputs:
    New Rrs .tifs with units of sr^-1 
    New .csv file with average Ed measurements (mW/m2/nm) calcualted from DLS measurements
    """
    capture_imgset = imageset.ImageSet.from_directory(raw_water_dir).captures
    ed_data = []
    ed_columns = ['image', 'ed_475', 'ed_560', 'ed_668', 'ed_717', 'ed_842']
    
    if not dls_corr:
        for i,capture in enumerate(capture_imgset):
            ed = capture.dls_irradiance()
            ed[3], ed[4] = ed[4], ed[3] #flip last two bands (red edge and NIR)
            ed_row = ['capture_'+str(i+1)]+[np.mean(ed[0]*1000)]+[np.mean(ed[1]*1000)]+[np.mean(ed[2]*1000)]+[np.mean(ed[3]*1000)]+[np.mean(ed[4]*1000)] #multiply by 1000 to scale to mW 
            ed_data.append(ed_row)

        ed_data_df = pd.DataFrame.from_records(ed_data, index='image', columns = ed_columns)
        ed_data_df.to_csv(output_csv_path+'/dls_ed.csv')

    if dls_corr:
        panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures
        panels = np.array(panel_imgset)  

        panel_ed_data = []  
        dls_ed_data = []
        for i, capture in enumerate(panels): 
            #calculate panel Ed from every panel capture
            panel_ed = np.array(panels[i].panel_irradiance()) # this function automatically finds the panel albedo and uses that to calcuate Ed, otherwise raises an error
            panel_ed[3], panel_ed[4] = panel_ed[4], panel_ed[3] #flip last two bands
            panel_ed_row = ['capture_'+str(i+1)]+[np.mean(panel_ed[0])]+[np.mean(panel_ed[1])]+[np.mean(panel_ed[2])]+[np.mean(panel_ed[3])]+[np.mean(panel_ed[4])] #multiply by 1000 to scale to mW (but want ed to still be in W to divide by Lw which is in W)
            panel_ed_data.append(panel_ed_row)

            #calculate DLS Ed from every panel capture
            dls_ed = capture.dls_irradiance()
            dls_ed[3], dls_ed[4] = dls_ed[4], dls_ed[3] #flip last two bands (red edge and NIR)
            dls_ed_row = ['capture_'+str(i+1)]+[np.mean(dls_ed[0]*1000)]+[np.mean(dls_ed[1]*1000)]+[np.mean(dls_ed[2]*1000)]+[np.mean(dls_ed[3]*1000)]+[np.mean(dls_ed[4]*1000)] #multiply by 1000 to scale to mW 
            dls_ed_data.append(dls_ed_row)         

        dls_ed_corr = np.array(panel_ed)/(np.array(dls_ed[0:5])*1000)        

        # this is the DLS ed corrected by the panel correction factor
        dls_ed_corr_data = []
        for i,capture in enumerate(capture_imgset):
            ed = capture.dls_irradiance()
            ed = (ed[0:5]*dls_ed_corr)*1000
            ed = np.append(ed, [0]) #add zero because other ed ends with a 0
            dls_ed_corr_row = ['capture_'+str(i+1)]+[ed[0]]+[ed[1]]+[ed[2]]+[ed[3]]+[ed[4]]
            dls_ed_corr_data.append(dls_ed_corr_row)

        dls_ed_corr_data_df = pd.DataFrame.from_records(dls_ed_corr_data, index='image', columns = ed_columns)
        dls_ed_corr_data_df.to_csv(output_csv_path+'/dls_corr_ed.csv')

    # now divide the lw_imagery by ed to get rrs
    # go through each Lt image in the dir and divide it by the lsky
    for idx, im in enumerate(glob.glob(lw_dir + "/*.tif")):
        with rasterio.open(im, 'r') as Lw_src:
            profile = Lw_src.profile
            profile['count']=5
            rrs_all = []
            # could vectorize this for speed
            for i in range(1,6):
                lw = Lw_src.read(i)
                if dls_corr:
                    rrs = lw/dls_ed_corr_data[idx][i]
                else:
                    rrs = lw/ed_data[idx][i]
                rrs_all.append(rrs) #append each band
            stacked_rrs = np.stack(rrs_all) #stack into np.array 

            #write new stacked Rrs tifs w/ Rrs units
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(rrs_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_rrs)
    return(True)

# glint removal
def rrs_threshold_pixel_masking(rrs_dir, masked_rrs_dir, nir_threshold = 0.01, green_threshold = 0.005):
    """
    This function masks pixels based on user supplied Rrs thresholds in an effort to remove instances of specular sun glint, shadowing, or adjacent land when present in the images. 
    
    Inputs: 
    rrs_dir: A string containing the directory filepath to write the new masked .tifs
    masked_rrs_dir: A string containing the name of the directory to store masked Rrs images. 
    nir_threshold: An Rrs(NIR) value where pixels above this will be masked. Default is 0.01. These are usually pixels of specular sun glint or land features.
    green_threshold: A Rrs(green) value where pixels below this will be masked. Default is 0.005. These are usually pixels of vegetation shadowing. 
    
    Output: New masked Rrs.tifs with units of sr^-1

    """    
    
    # go through each rrs image in the dir and mask pixels > nir_threshold and < green_threshold
    for im in glob.glob(rrs_dir + "/*.tif"):
        with rasterio.open(im, 'r') as rrs_src:
            profile = rrs_src.profile
            profile['count']=5
            rrs_mask_all = []
            nir = rrs_src.read(5)
            green = rrs_src.read(2)
            nir[nir > nir_threshold] = np.nan
            green[green < green_threshold] = np.nan

            nir_nan_index = np.isnan(nir)
            green_nan_index = np.isnan(green)

            #filter nan pixel indicies across all bands
            for i in range(1,6):

                rrs_mask = rrs_src.read(i)
                rrs_mask[nir_nan_index] = np.nan 
                rrs_mask[green_nan_index] = np.nan 

                rrs_mask_all.append(rrs_mask)

            stacked_rrs_mask = np.stack(rrs_mask_all) #stack into np.array

            #write new stacked rrs tifs
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(masked_rrs_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_rrs_mask)
                
    return(True)

def rrs_std_pixel_masking(rrs_dir, masked_rrs_dir, num_images=10, mask_std_factor=1):
    """
    This function masks pixels based on a user supplied value in an effort to remove instances of specular sun glint. The mean and standard deviation of NIR values from the first N images is calculated and any pixels containing an NIR value > mean + std*mask_std_factor is masked across all bands. The lower the mask_std_factor, the more pixels will be masked. 
    
    Inputs: 
    rrs_dir: A string containing the directory filepath of images to be processed
    masked_rrs_dir: A string containing the directory filepath to write the new masked .tifs
    num_images: Number of images in the dataset to calculate the mean and std of NIR. Default is 10. 
    mask_std_factor: A factor to multiply to the standard deviation of NIR values. Default is 1. 
    
    Output: New masked .tifs
    
    """
    # grab the first num_images images, finds the mean and std of NIR, then anything times the glint factor is classified as glint
    rrs_imgs, rrs_img_metadata = retrieve_imgs_and_metadata(rrs_dir, count=num_images, start=0, altitude_cutoff=0)
    rrs_nir_mean = np.nanmean(rrs_imgs,axis=(0,2,3))[4] # mean of NIR band
    rrs_nir_std = np.nanstd(rrs_imgs,axis=(0,2,3))[4] # std of NIR band
    print('The mean and std of Rrs from first N images is: ', rrs_nir_mean, rrs_nir_std)
    print('Pixels will be masked where Rrs(NIR) > ', rrs_nir_mean+rrs_nir_std*mask_std_factor)
    del rrs_imgs # free up the memory

    # go through each Rrs image in the dir and mask any pixels > mean+std*glint factor
    for im in glob.glob(rrs_dir + "/*.tif"):
        with rasterio.open(im, 'r') as rrs_src:
            profile = rrs_src.profile
            profile['count']=5
            rrs_deglint_all = []
            rrs_nir_deglint = rrs_src.read(5) #nir band
            rrs_nir_deglint[rrs_nir_deglint > (rrs_nir_mean+rrs_nir_std*mask_std_factor)] = np.nan
            nan_index = np.isnan(rrs_nir_deglint)
            #filter nan pixel indicies across all bands
            for i in range(1,6):
                rrs_deglint = rrs_src.read(i)
                rrs_deglint[nan_index] = np.nan 
                rrs_deglint_all.append(rrs_deglint) #append all for each band
            stacked_rrs_deglint = np.stack(rrs_deglint_all) #stack into np.array
            #write new stacked tifs
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(masked_rrs_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_rrs_deglint)
    return(True)

def process_raw_to_rrs(main_dir, rrs_dir_name, output_csv_path, lw_method='mobley_rho_method', random_n=10, mask_pixels=False, pixel_masking_method='value_threshold', mask_std_factor=1, nir_threshold=0.01, green_threshold=0.005, ed_method='dls_ed', overwrite=False, clean_intermediates=True):
    """
    This functions is the main processing script that processs raw imagery to units of remote sensing reflectance (Rrs). Users can select which processing parameters to use to calculate Rrs.
    
    Inputs: 
    main_dir: A string containing the main image directory
    rrs_dir_name: A string containing the directory filepath of new rrs images
    output_csv_path: A string containing the filepath to write the metadata.csv 
    lw_method: Method used to calculate water leaving radiance. Default is mobley_rho_method().
    random_n: The amount of random images to calculate ambient NIR level. Default is 10. Only need if lw_method = 'hedley_method'
    mask_pixels: Option to mask pixels containing specular sun glint, shadowing, adjacent vegetation, etc. Default is False. 
    pixel_masking_method: Method to mask pixels. Options are 'value_threshold' or 'std_threshold'. Default is value_threshold.
    mask_std_factor: A factor to multiply to the standard deviation of NIR values. Default is 1. Only need if pixel_masking_method = 'std_threshold'
    nir_threshold: An Rrs(NIR) value where pixels above this will be masked. Default is 0.01. These are usually pixels of specular sun glint or land features. Only need if pixel_masking_method = 'value_threshold'.
    green_threshold: A Rrs(green) value where pixels below this will be masked. Default is 0.005. These are usually pixels of vegetation shadowing.  Only need if pixel_masking_method = 'value_threshold'.
    ed_method: Method used to calculate downwelling irradiance (Ed). Default is dls_ed(). 
    overwrite: Option to overwrite files that have been written previously. Default is False but this is only applied to the Lt images.
    clean_intermediates: Option to erase intermediates of processing (Lt, Lw, unmasked Rrs) 
    
    Output: New Rrs tifs (masked or unmasked) with units of sr^-1. 
    """
    
    ############################
    #### setup the workspace ###
    ############################
    
    # specify the locations of the different levels of imagery
    # I do this partially so I can just change these pointers to the data and not have to copy it or have complex logic repeated
    
    ### os join here
    raw_water_img_dir = os.path.join(main_dir,'raw_water_imgs')
    raw_sky_img_dir = os.path.join(main_dir,'raw_sky_imgs')
    
    lt_dir = os.path.join(main_dir,'lt_imgs')
    sky_lt_dir = os.path.join(main_dir,'sky_lt_imgs')
    lw_dir = os.path.join(main_dir,'lw_imgs')
    panel_dir = os.path.join(main_dir, 'panel')
    rrs_dir = os.path.join(main_dir, rrs_dir_name)
    masked_rrs_dir = os.path.join(main_dir, 'masked_'+rrs_dir_name)
    
    
    # make all these directories if they don't already exist
    all_dirs = [lt_dir, lw_dir, rrs_dir]
    for directory in all_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
        
    if mask_pixels == True:
        Path(masked_rrs_dir).mkdir(parents=True, exist_ok=True)
    
    # this makes an assumption that there is only one panel image put in this directory
    panel_names = glob.glob(os.path.join(panel_dir, 'IMG_*.tif'))
   
    files = os.listdir(raw_water_img_dir) # your directory path
    print('Processing a total of ' + str(len(files)) + ' captures or ' + str(round(len(files)/5)) + ' image sets.')
    
    ### convert raw imagery to radiance (Lt)
    print("Converting raw images to radiance (raw -> Lt).")
    process_micasense_images(main_dir, warp_img_dir=os.path.join(main_dir,'align_img'), overwrite=overwrite, sky=False)
    
    # deciding if we need to process raw sky images to radiance 
    if lw_method in ['mobley_rho_method','blackpixel_method']:
        print("Converting raw sky images to radiance (raw sky -> Lsky).")
        # we're also making an assumption that we don't need to align/warp these images properly because they'll be medianed
        process_micasense_images(main_dir, warp_img_dir=None, overwrite=overwrite, sky=True)
    
    ##################################
    ### correct for surface reflected light ###
    ##################################
    
    if  lw_method == 'mobley_rho_method':
        print('Applying the mobley_rho_method (Lt -> Lw).')
        mobley_rho_method(sky_lt_dir, lt_dir, lw_dir)
        
    elif lw_method == 'blackpixel_method':
        print('Applying the blackpixel_method (Lt -> Lw)')
        blackpixel_method(sky_lt_dir, lt_dir, lw_dir)
        
    elif lw_method == 'hedley_method':
        print('Applying the Hochberg/Hedley (Lt -> Lw)')
        hedley_method(lt_dir, lw_dir, random_n)
     
    else: # just change this pointer if we didn't do anything the lt over to the lw dir
        print('Not doing any Lw calculation.')
        lw_dir = lt_dir 
        
    #####################################
    ### normalize Lw by Ed to get Rrs ###
    #####################################
    
    if ed_method == 'panel_ed':
        print('Normalizing by panel irradiance (Lw/Ed -> Rrs).')
        panel_ed(panel_dir, lw_dir, rrs_dir, output_csv_path)
        
    elif ed_method == 'dls_ed':
        print('Normalizing by DLS irradiance (Lw/Ed -> Rrs).')
        dls_ed(raw_water_img_dir, lw_dir, rrs_dir, output_csv_path)

    elif ed_method == 'dls_and_panel_ed':
        print('Normalizing by DLS corrected by panel irradiance (Lw/Ed -> Rrs).')
        dls_ed(raw_water_img_dir, lw_dir, rrs_dir, output_csv_path, panel_dir=panel_dir, dls_corr = True)

    else:
        print('No other irradiance normalization methods implemented yet, panel_ed is recommended.')
        return(False)
    
    print('All data has been saved as Rrs using the ' + str(lw_method)  + ' to calcualte Lw and normalized by '+ str(ed_method)+ ' irradiance.')
    
    ########################################
    ### mask pixels in the imagery (from glint, vegetation, shadows) ###
    ########################################
    if mask_pixels == True and pixel_masking_method == 'value_threshold':
        print('Masking pixels using NIR and green Rrs thresholds')
        rrs_threshold_pixel_masking(rrs_dir, masked_rrs_dir, nir_threshold=nir_threshold, green_threshold=green_threshold)
    elif mask_pixels == True and pixel_masking_method == 'std_threshold': 
        print('Masking pixels using std Rrs(NIR)')
        rrs_std_pixel_masking(rrs_dir, masked_rrs_dir, mask_std_factor)
                    
    else: # if we don't do the glint correction then just change the pointer to the lt_dir
        print('Not masking pixels.')
    
    ################################################
    ### finalize and add point output ###
    ################################################
    
    if clean_intermediates:
        dirs_to_delete = [lt_dir, sky_lt_dir, glint_corrected_lt_dir, lw_dir]
        for d in dirs_to_delete:
            shutil.rmtree(d,ignore_errors=True)
                
    return(True)

                  
############ water quality retrieval algorithms ############

def chl_hu(Rrsblue, Rrsgreen, Rrsred):
    """
    This is the Ocean Color Index (CI) three-band reflectance difference algorithm (Hu et al. 2012). This should only be used for chlorophyll retrievals below 0.15 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. doi: 10.1029/2011jc007395
    
    Inputs:
    Rrs_x: numpy array of Rrs in each band. 
    
    Output: numpy array of derived chlorophyll
    
    """
    
    ci1 = -0.4909
    ci2 = 191.6590

    CI = Rrsgreen - ( Rrsblue + (560 - 475)/(668 - 475) * (Rrsred - Rrsblue) )
    ChlCI = 10**(ci1 + ci2*CI)
    return(ChlCI)


def chl_ocx(Rrsblue, Rrsgreen):
    """
    This is the OCx algorithm which uses a fourth-order polynomial relationship (O'Reilly et al. 1998). This should be used for chlorophyll retrievals above 0.2 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. The coefficients for OC2 (OLI/Landsat 8) are used as default. doi: 10.1029/98JC02160.
    
    Inputs:
    Rrs_x: numpy array of Rrs in each band. 
    
    Output: numpy array of derived chlorophyll
    
    """
    
    # L8 OC2 coefficients
    a0 = 0.1977
    a1 = -1.8117
    a2 = 1.9743
    a3 = 2.5635
    a4 = -0.7218

    log10chl = a0 + a1 * (np.log10(Rrsblue / Rrsgreen)) \
        + a2 * (np.log10(Rrsblue / Rrsgreen))**2 \
            + a3 * (np.log10(Rrsblue / Rrsgreen))**3 \
                + a4 * (np.log10(Rrsblue / Rrsgreen))**4

    ocx = np.power(10, log10chl)
    return(ocx)

def chl_hu_ocx(Rrsblue, Rrsgreen, Rrsred):
    ''' 
    This is the blended NASA chlorophyll algorithm which combines Hu color index (CI) algorithm (chl_hu) and the O'Reilly band ratio OCx algortihm (chl_ocx). This specific code is grabbed from https://github.com/nasa/HyperInSPACE. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/.
    
    Inputs:
    Rrs_x: numpy array of Rrs in each band. 
    
    Output: numpy array of derived chlorophyll
    '''

    thresh = [0.15, 0.20]
    a0 = 0.1977
    a1 = -1.8117
    a2 = 1.9743
    a3 = 2.5635
    a4 = -0.7218

    ci1 = -0.4909
    ci2 = 191.6590

    log10chl = a0 + a1 * (np.log10(Rrsblue / Rrsgreen)) \
        + a2 * (np.log10(Rrsblue / Rrsgreen))**2 \
            + a3 * (np.log10(Rrsblue / Rrsgreen))**3 \
                + a4 * (np.log10(Rrsblue / Rrsgreen))**4

    ocx = np.power(10, log10chl)

    CI = Rrsgreen - ( Rrsblue + (560 - 475)/(668 - 475) * \
        (Rrsred -Rrsblue) )
        
    ChlCI = 10** (ci1 + ci2*CI)

    if ChlCI.any() <= thresh[0]:
        chlor_a = ChlCI
    elif ChlCI.any() > thresh[1]:
        chlor_a = ocx
    else:
        chlor_a = ocx * (ChlCI-thresh[0]) / (thresh[1]-thresh[0]) +\
            ChlCI * (thresh[1]-ChlCI) / (thresh[1]-thresh[0])

    return chlor_a

def chl_gitelson(Rrsred, Rrsrededge):
    """
    This algorithm estimates chlorophyll a concentrations using a 2-band algorithm with coefficients from Gitelson et al. 2007. This algorithm is recommended for coastal (Case 2) waters. doi:10.1016/j.rse.2007.01.016
    
    Inputs:
    Rrs_x: numpy array of Rrs in each band. 
    
    Output: numpy array of derived chlorophyll
    """
    
    chl = 59.826 * (Rrsrededge/Rrsred) - 17.546
    return chl

######## TSM retrieval algs ######

def nechad_tsm(Rrsred):
    """
    This algorithm estimates total suspended matter (TSM) concentrations using the Nechad et al. (2010) algorithm. doi:10.1016/j.rse.2009.11.022
    
    Inputs:
    Rrs_x: numpy array of Rrs(red)
    
    Output: numpy array of derived chlorophyll
    """
    A = 374.11
    B = 1.61
    C = 17.38
    
    tsm = (A*Rrsred/(1-(Rrsred/C))) + B
    return(tsm)


def save_wq_imgs(main_dir, rrs_img_dir, wq_dir_name, imgs, img_metadata, wq_alg="chl_gitelson", start=0, count=10000):
    """
    This function saves new .tifs with units of chl (ug/L) or TSM (mg/m3).
    Inputs:
    main_dir: A string containing main directory
    rrs_img_dir: A string containing directory of Rrs images
    wq_dir_name: A string containing the directory that the wq images will be saved
    wq_alg: what wq algorithm to apply
    imgs: images to apply - typically from retrieve_imgs_and_metadata() function
    img_metadata: all image metadata - typically from retrieve_imgs_and_metadata() function
    start: The image to start loading from. Default is 0.
    count: The amount of images to load. Default is 10000

    Outputs: New georeferenced .tifs with same units of images in img_dir
    """
    # make wq_dir directory 
    wq_dir = wq_dir_name
    if not os.path.exists(wq_dir):
        os.makedirs(wq_dir)

    for im in glob.glob(rrs_img_dir + "/*.tif")[start:count]:
        with rasterio.open(im, 'r') as Rrs_src:
            profile = Rrs_src.profile
            profile['count']=5
            Rrsblue=Rrs_src.read(1)
            Rrsgreen=Rrs_src.read(2)
            Rrsred=Rrs_src.read(3)
            Rrsrededge=Rrs_src.read(4)
            Rrsnir=Rrs_src.read(5)

        if wq_alg == 'chl_hu':
            wq = chl_hu(Rrsblue, Rrsgreen, Rrsred)

        elif wq_alg == 'chl_ocx':
            wq = chl_ocx(Rrsblue, Rrsgreen)

        elif wq_alg == 'chl_hu_ocx':
            wq = chl_hu_ocx(Rrsblue, Rrsgreen, Rrsred)

        elif wq_alg == 'chl_gitelson':
            wq = chl_gitelson(Rrsred, Rrsrededge)

        elif wq_alg == 'nechad_tsm':
            wq = nechad_tsm(Rrsred)

    for i in range(len(img_metadata)):
        with rasterio.open(os.path.join(rrs_img_dir, img_metadata.index[i]), 'r') as src:
            src_crs = "EPSG:4326"  # This is the crs of the GCPs
            dst_crs = "EPSG:4326"
            profile.update(dtype=rasterio.float32,crs=dst_crs,count=1)

            #write new stacked tifs w
            with rasterio.open(os.path.join(wq_dir, img_metadata.index[i]), 'w', **profile) as dst:
                dst.write(wq, 1)
    
#################### Georeferencing #########################

def spacetotopdown(top_im, cam, image_size, scaling):
    """
    This function defines the coordinates of the four corners in image coordinates space
    
    Inputs:
    top_im: projected image derived from the getTopViewOfImage() function in CameraTransform
    cam: camera object from ct.Camera() transform
    image_size: image width and height from metadata
    scaling: pixel size on the ground in meters
    
    Output: numpy array of projected top down image coordinates
    """
    x1 = top_im.shape[0]/2 + cam.spaceFromImage([0,0])[0] / scaling
    y1 = top_im.shape[1]/2 - cam.spaceFromImage([0,0])[1] / scaling
    
    x2 = top_im.shape[0]/2 + cam.spaceFromImage([image_size[0]-1,0])[0] / scaling
    y2 = top_im.shape[1]/2 - cam.spaceFromImage([image_size[0]-1,0])[1] / scaling
    
    x3 = top_im.shape[0]/2 + cam.spaceFromImage([image_size[0]-1,image_size[1]-1])[0] / scaling
    y3 = top_im.shape[1]/2 - cam.spaceFromImage([image_size[0]-1,image_size[1]-1])[1] / scaling
    
    x4 = top_im.shape[0]/2 + cam.spaceFromImage([0,image_size[1]-1])[0] / scaling
    y4 = top_im.shape[1]/2 - cam.spaceFromImage([0,image_size[1]-1])[1] / scaling
    
    return(np.array([[x1,y1], [x2,y2], [x3,y3], [x4,y4]]))


def georeference(main_dir, img_dir, output_dir_name, imgs, img_metadata, 
                 scaling=0.2, extent=80, flip=False, plot=False, yaw_name='GPSImgDirection', 
                 pitch_name='GPSPitch', roll_name='GPSRoll', pitch_offset=0):
    """
    This function applies georeferencing based on MicaSense image metadata (altitude, pitch, roll, yaw, lat, lon). 
    
    Inputs:
    main_dir: A string containing main directory
    img_dir: A string containing directory of images to georeference
    imgs: images to georeference - typically from retrieve_imgs_and_metadata() function
    img_metadata: all image metadata - typically from retrieve_imgs_and_metadata() function
    output_dir_name: A string containing directory of georeferenced images 
    start: The number of image to start on. Default is 0 (first image in img_dir). 
    count: The amount of images you want to process. Default is 10000.
    scaling: pixel size on the ground in meters. Default is 0.2
    extent: The offset of image in four directions from center lat,lon of drone. The default of 80 is approximate and based on altitude, FOV, and viewing geometry. For example, with a higher altitude or pitch angle, the value should be larger because the footprint on the ground will be larger. 
    flip: Option to flip camera orientation if camera is integrated 180 deg away from DLS. Default is False.
    plot: Option to plot georeferenced images. Default is False.
    yaw: movement along the left-right axis. Default is 'GPSImgDirection'
    pitch: movement along up-down axis. Default is 'GPSPitch'
    roll: movement around front-back axis. Default is 'GPSRoll'
    
    Output: New georeferenced .tifs with same units of images in img_dir
    """
    
    # make georeference directory 
    georeference_dir = output_dir_name
    if not os.path.exists(georeference_dir):
        os.makedirs(georeference_dir)
    
    for i in range(len(img_metadata)):
        f = img_metadata.iloc[i]['FocalLength']
        image_size = [img_metadata.iloc[i]['ImageWidth'], img_metadata.iloc[i]['ImageHeight']]
        sensor_size = (4.8,3.6) #got from MicaSense specs
        pitch = img_metadata.iloc[i][pitch_name]+pitch_offset
        roll = img_metadata.iloc[i][roll_name]
        yaw = img_metadata.iloc[i][yaw_name]
        alt = img_metadata.iloc[i]['GPSAltitude']
        lat = img_metadata.iloc[i]['GPSLatitude']
        lon = img_metadata.iloc[i]['GPSLongitude']

        cam = ct.Camera(ct.RectilinearProjection(focallength_mm=f,
                                             sensor=sensor_size,
                                             image_width_px=imgs[i,0,:,:].shape[1], # columns aka width
                                             image_height_px=imgs[i,0,:,:].shape[0], # rows aka height
                                            view_x_deg = 47.2, #This is the horizontal and vertical FOV from MicaSense specs
                                            view_y_deg=35.4),
                   ct.SpatialOrientation(elevation_m=alt,
                                         tilt_deg=pitch,
                                         roll_deg=roll,
                                        heading_deg=yaw,
                                        pos_x_m=0, pos_y_m=0))
        # gps pts are lat lon
        cam.setGPSpos(lat, lon, alt)

        #Option to flip if camera is integrated 180 from each other
        if flip == True:
            input_img = np.fliplr(np.flipud(imgs[i,:,:,:]))
        else:
            input_img = imgs[i,:,:,:]

        top_im_append = []
        for j in range(0,5):
            top_im = cam.getTopViewOfImage(input_img[j,:,:], extent=[-extent,extent,-extent,extent], scaling=scaling)
            top_im_append.append(top_im)
        top_im_5 = np.array(top_im_append)

        if plot==True:
            plt.imshow(top_im_5[0,:,:], interpolation='nearest')
            plt.show()
            
        # Now get the image coordinates of the corners of the original image but in the top down image
        # this scaling factor is the size of the pixels in the final image so we can tune it depending on needs.
        # when set to 0.2, the image size to -80 to 80 meters (160m), so the image size is 160/.2 = 800 pixels
        image_coords = spacetotopdown(top_im, cam, image_size, scaling=scaling)

        # these are the coordinates of the image corners   
        coords = np.array([
            cam.gpsFromImage([0               , 0]), \
            cam.gpsFromImage([image_size[0]-1 , 0]), \
            cam.gpsFromImage([image_size[0]-1 , image_size[1]-1]), \
            cam.gpsFromImage([0               , image_size[1]-1])])

        gcp1 = rasterio.control.GroundControlPoint(row=image_coords[0,1], col=image_coords[0,0], x=coords[0,1], y=coords[0,0], 
                                                   z=coords[0,2], id=None, info=None)
        gcp2 = rasterio.control.GroundControlPoint(row=image_coords[1,1], col=image_coords[1,0], x=coords[1,1], y=coords[1,0], 
                                                   z=coords[1,2], id=None, info=None)
        gcp3 = rasterio.control.GroundControlPoint(row=image_coords[2,1], col=image_coords[2,0], x=coords[2,1], y=coords[2,0], 
                                                   z=coords[2,2], id=None, info=None)
        gcp4 = rasterio.control.GroundControlPoint(row=image_coords[3,1], col=image_coords[3,0], x=coords[3,1], y=coords[3,0], 
                                                   z=coords[3,2], id=None, info=None)

        with rasterio.Env():
            # open the original image to get some of the basic metadata
            with rasterio.open(os.path.join(img_dir, img_metadata.index[i]), 'r') as src:
                profile = src.profile
                src_crs = "EPSG:4326"  # This is the crs of the GCPs
                dst_crs = "EPSG:4326"
                tsfm = rasterio.transform.from_gcps([gcp1,gcp2,gcp3,gcp4])
                profile.update(
                    dtype=rasterio.float32,
                    transform = tsfm,
                    crs=dst_crs,
                    width=top_im.shape[1], # TODO unsure if this is correct order but they're the same value so okay for now
                    height=top_im.shape[0])
                with rasterio.open(os.path.join(georeference_dir, img_metadata.index[i]), 'w', **profile) as dst:
                    dst.write(top_im_5.astype(rasterio.float32))
    return(True)

def mosaic(main_dir, img_dir, output_name, save=True, plot=True, start=0, count=10000, band_to_plot=0):
    """
    This function mosaics georeferenced .tifs to create one large .tif
    
    Inputs: 
    main_dir: String containing main directory
    img_dir: String containing image directory of .tifs to mosaic. 
    output_name: String containing name of mosaicked .tif
    start: The number of image to start on. Default is 0 (first image in img_dir).
    count: The amount of images you want to list. Default is 10000
    save: Option to save mosaicked .tif in main_dir. Default is True.
    plot: Option to plot mosaicked tif. Default is True. 
    band_to_plot: What band to plot. Default is 0 (blue). 
    
    Output: numpy array of mosaicked georeferenced images 
    """
        
    mosaic_tifs = []
    for i in glob.glob(img_dir + "/*.tif")[start:count]:
        src = rasterio.open(i)
        mosaic_tifs.append(src)

    mosaic, out_trans = merge(mosaic_tifs)

    if plot==True:
        fig,ax = plt.subplots(figsize=(10,10))
        foo = mosaic[band_to_plot,:,:]
        #foo[foo == 0] = 'nan'
        plt.imshow(foo)
    
    if save==True:
        output_meta = src.meta.copy()
        output_meta.update(
            {"driver": "GTiff",
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": out_trans})

        with rasterio.open(os.path.join(main_dir, output_name + '.tif'), "w", **output_meta) as m:
            m.write(mosaic)
    
    return(mosaic)
