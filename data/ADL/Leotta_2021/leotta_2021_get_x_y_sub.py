# -*- coding: utf-8 -*-
"""Leotta_2021_get_X_y_sub.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1S59WDs0nbTeuTGpms2v1rBUM-LYJp8FG

#Leotta_2021_get_X_y_sub.ipynb
Loads the dataset from a local zip file and converts the data into numpy arrays of X (data), y(labels), and sub (subject numbers)
>X = (samples, time steps per sample, accel_x/y/z/total_accel)  
>y = (samples, {0,1,...17}) #activity classification  
>s = subject number  

This is an intermediate representation that can be used to build the train/validate/test arrays.

Some functions are defined, but this is mostly meant to be run in interactive
mode with the files saved at the end.

The dataset citation and link to the paper and download are available on this site https://sepl.dibris.unige.it/2020-DailyActivityDataset.php

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

[Lee B. Hinkle](https://userweb.cs.txstate.edu/~lbh31/), Texas State University, [IMICS Lab](https://imics.wp.txstate.edu/)  
TODO:
* This is still work-in-progress
* Figure out how to replace int labels with strings - seems like it should be easy, but apparently not.
* Reshape from big df to numpy arrays crashes unless run on colab high RAM runtime.   Maybe reduce y and sub types to int8?
* Make timesteps and stepsize passed parameters from get_X_y_sub
"""

import os
import shutil #https://docs.python.org/3/library/shutil.html
from shutil import unpack_archive # to unzip
#from shutil import make_archive # to create zip for storage
import requests #for downloading zip file
from scipy import io #for loadmat, matlab conversion
import time
import pandas as pd
import numpy as np
from numpy import savetxt
import matplotlib.pyplot as plt # for plotting - pandas uses matplotlib
from tabulate import tabulate # for verbose tables
from tensorflow.keras.utils import to_categorical # for one-hot encoding
import gc #trying to resolve crash on reshape method

interactive = False # enables functions for exploring data and dataframes

#Helper functions especially useful in colab
from requests import get
def what_is_my_name():
    """returns the name of the running colab ipynb file"""
    #code is readily available on web - not original
    my_name = get('http://172.28.0.2:9000/api/sessions').json()[0]['name']
    return my_name
#credit https://stackoverflow.com/users/4944093/george-petrov for name method
def namestr(obj, namespace):
    return [name for name in namespace if namespace[name] is obj]
def get_shapes(np_arr_list):
    """Returns text, each line is shape and dtype for numpy array in list
       example: print(get_shapes([X_train, X_test, y_train, y_test]))
       WARNING: Gets 'list index out of range' if called within method."""
    return # do nothing until out of range issue fixed
    #probably related to this https://stackoverflow.com/questions/592746/how-can-you-print-a-variable-name-in-python
    #bonus for LOL comments
    shapes = ""
    print(np_arr_list)
    for i in np_arr_list:
        print(' i = ', i)
        my_name = namestr(i,globals())
        print ('my_name = ',my_name)
        shapes += (my_name[0] + " shape is " + str(i.shape) \
            + " data type is " + str(i.dtype) + "\n")
    return shapes

def unzip_leotta(
    orig_zipfile, #full file name of original dataset zipfile
    working_dir = '/content/dataset' # location of unzipped files in colab
    ):
    """check for local copy, if none unzips the dataset structure in working_dir"""
    if (os.path.isdir(working_dir)):
        print("Using existing archive in colab")
        return
    else:
        print("Unzipping Leotta 2021 dataset")
        if (os.path.exists(orig_zipfile)):
            print("Using source file", orig_zipfile)
            shutil.unpack_archive(orig_zipfile,'/content/dataset','zip')
        else:
            print("Error: ", orig_zipfile, " not found, exiting")
            return
if interactive:
    unzip_leotta(orig_zipfile = '/content/drive/My Drive/Datasets/ADL_Leotta_2021.zip')

