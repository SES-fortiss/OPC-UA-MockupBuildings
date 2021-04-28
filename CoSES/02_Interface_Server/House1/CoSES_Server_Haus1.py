# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 17:20:59 2020
Modified on Fr May 15 10:50:00 2020

@author: licklederer (TUM), mayer (fortiss)
"""


from createBuilding import *

import time
import numpy as np
import json
import random

from scipy.interpolate import splrep, splev
import matplotlib.pyplot as plt

from importForecastsCSV import *



# General Information:
objectName = "CoSES"
opc_port = "4851"

# TIMING
mpc = 5  # number of mpc horizont steps, usually 5-48
mpc_time_factor = 0.25  # time factor as ratio of hours,
    # determining the time different between steps, 0.25 = 15 min
profile_time_factor = 0.25  # time factor as ratio of hours,
    # for time difference between read values from profile, 0.25 = 15 min
CoSES_time_factor = 1 / 60  # time factor as ratio of hours,
    # for wished time difference for CoSES-Demand-Values, 1/60 = 1 min
simulation_time_factor = 60  # 1 s in simulation time equals X seconds in real time
karenzzeit = max(int(0.02*mpc_time_factor*(1/simulation_time_factor)*3600),3) # sekunden

nrOfEms = 1

demandPath  =   "FC_data_series/Test1_Last.csv"
pricePath    =   "FC_data_series/Test1_Preise.csv"
interp_type = "spline" # alternatives: "step", "linear", "spline",
plot_forecasts = False


# Add Counter list/array to count for number of EMS x Device Types and construct display names
# Entries for DEMND, PROD, VPROD, COUPL, STRGE
counter = np.zeros([nrOfEms,7])
myNodeIDcntr = 100


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
print("\n")
### add_Demand
(myNodeIDcntr, counter, DMND01_DemandSetPt, DMND01_demandFC, DMND01_currDemand,
    DMND01_GrdBuyCost, DMND01_GrdSellCost, DMND01_GrdBuy, DMND01_GrdSell,
    DMND01_curPriceBuy, DMND01_curPriceSell, DMND01_GrdBuyCO2, DMND01_GrdSellCO2,
    DMND01_curCO2Buy, DMND01_curCO2Sell) = add_Demand(
    counter, naming, idx, myNodeIDcntr, Demand, "heat", "Wärmebedarf_Haus1", mpc)


(myNodeIDcntr, counter, DMND02_DemandSetPt, DMND02_demandFC, DMND02_currDemand,
    DMND02_GrdBuyCost, DMND02_GrdSellCost, DMND02_GrdBuy, DMND02_GrdSell,
    DMND02_curPriceBuy, DMND02_curPriceSell, DMND02_GrdBuyCO2, DMND02_GrdSellCO2,
    DMND02_curCO2Buy, DMND02_curCO2Sell) = add_Demand(
    counter, naming, idx, myNodeIDcntr, Demand, "elec", "Strombedarf_Haus1", mpc)

### Devices
# add_Producer
# (myNodeIDcntr, CPROD1_production, CPROD1_GenCosts, CPROD1_CO2PerKWh, CPROD1_SPDevPwr,
#       CPROD1curPrice, CPROD1curCO2costs) = add_Producer(counter, naming, mpc, idx,
#                myNodeIDcntr, "SFH1_EB1", Producer, "heat", 0.88, 5, 14)

# add_coupler
(myNodeIDcntr, BHKW_Prod1, BHKW_Prod2, BHKW_GenCosts, BHKW_CO2PerKWh, BHKW_SPDevPwr,
    BHKWcurPrice, BHKWcurCO2costs) = add_Coupler(
     counter, naming, idx, myNodeIDcntr, 'SFH1_BHKW', Coupler, 'heat', 'elec', 0.723, 0.278, 4.9, 5.1, mpc)

# add_Storage 
(myNodeIDcntr, STOR1_SOC, STOR1_calcSOC, STOR1_setpointChg, STOR1_setpointDisChg) = add_Storage(counter, naming,
                                                mpc, idx, myNodeIDcntr,
                                                "SFH1_TS1", Storage, "heat", 0.97, 0.97, 36.1, 24, 56, 56, 18.05)




# ========= Load forecasts from file ======================================

demand1_profile, demandtime_profile = ImportFromCSV (demandPath, "\n", profile_time_factor)
demand1_MEMAP, demandtime_MEMAP = InterpolateProfile (demand1_profile, interp_type, profile_time_factor, mpc_time_factor)
demand1_CoSES, demandtime_CoSES = InterpolateProfile (demand1_profile, interp_type, profile_time_factor, CoSES_time_factor)

price1_profile, pricetime_profile = ImportFromCSV (pricePath, "\n", profile_time_factor)
price1_MEMAP, pricetime_MEMAP = InterpolateProfile (price1_profile, interp_type, profile_time_factor, mpc_time_factor)


if plot_forecasts:

    PlotProfile(demand1_profile, demandtime_profile, "demand1", "kW", "figures")
    PlotProfile(demand1_MEMAP, demandtime_MEMAP, "demand1_MEMAP", "kW", "figures")
    PlotProfile(demand1_CoSES, demandtime_CoSES, "demand1_CoSES", "kW", "figures")
    PlotProfile(price1_profile, pricetime_profile, "price1", "€/kWh", "figures")
    PlotProfile(price1_MEMAP, pricetime_MEMAP, "price1_MEMAP", "€/kWh", "figures")


# =============================== Start ===================================
# ============================= scheme =================================
# Standby
# 1.    Server provides forecasts for steps [0,1,2,3,4] for MEMAP, nothing for CoSES

# Initialization
# 2.    MEMAP triggers, reads forecasts (nothing to write)
# 3.    Server waits a few seconds (kadenz of 5-20 seconds) to give MEMAP time to read
# 4.a.  Server updates forecasts for steps [1,2,3,4,5] for MEMAP
# 4.b.  MEMAP optimizes for [0,1,2,3,4] and waits for next step (e.g. next 15 minutes)

# Step 0
# 5.a.  MEMAP writes setpoints for devices to Server for steps [0,1,2,3,4],
#       triggers and reads forecasts from Server for [1,2,3,4,5]
# 5.b.  Server provides demand setpoints to CoSES for steps [0, 0.01, 0.02, ... 0.98, 0.99],
#       CoSES executes these demand setpoints and MEMAP setpoint for [0]
# 6.    Server waits a few seconds (kadenz of 5-20 seconds) to give MEMAP time to read
# 7.a.  Server updates forecasts for steps [2,3,4,5,6] for MEMAP
# 7.b.  MEMAP optimizes for [1,2,3,4,5] and waits for next step (e.g. next 15 minutes)

# Step 1
# 8.a.  MEMAP writes setpoints for devices to Server for steps [1,2,3,4,5],
#       triggers and reads forecasts from Server for [2,3,4,5,6]
# 8.b.  Server provides demand setpoints to CoSES for steps [1, 1.01, 1.02, ... 1.98, 1.99],
#       CoSES executes these demand setpoints and MEMAP setpoint for [1]
# 9.    Server waits a few seconds (kadenz of 5-20 seconds) to give MEMAP time to read
# 10.a. Server updates forecasts for steps [3,4,5,6,7] for MEMAP
# 10.b. MEMAP optimizes for [2,3,4,5,6] and waits for next step (e.g. next 15 minutes)
# to be repeated for further steps
# ============================================================================
print("\n### Startup ###")
server1.start()
print("Server " + naming + " started at {}".format(url1))
server1.PublishingEnabled = True

delta_t_for_setting_CoSES = CoSES_time_factor*3600 / simulation_time_factor  # in seconds
print('delta_t_for_setting_CoSES: ', delta_t_for_setting_CoSES, " seconds")
delta_t_for_setting_MEMAP = mpc_time_factor*3600 / simulation_time_factor  # in seconds
print('delta_t_for_setting_MEMAP: ', delta_t_for_setting_MEMAP , " seconds")
time_ratio = int(delta_t_for_setting_MEMAP / delta_t_for_setting_CoSES)
maxsteps = np.size(demand1_profile)
print("### Startup finished ###\n")

# ## Standby --------------------------------------------------------
print("### Prepare for STANDBY ###")
# ## # Iterators / programming stuff
j = 0 # time step since start of experiment
horizon = list(range(0, mpc))
horizon_min_MEMAP = list(np.array(range(j+1, j+1+mpc))*mpc_time_factor*60)

Trigger.set_value(0)
lasttriggertime = time.monotonic()
oldTriggerValue = Trigger.get_value()

demand1_MEMAP_FC = Profile2Forecast (demand1_MEMAP, j, mpc)
price1_MEMAP_FC = Profile2Forecast (price1_MEMAP, j, mpc)
DMND01_demandFC.set_value(demand1_MEMAP_FC)
# DMND02_demandFC.set_value(demand1_MEMAP_FC)
# CPROD1_GenCosts.set_value(price1_MEMAP_FC)
BHKW_GenCosts.set_value(price1_MEMAP_FC)
print(BHKW_GenCosts.get_value())
DMND02_GrdBuyCost.set_value(list(0.30 * np.ones(mpc)))
DMND02_GrdSellCost.set_value(list(0.10 * np.ones(mpc)))

# print
print('demand forecast heat: ', demand1_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
print('demand forecast electricity: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
# print('price forecast gas boiler: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
print('price forecast BHKW: ', list(price1_MEMAP_FC), ', for minutes', horizon_min_MEMAP)
print('price forecast electricity buy: ', list(0.30 * np.ones(mpc)), ', for minutes', horizon_min_MEMAP)
print('price forecast electricity sell: ', list(0.10 * np.ones(mpc)), ', for minutes', horizon_min_MEMAP)

print("### Server in STANDBY ###\n")

# =========================================================================
# Export Namespace as XML
# server1.export_xml(Devices.get_children(), "CoSES_Server_raw.xml")
# server1.export_xml_by_ns("CoSES_Server_full.xml")

# ============================= wait ======================================
myinput = input('-------------PRESS ENTER TO START EXPERIMENT!--------------')

while myinput != '':
    pass
t = time.localtime()
current_time = time.strftime("%d.%m.%Y, %H:%M:%S", t)

print('############## EXPERIMENT STARTED: ', current_time, ' (= minute 0.0) ##############\n')

# ============================= RUNNING Experiment =================================

# ## Initialization ----------------------------------------------------------------
newTriggerValue = oldTriggerValue
while newTriggerValue == oldTriggerValue:
    newTriggerValue = Trigger.get_value()

oldTriggerValue = newTriggerValue
lasttriggertime = time.monotonic()

while time.monotonic() < lasttriggertime + karenzzeit:
    pass
print("### INITIALIZATION ###")
j += 1
k = 99999
updatedone = True
horizon_min_MEMAP = list(np.array(range(j+1, j+1+mpc))*mpc_time_factor*60)
demand1_MEMAP_FC = Profile2Forecast(demand1_MEMAP, j, mpc)
price1_MEMAP_FC = Profile2Forecast(price1_MEMAP, j, mpc)
DMND01_demandFC.set_value(demand1_MEMAP_FC)
# DMND02_demandFC.set_value(demand1_MEMAP_FC)
# CPROD1_GenCosts.set_value(price1_MEMAP_FC)
BHKW_GenCosts.set_value(price1_MEMAP_FC)
DMND02_GrdBuyCost.set_value(list(0.30 * np.ones(mpc)))
DMND02_GrdSellCost.set_value(list(0.10 * np.ones(mpc)))

# print
print('demand forecast heat: ', demand1_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
print('demand forecast electricity: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
# print('price forecast gas boiler: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
print('price forecast BHKW: ', list(price1_MEMAP_FC), ', for minutes', horizon_min_MEMAP)
print('price forecast electricity buy: ', list(0.30 * np.ones(mpc)), ', for minutes', horizon_min_MEMAP)
print('price forecast electricity sell: ', list(0.10 * np.ones(mpc)), ', for minutes', horizon_min_MEMAP)
print("### INITIALIZATION DONE ###\n")

# ## Loop ---------------------------------------------------------------------------
while True:
    newTriggerValue = Trigger.get_value()

    if newTriggerValue != oldTriggerValue:
        oldTriggerValue = newTriggerValue
        lasttriggertime = time.monotonic()
        print("### LOOP ", j, " ###")
        j += 1
        k = 0 # number of iteration during timestep
        updatedone = False
        horizon_min_MEMAP = list(np.array(range(j+1, j+1+mpc))*mpc_time_factor*60)

        print("\n")

    else:
        pass

    if j%maxsteps <= maxsteps - mpc: # normal experiment, no repetition so far
        j = j % maxsteps
        if (time.monotonic() > lasttriggertime + karenzzeit) and not updatedone:
            # update forecasts
            demand1_MEMAP_FC = Profile2Forecast(demand1_MEMAP, j, mpc)
            price1_MEMAP_FC = Profile2Forecast(price1_MEMAP, j, mpc)
            DMND01_demandFC.set_value(demand1_MEMAP_FC)
            # DMND02_demandFC.set_value(demand1_MEMAP_FC)
            # CPROD1_GenCosts.set_value(price1_MEMAP_FC)
            BHKW_GenCosts.set_value(price1_MEMAP_FC)
            DMND02_GrdBuyCost.set_value(list(0.30*np.ones(mpc)))
            DMND02_GrdSellCost.set_value(list(0.10*np.ones(mpc)))

            # only for debugging tests!!!
            STOR1_SOC.set_value(STOR1_calcSOC.get_value())

            # print
            print('demand forecast heat: ', demand1_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            print('demand forecast electricity: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
            # print('price forecast gas boiler: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
            print('price forecast BHKW: ', list(price1_MEMAP_FC), ', for minutes', horizon_min_MEMAP)
            print('price forecast electricity buy: ', list(0.30*np.ones(mpc)), ', for minutes', horizon_min_MEMAP)
            print('price forecast electricity sell: ', list(0.10 * np.ones(mpc)), ', for minutes', horizon_min_MEMAP)

            updatedone = True

            print("\n")

    elif j%maxsteps > maxsteps - mpc:   # run experiment in cycles, repeat the profiles from beginning
        j = j%maxsteps
        x2 = j - (maxsteps-mpc)
        x1 = mpc - x2
        # print('!!!!!!!!!!!!!!!!!!!!!!!!!!!noW!!!!!!!!!!!!!!!!!')
        if (time.monotonic() > lasttriggertime + karenzzeit) and not updatedone:
            # update forecasts
            demand1_MEMAP_FC = Profile2Forecast(demand1_MEMAP, j, x1)+Profile2Forecast(demand1_MEMAP, 0, x2)
            price1_MEMAP_FC = Profile2Forecast(price1_MEMAP, j, x1)+Profile2Forecast(price1_MEMAP, 0, x2)
            DMND01_demandFC.set_value(demand1_MEMAP_FC)
            # DMND02_demandFC.set_value(demand1_MEMAP_FC)
            # CPROD1_GenCosts.set_value(price1_MEMAP_FC)
            BHKW_GenCosts.set_value(price1_MEMAP_FC)
            DMND02_GrdBuyCost.set_value(list(0.30 * np.ones(mpc)))
            DMND02_GrdSellCost.set_value(list(0.10 * np.ones(mpc)))

            # only for debugging tests!!!
            STOR1_SOC.set_value(STOR1_calcSOC.get_value())

            # print
            print('demand forecast heat: ', demand1_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            print('demand forecast electricity: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
            # print('price forecast gas boiler: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
            print('price forecast BHKW: ', list(price1_MEMAP_FC), ', for minutes', horizon_min_MEMAP)
            print('price forecast electricity buy: ', list(0.30 * np.ones(mpc)), ', for minutes', horizon_min_MEMAP)
            print('price forecast electricity sell: ', list(0.10 * np.ones(mpc)), ', for minutes', horizon_min_MEMAP)

            updatedone = True

            print("\n")

    if j < 2:
        l = maxsteps + (j-2)
    else:
        l = j

    if k == 0: # first iteration in timestep
        print(j)
        print(k)
        print(l)
        print("index ", ((l-2)*time_ratio)+k)
        # CoSES demand setpoints
        DMND01_DemandSetPt.set_value(demand1_CoSES[((l-2)*time_ratio)+k])
        #DMND02_DemandSetPt.set_value(0.0)
        refminute_CoSESset = (((l-1)*time_ratio)+k)*60*CoSES_time_factor
        refminute_CoSESset2 = (((l-1)*time_ratio)+k+1)*60*CoSES_time_factor

        # Boundary Conditions
        refmin_bounds = horizon_min_MEMAP[0]-2*(60*mpc_time_factor)
        refmin_bounds2 = horizon_min_MEMAP[0]-1*(60*mpc_time_factor)
        BHKWcurPrice.set_value(price1_MEMAP[l-1])
        DMND02_curPriceBuy.set_value(30.0)
        DMND02_curPriceSell.set_value(10.0)
        # CPROD1curPrice.set_value(0.0)

        # print
        print('demand setpoint CoSES heat: ', demand1_CoSES[((j-2)*time_ratio)+k], ', for minute ', refminute_CoSESset, 'to ', refminute_CoSESset2)
        print('demand setpoint CoSES electricity: ', 0.0, ', for minute ', refminute_CoSESset, 'to ', refminute_CoSESset2)
        print("\n")
        print('current price gas BHKW: ', price1_MEMAP[j-2], ', for minute ', refmin_bounds, 'to ', refmin_bounds2)
        print('current price electricity buy: ', 30.0, ', for minute ', refmin_bounds, 'to ', refmin_bounds2)
        print('current price electricity sell: ', 10.0, ', for minute ', refmin_bounds, 'to ', refmin_bounds2)
        # print('current price gas boiler: ', 0.0, ', for minute ', refmin_bounds, 'to ', refmin_bounds2)

        #iterator
        k+=1

        print("\n")

    elif (time.monotonic() > lasttriggertime + (k * delta_t_for_setting_CoSES)) & (k < time_ratio):
        # iterations in timestep

        # CoSES demand setpoints
        # CoSES demand setpoints
        DMND01_DemandSetPt.set_value(demand1_CoSES[((j-2)*time_ratio)+k])
        #DMND02_DemandSetPt.set_value(0.0)
        refminute_CoSESset = (((j-1)*time_ratio)+k)*60*CoSES_time_factor
        refminute_CoSESset2 = (((j-1)*time_ratio)+k+1)*60*CoSES_time_factor

        # print
        print('demand setpoint CoSES heat: ', demand1_CoSES[((j - 2) * time_ratio) + k], ', for minute ',
              refminute_CoSESset, 'to ', refminute_CoSESset2)
        print('demand setpoint CoSES electricity: ', 0.0, ', for minute ', refminute_CoSESset, 'to ',
              refminute_CoSESset2)

        # iterator
        k+=1

        print("\n")

    else:
        pass






# ## Initialization
# k=0
# Trigger.set_value(0)
# oldTriggerValue = Trigger.get_value()
# lasttriggertime = time.monotonic()
# mytime2 = lasttriggertime - delta_t_for_setting_CoSES
# print('MEMAP alle ', delta_t_for_setting_MEMAP, ' Sekunden =  alle ',
#       delta_t_for_setting_MEMAP * simulation_time_factor, " Sekunden Realzeit")
# print('CoSES alle ', delta_t_for_setting_CoSES, ' Sekunden =  alle ', delta_t_for_setting_CoSES*simulation_time_factor,
#               " Sekunden Realzeit")
# myforecast = [demand1_interp_mpc[x] for x in range(mpc)]
# mypriceforecast = [prices_interp_mpc[x] for x in range(mpc)]
# DMND01_demandFC.set_value(myforecast)
# # DMND02_demandFC.set_value(myforecast)
# # DMND02_GrdBuyCost.set_value(list(0.30*np.ones(mpc)))
# # DMND02_GrdSellCost.set_value(list(0.10*np.ones(mpc)))
# # #CPROD1_GenCosts.set_value(mypriceforecast)
# # BHKW_GenCosts.set_value(mypriceforecast)
# print('demand forecast heat: ', myforecast, ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
# print('demand forecast electricity: ', list(np.zeros(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
# print('price forecast electricity buy: ', list(0.30*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
# print('price forecast electricity sell: ', list(0.10*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
# #print('price forecast producer 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
# print('price forecast coupler 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
# done1 = 1
# i = time_ratio+1
# l = 0
# timing_delta1 = 0
# timing_delta2 = 0
# startup = True
#
# ## Loop
#
# while True:
#     newTriggerValue = Trigger.get_value()
#
#     if newTriggerValue != oldTriggerValue:
#         if startup==True:
#             startup = False
#             oldTriggerValue = newTriggerValue
#         else:
#             lasttriggertime = time.monotonic()
#             done1 = 0
#             k+=1
#             mytime2 = lasttriggertime - delta_t_for_setting_CoSES
#             i=0
#             oldTriggerValue = newTriggerValue
#
#     timing_delta1 = time.monotonic() - lasttriggertime
#     timing_delta2 = time.monotonic() - mytime2
#
#     # update forecasts
#     if (timing_delta1 >= karenzzeit) & (done1 == 0):
#
#         lastforecastupdate = time.monotonic()
#
#         if k%(np.shape(demand1_interp_mpc)[0])<=np.shape(demand1_interp_mpc)[0]-mpc:
#             mycntr = k%(np.shape(demand1_interp_mpc)[0])
#             myforecast = [demand1_interp_mpc[mycntr + x] for x in range(mpc)]
#             mypriceforecast = [prices_interp_mpc[mycntr + x] for x in range(mpc)]
#
#             DMND01_demandFC.set_value(myforecast)
#             DMND02_demandFC.set_value(myforecast)
#             DMND02_GrdBuyCost.set_value(list(0.30*np.ones(mpc)))
#             DMND02_GrdSellCost.set_value(list(0.10*np.ones(mpc)))
#             #CPROD1_GenCosts.set_value(mypriceforecast)
#             BHKW_GenCosts.set_value(mypriceforecast)
#             print('demand forecast heat: ', myforecast, ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
#             print('demand forecast electricity: ', list(np.zeros(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
#             print('price forecast electricity buy: ', list(0.30*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
#             print('price forecast electricity sell: ', list(0.10*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
#             #print('price forecast producer 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
#             print('price forecast coupler 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
#
#             # just for tests
#             # Stor1_calcSOC.set_value(random.randint(0, 100))
#             # Prod1_Setpoint.set_value(myforecast)
#             # STOR1_SOC.set_value(STOR1_calcSOC.get_value())
#             print('measured SOC storage 1: ', STOR1_SOC.get_value(), ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
#
#         elif k%(np.shape(demand1_interp_mpc)[0]) > np.shape(demand1_interp_mpc)[0]-mpc:
#             mycntr = k % (np.shape(demand1_interp_mpc)[0])
#             x2 = (k%(np.shape(demand1_interp_mpc)[0])) - (np.shape(demand1_interp_mpc)[0]-mpc)
#             x1 = mpc - x2
#
#             myforecast = [demand1_interp_mpc[mycntr+x +1 ] for x in range(x1)] +\
#                          [demand1_interp_mpc[x] for x in range(x2)]
#             mypriceforecast = [prices_interp_mpc[mycntr+x] for x in range(x1)] +\
#                               [prices_interp_mpc[x] for x in range(x2)]
#
#
#             DMND01_demandFC.set_value(myforecast)
#             DMND02_demandFC.set_value(myforecast)
#             DMND02_GrdBuyCost.set_value(list(0.30*np.ones(mpc)))
#             DMND02_GrdSellCost.set_value(list(0.10*np.ones(mpc)))
#             #CPROD1_GenCosts.set_value(mypriceforecast)
#             BHKW_GenCosts.set_value(mypriceforecast)
#             print('demand forecast heat: ', myforecast, ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
#             print('demand forecast electricity: ', list(np.zeros(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
#             print('price forecast electricity buy: ', list(0.30*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
#             print('price forecast electricity sell: ', list(0.10*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
#             #print('price forecast producer 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
#             print('price forecast coupler 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
#
#             # just for tests
#             # Stor1_calcSOC.set_value(random.randint(0, 100))
#             # Prod1_Setpoint.set_value(myforecast)
#             # STOR1_SOC.set_value(STOR1_calcSOC.get_value())
#
#         # iterator
#         done1 = 1
#
#     # demand setpoint for CoSES
#     if (timing_delta2 >= delta_t_for_setting_CoSES) & (k>0):
#         mytime2 = time.monotonic()
#
#         if i < time_ratio:
#             mycntr2 = (k-1)*time_ratio + i   #l%np.shape(demand1_interp_CoSES)[0]
#             mynr = i # (l%np.shape(demand1_interp_CoSES)[0])%(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0])
#             # write CoSES values in cycles
#             DMND01_DemandSetPt.set_value(demand1_interp_CoSES[mycntr2])
#             DMND02_DemandSetPt.set_value(demand1_interp_CoSES[mycntr2])
#             print('demand setpoint heat: ', demand1_interp_CoSES[mycntr2], ', nr.', k, '+ (', int(mynr+1), '/',
#                   int(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0]),')')
#             print('demand setpoint electricity: ', demand1_interp_CoSES[mycntr2], ', nr.', k, '+ (', int(mynr+1), '/',
#                   int(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0]),')')
#
#             i += 1
#             l += 1
#
#             # just for tests
#             # STOR1_SOC.set_value(STOR1_calcSOC.get_value())