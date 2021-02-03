# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 17:20:59 2020
Modified on Fr May 15 10:50:00 2020

@author: mayer, licklederer (TUM)
"""


from createBuilding import create_Server_Basics, create_Namespace, add_General, add_Demand, add_VolatileProducer, add_Coupler, add_Producer, add_Storage

import time
import numpy as np
import json
import random

from scipy.interpolate import splrep, splev
import matplotlib.pyplot as plt

# General Information:
objectName = "CoSES"
opc_port = "4850"

# TIMING
mpc = 5  # number of mpc horizont steps, usually 5-48
mpc_time_factor = 0.25  # time factor as ratio of hours,
    # determining the time different between steps, 0.25 = 15 min
profile_time_factor = 0.25  # time factor as ratio of hours,
    # for time difference between read values from profile, 0.25 = 15 min
CoSES_time_factor = 1 / 120  # time factor as ratio of hours,
    # for wished time difference for CoSES-Demand-Values, 1/60 = 1 min
simulation_time_factor = 30  # 1 s in simulation time equals X seconds in real time

nrOfEms = 1

demandPath  =   "FC_data_series/Test1_Last.csv"
pricePath    =   "FC_data_series/Test1_Preise.csv"
interp_type = "spline" # alternatives: "step", "linear", "spline",


# Add Counter list/array to count for number of EMS x Device Types and construct display names
# Entries for DEMND, PROD, VPROD, COUPL, STRGE
counter = np.zeros([nrOfEms,5])
myNodeIDcntr = 100
#print(counter)

# ================= Defining the Namespace of the Building =====================

# ============================== EMS 1 - General ==============================
EMS = "EMS01"
(server1, url1, idx, objects) = create_Server_Basics(objectName, EMS, opc_port)
(General, Demand, Devices, Producer, VolatileProducer, Coupler, Storage) = create_Namespace(idx, objects)
naming = objectName + EMS + "OBJ01"

# add_General
(myNodeIDcntr, EMSnameID, Trigger) = add_General(idx, myNodeIDcntr, naming, General, "SFH1")


# ============================== EMS 1 - Devices ==============================
# (Add Demand, Producer, Volatile Producer, Coupler, Storage)

### add_Demand
(myNodeIDcntr, heatDemandSP, htDemFCarray) = add_Demand(counter, naming, idx, myNodeIDcntr, Demand,
                                                        "heat", "Wärmebedarf_Haus1", mpc)

### Devices
# add_Producer
(myNodeIDcntr, Prod1_Power, Prod1_Setpoint, Prod1_priceFC) = add_Producer(counter, naming, mpc, idx,
                                                            myNodeIDcntr, "SFH1_EB1", Producer, "heat",
                                                            0.88, 5, 14, 0.07, 0.202)

# add_Storage
(myNodeIDcntr, Stor1_setpointChgFC, Stor1_setpointDisChgFC, Stor1_SOC, Stor1_calcSOC) = add_Storage(counter, naming,
                                                mpc, idx, myNodeIDcntr,
                                                "SFH1_TS1", Storage, "heat", 0.97, 0.97, 36.1, 24, 56, 56, 18.05)

# =========================================================================

# ==================== Load demand from file ========================
# reading
Consumption_B1 = np.genfromtxt(demandPath, delimiter="\n")
size = np.shape(Consumption_B1)[0]
# scaling
#demand1_old_max = np.max(Consumption_B1)
#demand1_max_set = 14
#demand1_scaled = Consumption_B1 * (demand1_max_set / demand1_old_max)
#demand1_max = np.max(demand1_scaled)
#print("scaled max. demand: ", demand1_max)
demand1_scaled = Consumption_B1
# interpolating
delta_t_profile = profile_time_factor * 60  # in min
delta_t_mpc = mpc_time_factor * 60  # in min
delta_t_CoSES = CoSES_time_factor * 60  # in min
timeline_profile = np.arange(0, delta_t_profile * (size), delta_t_profile)
timeline_mpc = np.arange(0, delta_t_profile * (size), delta_t_mpc)
timeline_CoSES = np.arange(0, delta_t_profile * (size), delta_t_CoSES)

if interp_type == "spline":
    mydegree = 5
    tck1 = splrep(timeline_profile, demand1_scaled, k=mydegree, s=0)
    demand1_interp_mpc = splev(timeline_mpc, tck1, ext=3)
    demand1_interp_CoSES = splev(timeline_CoSES, tck1, ext=3)
elif interp_type == "linear":
    mydegree = 1
    tck1 = splrep(timeline_profile, demand1_scaled, k=mydegree, s=0)
    demand1_interp_mpc = splev(timeline_mpc, tck1, ext=3)
    demand1_interp_CoSES = splev(timeline_CoSES, tck1, ext=3)
elif interp_type == "step":
    nbr_reps_mpc = int(delta_t_profile/delta_t_mpc)
    demand1_interp_mpc = np.array([np.repeat(step,nbr_reps_mpc) for step in demand1_scaled]).flatten()
    nbr_reps_CoSES = int(delta_t_profile / delta_t_CoSES)
    demand1_interp_CoSES = np.array([np.repeat(step, nbr_reps_CoSES) for step in demand1_scaled]).flatten()
else:
    raise ValueError('wrong value for interp_type')

nbr_reps_mpc_plot = int(delta_t_profile/delta_t_CoSES)
demand1_interp_mpc_plot = np.array([np.repeat(step,nbr_reps_mpc_plot) for step in demand1_interp_mpc]).flatten()

fig1=plt.figure(num='heat demand', figsize=[8.3, 5.8], dpi=300.0)
plt.plot(timeline_CoSES/60, demand1_interp_CoSES, label="interpolated reality", linestyle="-")
plt.plot(timeline_CoSES/60, demand1_interp_mpc_plot, label="mpc", linestyle="-", color = 'g')
plt.plot(timeline_mpc/60, demand1_interp_mpc, label="mpc write", marker="o", linestyle="none", color = 'g')
plt.plot(timeline_profile/60, demand1_scaled, label="original measurement", marker="x", linestyle="none", color = 'k')
plt.legend()
plt.title('heat demand')
plt.xlabel('time [hours]')
plt.ylabel('power [kW]')
#plt.show(block=False)
fig1.savefig('heat_demand.png')



# ==================== Load prices from file ========================
# reading
dynamic_prices = np.genfromtxt(pricePath, delimiter="\n")
size = np.shape(dynamic_prices)[0]
# interpolating
delta_t_profile = profile_time_factor * 60  # in min
delta_t_mpc = mpc_time_factor * 60  # in min

nbr_reps_mpc = int(delta_t_profile / delta_t_mpc)
prices_interp_mpc = np.array([np.repeat(step, nbr_reps_mpc) for step in dynamic_prices]).flatten()
nbr_reps_mpc_plot = int(delta_t_profile / delta_t_CoSES)
prices_interp_mpc_plot = np.array([np.repeat(step, nbr_reps_mpc_plot) for step in dynamic_prices]).flatten()

fig2 =plt.figure(num='gas price', figsize=[8.3, 5.8], dpi=300.0)
plt.plot(timeline_CoSES[nbr_reps_mpc_plot:]/60, prices_interp_mpc_plot[nbr_reps_mpc_plot:],
         label="mpc", linestyle="-", color = 'g')
plt.plot(timeline_mpc[1:]/60, prices_interp_mpc[1:],
         label="mpc write", marker="o", linestyle="none", color = 'g')
plt.plot(timeline_profile[1:]/60, dynamic_prices[1:],
         label="original measurement", marker="x", linestyle="none", color = 'k')
plt.legend()
plt.title('gas price')
plt.xlabel('time [hours]')
plt.ylabel('price [€]')
#plt.show(block=False)
fig2.savefig('gas_price.png')

def forecast_to_json(FC_step, timefactor, FC_array):
    Forecast = {}
    for j in range(FC_step-1):
        Str = 'Forecast_t' + str(60*timefactor*(j+1))
        Forecast[Str] = str(FC_array[j].get_value())
    return json.dumps(Forecast)

# =============================== Start ===================================
server1.start()
print("Server " + naming + " started at {}".format(url1))
server1.PublishingEnabled = True

# =========================================================================
# Export Namespace as XML
server1.export_xml(Devices.get_children(), "CoSES_Server_raw.xml")
server1.export_xml_by_ns("CoSES_Server_full.xml")

# ============================= wait =================================
myinput = input('Press enter to start experiment!')

while myinput != '':
    pass
t = time.localtime()
current_time = time.strftime("%d.%m.%Y, %H:%M:%S", t)

print('############## EXPERIMENT STARTED: ', current_time, ' ##############')

# ============================= set values =================================

delta_t_for_setting_CoSES = 60 * delta_t_CoSES / simulation_time_factor  # in seconds
print('delta_t_for_setting_CoSES: ', delta_t_for_setting_CoSES)
delta_t_for_setting_MEMAP = 60 * delta_t_mpc / simulation_time_factor  # in seconds
print('delta_t_for_setting_MEMAP: ', delta_t_for_setting_MEMAP)
timing_delta1 = 0
timing_delta2 = 0
i = 0
k = 0
l = 0
while True:
    if i == 0:
        mytime1 = time.monotonic()-delta_t_for_setting_MEMAP
        mytime2 = time.monotonic()-delta_t_for_setting_CoSES
        i += 1

    timing_delta1 = time.monotonic() - mytime1
    timing_delta2 = time.monotonic() - mytime2

    if timing_delta1 >= delta_t_for_setting_MEMAP:
        print('MEMAP alle ', timing_delta1, ' Sekunden =  alle ',
              timing_delta1*simulation_time_factor, " Sekunden Realzeit")
        mytime1 = time.monotonic()
        timing_delta1 = 0

        ## write MEMAP values
        # in cycle

        Trigger.set_value(k)

        if k%(np.shape(demand1_interp_mpc)[0])<=np.shape(demand1_interp_mpc)[0]-mpc:
            mycntr = k%(np.shape(demand1_interp_mpc)[0])
            myforecast = [demand1_interp_mpc[mycntr + x] for x in range(mpc)]
            print('demand forecast: ', myforecast, ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            htDemFCarray.set_value(myforecast)

            mypriceforecast = [prices_interp_mpc[mycntr + x] for x in range(mpc)]
            print('price forecast: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
            Prod1_priceFC.set_value(mypriceforecast)

            # just for tests
            # Stor1_calcSOC.set_value(random.randint(0, 100))
            # Prod1_Setpoint.set_value(myforecast)
            Stor1_SOC.set_value(Stor1_calcSOC.get_value())

        elif k%(np.shape(demand1_interp_mpc)[0]) > np.shape(demand1_interp_mpc)[0]-mpc:
            mycntr = k % (np.shape(demand1_interp_mpc)[0])
            x2 = (k%(np.shape(demand1_interp_mpc)[0])) - (np.shape(demand1_interp_mpc)[0]-mpc)
            x1 = mpc - x2

            myforecast = [demand1_interp_mpc[mycntr+x] for x in range(x1)] +\
                         [demand1_interp_mpc[x] for x in range(x2)]
            print('demand forecast: ', myforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
            htDemFCarray.set_value(myforecast)

            mypriceforecast = [prices_interp_mpc[mycntr+x] for x in range(x1)] +\
                              [prices_interp_mpc[x] for x in range(x2)]
            print('price forecast: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
            Prod1_priceFC.set_value(mypriceforecast)

            # just for tests
            # Stor1_calcSOC.set_value(random.randint(0, 100))
            # Prod1_Setpoint.set_value(myforecast)
            Stor1_SOC.set_value(Stor1_calcSOC.get_value())

        # iterator
        k += 1
        Trigger.set_value(k)


    if timing_delta2 >= delta_t_for_setting_CoSES:
        print('CoSES alle ', timing_delta2, ' Sekunden =  alle ', timing_delta2*simulation_time_factor,
              " Sekunden Realzeit")
        mytime2 = time.monotonic()
        timing_delta2 = 0

        mycntr2 = l%np.shape(demand1_interp_CoSES)[0]
        mynr = (l%np.shape(demand1_interp_CoSES)[0])%(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0])
        # write CoSES values in cycles
        heatDemandSP.set_value(demand1_interp_CoSES[mycntr2])
        print('demand setpoint: ', demand1_interp_CoSES[mycntr2], ', nr.', k, '+ (', int(mynr+1), '/',
              int(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0]),')')

        # just for tests
        Stor1_SOC.set_value(Stor1_calcSOC.get_value())

        l += 1