def df_from_csv (
    sub_num, # 1 - 8
    sensor_loc, # ankle, hip, wrist
    working_dir = '/content/dataset'): # location of unzipped files in colab 
    """reads csv, returns df with accel x/y/z/ttl, label, sub_num"""
    fnameX = sensor_loc + '_X_0' + str(sub_num) +  '.csv'
    fnamey = sensor_loc + '_Y_0' + str(sub_num) +  '.csv'
    ffnameX = os.path.join(working_dir, sensor_loc, fnameX)
    ffnamey = os.path.join(working_dir, sensor_loc, fnamey)
    print ('Processing: ', ffnameX, ffnamey)
    df = pd.read_csv(ffnameX)
    if (sensor_loc == 'wrist'): # Centrepoint device has different header name
        df.rename(columns={'Timestamp UTC': 'Timestamp'}, inplace=True)
    # the imported Timestamp is an object - need to convert to DateTime
    # in order to set the index to DateTime format.  Enables resampling etc.
    # Leaving these here - helpful to debug if leveraging this code!
        #print("*** Start ***")
        #print(type(df.index))
        #print(df.info(verbose=True))  
    df['Timestamp'] = pd.to_datetime(df['Timestamp']) 
    df.set_index('Timestamp', drop = True, inplace = True)
    if (sensor_loc != 'wrist'): # Centrepoint doesn't have non-accel columnns
        df = df.drop(['Temperature','Gyroscope X','Gyroscope Y','Gyroscope Z',
                      'Magnetometer X','Magnetometer Y','Magnetometer Z'], axis=1)
    df_sqd = df.pow(2)[['Accelerometer X','Accelerometer Y','Accelerometer Z']] #square each accel
    df_sum = df_sqd.sum(axis=1) #add sum of squares, new 1 col df
    df.loc[:,'accel_ttl'] = df_sum.pow(0.5)-1  # sqrt and remove 1g due to gravity
    del df_sqd, df_sum
    df.columns = [sensor_loc + '_accel_x', sensor_loc + '_accel_y', sensor_loc + '_accel_z', sensor_loc + '_accel_ttl']
    # add activity numbers - number of rows are the same in this dataset
    # Why doesn't this work? df['label'] = pd.read_csv(ffnamey, dtype='Int64')
    dfy = pd.read_csv(ffnamey)
    df['label']=dfy['label'].to_numpy() # this works, above doesn't?
    df['label'] = df['label'].astype(int) # change from float to int
    del dfy
    # add column with subject number
    df['sub'] = sub_num
    return df

def df_from_one_sub (sub_num): # 1 - 8
    """reads 3 csv files for a single subject, combines an returns a single dataframe"""
    my_sub_num = sub_num # not sure necessary but easier to follow...
    df_ankle = df_from_csv(sub_num = my_sub_num, sensor_loc = 'ankle')
    df_hip = df_from_csv(sub_num = my_sub_num, sensor_loc = 'hip')
    #wrist is a bit more complicated since the sample rate is different
    df_wrist = df_from_csv(sub_num = my_sub_num, sensor_loc = 'wrist')
    df_wrist = to_fixed_timedelta(df_wrist,new_time_step='10ms')

    if ((df_ankle['label'].equals(df_hip['label']))
            and (df_ankle['sub'].equals(df_hip['sub']))
            and (df_ankle['label'].equals(df_wrist['label']))
            and (df_ankle['sub'].equals(df_wrist['sub']))) :
        print('confirmed label and sub match - dropping from ankle and hip')
        df_ankle.drop(['label','sub'], axis=1, inplace=True)
        df_hip.drop(['label','sub'], axis=1, inplace=True)
    else:
        print('Error:  label and sub do not match, cannot combine dataframes')
        print('label match = ',df_ankle['label'].equals(df_hip['label']))
        print('sub match = ',df_ankle['sub'].equals(df_hip['sub']))
    df_temp = df_ankle.join(df_hip)
    df_final = df_temp.join(df_wrist)
    del df_temp
    return df_final

def to_fixed_timedelta(df_in, new_time_step='50ms'):
    """resamples DateTime indexed dataframe to new_time_step.  Will
    return NaN per resample method (happens on irregular samples)"""
    #print("Resampling at ",new_time_step,": Original # rows = ",len(df_in.index))
    orig_rows = len(df_in.index)
    df_out = df_in.resample(new_time_step).mean()
    df_out = df_out.interpolate() #linear interpolation for nan
    print("Resample: Original/New # rows = ",orig_rows,len(df_out.index))
    return df_out
# method copied from MobiAct_ADL_get_X_y_sub.ipynb, it is named this way
# because it can also be used to "correct" sample jitter in smartphone data

# exploratory code to try and figure out why plots seem off
# confirmed units in g's https://actigraphcorp.com/support/downloads/#Manuals
if interactive:
    snum = 1
    df_ankle = df_from_csv(sub_num = snum, sensor_loc = 'ankle')
    display(df_ankle.head())
    df_hip = df_from_csv(sub_num = snum, sensor_loc = 'hip')
    display(df_hip.head())
    df_wrist = df_from_csv(sub_num = snum, sensor_loc = 'wrist')
    display(df_wrist.head())
    print('ankle')
    print(np.amin(df_ankle, axis=0))
    print(np.amax(df_ankle, axis=0))
    print('hip')
    print(np.amin(df_hip, axis=0))
    print(np.amax(df_hip, axis=0))
    print('wrist')
    print(np.amin(df_wrist, axis=0))
    print(np.amax(df_wrist, axis=0))

