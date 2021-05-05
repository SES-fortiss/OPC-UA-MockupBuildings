# -*- coding: utf-8 -*-
"""
Created on Wed April  28 09:43 2020

@author: thomas licklederer (TUM)
"""
from scipy.interpolate import splrep, splev
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
    timeline_profile = np.arange(0+(delta_t_profile/2), delta_t_profile * (size)+(delta_t_profile/2), delta_t_profile)
    #timeline_profile = np.arange(0, delta_t_profile * (size), delta_t_profile)
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

