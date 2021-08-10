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

from scipy.interpolate import splrep, splev, spalde
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
CoSES_time_factor = 1/60 # 1 / 60  # time factor as ratio of hours,
    # for wished time difference for CoSES-Demand-Values, 1/60 = 1 min
simulation_time_factor = 60  # 1 s in simulation time equals X seconds in real time
SOCsetHOR = 0.7
karenzzeit = max(int(0.02*mpc_time_factor*(1/simulation_time_factor)*3600),3) # sekunden

nrOfEms = 1

demandPath_heat  =   "FC_data_series/SF1_demand_heat.csv"
demandPath_elec  =   "FC_data_series/SF1_demand_elec.csv"
pricePath_gas    =   "FC_data_series/SF1_gas_price.csv"
pricePath_elec_buy    =   "FC_data_series/SF1_elec_price_buy.csv"
pricePath_elec_sell    =   "FC_data_series/SF1_elec_price_sell.csv"
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
     counter, naming, idx, myNodeIDcntr, 'SFH1_BHKW', Coupler, 'heat', 'elec', 0.723, 0.278, 5.0, 5.0, mpc)

# add_Storage 
(myNodeIDcntr, STOR1_SOC, STOR1_calcSOC, STOR1_setpointChg, STOR1_setpointDisChg, SOCminHOR) = add_Storage(counter, naming,
                                                mpc, idx, myNodeIDcntr,
                                                "SFH1_TS1", Storage, "heat", 0.97, 0.97, 62.94, 0.0278, 5.0, 5.0, 0.5)




# ========= Load forecasts from file ======================================

demand1_profile, demandtime_profile = ImportFromCSV (demandPath_heat, "\n", profile_time_factor)
demand1_MEMAP, demandtime_MEMAP = InterpolateProfileMEMAP (demand1_profile, interp_type, profile_time_factor, mpc_time_factor)
demand1_CoSES, demandtime_CoSES = InterpolateProfileCoSES (demand1_profile, interp_type, profile_time_factor, CoSES_time_factor)

demand2_profile, demandtime_profile = ImportFromCSV (demandPath_elec, "\n", profile_time_factor)
demand2_MEMAP, demandtime_MEMAP = InterpolateProfileMEMAP (demand2_profile, interp_type, profile_time_factor, mpc_time_factor)
demand2_CoSES, demandtime_CoSES = InterpolateProfileCoSES (demand2_profile, interp_type, profile_time_factor, CoSES_time_factor)

priceGas_profile, pricetime_profile = ImportFromCSV (pricePath_gas, "\n", profile_time_factor)
priceGas_MEMAP, pricetime_MEMAP = InterpolateProfileMEMAP (priceGas_profile, interp_type, profile_time_factor, mpc_time_factor)

priceElecbuy_profile, pricetime_profile = ImportFromCSV (pricePath_elec_buy, "\n", profile_time_factor)
priceElecbuy_MEMAP, pricetime_MEMAP = InterpolateProfileMEMAP (priceElecbuy_profile, interp_type, profile_time_factor, mpc_time_factor)

priceElecsell_profile, pricetime_profile = ImportFromCSV (pricePath_elec_sell, "\n", profile_time_factor)
priceElecsell_MEMAP, pricetime_MEMAP = InterpolateProfileMEMAP (priceElecsell_profile, interp_type, profile_time_factor, mpc_time_factor)


