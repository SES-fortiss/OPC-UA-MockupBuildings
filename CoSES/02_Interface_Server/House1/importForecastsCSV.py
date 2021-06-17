# -*- coding: utf-8 -*-
"""
Created on Wed April  28 09:43 2020

@author: thomas licklederer (TUM)
"""
from scipy.interpolate import splrep, splev, spalde
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


def ImportFromCSV (sourcepath, mydelimiter, time_factor):

    profile =  np.genfromtxt(sourcepath, delimiter=mydelimiter)
    size = np.shape(profile)[0]
    delta_t = time_factor * 60  # in min
    timeline = np.arange(0+(delta_t/2), delta_t * (size)+(delta_t/2), delta_t)

    return profile, timeline

def InterpolateProfileCoSES (profile, interp_type, time_factor_profile, time_factor_interp) :

    size = np.shape(profile)[0]
    delta_t_profile = time_factor_profile * 60 # in min
    delta_t_interp= time_factor_interp * 60 # in min
    #timeline_profile = np.arange(0+(delta_t_profile/2), delta_t_profile * (size)+(delta_t_profile/2), delta_t_profile)
    #timeline_profile = np.arange(0, delta_t_profile * (size), delta_t_profile)
    timeline_interp = np.arange(0, delta_t_profile * (size), delta_t_interp)


    if interp_type == "spline":
        mydegree = 5
        #tck = splrep(timeline_profile, profile, k=mydegree, s=0)
        #profile_interp = splev(timeline_interp, tck, ext=3)
        X = np.arange(0, delta_t_profile * 3*(size), delta_t_profile)
        timeline_interp2 = np.arange(0, delta_t_profile *3 * (size), delta_t_interp)
        avg = np.concatenate((profile, profile, profile))
        tck = mean_pres_spline(X, avg, mydegree)
        interpolated = splev(timeline_interp2, tck, der=1, ext=0)
        profile_interp = interpolated[int(delta_t_profile/delta_t_interp)*size:(2*int(delta_t_profile/delta_t_interp)*size)]


    elif interp_type == "linear":
        timeline_profile = np.arange(0 + (delta_t_profile / 2), delta_t_profile * (size) + (delta_t_profile / 2),
                                     delta_t_profile)
        mydegree = 1
        tck = splrep(timeline_profile, profile, k=mydegree, s=0)
        profile_interp = splev(timeline_interp, tck, ext=3)

    elif interp_type == "step":
        nbr_reps = int( time_factor_profile / time_factor_interp )
        profile_interp = np.array([np.repeat(step, nbr_reps) for step in profile]).flatten()

    else:
        raise ValueError('wrong value for interp_type')

    profile_interp = [x if x >= 0 else np.float64(0.0) for x in profile_interp]

    return profile_interp, timeline_interp

def InterpolateProfileMEMAP (profile, interp_type, time_factor_profile, time_factor_interp) :

    size = np.shape(profile)[0]
    delta_t_profile = time_factor_profile * 60 # in min
    delta_t_interp= time_factor_interp * 60 # in min
    timeline_profile = np.arange(0, delta_t_profile * (size), delta_t_profile)
    timeline_interp = np.arange(0, delta_t_profile * (size), delta_t_interp)


    if interp_type == "spline":
        mydegree = 5
        tck = splrep(timeline_profile, profile, k=mydegree, s=0)
        profile_interp = splev(timeline_interp, tck, ext=3)

    elif interp_type == "linear":
        mydegree = 1
        tck = splrep(timeline_profile, profile, k=mydegree, s=0)
        profile_interp = splev(timeline_interp, tck, ext=3)

    elif interp_type == "step":
        nbr_reps = int( time_factor_profile / time_factor_interp )
        profile_interp = np.array([np.repeat(step, nbr_reps) for step in profile]).flatten()

    else:
        raise ValueError('wrong value for interp_type')

    profile_interp = [x if x >= 0 else np.float64(0.0) for x in profile_interp]


    return profile_interp, timeline_interp




def PlotProfile (profile, timeData, name, ylabel, savepath):

    fig1=plt.figure(num=name, figsize=[8.3, 5.8], dpi=400.0)
    plt.plot(timeData, profile, linestyle="-", color = 'k')
    plt.title(name)
    plt.xlabel('')
    plt.ylabel(ylabel)
    plt.show(block=False)
    whattimeisit = datetime.now()
    now_string = whattimeisit.strftime("%Y%m%d_%H%M%S")
    filename = savepath + "/" + name + "_" + now_string + ".png"
    fig1.savefig(filename)
    print("Plot was saved.")

    return 0

def Profile2Forecast (profile, startindex, horizon):

    Forecast = list(profile[startindex:(startindex+horizon)])

    return Forecast

def mean_pres_spline (X, avg, mydegree): # according to https://kluge.in-chemnitz.de/opensource/spline/

    Y = np.zeros(len(X))

    for i in range(len(X)):
        Y[i] = Y[i-1] + avg[i-1] * (X[i]-X[i-1])

    tck = splrep(X, Y, k=mydegree, s=1)
    #integral_interp = splev(X, tck, ext=3)
    # interpolated = spalde(X, tck)

    return tck