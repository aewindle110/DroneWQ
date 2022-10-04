import multiprocessing, glob, shutil, os, datetime, subprocess, math

import geopandas as gpd
import pandas as pd

import numpy as np
import matplotlib.pyplot as plt

import cv2
import exiftool
import rasterio
from GPSPhoto import gpsphoto
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

############ general functions for processing micasense imagery ############

def write_exif_csv(img_set, outputPath):
    """
    This function writes specific EXIF metadata from img_set to outputPath/metadata.csv. Other metadata could be added based on what is needed in your workflow.
    
    Inputs: img_set: An ImageSet is a container for a group of Captures that are processed together. It is defined by running the ImageSet.from_directory() function found in Micasense's imageset.py 
    
    Output: outputPath: A string containing the filepath to store the metadata.csv containing EXIF metadata 
    
    """

    header = "SourceFile,\
    GPSDateStamp,\
    GPSTimeStamp,\
    GPSLatitude,\
    GPSLatitudeRef,\
    GPSLongitude,\
    GPSLongitudeRef,\
    GPSAltitude,\
    FocalLength,\
    ImageWidth,ImageHeight,\
    GPSImgDirection,GPSPitch,GPSRoll\n"
    
    lines = [header]
    for i,capture in enumerate(img_set.captures):
        #get lat,lon,alt,time
        outputFilename = 'capture_' + str(i+1)+'.tif'
        fullOutputPath = os.path.join(outputPath, outputFilename)
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

    fullCsvPath = os.path.join(outputPath,'metadata.csv')
    with open(fullCsvPath, 'w') as csvfile: #create CSV
        csvfile.writelines(lines)
        
    return(fullCsvPath)

def get_warp_matrix(img_capture, max_alignment_iterations = 50):
    """
    This function uses the MicaSense imageutils.align_capture() function to determine an alignment (warp) matrix of a single capture that can be applied to all images. From MicaSense: "For best alignment results it's recommended to select a capture which has features which visible in all bands. Man-made objects such as cars, roads, and buildings tend to work very well, while captures of only repeating crop rows tend to work poorly. Remember, once a good transformation has been found for flight, it can be generally be applied across all of the images." Ref: https://github.com/micasense/imageprocessing/blob/master/Alignment.ipynb
    
    *********AW_question: is an image of homogenous water okay to use as a warp matrix then? 
    
    Inputs: 
    img_capture: A capture is a set of images taken by one MicaSense camera which share the same unique capture identifier (capture_id). These images share the same filename prefix, such as IMG_0000_*.tif. It is defined by running ImageSet.from_directory().captures. 
    
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

    print("Finished Aligning, warp matrices={}".format(warp_matrices))
    return(warp_matrices)

def save_images(img_set, outputPath, thumbnailPath, warp_img_capture, generateThumbnails = True, overwrite=False):
    """
    This function processes each capture in an imageset to compute radiace, apply a warp matrix, and save new .tifs with units of radiance (W/sr/nm) and optional RGB .jpgs.
    
    Inputs: 
    
    img_set: An ImageSet is a container for a group of Captures that are processed together. It is defined by running the ImageSet.from_directory() function found in Micasense's imageset.py 
    outputPath: A string containing the filepath to store a new folder of radiance .tifs
    thumbnailPath: A string containing the filepath to store a new folder of RGB thumnail .jpgs
    warp_img_capture: A Capture chosen to align all images. Can be created by using Micasense's ImageSet-from_directory().captures function
    generateThumbnails: Option to create RGB .jpgs of all the images. Default is True
    overwrite: Option to overwrite files that have been written previously. Default is False
    
    Output: New .tif files for each capture with units of radiance (W/sr/nm) and optional new .jpg files for each capture containing an RGB thumbail
    """

    warp_matrices = get_warp_matrix(warp_img_capture)

    if not os.path.exists(outputPath):
        os.makedirs(outputPath)
    if generateThumbnails and not os.path.exists(thumbnailPath):
        os.makedirs(thumbnailPath)

    start = datetime.datetime.now()
    for i,capture in enumerate(img_set.captures):
        outputFilename = 'capture_' + str(i+1) + '.tif'
        thumbnailFilename = 'capture_' + str(i+1) + '.jpg'
        fullOutputPath = os.path.join(outputPath, outputFilename)
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

def process_micasense_subset(project_dir, warp_img_dir=None, overwrite=False, sky=False):
    """
    This function is wrapper function for the save_images() function to read in an image directory and produce new .tifs with units of radiance (W/sr/nm).  
    
    Inputs: 
    
    project_dir: a string containing the filepath of the raw .tifs
    warp_img_dir: a string containing the filepath of the capture to use to create the warp matrix
    overwrite: Option to overwrite files that have been written previously. Default is False
    sky: Option to select to run raw water captures or raw sky captures. If True, the save_images() is run on raw .tif files and saves new .tifs in sky_lt directories. If False, save_images() is run on raw .tif files and saves new .tifs in lt directories. 
        
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
        thumbnailPath = os.path.join(project_dir, 'sky_lt_thumbnails')
    else:
        outputPath = os.path.join(project_dir,'lt_imgs')
        thumbnailPath = os.path.join(project_dir, 'lt_thumbnails')
    
    if save_images(imgset, outputPath, thumbnailPath, warp_img_capture, overwrite=overwrite) == True:
        print("Finished saving images.")
        fullCsvPath = write_exif_csv(imgset, outputPath)
        print("Finished saving image metadata.")
            
    return(outputPath)


