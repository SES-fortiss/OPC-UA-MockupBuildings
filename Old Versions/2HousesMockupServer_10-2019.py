# -*- coding: utf-8 -*-
"""
Created on Tue Oct 16 17:20:59 2018

@author: mayer
"""

#from opcua import Server
from createBuilding import create_Server_Basics, create_Namespace, add_Demand, add_VolatileProducer, add_Coupler, add_Producer, add_Storage

import time
import numpy as np
import json
#import requests, json
#import random

mpc = 5
time_factor = 0.25
n = 192
size = n
#size = 1440


# ============================== Building 1 ==============================
Geb = "Building1"
(server1, url1, idx, objects) = create_Server_Basics(Geb,"4880")

# ================= Defining the Namespace Building 1 =====================
(General, Demand, Systems, Producer, VolatilePruducer, Coupler, Storage) = create_Namespace(server1, idx, objects)

### General
BuildingClass =  General.add_variable(idx, "BuildingClass", "Multi-Family-Home")

### Demand   -   add_Demand(idx, Demand, H_minT, C_maxT, E_cost, H_cost, C_cost)
(HeatPower_B1, H_Costs, ElecPower_B1, E_Costs, ColdPower_B1, C_Costs) = add_Demand(idx, Demand, 75, 20, 0 , 5.34, 0)


### Anlagen
# Producer - add_Producer(idx, Geb, Producer, Medium, Eff, P_min, P_max, Temp)
#(B1_Prod1, B1_Prod1_Eff) = add_Producer(idx, Geb, Producer, "Heat", 0.98, 30, 80, 80)
#(B1_Prod2, B1_Prod2_Eff) = add_Producer(idx, Geb, Producer, "Electricity", 0.86, 3, 12, 0)

# VolatileProducer - add_VolatileProducer(idx, Geb, VolatilePruducer, Medium, Eff, Area, Temp):
(B1_P_VProd1, B1_Eff_VProd1, B1_Ppeak_VProd1) = add_VolatileProducer(idx, Geb+"_Photovoltaik", VolatilePruducer, "Electricity", 0.18, 18, 0)

# Coupler - add_Coupler(idx, Geb, Coupler, Medium1, Medium2, Eff1, Eff2, P_min, P_max, Temp)
(B1_Pp_Coup1, B1_Eff1_Coup1, B1_Ps_Coup1, B1_Eff2_Coup1, B1_P_max1_Coup1, B1_P_max2_Coup1) = add_Coupler(idx,  Geb+"_Heatpump", Coupler, "Heat", "Electricity", 3.8, -1, 0, 10, 40)

# Storage - add_Storage(idx, name, Storage, Medium, Eff, Capacity, Pmax_in, Pmax_Out, Temp, SOC_alt)
(B1_Eff_Stor1, B1_Cap_Stor1, B1_P_in_Stor1, B1_P_out_Stor1, B1_SOC_Stor1, B1_P_maxOut_Stor1) = add_Storage(idx, Geb+"_Battery", Storage, "Electricity", 0.98, 12, 3.3, 3.3, 0, 0.5)

# Anlagen - Allgemein
# nicht sehr allgemein gehalten. Hier wäre if (VolatilePruducer.get_variables(Med) == "Electricity"): besser 
B1_Elec_MaxP_total = Systems.add_variable(idx, Geb+"totalPowerCapacity_Elec", B1_Ppeak_VProd1 + B1_P_max2_Coup1 + B1_P_maxOut_Stor1)
B1_Heat_MaxP_total = Systems.add_variable(idx, Geb+"totalPowerCapacity_Heat", B1_P_max1_Coup1)

# Forecast
Forecast = Demand.add_folder(idx, "Forecast")

Heat_FC = Forecast.add_folder(idx, "Heat_FC")
B1_HeatFC = Heat_FC.add_variable(idx, "HeatFC", "")  
                  
Elec_FC = Forecast.add_folder(idx, "Elec_FC")
B1_ElecFC = Elec_FC.add_variable(idx, "ElecFC", "")