if interactive:
    df_temp = df_from_one_sub (sub_num = 8)
    print(type(df_temp.index)) # should be DateTimeIndex
    print(df_temp.info(verbose=True))
    display(df_temp.head())

if interactive:
    #df_temp = my_df[my_df['label'] != 0] # drop 'other' labeled activities
    fig, axes = plt.subplots(nrows=1,ncols=2,figsize=(12,6))
    df_temp['label'].plot(ax = axes[0], subplots=True) 
    df_temp['sub'].plot(ax = axes[1], subplots=True)
    plt.show()

if interactive:
    print('Act. # instances (rows)')
    print(df_temp['label'].value_counts()) # shows the number of each activity

if interactive:
    # shows stacked acceleration diagrams for given label
    df_temp[df_temp['label'] == 1].plot(figsize=(12, 8),subplots = True)

"""# Dataframe pieces in place, next method takes dataframe and parses to numpy arrays
In order to limit memory requirements it is done by subject rather than creating one big dataframe as in other datasets
"""

def split_df_to_timeslice_nparrays(df, features, time_steps, step):
    """slice the df into segments of time_steps length and return X, y, sub
    ndarrays.  if step = time_steps there is no overlap. Updated from original
    in e4_get_X_y_sub to accept list of features."""
    N_FEATURES = len(features)
    segments = []
    labels = []
    subject = []
    for i in range(0, len(df) - time_steps, step):
        #df_segX = df[['accel_x', 'accel_y', 'accel_z','accel_ttl']].iloc[i: i + time_steps]
        df_segX = df[features].iloc[i: i + time_steps]
        df_lbl = df['label'].iloc[i: i + time_steps]
        df_sub = df['sub'].iloc[i: i + time_steps]
        # Save only if labels are the same for the entire segment and valid
        if (df_lbl.value_counts().iloc[0] != time_steps):
            #print('Segment starting at',i,'contains multiple labels.  Discarding.')
            continue

        if 0 in df_lbl.values :
            #print('Segment starting at',i,'contains Undefined labels.  Discarding')
            continue
        # Save only if sub is the same for the entire segment and valid
        if (df_sub.value_counts().iloc[0] != time_steps):
            #print('Segment starting at',i,'contains multiple subjects.  Discarding.')
            continue
        segments.append(df_segX.to_numpy())
        labels.append(df['label'].iloc[i])
        subject.append(df['sub'].iloc[i])
        #this still requires high memory instance on colab.
        #del [[df_segX,df_lbl,df_sub]]
        del df_segX
        del df_lbl
        del df_sub
        gc.collect

    # Bring the segments into a better shape, convert to nparrays
    reshaped_segments = np.asarray(segments, dtype= np.float32).reshape(-1, time_steps, N_FEATURES)
    labels = np.asarray(labels)
    subject = np.asarray(subject)
    # both labels and sub are row arrays, change to single column arrays
    labels = labels[np.newaxis].T
    subject = subject[np.newaxis].T
    # check for nan - issue with resampled data
    bad_data_locations = np.argwhere(np.isnan(reshaped_segments))
    np.unique(bad_data_locations[:,0]) #[:,0] accesses just 1st column
    if (bad_data_locations.size==0):
        print("No NaN entries found")
    else:
        print("Warning: Output arrays contain NaN entries")
        print("execute print(X[99]) # to view single sample")
    return reshaped_segments, labels, subject

def get_X_y_sub(
    # you probably need to change this path to your google drive mount
    orig_zipfile = '/content/drive/My Drive/Datasets/ADL_Leotta_2021.zip',
    working_dir='/content/temp', # this directory will be created inside colab
    time_steps = 0, #TODO - the timesteps do not propagate, set to 300 & 300
    step = 0 #if equal to time_steps there will be no overlap of sliding window
    ):
    """processes dataset zip file to extract csv file and convert into X (data),
     y (labels), and sub (subject number) ndarrays.
     Returns X, y, sub, xys_info (a text file)
    """
    unzip_leotta(orig_zipfile = orig_zipfile, working_dir = working_dir)
    xys_info = 'not setup for Leotta dataset'
    for i in range(1,9):
        print('Processing subject number', i)
        df_temp = df_from_one_sub (sub_num = i)
        feature_list = list(df_temp.columns)
        feature_list.remove('label')
        feature_list.remove('sub')
        print("Using",len(feature_list),'features',feature_list)
        my_X, my_y, my_sub = split_df_to_timeslice_nparrays(df_temp, feature_list, 300, 300)
        if i==1:
            X = my_X
            y = my_y
            sub = my_sub
        else:
            X = np.vstack([X, my_X])
            y = np.vstack([y, my_y])
            sub = np.vstack([sub, my_sub])
        print(get_shapes([X, y, sub]))
    return X, y, sub, xys_info

