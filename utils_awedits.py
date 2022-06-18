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
    This is the specific EXIF format we write into the images. More could be added based on what is needed in your workflow.
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
    XResolution,YResolution,ResolutionUnits,\
    GPSImgDirection,GPSPitch,GPSRoll\n"

    lines = [header]
    for i,capture in enumerate(img_set.captures):
        #get lat,lon,alt,time
        #outputFilename = capture.uuid+'.tif'
        outputFilename = 'capture_' + str(i+1)+'.tif'
        fullOutputPath = os.path.join(outputPath, outputFilename)
        lat,lon,alt = capture.location()
        
        resolution = capture.images[0].focal_plane_resolution_px_per_mm
        
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
        linestr += '{},{},mm,'.format(resolution[0],resolution[1])
        linestr += '{},{},{}'.format(yaw, pitch, roll)
        linestr += '\n' # when writing in text mode, the write command will convert to os.linesep
        lines.append(linestr)

    fullCsvPath = os.path.join(outputPath,'metadata.csv')
    with open(fullCsvPath, 'w') as csvfile: #create CSV
        csvfile.writelines(lines)
        
    return(fullCsvPath)

def get_warp_matrix(img_capture, max_alignment_iterations = 50):
    """
    This function aligns the images and outputs a warp matrix. These settings could be changed but generally work well on a variety of images.
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

    #print("Finished Aligning, warp matrices={}".format(warp_matrices))
    return(warp_matrices)

'''
def decdeg2dms(dd):
    """ Convert from decimal degrees to degrees minutes seconds"""
    
    is_positive = dd >= 0
    dd = abs(dd)
    minutes,seconds = divmod(dd*3600,60)
    degrees,minutes = divmod(minutes,60)
    degrees = degrees if is_positive else -degrees
    return (degrees,minutes,seconds)
'''

def save_images(img_set, outputPath, thumbnailPath, warp_img_capture, generateThumbnails = True, overwrite=False):
    """
    This function does the actual processing of running through each capture within an imageset, undistorting it, aligning via a warp matrix, and all the necessary Micasense processing and saving as a .tiff.
    """

    warp_matrices = get_warp_matrix(warp_img_capture)

    if not os.path.exists(outputPath):
        os.makedirs(outputPath)
    if generateThumbnails and not os.path.exists(thumbnailPath):
        os.makedirs(thumbnailPath)

    # Save out geojson data so we can open the image capture locations in our GIS
    # with open(os.path.join(outputPath,'imageSet.json'),'w') as f:
    #     f.write(str(geojson_data))


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

def write_img_exif(fullCsvPath, outputPath):  
    """
    write out the EXIF data into the images using the tool installed in this docker container.
    If you don't use docker you might need to change the path of this tool
    """
    
    exiftool_cmd = '/usr/local/envs/micasense/bin/exiftool'
   
    cmd = '{} -csv="{}" -overwrite_original {}'.format(exiftool_cmd, fullCsvPath, outputPath)
    #print(cmd)
    subprocess.check_call(cmd, shell=True)
    return(True)

def process_micasense_subset(project_dir, warp_img_dir=None, overwrite=False, sky=False):
    """
    This function takes in an image directory and saves warped and cropped images, corrected for vignetting.
    
    It can take images and no panels and calculate radiance or panels/DLS data and process it to irradiance reflectance (R) using the Micasense code. R isn't often used in ocean color work so we typically process to radiance and then have custom functions for going to Lw and then Rrs.
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
        if write_img_exif(fullCsvPath, outputPath) == True:
            print("Finished saving image metadata.")
            
    return(outputPath)




############ general functions for ingesting processed imagery and metadata ############

def key_function(item_dictionary):
    '''Extract datetime string from given dictionary, and return the parsed datetime object'''
    
    datetime_string = item_dictionary['UTC-Time']
    return datetime.datetime.strptime(datetime_string, '%H:%M:%S')