# ============================== Building 2 ==============================
Geb = "Building2"
(server2, url2, idx, objects) = create_Server_Basics(Geb,"4890")

# ================= Defining the Namespace Building 2 =====================
(General, Demand, Systems, Producer, VolatilePruducer, Coupler, Storage) = create_Namespace(server2, idx, objects)


#General = objects.add_object(idx, "General")
BuildingClass =  General.add_variable(idx, "BuildingClass", "Multi-Family-Home")

### Demand   -   add_Demand(idx, Demand, minT, maxT, E_cost, H_cost, C_cost)
(HeatPower_B2, H_Costs, ElecPower_B2, E_Costs, ColdPower_B2, C_Costs) = add_Demand(idx, Demand, 40, 22, 0, 5.34, 0)


### Anlagen

# Producer - add_Producer(idx, Geb, Producer, Medium, Eff, P_min, P_max, Temp)

# VolatileProducer - add_VolatileProducer(idx, Geb, VolatilePruducer, Medium, Eff, Area, Temp):
(B2_P_VProd1, B2_Eff_VProd1, B2_Ppeak_VProd1) = add_VolatileProducer(idx, Geb+"_Solarthermic", VolatilePruducer, "Heat", 0.5, 3, 110)

# Coupler - add_Coupler(idx, Geb, Coupler, Medium1, Medium2, Eff1, Eff2, P_min, P_max, Temp)
(B2_Pp_Coup1, B2_Eff1_Coup1, B2_Ps_Coup1, B2_Eff2_Coup1, B2_P_max1_Coup1, B2_P_max2_Coup1) = add_Coupler(idx,  Geb+"_CHP", Coupler, "Heat", "Electricity", 0.6, 0.25, 0, 3.6, 80)

# Storage - add_Storage(idx, name, Storage, Medium, Eff, Capacity, Pmax_in, Pmax_Out, Temp, SOC_alt)
(B2_Eff_Stor1, B2_Cap_Stor1, B2_P_in_Stor1, B2_P_out_Stor1, B2_SOC_Stor1, B2_P_maxOut_Stor1) = add_Storage(idx, Geb+"_ThermalStorage", Storage, "Heat", 0.98, 20, 5, 5, 80, 0.5)

# Anlagen - Allgemein
# nicht sehr allgemein gehalten. Hier wäre if (VolatilePruducer.get_variables(Med) == "Electricity"): besser 
B2_Elec_MaxP_total = Systems.add_variable(idx, Geb+"totalPowerCapacity_Elec",  B2_P_max2_Coup1)
B2_Heat_MaxP_total = Systems.add_variable(idx, Geb+"totalPowerCapacity_Heat", B2_Ppeak_VProd1 + B2_P_max1_Coup1 + B2_P_maxOut_Stor1)

# Forecast

# Forecast
Forecast = Demand.add_folder(idx, "Forecast")

Heat_FC = Forecast.add_folder(idx, "Heat_FC")
B2_HeatFC = Heat_FC.add_variable(idx, "HeatFC", "")  
                    
Elec_FC = Forecast.add_folder(idx, "Elec_FC")
B2_ElecFC = Elec_FC.add_variable(idx, "ElecFC", "")     



# =============================== Start ===================================
server1.start()
print("Server1 started at {}".format(url1))
server1.PublishingEnabled = True

server2.start()
print("Server2 started at {}".format(url2))
server2.PublishingEnabled = True
# =========================================================================


# ==================== Load 2 Days from Simulation ========================
Consumption_B1 = np.genfromtxt("ConsumptionGEB1.csv", delimiter=";")
Consumption_B2 = np.genfromtxt("ConsumptionGEB2.csv", delimiter=";")

P_Geb1 = np.genfromtxt("XvectorGEB1.csv", delimiter=";")
P_Geb2 = np.genfromtxt("XvectorGEB2.csv", delimiter=";")
E_Price = np.genfromtxt("YIpriceOrig.csv", delimiter=";")



# ============================= set values =================================
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
