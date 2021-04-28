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
    timeline = np.arange(0, delta_t * (size), delta_t)

    return profile, timeline

def InterpolateProfile (profile, interp_type, time_factor_profile, time_factor_interp) :

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
        nbr_reps = int(( time_factor_profile * 60 ) / delta_t )
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


# # reading
# Consumption_B1 = np.genfromtxt(demandPath, delimiter="\n")
# size = np.shape(Consumption_B1)[0]
#
# demand1_scaled = Consumption_B1
# # interpolating
# delta_t_profile = profile_time_factor * 60  # in min
# delta_t_mpc = mpc_time_factor * 60  # in min
# delta_t_CoSES = CoSES_time_factor * 60  # in min
# timeline_profile = np.arange(0, delta_t_profile * (size), delta_t_profile)
# timeline_mpc = np.arange(0, delta_t_profile * (size), delta_t_mpc)
# timeline_CoSES = np.arange(0, delta_t_profile * (size), delta_t_CoSES)
#
# if interp_type == "spline":
#     mydegree = 5
#     tck1 = splrep(timeline_profile, demand1_scaled, k=mydegree, s=0)
#     demand1_interp_mpc = splev(timeline_mpc, tck1, ext=3)
#     demand1_interp_CoSES = splev(timeline_CoSES, tck1, ext=3)
# elif interp_type == "linear":
#     mydegree = 1
#     tck1 = splrep(timeline_profile, demand1_scaled, k=mydegree, s=0)
#     demand1_interp_mpc = splev(timeline_mpc, tck1, ext=3)
#     demand1_interp_CoSES = splev(timeline_CoSES, tck1, ext=3)
# elif interp_type == "step":
#     nbr_reps_mpc = int(delta_t_profile/delta_t_mpc)
#     demand1_interp_mpc = np.array([np.repeat(step,nbr_reps_mpc) for step in demand1_scaled]).flatten()
#     nbr_reps_CoSES = int(delta_t_profile / delta_t_CoSES)
#     demand1_interp_CoSES = np.array([np.repeat(step, nbr_reps_CoSES) for step in demand1_scaled]).flatten()
# else:
#     raise ValueError('wrong value for interp_type')
#
# nbr_reps_mpc_plot = int(delta_t_profile/delta_t_CoSES)
# demand1_interp_mpc_plot = np.array([np.repeat(step,nbr_reps_mpc_plot) for step in demand1_interp_mpc]).flatten()
#
# #fig1=plt.figure(num='heat demand', figsize=[8.3, 5.8], dpi=300.0)
# #plt.plot(timeline_CoSES/60, demand1_interp_CoSES, label="interpolated reality", linestyle="-")
# #plt.plot(timeline_CoSES/60, demand1_interp_mpc_plot, label="mpc", linestyle="-", color = 'g')
# #plt.plot(timeline_mpc/60, demand1_interp_mpc, label="mpc write", marker="o", linestyle="none", color = 'g')
# #plt.plot(timeline_profile/60, demand1_scaled, label="original measurement", marker="x", linestyle="none", color = 'k')
# #plt.legend()
# #plt.title('heat demand')
# #plt.xlabel('time [hours]')
# #plt.ylabel('power [kW]')
# #plt.show(block=False)
# #fig1.savefig('heat_demand.png')
#
# # reading
# dynamic_prices = np.genfromtxt(pricePath, delimiter="\n")
# size = np.shape(dynamic_prices)[0]
# # interpolating
# delta_t_profile = profile_time_factor * 60  # in min
# delta_t_mpc = mpc_time_factor * 60  # in min
#
# nbr_reps_mpc = int(delta_t_profile / delta_t_mpc)
# prices_interp_mpc = np.array([np.repeat(step, nbr_reps_mpc) for step in dynamic_prices]).flatten()
# nbr_reps_mpc_plot = int(delta_t_profile / delta_t_CoSES)
# prices_interp_mpc_plot = np.array([np.repeat(step, nbr_reps_mpc_plot) for step in dynamic_prices]).flatten()
#
# #fig2 =plt.figure(num='gas price', figsize=[8.3, 5.8], dpi=300.0)
# #plt.plot(timeline_CoSES[nbr_reps_mpc_plot:]/60, prices_interp_mpc_plot[nbr_reps_mpc_plot:],
#         # label="mpc", linestyle="-", color = 'g')
# #plt.plot(timeline_mpc[1:]/60, prices_interp_mpc[1:],
#         # label="mpc write", marker="o", linestyle="none", color = 'g')
# #plt.plot(timeline_profile[1:]/60, dynamic_prices[1:],
#         # label="original measurement", marker="x", linestyle="none", color = 'k')
# #plt.legend()
# #plt.title('gas price')
# #plt.xlabel('time [hours]')
# #plt.ylabel('price [€]')
# #plt.show(block=False)
# #fig2.savefig('gas_price.png')
#
# def forecast_to_json(FC_step, timefactor, FC_array):
#     Forecast = {}
#     for j in range(FC_step-1):
#         Str = 'Forecast_t' + str(60*timefactor*(j+1))
#         Forecast[Str] = str(FC_array[j].get_value())
#     return json.dumps(Forecast)