def load_img_fn_and_meta(img_dir, count=10000, start=0):
    """
    This function simply returns a list of metadata in case a user wants to visualize hundreds or thousands of images worth of metadata that couldn't be loaded fully into memory with the images.
    """
    
    df = pd.read_csv(img_dir + '/metadata.csv')
    df['filename'] = df['SourceFile'].str.split('/').str[-1]
    df = df.set_index('filename')
    img_metadata = []
    for file in glob.glob(img_dir + "/*.tif"):
        md = gpsphoto.getGPSData(file)
        md['full_filename'] = file
        filename = file.split('/')[-1]
        md['filename'] = filename
        
        # this isn't correctly loaded into the exifdata so pulling it manually into the dataframe
        md['yaw']   = (df.loc[filename]['    GPSImgDirection'] + 360) % 360
        md['pitch'] = (df.loc[filename]['GPSPitch'] + 360) % 360
        md['roll']  = (df.loc[filename]['GPSRoll'] + 360) % 360

        img_metadata.append(md)

    # sort it by time now
    img_metadata.sort(key=key_function)
    # cut off if necessary
    img_metadata = img_metadata[start:start+count]
    return(img_metadata)

def load_images(img_list):
    """
    simple helper function for grabbing images from a filename list
    """
    
    all_imgs = []
    for im in img_list:
        with rasterio.open(im, 'r') as src:
            all_imgs.append(src.read())
    return(all_imgs)

def retrieve_imgs_and_metadata(img_dir, count=10000, start=0, altitude_cutoff = 0):
    """
    This function is the main interface we expect the user to use when grabbing a subset of imagery from any stage in processing. This returns the images as a numpy array and metadata as a pandas dataframe. 
    """
    
    img_metadata = load_img_fn_and_meta(img_dir, count=count, start=start)
    idxs = []
    for i, md in enumerate(img_metadata):
        if md['Altitude'] > altitude_cutoff:
            idxs.append(i)
    
    imgs = load_images([img_metadata[i]['full_filename'] for i in idxs])
    imgs = np.array(imgs)
    # give the metadata the index of each image it is connected to so that I can sort them later and still
    # pull out ids to visualize from imgs
    img_metadata = [img_metadata[i] for i in idxs]
    i = 0
    for md in img_metadata:
        md['id'] = i
        i += 1
        
    df = pd.DataFrame.from_records(img_metadata, index='id')
    df['DateTimeStamp'] = pd.to_datetime(df['Date']+' '+df['UTC-Time'])
    return(imgs, df)



############ chla retrieval algorithms ############

def oc_index(blue, green, red):
    """
    This is just the Ocean Color Index algorithm (Hu et al. 2012)
    """
    
    ci1 = -0.4909
    ci2 = 191.6590

    CI = green - ( blue + (555 - 477)/(667 - 477) * (red - blue) )
    ChlCI = 10**(ci1 + ci2*CI)
    return(ChlCI)

def L2chlor_a(Rrs443, Rrs488, Rrs547, Rrs555, Rrs667):
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
    
    if Rrs443 > Rrs488:
        Rrsblue = Rrs443
    else:
        Rrsblue = Rrs488

    log10chl = a0 + a1 * (np.log10(Rrsblue / Rrs547)) \
        + a2 * (np.log10(Rrsblue / Rrs547))**2 \
            + a3 * (np.log10(Rrsblue / Rrs547))**3 \
                + a4 * (np.log10(Rrsblue / Rrs547))**4

    oc3m = np.power(10, log10chl)

    CI = Rrs555 - ( Rrs443 + (555 - 443)/(667 - 443) * \
        (Rrs667 -Rrs443) )
        
    ChlCI = 10** (ci1 + ci2*CI)

    if ChlCI <= thresh[0]:
        chlor_a = ChlCI
    elif ChlCI > thresh[1]:
        chlor_a = oc3m
    else:
        chlor_a = oc3m * (ChlCI-thresh[0]) / (thresh[1]-thresh[0]) +\
            ChlCI * (thresh[1]-ChlCI) / (thresh[1]-thresh[0])

    return chlor_a

def convert_to_ocean_color_gdf(chla_list, spectra_list, img_metadata):
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


def vec_chla_img(blue, green):
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

    log10chl = a0 + a1 * (np.log10(blue / green)) \
        + a2 * (np.log10(blue / green))**2 \
            + a3 * (np.log10(blue / green))**3 \
                + a4 * (np.log10(blue / green))**4

    oc3m = np.power(10, log10chl)
    return(oc3m)


######## workflow functions for cleanly running all of this ########

