# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 17:20:59 2020

@author: mayer
"""


from createBuilding import create_Server_Basics, create_Namespace, add_General, add_Demand, add_VolatileProducer, add_Coupler, add_Producer, add_Storage

import time
import numpy as np
import json

# General Information:
objectName = "CoSES"
opc_port = "4850"

mpc = 5
time_factor = 0.25

nrOfEms = 1

demandPath = "data/SkalierteDatenGeb1.csv"


# Add Counter list/array to count for numer of EMS x Device Types and construct display names
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
(heatDemandSP, htDemFCarray) = add_Demand(counter, naming, idx, Demand, "heat", "Wärmebedarf_Haus1", mpc, 60*time_factor, 60, 120, 999, 0.0)
(elecDemandSP, elDemFCarray) = add_Demand(counter, naming, idx, Demand, "elec", "Strombedarf_Haus1", mpc, 60*time_factor, 0.0, 0.0, 0.285, 0.0)

### Devices
# Producer -                            add_Producer(counter, naming, FC_step, idx, name, Producer, inMEMAP, PrimSect, EffPrim, P_min, P_max, Temp_min, Temp_max, PrimEnCost, GenCosts, PrimCO2Cost):
(Prod1_Setpoint, Prod1_Power) = add_Producer(counter, naming, mpc, idx, "SFH1_EB1", Producer, True, "heat", 0.88, 3.8, 18.9, 50, 90, 0.07, 0.11, 0.202)

# Storage -                             add_Storage(counter, naming, FC_step, idx, name, Storage, inMEMAP, PrimSect, CEffPrim, DisCEffPrim, Capacity, loss, Pmax_in, Pmax_Out, minTemp, maxTemp, minTempOut, SOC_init, PrimEnCost, GenCosts, PrimCO2Cost
(Stor1_setpointChgFC, Stor1_setpointDisChgFC, Stor1_SOC) = add_Storage(counter, naming, mpc, idx, "SFH1_TS1", Storage, True, "heat", 0.97, 0.97, 69.5, 2.59, 95, 95, 20, 95, 60, 0.0, 0.0, 0.0, 0.0)


# =============================== Start ===================================
server1.start()
print("Server " + naming + " started at {}".format(url1))
server1.PublishingEnabled = True

# =========================================================================
# Export Namespace as XML
#server1.export_xml(Systems.get_children(), "CoSES_Server_raw.xml")
#server1.export_xml_by_ns("CoSES_Server_full.xml")


# ==================== Load 2 Days from Simulation ========================
size=10000
i = 0

# 15 min values
profile_time_factor = 0.25
Consumption_B1 = np.genfromtxt(demandPath, delimiter=";")







def forecast_to_json(FC_step, timefactor, FC_array):
    Forecast = {}
    for j in range(FC_step-1):
        Str = 'Forecast_t' + str(60*timefactor*(j+1))
        Forecast[Str] = str(FC_array[j].get_value())
    return json.dumps(Forecast)


# ============================= set values =================================



while True:

    # Werte auf time_factor/profile_time_factor skalieren   
    htDemFCarray.set_value([Consumption_B1[i],Consumption_B1[i+1]*time_factor/profile_time_factor,Consumption_B1[i+2]*time_factor/profile_time_factor,
                            Consumption_B1[i+3]*time_factor/profile_time_factor,Consumption_B1[i+4]*time_factor/profile_time_factor])
        
    
    # We cut away 5 timesteps from the day here for the MPC
    if i < size-mpc:
        i += 1
    else:
        i = 0
        
    time.sleep(10)