############ general functions for ingesting processed imagery and metadata ############

def key_function(item_dictionary):
    """
    Extract datetime string from given dictionary, and return the parsed datetime object
    
    *****AW_question: do we need this function?? 
    """
    
    datetime_string = item_dictionary['UTC-Time']
    return datetime.datetime.strptime(datetime_string, '%H:%M:%S')

def load_img_fn_and_meta(img_dir, count=10000, start=0):
    """
    This function returns a pandas dataframe of captures and associated metadata with the options of how many to list and what nunmber of image to start on.  

*****AW_queston: What is the benefit of this function since we have the write_exif_csv() function that saves all metadata as a .csv? 

    """
    
    df = pd.read_csv(img_dir + '/metadata.csv')
    df['filename'] = df['SourceFile'].str.split('/').str[-1]
    df = df.set_index('filename')
    df['UTC-Time'] = pd.to_datetime(df['    GPSTimeStamp'])    
    # cut off if necessary
    df = df.iloc[start:start+count]
    return(df)

def load_images(img_list):
    """
    This function loads all images in a directory as a multidimensional numpy array. 
    
    Inputs: img_list: A list of .tif files, usually called by using glob.glob(filepath)
    Outputs: A multidimensional numpy array of all image captures in a directory 
    
    """
    all_imgs = []
    for im in img_list:
        with rasterio.open(im, 'r') as src:
            all_imgs.append(src.read())
    return(np.array(all_imgs))

def retrieve_imgs_and_metadata(img_dir, count=10000, start=0, altitude_cutoff = 0):
    """
    *****AW_question: this function is just a combiation of load_img_fn_and_meta() and load_images(), right? I feel like all these functions along with write_exif_csv() are redudant- we should talk about the benefits of having them all. 
    
    This function is the main interface we expect the user to use when grabbing a subset of imagery from any stage in processing. This returns the images as a numpy array and metadata as a pandas dataframe. 
    """
    
    # this returns a pandas dataframe with the metadata of this image directory
    img_metadata = load_img_fn_and_meta(img_dir, count=count, start=start)

    img_metadata_subset = img_metadata[img_metadata['    GPSAltitude'] > altitude_cutoff]
    
    imgs = load_images(img_metadata_subset['SourceFile'].values)
        
    ids = np.arange(1,len(img_metadata_subset)+1)
    img_metadata_subset['id'] = ids    
    img_metadata_subset.set_index('id')

    return(imgs, img_metadata_subset)

######## workflow functions for cleanly running all of this ########

