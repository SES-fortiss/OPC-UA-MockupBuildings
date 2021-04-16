# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 17:20:59 2020
Modified on Fr May 15 10:50:00 2020

@author: licklederer (TUM), mayer (fortiss)
"""


from createBuilding import create_Server_Basics, create_Namespace, add_General,\
    add_Demand, add_VolatileProducer, add_Coupler, add_Producer, add_Storage

import time
import numpy as np
import json
import random

from scipy.interpolate import splrep, splev
import matplotlib.pyplot as plt

# General Information:
objectName = "CoSES"
opc_port = "4852"

# TIMING
mpc = 5  # number of mpc horizont steps, usually 5-48
mpc_time_factor = 0.25  # time factor as ratio of hours,
    # determining the time different between steps, 0.25 = 15 min
profile_time_factor = 0.25  # time factor as ratio of hours,
    # for time difference between read values from profile, 0.25 = 15 min
CoSES_time_factor = 1 / 120  # time factor as ratio of hours,
    # for wished time difference for CoSES-Demand-Values, 1/60 = 1 min
simulation_time_factor = 60  # 1 s in simulation time equals X seconds in real time
karenzzeit = max(int(0.02*mpc_time_factor*(1/simulation_time_factor)*3600),5) # sekunden

nrOfEms = 1

demandPath  =   "FC_data_series/Test1_Last.csv"
pricePath    =   "FC_data_series/Test1_Preise.csv"
interp_type = "spline" # alternatives: "step", "linear", "spline",


# Add Counter list/array to count for number of EMS x Device Types and construct display names
# Entries for DEMND, PROD, VPROD, COUPL, STRGE, HTCONN, ELMRKT
counter = np.zeros([nrOfEms,7])
myNodeIDcntr = 100


# ================= Defining the Namespace of the Building =====================

# ============================== EMS 1 - General ==============================
EMS = "EMS02"
(server1, url1, idx, objects) = create_Server_Basics(objectName, EMS, opc_port)
(General, Demand, Devices, Producer, VolatileProducer, Coupler, Storage) = create_Namespace(idx, objects)
naming = objectName + EMS + "OBJ01"

# add_General
(myNodeIDcntr, EMSnameID, Trigger) = add_General(idx, myNodeIDcntr, naming, General, "SFH2")


# ============================== EMS 1 - Devices ==============================
# (Add Demand, Producer, Volatile Producer, Coupler, Storage)

### add_Demand
(myNodeIDcntr, counter, DMND01_DemandSetPt, DMND01_demandFC, DMND01_currDemand,
    DMND01_GrdBuyCost, DMND01_GrdSellCost, DMND01_GrdBuy, DMND01_GrdSell) = add_Demand(
    counter, naming, idx, myNodeIDcntr, Demand, "heat", "Wärmebedarf_Haus2", mpc)

(myNodeIDcntr, counter, DMND02_DemandSetPt, DMND02_demandFC, DMND02_currDemand,
    DMND02_GrdBuyCost, DMND02_GrdSellCost, DMND02_GrdBuy, DMND02_GrdSell) = add_Demand(
    counter, naming, idx, myNodeIDcntr, Demand, "elec", "Strombedarf_Haus2", mpc)

### Devices
# # add_Producer
# (myNodeIDcntr, CPROD1_production, CPROD1_GenCosts, CPROD1_CO2PerKWh, CPROD1_SPDevPwr) = add_Producer(counter, naming, mpc, idx,
                                                            # myNodeIDcntr, "SFH1_EB1", Producer, "heat", 0.88, 5, 14)

# add_Storage 
(myNodeIDcntr, STOR1_SOC, STOR1_calcSOC, STOR1_setpointChg, STOR1_setpointDisChg) = add_Storage(counter, naming,
                                                mpc, idx, myNodeIDcntr,
                                                "SFH2_TS1", Storage, "heat", 0.97, 0.97, 36.1, 24, 56, 56, 18.05)

# add_coupler
(myNodeIDcntr, BHKW_Prod1, BHKW_Prod2, BHKW_GenCosts, BHKW_CO2PerKWh, BHKW_SPDevPwr) = add_Coupler(
    counter, naming, idx, myNodeIDcntr, 'SFH2_BHKW', Coupler, 'heat', 'elec', 0.4, 0.2, 2, 2, mpc)



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
time_ratio = int(delta_t_for_setting_MEMAP / delta_t_for_setting_CoSES)

## Initialization
k=0
Trigger.set_value(0)
oldTriggerValue = Trigger.get_value()
lasttriggertime = time.monotonic()
mytime2 = lasttriggertime - delta_t_for_setting_CoSES
print('MEMAP alle ', delta_t_for_setting_MEMAP, ' Sekunden =  alle ',
      delta_t_for_setting_MEMAP * simulation_time_factor, " Sekunden Realzeit")
print('CoSES alle ', delta_t_for_setting_CoSES, ' Sekunden =  alle ', delta_t_for_setting_CoSES*simulation_time_factor,
              " Sekunden Realzeit")
myforecast = [demand1_interp_mpc[x] for x in range(mpc)]
mypriceforecast = [prices_interp_mpc[x] for x in range(mpc)]
DMND01_demandFC.set_value(myforecast)
DMND02_demandFC.set_value(myforecast)
DMND02_GrdBuyCost.set_value(list(0.30*np.ones(mpc)))
DMND02_GrdSellCost.set_value(list(0.10*np.ones(mpc)))
#CPROD1_GenCosts.set_value(mypriceforecast)
BHKW_GenCosts.set_value(mypriceforecast)
print('demand forecast heat: ', myforecast, ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
print('demand forecast electricity: ', list(np.zeros(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
print('price forecast electricity buy: ', list(0.30*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
print('price forecast electricity sell: ', list(0.10*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
print('price forecast producer 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
# print('price forecast coupler 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
done1 = 1
i = time_ratio+1
l = 0
timing_delta1 = 0
timing_delta2 = 0
startup = True

## Loop

while True:
    newTriggerValue = Trigger.get_value()

    if newTriggerValue != oldTriggerValue:
        if startup==True:
            startup = False
            oldTriggerValue = newTriggerValue
        else:
            lasttriggertime = time.monotonic()
            done1 = 0
            k+=1
            mytime2 = lasttriggertime - delta_t_for_setting_CoSES
            i=0
            oldTriggerValue = newTriggerValue

    timing_delta1 = time.monotonic() - lasttriggertime
    timing_delta2 = time.monotonic() - mytime2

    # update forecasts
    if (timing_delta1 >= karenzzeit) & (done1 == 0):

        lastforecastupdate = time.monotonic()

        if k%(np.shape(demand1_interp_mpc)[0])<=np.shape(demand1_interp_mpc)[0]-mpc:
            mycntr = k%(np.shape(demand1_interp_mpc)[0])
            myforecast = [demand1_interp_mpc[mycntr + x] for x in range(mpc)]
            mypriceforecast = [prices_interp_mpc[mycntr + x] for x in range(mpc)]
            
            DMND01_demandFC.set_value(myforecast)
            DMND02_demandFC.set_value(myforecast)
            DMND02_GrdBuyCost.set_value(list(0.30*np.ones(mpc)))
            DMND02_GrdSellCost.set_value(list(0.10*np.ones(mpc)))
            #CPROD1_GenCosts.set_value(mypriceforecast)
            BHKW_GenCosts.set_value(mypriceforecast)
            print('demand forecast heat: ', myforecast, ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            print('demand forecast electricity: ', list(np.zeros(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            print('price forecast electricity buy: ', list(0.30*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            print('price forecast electricity sell: ', list(0.10*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            print('price forecast producer 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
            # print('price forecast coupler 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])

            # just for tests
            # Stor1_calcSOC.set_value(random.randint(0, 100))
            # Prod1_Setpoint.set_value(myforecast)
            # STOR1_SOC.set_value(STOR1_calcSOC.get_value())
            print('measured SOC storage 1: ', STOR1_SOC.get_value(), ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])

        elif k%(np.shape(demand1_interp_mpc)[0]) > np.shape(demand1_interp_mpc)[0]-mpc:
            mycntr = k % (np.shape(demand1_interp_mpc)[0])
            x2 = (k%(np.shape(demand1_interp_mpc)[0])) - (np.shape(demand1_interp_mpc)[0]-mpc)
            x1 = mpc - x2

            myforecast = [demand1_interp_mpc[mycntr+x] for x in range(x1)] +\
                         [demand1_interp_mpc[x] for x in range(x2)]
            mypriceforecast = [prices_interp_mpc[mycntr+x] for x in range(x1)] +\
                              [prices_interp_mpc[x] for x in range(x2)]             
                         
                         
            DMND01_demandFC.set_value(myforecast)
            DMND02_demandFC.set_value(myforecast)
            DMND02_GrdBuyCost.set_value(list(0.30*np.ones(mpc)))
            DMND02_GrdSellCost.set_value(list(0.10*np.ones(mpc)))
            #CPROD1_GenCosts.set_value(mypriceforecast)
            BHKW_GenCosts.set_value(mypriceforecast)
            print('demand forecast heat: ', myforecast, ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            print('demand forecast electricity: ', list(np.zeros(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            print('price forecast electricity buy: ', list(0.30*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            print('price forecast electricity sell: ', list(0.10*np.ones(mpc)), ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            print('price forecast producer 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
            # print('price forecast coupler 1: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])

            # just for tests
            # Stor1_calcSOC.set_value(random.randint(0, 100))
            # Prod1_Setpoint.set_value(myforecast)
            # STOR1_SOC.set_value(STOR1_calcSOC.get_value())

        # iterator
        done1 = 1

    # demand setpoint for CoSES
    if (timing_delta2 >= delta_t_for_setting_CoSES) & (k>0):
        mytime2 = time.monotonic()

        if i < time_ratio:
            mycntr2 = (k-1)*time_ratio + i   #l%np.shape(demand1_interp_CoSES)[0]
            mynr = i # (l%np.shape(demand1_interp_CoSES)[0])%(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0])
            # write CoSES values in cycles
            DMND01_DemandSetPt.set_value(demand1_interp_CoSES[mycntr2])
            DMND02_DemandSetPt.set_value(demand1_interp_CoSES[mycntr2])
            print('demand setpoint heat: ', demand1_interp_CoSES[mycntr2], ', nr.', k, '+ (', int(mynr+1), '/',
                  int(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0]),')')
            print('demand setpoint electricity: ', demand1_interp_CoSES[mycntr2], ', nr.', k, '+ (', int(mynr+1), '/',
                  int(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0]),')')

            i += 1
            l += 1

            # just for tests
            # STOR1_SOC.set_value(STOR1_calcSOC.get_value())