def std_glint_removal_method(lt_dir, glint_corrected_lt_dir, glint_std_factor=1.5):
    """
    the glint_std_factor is anything > than mean+std*glint_std_factor will be filtered out so the lower it is the more will be filtered
    """
    
    # grab the first ten images, find the mean and std, then anything 3x that is classified as glint
    lt_imgs, lt_img_metadata = retrieve_imgs_and_metadata(lt_dir, count=10, start=0, altitude_cutoff=0)
    lt_mean = np.mean(lt_imgs,axis=(0,2,3)) # here we want the mean of each band
    lt_std = np.std(lt_imgs,axis=(0,2,3)) # here we want the std of each band
    del lt_imgs # free up the memory

    # go through each Lt image in the dir and divide it by the lsky
    for im in glob.glob(lt_dir + "/*.tif"):
        with rasterio.open(im, 'r') as Lt_src:
            profile = Lt_src.profile
            lt_deglint_all = []
            for i in range(1,6):
                # todo this is probably faster if we read them all and divide by the vector
                lt_deglint = Lt_src.read(i)

                lt_deglint[lt_deglint > lt_mean[i-1]+lt_std[i-1]*glint_std_factor] = np.nan
                lt_deglint_all.append(lt_deglint) #append all for each band
            stacked_lt_deglint = np.stack(lt_deglint_all) #stack into np.array
            
            #write new stacked lw tifs
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(glint_corrected_lt_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_lt_deglint)
    return(True)