if plot_forecasts:

    PlotProfile(demand1_profile, demandtime_profile, "demand1", "kW", "figures")
    PlotProfile(demand1_MEMAP, demandtime_MEMAP, "demand1_MEMAP", "kW", "figures")
    PlotProfile(demand1_CoSES, demandtime_CoSES, "demand1_CoSES", "kW", "figures")

    PlotProfile(demand2_profile, demandtime_profile, "demand2", "kW", "figures")
    PlotProfile(demand2_MEMAP, demandtime_MEMAP, "demand2_MEMAP", "kW", "figures")
    PlotProfile(demand2_CoSES, demandtime_CoSES, "demand2_CoSES", "kW", "figures")

    PlotProfile(priceGas_profile, pricetime_profile, "priceGas", "€/kWh", "figures")
    PlotProfile(priceGas_MEMAP, pricetime_MEMAP, "priceGas_MEMAP", "€/kWh", "figures")

    PlotProfile(priceElecbuy_profile, pricetime_profile, "priceElecbuy", "€/kWh", "figures")
    PlotProfile(priceElecbuy_MEMAP, pricetime_MEMAP, "priceElecbuy_MEMAP", "€/kWh", "figures")

    PlotProfile(priceElecsell_profile, pricetime_profile, "priceElecsell", "€/kWh", "figures")
    PlotProfile(priceElecsell_MEMAP, pricetime_MEMAP, "priceElecsell_MEMAP", "€/kWh", "figures")

    demand1_MEMAP_step, demandtime_MEMAP2 = InterpolateProfileMEMAP(demand1_profile, "step", profile_time_factor,
                                                              CoSES_time_factor)
    demand2_MEMAP_step, demandtime_MEMAP2 = InterpolateProfileMEMAP(demand2_profile, "step", profile_time_factor,
                                                                    CoSES_time_factor)

    #demandtime_MEMAP_adj = [x+profile_time_factor*60/2 for x in demandtime_MEMAP]
    fig1 = plt.figure(num="MEMAP vs CoSES", figsize=[8.3, 5.8], dpi=400.0)
    plt.plot(demandtime_MEMAP2, demand1_MEMAP_step, linestyle="-", color='g')
    plt.plot(demandtime_CoSES, demand1_CoSES, linestyle="-", color='k')
    plt.plot(demandtime_MEMAP2, demand2_MEMAP_step, linestyle="-", color='y')
    plt.plot(demandtime_CoSES, demand2_CoSES, linestyle="-", color='b')
    plt.title("MEMAP vs CoSES")
    plt.xlabel('')
    plt.ylabel("")
    plt.show(block=False)
    whattimeisit = datetime.now()
    now_string = whattimeisit.strftime("%Y%m%d_%H%M%S")
    filename = "figures" + "/" + "MEMAP vs CoSES" + "_" + now_string + ".png"
    fig1.savefig(filename)
    print("Plot was saved.")

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
horizon_min_MEMAP = list(np.array(range(j, j+mpc))*mpc_time_factor*60)

Trigger.set_value(0)
lasttriggertime = time.monotonic()
oldTriggerValue = Trigger.get_value()

demand1_MEMAP_FC = Profile2Forecast (demand1_MEMAP, j, mpc)
demand2_MEMAP_FC = Profile2Forecast (demand2_MEMAP, j, mpc)
priceGas_MEMAP_FC = Profile2Forecast (priceGas_MEMAP, j, mpc)
priceElecbuy_MEMAP_FC = Profile2Forecast (priceElecbuy_MEMAP, j, mpc)
priceElecsell_MEMAP_FC = Profile2Forecast (priceElecsell_MEMAP, j, mpc)

DMND01_demandFC.set_value(demand1_MEMAP_FC)
DMND02_demandFC.set_value(demand2_MEMAP_FC)
# CPROD1_GenCosts.set_value(priceGas_MEMAP_FC)
BHKW_GenCosts.set_value(priceGas_MEMAP_FC)
DMND02_GrdBuyCost.set_value(priceElecbuy_MEMAP_FC)
DMND02_GrdSellCost.set_value(priceElecsell_MEMAP_FC)
SOCminHOR.set_value(SOCsetHOR)

