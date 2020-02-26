# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 17:20:59 2020

@author: mayer
"""

#from opcua import Server
from createBuilding import create_Server_Basics, create_Namespace, add_General, add_Demand, add_VolatileProducer, add_Coupler, add_Producer, add_Storage

import time
import numpy as np
import json
#import requests, json
#import random

mpc = 5
time_factor = 0.25


# Add Counter list/array to count for numer of Buildings/EMS/Devices and contruct Naming



# ============================== EMS 1 ==============================

# ================= Defining the Namespace Building 1 =====================
Geb = "EMS01"
(server1, url1, idx, objects) = create_Server_Basics(Geb,"4880")
(General, Demand, Systems, Producer, VolatileProducer, Coupler, Storage) = create_Namespace(server1, idx, objects)

### General   -                                         add_Demand(idx, General, url, ConnectionStat, EMSname, InMEMAP, BuildCat))
(EndPoint, ConnStat, MEMAPflag, EMSnameID, BCategory) = add_General(idx, General, url1, "FLASE", "SFH1_HS", "TRUE", "Single Family House")

### Demand   -                                                                add_Demand(idx, Demand, DemName, FC_Step, FC_Size, H_minT, C_maxT, E_cost, H_cost, C_cost)
(HeatPowerDemand, HtCostFC, HtDemdFC, ElecPowerDemand, ElDemdFC, ElCostFC)  = add_Demand(idx, Demand, "Consumer", mpc, 60*time_factor, 60, 15, 0.0, 0.0, 0.0)


### Anlagen
# Producer -                                                                         add_Producer(idx, name, Producer, PrimSect, EffPrim, P_min, P_max, Temp_min, Temp_max, PrimEnCost, GenCosts, PrimCO2Cost)
(B1_P_Prod1, B1_Eff_Prod1, P_min, P_max, MinTemp, MaxTemp, Setpoint, Production) = add_Producer(idx, "SFH1_EB1", Producer, "heat", 88, 3.8, 18.9, 50, 90, 0.07, 0.11, 0.202)




# VolatileProducer - add_VolatileProducer(idx, Geb, VolatileProducer, Medium, Eff, Area, Temp):
#(B1_P_VProd1, B1_Eff_VProd1, B1_Ppeak_VProd1) = add_VolatileProducer(idx, Geb+"_Photovoltaik", VolatileProducer, "Electricity", 0.18, 18, 0)

# Coupler - add_Coupler(idx, Geb, Coupler, Medium1, Medium2, Eff1, Eff2, P_min, P_max, Temp)
#(B1_Pp_Coup1, B1_Eff1_Coup1, B1_Ps_Coup1, B1_Eff2_Coup1, B1_P_min_Coup1, B1_P_max1_Coup1, B1_P_max2_Coup1) = add_Coupler(idx,  Geb+"_Heatpump", Coupler, "Heat", "Electricity", 3.8, -1, 3, 10, 40)

# Storage - add_Storage(idx, name, Storage, Medium, Eff, Capacity, Pmax_in, Pmax_Out, Temp, SOC_alt)
#(B1_Eff_Stor1, B1_Cap_Stor1, B1_P_in_Stor1, B1_P_out_Stor1, B1_SOC_Stor1, B1_P_maxOut_Stor1) = add_Storage(idx, Geb+"_Battery", Storage, "Electricity", 0.98, 6, 3.3, 3.3, 0, 0.5)





# =============================== Start ===================================
server1.start()
print("Server1 started at {}".format(url1))
server1.PublishingEnabled = True

# =========================================================================


# ==================== Load 2 Days from Simulation ========================
'''
Consumption_B1 = np.genfromtxt("data/ConsumptionGEB1.csv", delimiter=";")
Consumption_B2 = np.genfromtxt("data/ConsumptionGEB2.csv", delimiter=";")

P_Geb1 = np.genfromtxt("data/XvectorGEB1.csv", delimiter=";")
P_Geb2 = np.genfromtxt("data/XvectorGEB2.csv", delimiter=";")
E_Price = np.genfromtxt("data/YIpriceOrig.csv", delimiter=";")
'''

# ============================= set values =================================
'''
i = 0

while True:

    # convert from kwh to kw with time_factor
    
    HeatPower_B1.set_value(Consumption_B1[i]/time_factor)
    HeatPower_B2.set_value(Consumption_B2[i]/time_factor)
    ElecPower_B1.set_value(Consumption_B1[n+i]/time_factor)
    ElecPower_B2.set_value(Consumption_B2[n+i]/time_factor)
    
    Forecast1 = {}
    Forecast2 = {}
    Forecast3 = {}
    Forecast4 = {}
    for j in range(mpc-1):
        StrH = 'HeatForecast_t' + str(15*(j+1))
        StrE = 'ElecForecast_t' + str(15*(j+1))
        Forecast1[StrH] = str(Consumption_B1[i+(j+1)]/time_factor)
        Forecast2[StrH] = str(Consumption_B2[i+(j+1)]/time_factor)
        Forecast3[StrE] = str(Consumption_B1[n+i+j+1]/time_factor)
        Forecast4[StrE] = str(Consumption_B2[n+i+j+1]/time_factor)
    B1_HeatFC.set_value(json.dumps(Forecast1))
    B2_HeatFC.set_value(json.dumps(Forecast2))
    B1_ElecFC.set_value(json.dumps(Forecast3))
    B2_ElecFC.set_value(json.dumps(Forecast4))
        
    E_Costs.set_value(-E_Price[i])
    
    
    B1_Pp_Coup1.set_value(B1_Eff1_Coup1*P_Geb1[i]/time_factor)
    B1_Ps_Coup1.set_value(B1_Eff2_Coup1*P_Geb1[i]/time_factor)
    B1_P_VProd1.set_value(B1_Eff_VProd1*P_Geb1[n+i]/time_factor)
    B1_P_in_Stor1.set_value(B1_Eff_Stor1*P_Geb1[2*n+i]/time_factor)
    B1_P_out_Stor1.set_value(B1_Eff_Stor1*P_Geb1[3*n+i]/time_factor)
    # SOC in Prozent
    B1_SOC_Stor1.set_value(B1_SOC_Stor1.get_value()+B1_P_in_Stor1.get_value()/B1_Cap_Stor1-B1_P_out_Stor1.get_value()/B1_Cap_Stor1)


    B2_Pp_Coup1.set_value(B2_Eff1_Coup1*P_Geb2[i]/time_factor)
    B2_Ps_Coup1.set_value(B2_Eff2_Coup1*P_Geb2[i]/time_factor)
    B2_P_VProd1.set_value(B2_Eff_VProd1*P_Geb2[n+i]/time_factor)
    B2_P_in_Stor1.set_value(B2_Eff_Stor1*P_Geb2[2*n+i]/time_factor)
    B2_P_out_Stor1.set_value(B2_Eff_Stor1*P_Geb2[3*n+i]/time_factor)
    # SOC in Prozent
    B2_SOC_Stor1.set_value(B2_SOC_Stor1.get_value()+B2_P_in_Stor1.get_value()/B2_Cap_Stor1-B2_P_out_Stor1.get_value()/B2_Cap_Stor1)


    print(i+1, "B1: ", ElecPower_B1.get_value(), HeatPower_B1.get_value(), "B2: " , ElecPower_B2.get_value(), HeatPower_B2.get_value())
    #print(i, ElecPower_B1.get_value(), HeatPower_B1.get_value(), ElecPower_B2.get_value(), HeatPower_B2.get_value())
    #print(" ")
    
    # We cut away 5 timesteps from the day here for the MPC
    if i < size-5:
        i += 1
    else:
        i -= size
        
    time.sleep(10)
'''