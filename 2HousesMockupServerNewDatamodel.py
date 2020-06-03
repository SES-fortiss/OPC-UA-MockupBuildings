# -*- coding: utf-8 -*-
"""
Created on Tue Oct 16 17:20:59 2018
Updated on Tue May 22 11:20:00 2020


@author: mayer
"""

#from opcua import Server
from createBuildingNewDatamodel import create_Server_Basics, create_Namespace, add_Demand, add_VolatileProducer, add_Coupler, add_Producer, add_Storage, add_General

import time
import numpy as np
#import json
#import requests, json
#import random

mpc = 5
time_factor = 0.25
n = 192
size = n
#size = 1440
Value = 0.0

objectName = "LS02"
nrOfEms = 2

demandPath1 = "data/ConsumptionGEB1.csv"
demandPath2 = "data/ConsumptionGEB2.csv"

# Add Counter list/array to count for numer of EMS x Device Types and construct display names
# Entries for DEMND, PROD, VPROD, COUPL, STRGE
counter = np.zeros([nrOfEms,5])


# ================= Defining the Namespace of the Building =====================

# ============================== Building 1 ==============================
EMS = "EMS01"
naming = objectName + EMS + "OBJ01"
# Add Counter list/array to count for numer of EMS x Device Types and construct display names
# Entries for DEMND, PROD, VPROD, COUPL, STRGE
counter = np.zeros([nrOfEms,5])


(server1, url1, idx, objects) = create_Server_Basics(objectName, EMS,"4880")

# ================= Defining the Namespace Building 1 =====================
(General, Demand, Systems, Producer, VolatileProducer, Coupler, Storage) = create_Namespace(server1, idx, objects)

### General
# add_General(idx, naming, General, url, connectionStat, EMSname, buildCat)
(endPoint, connStat, EMSnameID, bCategory) = add_General(idx, naming, General, url1, True, "MFH1_EMS", "Multi-Family-Home")

### Demand
(B1_heatDemandSP, B1_htDemFCarray, B1_elBuyCost) = add_Demand(counter, naming, idx, Demand, "heat", "Wärmebedarf_Haus1", mpc, 60*time_factor, 30, 40, 5.34, 999.0)
(B1_elecDemandSP, B1_elDemFCarray, B1_htBuyCost) = add_Demand(counter, naming, idx, Demand, "elec", "Strombedarf_Haus1", mpc, 60*time_factor, 0.0, 0.0, B1_elBuyCost, 0.0)

### Anlagen

# VolatileProducer
B1_Eff_VProd1 = 0.18
(B1_vProd1_Power) = add_VolatileProducer(counter, naming, idx, "MFH1_PV", VolatileProducer, True, "elec", 3.24, 0.0, 0.0,  mpc, 60*time_factor,  0.0, 0.0, 0.0)

# Coupler 
B1_Eff1_Coup1 = 3.8
B1_Eff2_Coup1 = -1
(B1_Prod1_Setpoint, B1_Prod1_Power1, B1_Prod1_Power2) = add_Coupler(counter, naming, idx, "MFH1_HP", Coupler, True, "heat", "elec", B1_Eff1_Coup1 , B1_Eff2_Coup1, 3, 10, 30, 55, mpc, 0.0, 0.0, 0.0)
    
# Storage 
B1_Eff_Stor1 = 0.98
B1_Cap_Stor1 = 6
(B1_Stor1_setpointChgFC, B1_Stor1_setpointDisChgFC, B1_Stor1_SOC) = add_Storage(counter, naming, mpc, idx, "MFH1_Bat", Storage, True, "elec", B1_Eff_Stor1, B1_Eff_Stor1 , B1_Cap_Stor1, 0.0, 3.3, 3.3, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0)

# Anlagen - Allgemein
# nicht sehr allgemein gehalten. Hier wäre if (VolatileProducer.get_variables(Med) == "Electricity"): besser 
#B1_Elec_MaxP_total = Systems.add_variable(idx, Geb+"totalPowerCapacity_Elec", B1_Ppeak_VProd1 + B1_P_max2_Coup1 + B1_P_maxOut_Stor1)
#B1_Heat_MaxP_total = Systems.add_variable(idx, Geb+"totalPowerCapacity_Heat", B1_P_max1_Coup1)