def std_glint_removal_method(lt_dir, glint_corrected_lt_dir, glint_std_factor=1):
    """
    This function masks pixels based on a user supplied NIR threshold in an effort to remove instances of specular sun glint. The mean and standard deviation of NIR values from the first 30 images is calculated and any pixels containing an NIR value > mean + std*glint_std_factor is masked across all bands. The lower the glint_std_factor, the more pixels will be masked. 
    
    Inputs: 
    lt_dir: A string containing the directory filepath of images to be processed
    glint_corrected_lt_dir: A string containing the directory filepath to write the new masked .tifs
    glint_std_factor: A factor to multiply to the standard deviation of NIR values
    
    Output: New masked .tifs
    
    """
    # grab the first 30 images, find the mean and std of NIR, then anything times the glint factor is classified as glint
    lt_imgs, lt_img_metadata = retrieve_imgs_and_metadata(lt_dir, count=30, start=0, altitude_cutoff=0)
    lt_nir_mean = np.mean(lt_imgs,axis=(0,2,3))[4] # mean of NIR band
    lt_nir_std = np.std(lt_imgs,axis=(0,2,3))[4] # std of NIR band
    print('The mean and std of Lt from first 30 images is: ', lt_nir_mean, lt_nir_std)
    print('Pixels will be masked where Lt(NIR) > ', lt_nir_mean+lt_nir_std*glint_std_factor)
    del lt_imgs # free up the memory

    # go through each Lt image in the dir and mask any pixels > mean+std*glint factor
    for im in glob.glob(lt_dir + "/*.tif"):
        with rasterio.open(im, 'r') as Lt_src:
            profile = Lt_src.profile
            lt_deglint_all = []
            lt_nir_deglint = Lt_src.read(5) #nir band
            lt_nir_deglint[lt_nir_deglint > (lt_nir_mean+lt_nir_std*glint_std_factor)] = np.nan
            nan_index = np.isnan(lt_nir_deglint)
            #filter nan pixel indicies across all bands
            for i in range(1,6):
                
                lt_deglint = Lt_src.read(i)
                lt_deglint[nan_index] = np.nan 
                lt_deglint_all.append(lt_deglint) #append all for each band
                
            stacked_lt_deglint = np.stack(lt_deglint_all) #stack into np.array

            #write new stacked lw tifs
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(glint_corrected_lt_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_lt_deglint)
    return(True)