# print
print('demand forecast heat: ', demand1_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
print('demand forecast electricity: ', demand2_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
# print('price forecast gas boiler: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
print('price forecast BHKW: ', priceGas_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
print('price forecast electricity buy: ', priceElecbuy_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
print('price forecast electricity sell: ', priceElecsell_MEMAP_FC, ', for minutes', horizon_min_MEMAP)

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

print('############## EXPERIMENT STARTED: ', current_time, '##############\n')

# ============================= RUNNING Experiment =================================

# ## Initialization ----------------------------------------------------------------
newTriggerValue = oldTriggerValue
while newTriggerValue == oldTriggerValue:
    newTriggerValue = Trigger.get_value()

t = time.localtime()
current_time = time.strftime("%d.%m.%Y, %H:%M:%S", t)
print('############## FIRST TRIGGER RECEIVED: ', current_time, ' (= minute 0.0) ##############\n')
oldTriggerValue = newTriggerValue
lasttriggertime = time.monotonic()

while time.monotonic() < lasttriggertime + karenzzeit:
    pass
print("### INITIALIZATION ###")
j += 1 # time step since start of experiment
k = 99999 # loops within timestep
updatedone = True
horizon_min_MEMAP = list(np.array(range(j, j+mpc))*mpc_time_factor*60)

demand1_MEMAP_FC = Profile2Forecast (demand1_MEMAP, j, mpc)
demand2_MEMAP_FC = Profile2Forecast (demand2_MEMAP, j, mpc)
priceGas_MEMAP_FC = Profile2Forecast (priceGas_MEMAP, j, mpc)
priceElecbuy_MEMAP_FC = Profile2Forecast (priceElecbuy_MEMAP, j, mpc)
priceElecsell_MEMAP_FC = Profile2Forecast (priceElecsell_MEMAP, j, mpc)

DMND01_demandFC.set_value(demand1_MEMAP_FC)
DMND02_demandFC.set_value(demand2_MEMAP_FC)
# CPROD1_GenCosts.set_value(priceGas_MEMAP_FC)
BHKW_GenCosts.set_value(priceGas_MEMAP_FC)
DMND02_GrdBuyCost.set_value(priceElecbuy_MEMAP_FC)
DMND02_GrdSellCost.set_value(priceElecsell_MEMAP_FC)


# print
print('demand forecast heat: ', demand1_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
print('demand forecast electricity: ', demand2_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
# print('price forecast gas boiler: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
print('price forecast BHKW: ', priceGas_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
print('price forecast electricity buy: ', priceElecbuy_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
print('price forecast electricity sell: ', priceElecsell_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
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
        horizon_min_MEMAP = list(np.array(range(j, j+mpc))*mpc_time_factor*60)

        print("\n")

    else:
        pass

    if j%maxsteps <= maxsteps - mpc: # normal experiment, no repetition so far
        m = j % maxsteps
        if (time.monotonic() > lasttriggertime + karenzzeit) and not updatedone:
            # update forecasts
            demand1_MEMAP_FC = Profile2Forecast(demand1_MEMAP, m, mpc)
            demand2_MEMAP_FC = Profile2Forecast(demand2_MEMAP, m, mpc)
            priceGas_MEMAP_FC = Profile2Forecast(priceGas_MEMAP, m, mpc)
            priceElecbuy_MEMAP_FC = Profile2Forecast(priceElecbuy_MEMAP, m, mpc)
            priceElecsell_MEMAP_FC = Profile2Forecast(priceElecsell_MEMAP, m, mpc)

            DMND01_demandFC.set_value(demand1_MEMAP_FC)
            DMND02_demandFC.set_value(demand2_MEMAP_FC)
            # CPROD1_GenCosts.set_value(priceGas_MEMAP_FC)
            BHKW_GenCosts.set_value(priceGas_MEMAP_FC)
            DMND02_GrdBuyCost.set_value(priceElecbuy_MEMAP_FC)
            DMND02_GrdSellCost.set_value(priceElecsell_MEMAP_FC)

            # only for debugging tests!!!
            STOR1_SOC.set_value(STOR1_calcSOC.get_value())

            # print
            print('demand forecast heat: ', demand1_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            print('demand forecast electricity: ', demand2_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            # print('price forecast gas boiler: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
            print('price forecast BHKW: ', priceGas_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            print('price forecast electricity buy: ', priceElecbuy_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            print('price forecast electricity sell: ', priceElecsell_MEMAP_FC, ', for minutes', horizon_min_MEMAP)

            updatedone = True

            print("\n")

    elif j%maxsteps > maxsteps - mpc:   # run experiment in cycles, repeat the profiles from beginning
        m = j%maxsteps
        x2 = m - (maxsteps-mpc)
        x1 = mpc - x2
        # print('!!!!!!!!!!!!!!!!!!!!!!!!!!!noW!!!!!!!!!!!!!!!!!')
        if (time.monotonic() > lasttriggertime + karenzzeit) and not updatedone:
            # update forecasts
            demand1_MEMAP_FC = Profile2Forecast(demand1_MEMAP, m, x1)+Profile2Forecast(demand1_MEMAP, 0, x2)
            demand2_MEMAP_FC = Profile2Forecast(demand2_MEMAP, m, x1)+Profile2Forecast(demand2_MEMAP, 0, x2)
            priceGas_MEMAP_FC = Profile2Forecast(priceGas_MEMAP, m, x1) + Profile2Forecast(priceGas_MEMAP, 0, x2)
            priceElecbuy_MEMAP_FC = Profile2Forecast(priceElecbuy_MEMAP, m, x1) + Profile2Forecast(priceElecbuy_MEMAP, 0, x2)
            priceElecsell_MEMAP_FC = Profile2Forecast(priceElecsell_MEMAP, m, x1) + Profile2Forecast(priceElecsell_MEMAP, 0, x2)

            DMND01_demandFC.set_value(demand1_MEMAP_FC)
            DMND02_demandFC.set_value(demand2_MEMAP_FC)
            # CPROD1_GenCosts.set_value(priceGas_MEMAP_FC)
            BHKW_GenCosts.set_value(priceGas_MEMAP_FC)
            DMND02_GrdBuyCost.set_value(priceElecbuy_MEMAP_FC)
            DMND02_GrdSellCost.set_value(priceElecsell_MEMAP_FC)

            # only for debugging tests!!!
            STOR1_SOC.set_value(STOR1_calcSOC.get_value())

            # print
            print('demand forecast heat: ', demand1_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            print('demand forecast electricity: ', demand2_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            # print('price forecast gas boiler: ', list(np.zeros(mpc)), ', for minutes', horizon_min_MEMAP)
            print('price forecast BHKW: ', priceGas_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            print('price forecast electricity buy: ', priceElecbuy_MEMAP_FC, ', for minutes', horizon_min_MEMAP)
            print('price forecast electricity sell: ', priceElecsell_MEMAP_FC, ', for minutes', horizon_min_MEMAP)

            updatedone = True

            print("\n")

    if m < 2:
        l = maxsteps + m
    else:
        l = m

    if k == 0: # first iteration in timestep

        # CoSES demand setpoints
        DMND01_DemandSetPt.set_value(demand1_CoSES[((l-2)*time_ratio)+k])
        DMND02_DemandSetPt.set_value(demand2_CoSES[((l-2)*time_ratio)+k])
        refminute_CoSESset = (((l-2)*time_ratio)+k)*60*CoSES_time_factor
        refminute_CoSESset2 = (((l-2)*time_ratio)+k+1)*60*CoSES_time_factor

        # Boundary Conditions
        refmin_bounds = horizon_min_MEMAP[0]-2*(60*mpc_time_factor)
        refmin_bounds2 = horizon_min_MEMAP[0]-1*(60*mpc_time_factor)
        BHKWcurPrice.set_value(priceGas_MEMAP[l-2])
        DMND02_curPriceBuy.set_value(priceElecbuy_MEMAP[l-2])
        DMND02_curPriceSell.set_value(priceElecsell_MEMAP[l-2])
        # CPROD1curPrice.set_value(0.0)

        # print
        print('demand setpoint CoSES heat: ', demand1_CoSES[((l-2)*time_ratio)+k], ', for minute ', refminute_CoSESset, 'to ', refminute_CoSESset2)
        print('demand setpoint CoSES electricity: ', demand2_MEMAP[l-2], ', for minute ', refminute_CoSESset, 'to ', refminute_CoSESset2)
        print("\n")
        print('current price gas BHKW: ', priceGas_MEMAP[l-2], ', for minute ', refmin_bounds, 'to ', refmin_bounds2)
        print('current price electricity buy: ', priceElecbuy_MEMAP[l-2], ', for minute ', refmin_bounds, 'to ', refmin_bounds2)
        print('current price electricity sell: ', priceElecsell_MEMAP[l-2], ', for minute ', refmin_bounds, 'to ', refmin_bounds2)
        # print('current price gas boiler: ', 0.0, ', for minute ', refmin_bounds, 'to ', refmin_bounds2)

        #iterator
        k+=1

        print("\n")

    elif (time.monotonic() > lasttriggertime + (k * delta_t_for_setting_CoSES)) & (k < time_ratio):
        # iterations in timestep

        # CoSES demand setpoints
        # CoSES demand setpoints
        DMND01_DemandSetPt.set_value(demand1_CoSES[((l-2)*time_ratio)+k])
        DMND02_DemandSetPt.set_value(demand2_CoSES[((l-2)*time_ratio)+k])
        refminute_CoSESset = (((j-2)*time_ratio)+k)*60*CoSES_time_factor
        refminute_CoSESset2 = (((j-2)*time_ratio)+k+1)*60*CoSES_time_factor

        # print
        print('demand setpoint CoSES heat: ', demand1_CoSES[((l - 2) * time_ratio) + k], ', for minute ',
              refminute_CoSESset, 'to ', refminute_CoSESset2)
        print('demand setpoint CoSES electricity: ', demand2_MEMAP[l-2], ', for minute ', refminute_CoSESset, 'to ',
              refminute_CoSESset2)

        # iterator
        k+=1

        print("\n")

    else:
        pass