'''
# Forecast
Forecast = Demand.add_folder(idx, "Forecast")

Heat_FC = Forecast.add_folder(idx, "Heat_FC")
B1_HeatFC = Heat_FC.add_variable(idx, "HeatFC", "")  

                    
Elec_FC = Forecast.add_folder(idx, "Elec_FC")
B1_ElecFC = Elec_FC.add_variable(idx, "ElecFC", "")
'''

# Export Namespace as XML
# server1.export_xml_by_ns("NamespaceMockupServer1.xml")




# ============================== Building 2 ==============================
EMS = "EMS02"
naming = objectName + EMS + "OBJ01"
# Add Counter list/array to count for numer of EMS x Device Types and construct display names
# Entries for DEMND, PROD, VPROD, COUPL, STRGE
counter = np.zeros([nrOfEms,5])

(server2, url2, idx, objects) = create_Server_Basics(objectName, EMS, "4890")

# ================= Defining the Namespace Building 2 =====================
(General, Demand, Systems, Producer, VolatileProducer, Coupler, Storage) = create_Namespace(server2, idx, objects)

#General = objects.add_object(idx, "General")
(endPoint, connStat, EMSnameID, bCategory) = add_General(idx, naming, General, url2, True, "MFH2_EMS", "Multi-Family House")

### Demand
(B2_heatDemandSP, B2_htDemFCarray, B2_elBuyCost) = add_Demand(counter, naming, idx, Demand, "heat", "Wärmebedarf_Haus2", mpc, 60*time_factor, 40, 120, 5.34, 999.0)
(B2_elecDemandSP, B2_elDemFCarray, B2_htBuyCost) = add_Demand(counter, naming, idx, Demand, "elec", "Strombedarf_Haus2", mpc, 60*time_factor, 0.0, 0.0, B2_elBuyCost, 0.0)


### Anlagen

# VolatileProducer
B2_Eff_VProd1 = 0.5
(B2_vProd1_Power) = add_VolatileProducer(counter, naming, idx, "MFH2_ST", VolatileProducer, True, "heat", 1.5, 20.0, 110.0,  mpc, 60*time_factor,  0.0, 0.0, 0.0)

# Coupler
B2_Eff1_Coup1 = .6
B2_Eff2_Coup1 = .25
(B2_Prod1_Setpoint, B2_Prod1_Power1, B2_Prod1_Power2) = add_Coupler(counter, naming, idx, "MFH2_uCHP", Coupler, True, "heat", "elec", B2_Eff1_Coup1, B2_Eff2_Coup1, 1, 3.6, 80, 100, mpc, 0.0, 0.0, 0.0)

# Storage 
B2_Eff_Stor1 = 0.98
B2_Cap_Stor1 = 20
(B2_Stor1_setpointChgFC, B2_Stor1_setpointDisChgFC, B2_Stor1_SOC) = add_Storage(counter, naming, mpc, idx, "MFH2_TS", Storage, True, "heat", B2_Eff_Stor1, B2_Eff_Stor1 , B2_Cap_Stor1, 0.0, 5, 5, 60, 90, 60, 0.5, 0.0, 0.0, 0.0)


# Anlagen - Allgemein
# nicht sehr allgemein gehalten. Hier wäre if (VolatileProducer.get_variables(Med) == "Electricity"): besser 
# B2_Elec_MaxP_total = Systems.add_variable(idx, Geb+"totalPowerCapacity_Elec",  B2_P_max2_Coup1)
# B2_Heat_MaxP_total = Systems.add_variable(idx, Geb+"totalPowerCapacity_Heat", B2_Ppeak_VProd1 + B2_P_max1_Coup1 + B2_P_maxOut_Stor1)

'''
# Forecast
Forecast = Demand.add_folder(idx, "Forecast")

Heat_FC = Forecast.add_folder(idx, "Heat_FC")
B2_HeatFC = Heat_FC.add_variable(idx, "HeatFC", "")  

                    
Elec_FC = Forecast.add_folder(idx, "Elec_FC")
B2_ElecFC = Elec_FC.add_variable(idx, "ElecFC", "")     
'''

# Export Namespace as XML
# server2.export_xml(Systems.get_children(), "NamespaceMockupServer2.xml")







# =============================== Start ===================================
server1.start()
print("Server1 started at {}".format(url1))
server1.PublishingEnabled = True