def mobley_rho_method(sky_lt_dir, lt_dir, lw_dir, rho = 0.028): 
    """
    This function calculates water leaving radiance (Lw) by multiplying a single (or small set of) sky radiance (Lsky) images by a single rho value. The default is rho = 0.028, which is based off recommendations described in Mobley, 1999. This approach should only be used if sky conditions are not changing substantially during the flight. 
    
    Inputs: 
    sky_lt_dir: A string containing the directory filepath of sky_lt images
    lt_dir: A string containing the directory filepath of lt images 
    lw_dir: A string containing the directory filepath of new lw images
    rho = The effective sea-surface reflectance of a wave facet. The default 0.028
    
    Outputs: New .tifs with units of Lw
    """

    # grab the first ten of these images, average them, then delete this from memory
    sky_imgs, sky_img_metadata = retrieve_imgs_and_metadata(sky_lt_dir, count=10, start=0, altitude_cutoff=0)
    lsky_median = np.median(sky_imgs,axis=(0,2,3)) # here we want the median of each band
    del sky_imgs # free up the memory

    # go through each Lt image in the dir and subtract out rho*lsky to account for sky reflection
    for im in glob.glob(lt_dir + "/*.tif"):
        with rasterio.open(im, 'r') as Lt_src:
            profile = Lt_src.profile
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
    
    Outputs: New .tifs with units of Lw
        
    """
    # grab the first ten of these images, average them, then delete this from memory
    sky_imgs, sky_img_metadata = retrieve_imgs_and_metadata(sky_lt_dir, count=10, start=0, altitude_cutoff=0)
    lsky_median = np.median(sky_imgs,axis=(0,2,3)) # here we want the median of each band
    del sky_imgs

    for im in glob.glob(lt_dir + "/*.tif"):
        with rasterio.open(im, 'r') as Lt_src:
            profile = Lt_src.profile
           
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


def hedley_method(lt_dir, lw_dir):
    """
   This function calculates water leaving radiance (Lw) by modelling a constant 'ambient' NIR brightness level which is removed from all pixels across all bands. An ambient NIR level is calculated by averaging the minimum 10% of Lt(NIR) across all images. This value represents the NIR brightness of a pixel with no sun glint. A linear relationship between Lt(NIR) amd the visible bands (Lt) is established, and for each pixel, the slope of this line is multiplied by the difference between the pixel NIR value and the ambient NIR level. 
   
   Inputs: 
   lt_dir: A string containing the directory filepath of lt images 
   lw_dir: A string containing the directory filepath of new lw images
   
   Outputs: New .tifs with units of Lw
   
   """
    lt_all = []
    for im in glob.glob(lt_dir + "/*.tif"):
        with rasterio.open(im, 'r') as lt_src:
            profile = lt_src.profile
            lt = lt_src.read()
            lt_all.append(lt)

    stacked_lt = np.stack(lt_all)
    stacked_lt_reshape = stacked_lt.reshape(*stacked_lt.shape[:-2], -1) #flatten last two dims

    #apply linear regression between NIR and visible bands 
    for i in range(len(glob.glob(lt_dir + "/*.tif"))):
        im = glob.glob(lt_dir + "/*.tif")[i]
        im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
        min_lt_NIR = np.percentile(stacked_lt_reshape[i,4,:], .1) #calculate minimum 10% of Ruas(NIR)

        all_slopes = []
        lw_all = []
        for j in range(0,5):
            slopes = np.polyfit(stacked_lt_reshape[i,4,:], stacked_lt_reshape[i,j,:], 1)[0]
            all_slopes.append(slopes)

        for j in range(0,5):   
            #calculate Lw (Lt - b(Lt(NIR)-min(Lt(NIR))))
            lw = stacked_lt[i,j,:,:] - all_slopes[j]*(stacked_lt[i,4,:,:]-min_lt_NIR)
            lw_all.append(lw)

        stacked_lw = np.stack(lw_all) #stack into np.array

        #write new stacked Rrs tif w/ reflectance units
        with rasterio.open(os.path.join(lw_dir, im_name), 'w', **profile) as dst:
            dst.write(stacked_lw)
    return(True)

def panel_ed(panel_dir, lw_dir, rrs_dir, output_csv_path):
    """
    This function calculates remote sensing reflectance (Rrs) by dividing downwelling irradiance (Ed) from the water leaving radiance (Lw) .tifs. Ed is calculated from the calibrated reflectance panel. This method should only be used during clear, sunny days with no variable cloud conditions. 
    
    Inputs:
    panel_dir: A string containing the directory filepath of the panel image captures
    lw_dir: A string containing the directory filepath of lw images
    rrs_dir: A string containing the directory filepath of new rrs images
    output_csv_path: A string containing the filepath to save Ed measurements (mW/m2/nm) calculated from the panel
    
    Outputs:
    New .tifs with units of Rrs
    New .csv file with average Ed measurements (mW/m2/nm) calcualted from image cpatures of the calibrated reflectance panel
    
    """
    panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures
    panels = np.array(panel_imgset)  
    
    ed_data = []
    ed_columns = ['image', 'ed_475', 'ed_560', 'ed_668', 'ed_717', 'ed_842']
    
    for i in range(len(panels)):         
        #calculate panel Ed from every panel capture
        ed = np.array(panels[i].panel_irradiance()) # this function automatically finds the panel albedo and uses that to calcuate Ed, otherwise rases an error
        ed[3], ed[4] = ed[4], ed[3] #flip last two bands
        ed_row = ['capture_'+str(i+1)]+[np.mean(ed[0]*1000)]+[np.mean(ed[1]*1000)]+[np.mean(ed[2]*1000)]+[np.mean(ed[3]*1000)]+[np.mean(ed[4]*1000)] #multiply by 1000 to scale to mW (but want ed to still be in W to divide by Lw which is in W)
        ed_data.append(ed_row)
        
    ed_data = pd.DataFrame.from_records(ed_data, index='image', columns = ed_columns)
    ed_data.to_csv(output_csv_path+'/panel_ed.csv')

    # now divide the lw_imagery by Ed to get rrs
    # go through each Lt image in the dir and divide it by the lsky
    for im in glob.glob(lw_dir + "/*.tif"):
        with rasterio.open(im, 'r') as Lw_src:
            profile = Lw_src.profile
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

def dls_ed(raw_water_dir, lw_dir, rrs_dir, output_csv_path):
    """
    This function calculates remote sensing reflectance (Rrs) by dividing downwelling irradiance (Ed) from the water leaving radiance (Lw) .tifs. Ed is derived from the downwelling light sensor (DLS). This method does not perform well when light is constant due to movement of the drone which creates biased data. This method should be used during variable cloud conditions. 
    
    Inputs:
    raw_water_dir: A string containing the directory filepath of the raw water images
    lw_dir: A string containing the directory filepath of lw images
    rrs_dir: A string containing the directory filepath of new rrs images
    output_csv_path: A string containing the filepath to save Ed measurements (mW/m2/nm) derived from the DLS
    
    Outputs:
    New .tifs with units of Rrs
    New .csv file with average Ed measurements (mW/m2/nm) calcualted from DLS measurements
    """
    capture_imgset = imageset.ImageSet.from_directory(raw_water_dir).captures
    ed_data = []
    ed_columns = ['image', 'ed_475', 'ed_560', 'ed_668', 'ed_717', 'ed_842']
    
    for i,capture in enumerate(capture_imgset):
        ed = capture.dls_irradiance()
        ed[3], ed[4] = ed[4], ed[3] #flip last two bands (red edge and NIR)
        ed_row = ['capture_'+str(i+1)]+[np.mean(ed[0]*1000)]+[np.mean(ed[1]*1000)]+[np.mean(ed[2]*1000)]+[np.mean(ed[3]*1000)]+[np.mean(ed[4]*1000)] #multiply by 1000 to scale to mW 
        ed_data.append(ed_row)
        
    ed_data = pd.DataFrame.from_records(ed_data, index='image', columns = ed_columns)
    ed_data.to_csv(output_csv_path+'/dls_ed.csv')
    
    # now divide the lw_imagery by ed to get rrs
    # go through each Lt image in the dir and divide it by the lsky
    for im in glob.glob(lw_dir + "/*.tif"):
        with rasterio.open(im, 'r') as Lw_src:
            profile = Lw_src.profile
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

#def combine_panel_dls()

"""
**********AW_question: would like to create a function that combines both the DLS and panel data since MicaSense recommends it: https://support.micasense.com/hc/en-us/articles/360025336894-Using-Panels-and-or-DLS-in-Post-Processing