if __name__ == "__main__":
    print("Processing dataset zip files and label csv into X, y, sub ndarrays")
    X, y, sub, xys_info = get_X_y_sub()
    print("X shape ",X.shape,"dtype = ",X.dtype)
    print("y shape ",y.shape,"dtype = ",y.dtype)
    print("sub shape ",sub.shape,"dtype = ",sub.dtype)

"""# Save files to drive"""

if False: #change to True to save files
    xys_info = 'Early output, needs logging updates'
    output_dir = '/content/drive/MyDrive/Processed_Datasets/leotta/original'
    if (os.path.isdir(output_dir)):
        #quick check for existing files, '.ipynb_checkpoints' file 
        #makes it more complicated to see if directory is empty
        if (not os.path.isfile(output_dir + '/X.npy')):
            summary = "Leotta hand/wrist/ankle data\n"
            summary += "Saved to " + output_dir + "\n"
            summary += "Generated by " + what_is_my_name() 
            summary += " on " + time.strftime('%b-%d-%Y_%H%M', time.localtime())

            info_fname = output_dir +'/'+'info.txt'
            full_info = summary + "\n" + xys_info + "\n"
            print(full_info)

            with open(info_fname, "w") as file_object:
                file_object.write(full_info)

            if True:
                np.save(output_dir + '/'+'X.npy',X)
                np.save(output_dir + '/'+'y.npy',y)
                np.save(output_dir + '/'+'sub.npy',sub)
        else:
            print("Error "+output_dir+" contains X.npy, please delete files")
    else:
        print(output_dir + " not found, please create directory")

if interactive:
    # This labeling does not work - also not 100% sure strings are better.
    ALPHA_LABEL = ['OTHER','RELAX','KEYBOARD_WRITING','LAPTOP','HANDWRITING',
                'HANDWASHING','FACEWASHING','TEETHBRUSH','SWEEPING','VACUUMING',
                'EATING','DUSTING','RUBBING','DOWNSTAIRS','WALKING',
                'WALKING_FAST','UPSTAIRS_FAST','UPSTAIRS'] # from README.txt
    for i in range(18):
        print(i,ALPHA_LABEL[i])
    print(ALPHA_LABEL[2])
    print (df_temp.loc[df_temp.index[4000],'label'])
    print (ALPHA_LABEL[df_temp.loc[df_temp.index[4000],'label']])
    #arrggghhh
    #df_temp['alpha_label'] = df_temp.apply(lambda row: ALPHA_LABEL[df_temp.loc[df_temp.index[row],'label']], axis=1)
    #df['add'] = df.apply(lambda row : add(row['A'],row['B'], row['C']), axis = 1)
    #df_temp['alpha_label'] = df_temp.apply(lambda row : ALPHA_LABEL[row['index']], axis = 1)
    #df_temp['alpha_label'] = ALPHA_LABEL[df_temp['label']]
    #df_temp.head()

"""#More exploratory code for ndarrays - should probably be own notebook"""

if interactive:
    #show number of samples per subject
    unique_elements, counts_elements = np.unique(sub, return_counts=True)
    print(" subject #",int(unique_elements[np.argmin(counts_elements)]),
        "has ",np.amin(counts_elements)," samples (min)\n",
        "subject #",int(unique_elements[np.argmax(counts_elements)]),
        "has ",np.amax(counts_elements)," samples (max)\n")
    print("Sample count per subject:")
    print(np.asarray((unique_elements, counts_elements)))

def plot_subjects():
    uniques, s_num = np.unique(sub, return_inverse=True)
    print (uniques)
    plt.plot(s_num) 
    plt.show()
if interactive:    
    plot_subjects()

if interactive:
    #Find min and max values for consistent plot scales
    min_g = np.nanmin(X[::1])
    max_g = np.nanmax(X[::1])
    print ('min g value is',min_g,'max g value is',max_g)

if interactive:
    #Plot a sample
    #sample_num = 100 # activity is 3 using laptop - values are very small
    sample_num = 500 # activity is 14 walking fast - more typical plot
    plt.figure(figsize=(20,5))
    plt.ylim([min_g/2, max_g/2])
    plt.plot(X[sample_num])
    plt.title('sample '+str(sample_num)+' subject '+str(int(sub[sample_num,0]))+' activity '+str(y[sample_num]))
    plt.xlabel("time step")
    plt.ylabel("accel")
    plt.show()