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

from scipy.interpolate import splrep, splev
import matplotlib.pyplot as plt

# General Information:
objectName = "CoSES"
opc_port = "4850"

# TIMING
mpc = 5  # number of mpc horizont steps, usually 5-48
mpc_time_factor = 0.25  # time factor as ratio of hours, determining the time different between steps, 0.25 = 15 min
profile_time_factor = 0.25  # time factor as ratio of hours, for time difference between read values from profile, 0.25 = 15 min
CoSES_time_factor = 1 / 60  # time factor as ratio of hours, for wished time difference for CoSES-Demand-Values, 1/60 = 1 min
simulation_time_factor = 6  # 1 s in simulation time equals X seconds in real time

nrOfEms = 1

demandPath  =   "data/Test1_Last.csv"
pricePath    =   "data/Test1_Preise.csv"
interp_type = "step" # alternatives: "step", "linear", "spline",


# Add Counter list/array to count for number of EMS x Device Types and construct display names
# Entries for DEMND, PROD, VPROD, COUPL, STRGE
counter = np.zeros([nrOfEms,5])
#print(counter)

# ================= Defining the Namespace of the Building =====================

# ============================== EMS 1 - General ==============================
EMS = "EMS01"
(server1, url1, idx, objects) = create_Server_Basics(objectName, EMS, opc_port)
(General, Demand, Systems, Producer, VolatileProducer, Coupler, Storage) = create_Namespace(server1, idx, objects)
naming = objectName + EMS + "OBJ01"

#                                                       add_General(idx, naming, General, url, connectionStat, EMSname, buildCat):
(endPoint, connStat, EMSnameID, bCategory) = add_General(idx, naming, General, url1, True, "SFH1_HS", "Single Family House")


# ============================== EMS 1 - Systems ==============================
# (Add Demand, Producer, Volatile Producer, Coupler, ThermalStorage, ElectricStorage)

### Demand   -                          add_Demand(counter, naming, idx, Demand, sector, demName, FC_step, FC_size, minT, maxT, buyCost, sellCost):
(heatDemandSP, htDemFCarray) = add_Demand(counter, naming, idx, Demand, "heat", "Wärmebedarf_Haus1", mpc, 60*mpc_time_factor, 60, 120, 999, 0.0)
(elecDemandSP, elDemFCarray) = add_Demand(counter, naming, idx, Demand, "elec", "Strombedarf_Haus1", mpc, 60*mpc_time_factor, 0.0, 0.0, 0.285, 0.0)

### Devices
# Producer -                            add_Producer(counter, naming, FC_step, idx, name, Producer, inMEMAP, PrimSect, EffPrim, P_min, P_max, Temp_min, Temp_max, PrimEnCost, GenCosts, PrimCO2Cost):
(Prod1_Power, Prod1_Setpoint, Prod1_priceFC) = add_Producer(counter, naming, mpc, idx, "SFH1_EB1", Producer, True, "heat", 0.88, 2, 14, 40, 80, 0.045, 0.11, 0.202)

# Storage -                             add_Storage(counter, naming, FC_step, idx, name, Storage, inMEMAP, PrimSect, CEffPrim, DisCEffPrim, Capacity, loss, Pmax_in, Pmax_Out, minTemp, maxTemp, minTempOut, SOC_init, PrimEnCost, GenCosts, PrimCO2Cost
(Stor1_setpointChgFC, Stor1_setpointDisChgFC, Stor1_SOC) = add_Storage(counter, naming, mpc, idx, "SFH1_TS1", Storage, True, "heat", 0.97, 0.97, 36.1, 2.59, 56, 56, 40, 80, 60, 0.0, 0.0, 0.0, 0.0)

# =========================================================================

# =======
# for heat sink
# counter=np.append(counter, np.zeros([nrOfEms,2]), axis=1)
heat_sink = objects.add_folder(idx, "heat_sink")
heat_demand_setpoint = heat_sink.add_variable(idx, "heat_demand_setpoint", 0.0)
heat_demand_setpoint.set_writable()
heat_demand_is = heat_sink.add_variable(idx, "heat_demand_is", 0.0)
heat_demand_is.set_writable()

# for egston load simulator
egston_load_simulator = objects.add_folder(idx, "egston_load_simulator")
electric_demand_setpoint = egston_load_simulator.add_variable(idx, "electric_demand_setpoint", 0.0)
electric_demand_setpoint.set_writable()
electric_demand_is = egston_load_simulator.add_variable(idx, "electric_demand_is", 0.0)
electric_demand_is.set_writable()


# ==================== Load demand from file ========================
# reading
Consumption_B1 = np.genfromtxt(demandPath, delimiter="\n")
size = np.shape(Consumption_B1)[0]
# scaling
#demand1_old_max = np.max(Consumption_B1)
#demand1_max_set = 13
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