Could not figure out how they did it here: https://github.com/micasense/imageprocessing/blob/master/MicaSense%20Image%20Processing%20Tutorial%203.ipynb

"""

def rewrite_exif_data(lt_dir, output_dir):
    """
    This function saves new metadata in the folder of processed imagery. 
    
    *********AW_question: do we need this function anymore?? 
    """
    # first copy the log from lt_imgs where is it output by the micasense processing code to the dir of choice and change the file path within the csv line
    with open(lt_dir+"/metadata.csv", "rt") as fin:
        with open(output_dir+"/metadata.csv", "wt") as fout:
            for line in fin:
                # here we just grab the final sub-directory name and replace it, so this could look like fout.write(line.replace('lt_imgs', 'rrs_imgs'))
                fout.write(line.replace(lt_dir.split('/')[-1], output_dir.split('/')[-1]))

def process_raw_to_rrs(main_dir, output_csv_path, glint_correct=True, glint_std_factor=1, lw_method='mobley_rho_method', ed_method='dls_ed'):
    """
    This functions is the main processing script that processs raw imagery to units of remote sensing reflectance (Rrs). Users can select which processing parameters to use to calculate Rrs.
    
    Inputs: 
    main_dir: A string containing the main image directory
    output_csv_path: A string containing the filepath to write the metadata.csv 
    glint_correct: Option to apply the std_glint_removal_method() function to mask pixels with instances of specular sun glint. Default is True
    glint_std_factor: A factor to multiply to the standard deviation of NIR values. Default is 1.
    lw_method: Method used to calculate water leaving radiance. Default is mobley_rho_method()
    ed_method: Method used to calculate downwelling irradiance. Default is dls_ed(). 
    
    """
    
    ############################
    #### setup the workspace ###
    ############################
    
    # specify the locations of the different levels of imagery
    # I do this partially so I can just change these pointers to the data and not have to copy it or have complex logic repeated
    raw_water_img_dir = main_dir+'/raw_water_imgs'
    raw_sky_img_dir = main_dir+'/raw_sky_imgs'
    
    lt_dir = main_dir+'/lt_imgs'
    sky_lt_dir = main_dir+"/sky_lt_imgs"
    glint_corrected_lt_dir = main_dir+'/lt_glint_corrected_imgs'
    lw_dir = main_dir+'/lw_imgs'
    rrs_dir = main_dir+'/rrs_imgs'
    panel_dir = main_dir+'/panel'
    
    # make all these directories if they don't already exist
    all_dirs = [lt_dir, glint_corrected_lt_dir, lw_dir, rrs_dir, panel_dir]
    for directory in all_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # this makes an assumption that there is only one panel image put in this directory
    panel_names = glob.glob(os.path.join(panel_dir, 'IMG_*.tif'))
    
    ### convert raw imagery to radiance (Lt)
    print("Converting raw images to radiance (raw -> Lt).")
    process_micasense_subset(main_dir, warp_img_dir=main_dir+'/align_img', overwrite=True, sky=False)
    
    # deciding if we need to process raw sky images to radiance 
    if lw_method in ['mobley_rho_method','blackpixel_method']:
        print("Converting raw sky images to radiance (raw sky -> Lsky).")
        # we're also making an assumption that we don't need to align/warp these images properly because they'll be medianed
        process_micasense_subset(main_dir, warp_img_dir=None, overwrite=True, sky=True)

    ########################################
    ### correct for glint in the imagery ###
    ########################################
    if glint_correct == True:
        std_glint_removal_method(lt_dir, glint_corrected_lt_dir, glint_std_factor)
        # write all the exif data into the new files
        rewrite_exif_data(lt_dir, glint_corrected_lt_dir)
        print('Finished Lt glint correction.')
                    
    else: # if we don't do the glint correction then just change the pointer to the lt_dir
        glint_corrected_lt_dir = lt_dir
        print('No glint correction.')
    
    ##################################
    ### correct for surface reflected light ###
    ##################################
    
    if  lw_method == 'mobley_rho_method':
        mobley_rho_method(sky_lt_dir, glint_corrected_lt_dir, lw_dir)
        print('Doing the mobley_rho_method (Lt -> Lw).')
        # write all the exif data into the new files
        rewrite_exif_data(lt_dir, lw_dir)
    
    elif lw_method == 'blackpixel_method':
        blackpixel_method(sky_lt_dir, lt_dir, lw_dir)
        print('Doing the blackpixel_method (Lt -> Lw)')
        # write all the exif data into the new files
        rewrite_exif_data(lt_dir, lw_dir)
    
    elif lw_method == 'hedley_method':
        hedley_method(lt_dir, lw_dir)
        print('Doing the hedley_method (Lt -> Lw)')
        # write all the exif data into the new files
        rewrite_exif_data(lt_dir, lw_dir)
            
    else: # just change this pointer if we didn't do anything the lt over to the lw dir
        print('Not doing any Lw calculation.')
        lw_dir = glint_corrected_lt_dir 
        
        
    #####################################
    ### normalize Lw by Ed to get Rrs ###
    #####################################
    
    if ed_method == 'panel_ed':
        print('Normalizing by panel irradiance (Lw/Ed -> Rrs).')
        panel_ed(panel_dir, lw_dir, rrs_dir, output_csv_path)
        # write all the exif data into the new rrs files
        rewrite_exif_data(lt_dir, rrs_dir)
        
    elif ed_method == 'dls_ed':
        print('Normalizing by DLS irradiance (Lw/Ed -> Rrs).')
        dls_ed(raw_water_img_dir, lw_dir, rrs_dir, output_csv_path)
        # write all the exif data into the new rrs files
        rewrite_exif_data(lt_dir, rrs_dir) 

    else:
        print('No other irradiance normalization methods implemented yet, panel_ed is recommended.')
        return(False)
    

    ################################################
    ### finalize and add point output ###
    ################################################
        
    ### decide if the final output should be imagery or medianed points in a datafame
    print('All data has been saved as Rrs using the ' + str(lw_method)  + ' to calcualte Lw and normalized by '+ str(ed_method)+ ' irradiance.')
    
    # add function here that will convert the rrs data to points? 
    
    return(True)

                  
############ water quality retrieval algorithms ############

def chl_hu(Rrsblue, Rrsgreen, Rrsred):
    """
    This is the Ocean Color Index algorithm (Hu et al. 2012)
    """
    
    ci1 = -0.4909
    ci2 = 191.6590

    #CI = Rrsgreen - ( Rrsblue + (555 - 477)/(667 - 477) * (Rrsred - Rrsblue) )
    CI = Rrsgreen - ( Rrsblue + (560 - 475)/(668 - 475) * (Rrsred - Rrsblue) )
    ChlCI = 10**(ci1 + ci2*CI)
    return(ChlCI)


def chl_ocx(Rrsblue, Rrsgreen):
    # this is a vectorized version of the OCx chla algorithm
    # documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/
    
    # L8 OC2 coefficients
    a0 = 0.1977
    a1 = -1.8117
    a2 = 1.9743
    a3 = 2.5635
    a4 = -0.7218
    
#     # OC3m coefficients
    
#     a0 = 0.2424
#     a1 = -2.7423
#     a2 = 1.8017
#     a3 = 0.0015
#     a4 = -1.2280
    
#     #OC2m coefficients
#     a0 = 0.2500
#     a1 = -2.4752
#     a2 = 1.4061
#     a3 = -2.8233
#     a4 = 0.5405

    log10chl = a0 + a1 * (np.log10(Rrsblue / Rrsgreen)) \
        + a2 * (np.log10(Rrsblue / Rrsgreen))**2 \
            + a3 * (np.log10(Rrsblue / Rrsgreen))**3 \
                + a4 * (np.log10(Rrsblue / Rrsgreen))**4

    oc3m = np.power(10, log10chl)
    return(oc3m)

#def chl_oc3(Rrs443, Rrs488, Rrs547, Rrs555, Rrs667):
def chl_hu_ocx(Rrsblue, Rrsgreen, Rrsred):
    ''' 
    This is the full NASA oc3m blended algorithm with CI (Hu et al. 2012) 
    This specific code is grabbed from https://github.com/nasa/HyperInSPACE.
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

    oc3m = np.power(10, log10chl)

    CI = Rrsgreen - ( Rrsblue + (560 - 475)/(668 - 475) * \
        (Rrsred -Rrsblue) )
        
    ChlCI = 10** (ci1 + ci2*CI)

    if ChlCI.any() <= thresh[0]:
        chlor_a = ChlCI
    elif ChlCI.any() > thresh[1]:
        chlor_a = oc3m
    else:
        chlor_a = oc3m * (ChlCI-thresh[0]) / (thresh[1]-thresh[0]) +\
            ChlCI * (thresh[1]-ChlCI) / (thresh[1]-thresh[0])

    return chlor_a



def chl_gitelson(Rrsred, Rrsrededge):
    """
    This algortithm estimates chlorophyll a concentrations using the Gitelson et al. (__) algorithm. This algorithm is recommended for coastal (Case 2) waters.
    """
    
    chl = 59.826 * (Rrsrededge/Rrsred) - 17.546
    return chl

######## TSM retrieval algs ######

def nechad_tsm(Rrsred):
    """
    This algorithm estimates total suspended matter (TSM) concentrations using the Nechad et al. (2009) algorithm
    
    """
    A = 374.11
    B = 1.61
    C = 17.38
    
    tsm = (A*Rrsred/(1-(Rrsred/C))) + B
    return(tsm)
               

def convert_to_ocean_color_gdf(chla_list, spectra_list, img_metadata):
    """
    
    """
    chla_dates = []
    for im in img_metadata:
        date_time_str = im['Date'] + ' ' + im['UTC-Time']

        date_time_obj = datetime.strptime(date_time_str, '%m/%d/%Y %H:%M:%S')
        chla_dates.append(date_time_obj)
    lons = []
    lats = []
    alts = []
    for im in img_metadata:
        lons.append(im['Longitude'])
        lats.append(im['Latitude'])
        alts.append(im['Altitude'])
        
    chla_df = pd.DataFrame(
    {'chla': chla_list,
     'Latitude': lats,
     'Longitude': lons,
     'Altitude' : alts,
     'spectra' : spectra_list,
     'time' : chla_dates})

    chla_gdf = gpd.GeoDataFrame(
        chla_df, geometry=gpd.points_from_xy(chla_df.Longitude, chla_df.Latitude))
    
    return(chla_gdf)

#def georeferencing()
"""
"""
                  
                  
   
                  
        