def mobley_rho_method(sky_lt_dir, lt_dir, lw_dir, rho = 0.028): 
    """use a single (or small set of) Lsky image(s) and rho to calculate Lw for each image this approach is good if sky conditions aren't changing substantially during the flight
    
    the default rho of 0.028 is based on Mobley et al 1999
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
    # use dark pixel assumption (NIR=0) to derive rho, used to calculate rrs across all bands

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
    leave comment
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
            #calculate Rrs (Ruas - b(Ruas(NIR)-min(Ruas(NIR))))
            lw = stacked_lt[i,j,:,:] - all_slopes[j]*(stacked_lt[i,4,:,:]-min_lt_NIR)
            lw_all.append(lw)

        stacked_lw = np.stack(lw_all) #stack into np.array

        #write new stacked Rrs tif w/ reflectance units
        with rasterio.open(os.path.join(lw_dir, im_name), 'w', **profile) as dst:
            dst.write(stacked_lw)

                
def panel_reflectance_from_serial(panel_dir):
    """
    This function scans the QR code from the first reflectance calibration panel image in the panel directory to obtain known reflectance values
    """
    panel_ref_from_serial = []
    for i in range(5):
        first_panel_img = panel.Panel(image.Image(os.path.join(panel_dir, os.listdir(panel_dir)[i]))).reflectance_from_panel_serial()
        panel_ref_from_serial.append(first_panel_img)
    return(panel_ref_from_serial)

def panel_ed(panel_dir, lw_dir, rrs_dir, output_csv_path):
    """
    This grabs Ed from the panel and then divides the Lw images by that irradiance to calculate Rrs.
    """
    panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures
    panels = np.array(panel_imgset)  
    
    ed_data = []
    ed_columns = ['image', 'ed_475', 'ed_560', 'ed_668', 'ed_717', 'ed_842']
    
    for i in range(len(panels)):         
        #calculate panel Ed from every panel capture
        ed = np.array(panels[i].panel_irradiance()) # this function automatically finds the panel albedo and uses that to calcuate Ed, otherwise rases an error
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
            rrs_all = []
            # could vectorize this for speed
            for i in range(1,6):
                lw = Lw_src.read(i)
                
                rrs = lw/ed[i-1]
                rrs_all.append(rrs) #append each band
            stacked_rrs = np.stack(rrs_all) #stack into np.array
            
            # TODO need to swap the NIR and rededge bands

            #write new stacked Rrs tifs w/ Rrs units
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(rrs_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_rrs)
    return(True)

def dls_ed(raw_water_dir, lw_dir, rrs_dir, output_csv_path):
    """
    
    """
    capture_imgset = imageset.ImageSet.from_directory(raw_water_dir).captures
    ed_data = []
    ed_columns = ['image', 'ed_475', 'ed_560', 'ed_668', 'ed_717', 'ed_842']
    
    for i,capture in enumerate(capture_imgset):
        ed = capture.dls_irradiance()
        #Ed[3], Ed[4] = Ed[4], Ed[3] #flip last two bands (red edge and NIR)
        #Ed = np.array(Ed)*1000 #Scale to mW
        ed_row = ['capture_'+str(i+1)]+[np.mean(ed[0])]+[np.mean(ed[1])]+[np.mean(ed[2])]+[np.mean(ed[3])]+[np.mean(ed[4])]
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
            
            # TODO need to swap the NIR and rededge bands

            #write new stacked Rrs tifs w/ Rrs units
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(rrs_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_rrs)
    return(True)
    
def dls_corrected_ed(panel_dir, raw_water_dir, lw_dir, rrs_dir, output_csv_path):
    """
    This function calculates downwelling irradiance (Ed) from the DLS using a correction factor from the calibration reflectance panel
    """
    panel_ref_from_serial = panel_reflectance_from_serial(panel_dir)
    
    capture_imgset = imageset.ImageSet.from_directory(raw_water_dir).captures
    panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures
    panels = np.array(panel_imgset) 

    ed_data = []
    ed_columns = ['image', 'ed_475', 'ed_560', 'ed_668', 'ed_717', 'ed_842']

    for i,capture in enumerate(capture_imgset):
        panel_radiances = []
        for cap in panels:
            if cap.panels_in_all_expected_images():
                panel_radiances.append(cap.panel_radiance())
        panel_radiances = np.mean(np.asarray(panel_radiances), axis=0)
        panel_radiances[3], panel_radiances[4] = panel_radiances[4], panel_radiances[3] #flip last two bands

        #get mean irradiance from panel using known panel reflectance (from serial)
        irr_from_panel = math.pi * panel_radiances / panel_ref_from_serial

        #calculate DLS correction = irr from panel / DLS irradiances
        dls_correction = irr_from_panel/capture.dls_irradiance()
        ed = capture.dls_irradiance()*dls_correction
        ed_row = ['capture_'+str(i+1)]+[ed[0]]+[ed[1]]+[ed[2]]+[ed[3]]+[ed[4]]
        ed_data.append(ed_row)

    ed_data = pd.DataFrame.from_records(ed_data, index='image', columns = ed_columns)
    ed_data.to_csv(output_csv_path+'/dls_corr_ed.csv')

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
            
            # TODO need to swap the NIR and rededge bands

            #write new stacked Rrs tifs w/ Rrs units
            im_name = im.split('/')[-1] # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(rrs_dir, im_name), 'w', **profile) as dst:
                dst.write(stacked_rrs)
    return(True)    
    

def rewrite_exif_data(lt_dir, output_dir):
    """
    we want the metadata in each directory but we need to customize it to have the correct path when writing so doing that for each step
    """
    # first copy the log from lt_imgs where is it output by the micasense processing code to the dir of choice and change the file path within the csv line
    with open(lt_dir+"/metadata.csv", "rt") as fin:
        with open(output_dir+"/metadata.csv", "wt") as fout:
            for line in fin:
                # here we just grab the final sub-directory name and replace it, so this could look like fout.write(line.replace('lt_imgs', 'rrs_imgs'))
                fout.write(line.replace(lt_dir.split('/')[-1], output_dir.split('/')[-1]))
                
    # then write the exif data into these images
    write_img_exif(output_dir+"/metadata.csv", output_dir)

def process_raw_to_rrs(main_dir, ed_method='panel', glint_correct=True, glint_std_factor=2, sky_reflection_correction='nir_baseline'):
    """
    This is the main processing script
    arguments are:
    
    ed_method='panel' 
    glint_correct=True 
    glint_std_factor=2 
    sky_reflection_correction='nir_baseline'
    """
    
    ############################
    #### setup the workspace ###
    ############################
    
    # specify the locations of the different levels of imagery
    # I do this partially do I can just change these pointers to the data and not have to copy it or have complex logic repeated
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
    process_micasense_subset(raw_water_img_dir, panelNames=None, warp_img_dir=main_dir+'/align_img', 
                                           overwrite=True)
    
    # deciding if we need to process raw sky images to radiance 
    if sky_reflection_correction in ['single_lsky_mobley']:
        print("Converting raw sky images to radiance (raw sky -> Lsky).")
        # we're making an assumption here that the sky panel Ed is the same as the surface panel
        # we're also making an assumption that we don't need to align/warp these images properly because they'll be medianed
        process_micasense_subset(raw_sky_img_dir, panelNames=None, warp_img_dir=None, 
                                           overwrite=True, sky=True)

    ########################################
    ### correct for glint in the imagery ###
    ########################################
    
    if glint_correct == True:
        basic_std_glint_correction(lt_dir, glint_corrected_lt_dir, glint_std_factor)
        # write all the exif data into the new files
        rewrite_exif_data(lt_dir, glint_corrected_lt_dir)
        print('Finished Lt glint correction.')
                    
    else: # if we don't do the glint correction then just change the pointer to the lt_dir
        glint_corrected_lt_dir = lt_dir
        print('No glint correction.')
    
    ##################################
    ### correct for sky reflection ###
    ##################################
    
    if sky_reflection_correction == 'blackpixel_method':
        # apply the nir_baseline correction
        print('The NIR baseline subtraction is not implemented yet.')
        return(False)
    
    elif sky_reflection_correction == 'single_lsky_mobley':
        single_lsky_mobley(sky_lt_dir, lt_dir, lw_dir)
        print('Doing the single_lsky_mobley correction (Lt -> Lw).')
        # write all the exif data into the new files
        rewrite_exif_data(lt_dir, lw_dir)
    
    #elif sky_reflection_correction == 'hedley_correction':
      #  ruas_dir = ?
       # panel_irradiance_normalizaton(panel_dir, lw_dir, ruas_dir)
       # hoch_deglint(ruas_dir, rrs_dir):
  
            
    else: # just change this pointer if we didn't do anything the lt over to the lw dir
        print('Not doing any sky reflection correction.')
        lw_dir = glint_corrected_lt_dir 
        
        
    #####################################
    ### normalize Lt by Ed to get Rrs ###
    #####################################
    
    if ed_method == 'panel':
        print('Normalizing by panel irradiance (Lw -> Rrs).')
        panel_ed(panel_dir, lw_dir, rrs_dir)
        # write all the exif data into the new rrs files
        rewrite_exif_data(lt_dir, rrs_dir)
        
    elif ed_method == 'dls':
        print('Normalizing by panel irradiance (Lw -> Rrs).')
        dls_ed(raw_water_imgs, panel_dir, lw_dir, rrs_dir)
        # write all the exif data into the new rrs files
        rewrite_exif_data(lt_dir, rrs_dir) 
        
    #elif ed_method == 'dls_corr':
        

    else:
        print('No other irradiance normalization methods implemented yet, panel is recommended.')
        return(False)
    

    ################################################
    ### finalize and add point output ###
    ################################################
        
    ### decide if the final output should be imagery or medianed points in a datafame
    print('All data has been output as Rrs imagery with '+ str(glint_correct) + ' glint removal, XXX sky reflection and normalized by XXX irradiance.')
    
    # add function here that will convert the rrs data to points 
    
    return(True)

def visualization(project_path, img_type, ed_method='panel'):
    if img_type == 'lt':
        lt_imgs, lt_img_metadata = retrieve_imgs_and_metadata(img_dir = project_path+'/water_lt_imgs')
        plt.plot(lt_imgs[0].mean(axis=(1,2))) 
    if img_type == 'ed':
        if ed_method == 'panel':
            ed = pd.read_csv(project_path+'/panel_ed.csv')      
        elif ed_method ==  'dls':
            ed = pd.read_csv(project_path+'/dls_ed.csv')   
        elif ed_method == 'dls_corr':
            ed = pd.read_csv(project_path+'/dls_corr_ed.csv') 
       #plot Ed for every capture
        colors = plt.cm.viridis(np.linspace(0,1,len(ed)))
        wv = [475, 560, 668, 717, 842]
        for i in range(len(ed)):
            plt.plot(wv, ed.iloc[i,1:6]*1000,  marker = 'o', color=colors[i]) #multiply by 1000 to convert to mW
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('Ed ($mW/m^2/nm$)')       
                  
                  
                  
                  
                  
                  
                  
                  
        