#plt.figure()
#plt.plot(timeline_profile, demand1_scaled, label="origin scaled", marker="x")
#plt.plot(timeline_mpc, demand1_interp_mpc, label="mpc")
#plt.plot(timeline_CoSES, demand1_interp_CoSES, label="CoSES", marker=".", linestyle="none")
#plt.legend()
#plt.show(block=False)

# ==================== Load prices from file ========================
# reading
dynamic_prices = np.genfromtxt(pricePath, delimiter="\n")
size = np.shape(dynamic_prices)[0]
# interpolating
delta_t_profile = profile_time_factor * 60  # in min
delta_t_mpc = mpc_time_factor * 60  # in min
nbr_reps_mpc = int(delta_t_profile / delta_t_mpc)
prices_interp_mpc = np.array([np.repeat(step, nbr_reps_mpc) for step in dynamic_prices]).flatten()

#plt.figure()
#plt.plot(timeline_profile, dynamic_prices, label="origin scaled", marker="x")
#plt.plot(timeline_mpc, prices_interp_mpc, label="mpc", marker=".", linestyle="none")
##plt.plot(timeline_CoSES, prices_interp_CoSES, label="CoSES", marker=".", linestyle="none")
#plt.legend()
#plt.show(block=False)


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
server1.export_xml(Systems.get_children(), "CoSES_Server_raw.xml")
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
        print('MEMAP alle ', timing_delta1, ' Sekunden =  alle ', timing_delta1*simulation_time_factor, " Sekunden Realzeit")
        mytime1 = time.monotonic()
        timing_delta1 = 0

        ## write MEMAP values
        # in cycle
        if k%(np.shape(demand1_interp_mpc)[0])<=np.shape(demand1_interp_mpc)[0]-mpc:
            mycntr = k%(np.shape(demand1_interp_mpc)[0])
            myforecast = [demand1_interp_mpc[mycntr + x] for x in range(mpc)]
            print('demand forecast: ', myforecast, ', nr.', k+1, '/', np.shape(demand1_interp_mpc)[0])
            htDemFCarray.set_value(myforecast)

            mypriceforecast = [prices_interp_mpc[mycntr + x] for x in range(mpc)]
            print('price forecast: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
            Prod1_priceFC.set_value(mypriceforecast)

            # just for tests
            Prod1_Setpoint.set_value(myforecast)

        elif k%(np.shape(demand1_interp_mpc)[0]) > np.shape(demand1_interp_mpc)[0]-mpc:
            mycntr = k % (np.shape(demand1_interp_mpc)[0])
            x2 = (k%(np.shape(demand1_interp_mpc)[0])) - (np.shape(demand1_interp_mpc)[0]-mpc)
            x1 = mpc - x2

            myforecast = [demand1_interp_mpc[mycntr+x] for x in range(x1)] + [demand1_interp_mpc[x] for x in range(x2)]
            print('demand forecast: ', myforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
            htDemFCarray.set_value(myforecast)

            mypriceforecast = [prices_interp_mpc[mycntr+x] for x in range(x1)] + [prices_interp_mpc[x] for x in range(x2)]
            print('price forecast: ', mypriceforecast, ', nr.', k+1,'/', np.shape(demand1_interp_mpc)[0])
            Prod1_priceFC.set_value(mypriceforecast)

        #elDemFCjson.set_value(forecast_to_json(mpc, mpc_time_factor, elDemdFC))
        #htDemFCjson.set_value(forecast_to_json(mpc, mpc_time_factor, htDemdFC))
        #elCostFCjson.set_value(forecast_to_json(mpc, mpc_time_factor, elCostFC))
        #htCostFCjson.set_value(forecast_to_json(mpc, mpc_time_factor, htCostFC))

        # iterator
        k += 1


    if timing_delta2 >= delta_t_for_setting_CoSES:
        print('CoSES alle ', timing_delta2, ' Sekunden =  alle ', timing_delta2*simulation_time_factor, " Sekunden Realzeit")
        mytime2 = time.monotonic()
        timing_delta2 = 0

        mycntr2 = l%np.shape(demand1_interp_CoSES)[0]
        mynr = (l%np.shape(demand1_interp_CoSES)[0])%(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0])
        # write CoSES values in cycles
        heat_demand_setpoint.set_value(demand1_interp_CoSES[mycntr2])
        print('demand setpoint: ', demand1_interp_CoSES[mycntr2], ', nr.', k, '+ (', int(mynr+1), '/', int(np.shape(demand1_interp_CoSES)[0]/np.shape(demand1_interp_mpc)[0]),')')
        electric_demand_setpoint.set_value(0.0)



        l += 1