server2.start()
print("Server2 started at {}".format(url2))
server2.PublishingEnabled = True
# =========================================================================


# ==================== Load 2 Days from Simulation ========================
Consumption_B1 = np.genfromtxt("data/ConsumptionGEB1.csv", delimiter=";")
Consumption_B2 = np.genfromtxt("data/ConsumptionGEB2.csv", delimiter=";")

P_Geb1 = np.genfromtxt("data/XvectorGEB1.csv", delimiter=";")
P_Geb2 = np.genfromtxt("data/XvectorGEB2.csv", delimiter=";")
E_Price = np.genfromtxt("data/YIpriceOrig.csv", delimiter=";")


# ============================= set values =================================
i = 0

while True:
   
    '''
    # convert from kwh to kw with time_factor
    B1_heatDemandSP.set_value(Consumption_B1[i]/time_factor)
    B2_heatDemandSP.set_value(Consumption_B2[i]/time_factor)
    B1_elecDemandSP.set_value(Consumption_B1[n+i]/time_factor)
    B2_elecDemandSP.set_value(Consumption_B2[n+i]/time_factor)
    
    
    # Forecast in JSON Format
    Forecast1 = {}
    Forecast2 = {}
    Forecast3 = {}
    Forecast4 = {}
    
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
    ''' 
    
   
    for j in range(mpc):
        B1_elDemFCarray.get_value()[j] = Consumption_B1[n+i+j]/time_factor
        B2_elDemFCarray.get_value()[j] = Consumption_B2[n+i+j]/time_factor
        B1_htDemFCarray.get_value()[j] = Consumption_B1[i+j]/time_factor
        B2_htDemFCarray.get_value()[j] = Consumption_B2[i+j]/time_factor
    
    B1_elBuyCost.set_value(-E_Price[i])
    B2_elBuyCost.set_value(-E_Price[i])
    
    
    B1_Prod1_Power1.set_value(B1_Eff1_Coup1*P_Geb1[i]/time_factor)
    B1_Prod1_Power2.set_value(B1_Eff2_Coup1*P_Geb1[i]/time_factor)
    B1_vProd1_Power.set_value(B1_Eff_VProd1*P_Geb1[n+i]/time_factor)

    B1_Stor1_Chg = B1_Eff_Stor1*P_Geb1[2*n+i]/time_factor
    B1_Stor1_DisChg = B1_Eff_Stor1*P_Geb1[3*n+i]/time_factor
    
    # Wenn MEMAP Setpoints schreibt:
    # B1_Stor1_Chg = B1_Stor1_setpointChgFC.get_value()[0]
    
    # SOC in Prozent
    B1_SOC_change = B1_Stor1_Chg*time_factor - B1_Stor1_DisChg*time_factor # in kWh
    B1_Stor1_SOC.set_value(B1_Stor1_SOC.get_value() + B1_SOC_change/ B1_Cap_Stor1)


    B2_Prod1_Power1.set_value(B2_Eff1_Coup1*P_Geb2[i]/time_factor)
    B2_Prod1_Power2.set_value(B2_Eff2_Coup1*P_Geb2[i]/time_factor)
    B2_vProd1_Power.set_value(B2_Eff_VProd1*P_Geb2[n+i]/time_factor)
    B2_Stor1_Chg = B2_Eff_Stor1*P_Geb2[2*n+i]/time_factor
    B2_Stor1_DisChg = B2_Eff_Stor1*P_Geb2[3*n+i]/time_factor
    
    # SOC in Prozent
    B2_SOC_change = B2_Stor1_Chg*time_factor - B2_Stor1_DisChg*time_factor # in kWh
    B2_Stor1_SOC.set_value(B2_Stor1_SOC.get_value() + B2_SOC_change/ B2_Cap_Stor1)

    print(i+1, "B1: ", B1_elDemFCarray.get_value()[0], B1_htDemFCarray.get_value()[0], "B2: " , B2_elDemFCarray.get_value()[0], B2_htDemFCarray.get_value()[0])
    #print(i, ElecPower_B1.get_value(), HeatPower_B1.get_value(), ElecPower_B2.get_value(), HeatPower_B2.get_value())
    #print(" ")
    
    # We cut away 5 timesteps from the day here for the MPC
    if i < size-5:
        i += 1
    else:
        i -= size
        
    time.sleep(10)
