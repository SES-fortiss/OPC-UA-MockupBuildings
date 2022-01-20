# -*- coding: utf-8 -*-
"""
Created on Tue Oct 16 17:20:59 2018
Updated on Tue May 22 11:20:00 2020


@author: mayer
"""

#from opcua import Server
from createBuilding_NewDatamodel import create_Server_Basics, create_Namespace, add_Demand, add_VolatileProducer, add_Coupler, add_Producer, add_Storage, add_General

import time
import numpy as np
#import json
#import requests, json
#import random

mpc = 5
time_factor = 1
n = 24
size = n
#size = 1440
Value = 0.0

objectName = "LS02"
nrOfEms = 2

demandPath1 = "data/Geb1/Geb1_15min.csv"
demandPath2 = "data/Geb2/Geb2_15min.csv"


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
(B1_MemapActive, B1_endPoint, B1_EMSnameID, B1_trigger) = add_General(idx, naming, General, True, url1, True, "MFH1_EMS", "Electric-Multi-Family-Home")
### Demand
																								   
(B1_heatDemandSP, B1_htDemFCarray, B1_currHtDem, B1_htBuyCost, B1_htBuyCostAr, B1_htSellCost, B1_htSellCostAr) = add_Demand(counter, naming, idx, Demand, "heat", "Wärmebedarf_Haus1", mpc, 60*time_factor, 30, 40, 0.0534, 999.0)
(B1_elecDemandSP, B1_elDemFCarray, B1_currElDem, B1_elBuyCost, B1_elBuyCostAr, B1_elSellCost, B1_elSellCostAr) = add_Demand(counter, naming, idx, Demand, "elec", "Strombedarf_Haus1", mpc, 60*time_factor, 0.0, 0.0, 0.3, 0.15)

### Anlagen

# VolatileProducer - PV-Installation
B1_Eff_VProd1 = 0.181
B1_area_VProd1 = 18.23 #m²						   
(B1_vProd1_CrtPower, B1_vProd1_PowerFC) = add_VolatileProducer(counter, naming, idx, "MFH1_PV", VolatileProducer, True, "elec", B1_Eff_VProd1*B1_area_VProd1, 0.0, 0.0,  mpc, 60*time_factor,  0.0, 0.0, 0.0)

# Coupler  - Heatpump
B1_Eff1_Coup1 = 3.8
B1_Eff2_Coup1 = -1
B1_P_min_Coup1 = 0
B1_P_max_Coup1 = 12				  		   
(B1_Prod1_Setpoint, B1_Prod1_Power1, B1_Prod1_Power2) = add_Coupler(counter, naming, idx, "MFH1_HP", Coupler, True, "heat", "elec", B1_Eff1_Coup1 , B1_Eff2_Coup1, B1_P_min_Coup1, B1_P_max_Coup1, 30, 55, mpc, 0.0, 0.0, 0.0)
    
# Storage - Battery
B1_Eff_Stor1 = 0.97
B1_P_ChDisCh = 3.3				  
B1_Cap_Stor1 = 10
B1_StartSOC = 0.5				 
(B1_Stor1_In, B1_Stor1_Out, B1_Stor1_setpointChgFC, B1_Stor1_setpointDisChgFC, B1_Stor1_SOC, B1_Stor1_losses) = add_Storage(counter, naming, mpc, idx, "MFH1_Bat", Storage, True, "elec", B1_Eff_Stor1, B1_Eff_Stor1, B1_Cap_Stor1, 0.0, B1_P_ChDisCh, B1_P_ChDisCh, 0.0, 0.0, 0.0, B1_StartSOC, 0.0, 0.0, 0.0)

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
(B2_MemapActive, B2_endPoint, B2_EMSnameID, B2_trigger) = add_General(idx, naming, General, True, url2, True, "MFH2_EMS", "Gas-Multi-Family House")

### Demand
(B2_heatDemandSP, B2_htDemFCarray, B2_currHtDem, B2_htBuyCost, B2_htBuyCostAr, B2_htSellCost, B2_htSellCostAr) = add_Demand(counter, naming, idx, Demand, "heat", "Wärmebedarf_Haus2", mpc, 60*time_factor, 40, 120, 0.0534, 999.0)
(B2_elecDemandSP, B2_elDemFCarray, B2_currElDem, B2_elBuyCost, B2_elBuyCostAr, B2_elSellCost, B2_elSellCostAr) = add_Demand(counter, naming, idx, Demand, "elec", "Strombedarf_Haus2", mpc, 60*time_factor, 0.0, 0.0, 0.3, 0.15)


### Anlagen

# VolatileProducer
B2_Eff_VProd1 = 0.5
B2_area_VProd1 = 8				  
(B2_vProd1_CrtPower, B2_vProd1_PowerFC) = add_VolatileProducer(counter, naming, idx, "MFH2_ST", VolatileProducer, True, "heat", B2_Eff_VProd1*B2_area_VProd1, 20.0, 110.0,  mpc, 60*time_factor,  0.0, 0.0, 0.0)

# Coupler
B2_Eff1_Coup1 = .6
B2_Eff2_Coup1 = .25
B2_P_min_Coup1 = .5
B2_P_max_Coup1 = 6.6					
(B2_Prod1_Setpoint, B2_Prod1_Power1, B2_Prod1_Power2) = add_Coupler(counter, naming, idx, "MFH2_uCHP", Coupler, True, "heat", "elec", B2_Eff1_Coup1, B2_Eff2_Coup1, B2_P_min_Coup1, B2_P_max_Coup1, 80, 100, mpc, 0.059, 0.059, 0.202)

# Storage 
B2_Eff_Stor1 = 0.98
B2_P_ChDisCh = 10				 
B2_Cap_Stor1 = 20
B2_StartSOC = 0.5				 
(B2_Stor1_In, B2_Stor1_Out, B2_Stor1_setpointChgFC, B2_Stor1_setpointDisChgFC, B2_Stor1_SOC, B2_Stor1_losses) = add_Storage(counter, naming, mpc, idx, "MFH2_TS", Storage, True, "heat", B2_Eff_Stor1, B2_Eff_Stor1 , B2_Cap_Stor1, 0.0, B2_P_ChDisCh, 0, 60, 90, 60, B2_StartSOC, 0.0, 0.0, 0.0)


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
Consumption_B1 = np.genfromtxt(demandPath1, delimiter=";")
Consumption_B2 = np.genfromtxt(demandPath2, delimiter=";")

P_B1_Vprod = np.genfromtxt("data/Geb1/PVG1.csv", delimiter=";")
P_B2_Vprod = np.genfromtxt("data/Geb2/STG2.csv", delimiter=";")

P_B1_Strge = np.genfromtxt("data/Geb1/BATG1.csv", delimiter=";")
P_B2_Strge = np.genfromtxt("data/Geb2/WSPG2.csv", delimiter=";")


E_Price = np.genfromtxt("data/YIpriceOrig.csv", delimiter=";")

# ============================= set values =================================
i = 0

while True:
   
    # convert from kwh to kw with time_factor, New input is already in kW
    
    # ToDo: Methode: Add data to forecast for building 
    demForecast1 = [Consumption_B1[i+1 + x, 2] for x in range(mpc)]
    B1_elDemFCarray.set_value(demForecast1)
    
    demForecast2 = [Consumption_B2[i+1 + x, 2] for x in range(mpc)]
    B2_elDemFCarray.set_value(demForecast2)
    
    demForecast3 = [Consumption_B1[i+1 + x, 3] for x in range(mpc)]
    B1_htDemFCarray.set_value(demForecast3)
    
    demForecast4 = [Consumption_B2[i+1 + x, 3] for x in range(mpc)]
    B2_htDemFCarray.set_value(demForecast4)
   
    B1_currElDem.set_value(Consumption_B1[i,2])
    B2_currElDem.set_value(Consumption_B2[i,2])
    B1_currHtDem.set_value(Consumption_B1[i,3])
    B2_currHtDem.set_value(Consumption_B2[i,3])
        
    
    '''
    for j in range(mpc):
        B1_elDemFCarray.get_value()[j] = Consumption_B1[n+i+j]/time_factor
        B2_elDemFCarray.get_value()[j] = Consumption_B2[n+i+j]/time_factor
        B1_htDemFCarray.get_value()[j] = Consumption_B1[i+j]/time_factor
        B2_htDemFCarray.get_value()[j] = Consumption_B2[i+j]/time_factor
    '''
    
    # Variable Strompreise
    # Aber beide Häuser gleich
    elBuyCosts1 = [E_Price[i+1 + x]/100 for x in range(mpc)]
    B1_elBuyCostAr.set_value(elBuyCosts1)
    elBuyCosts2 = [E_Price[i+1 + x]/100 for x in range(mpc)]
    B2_elBuyCostAr.set_value(elBuyCosts2)
    

    # Solare Produktion
    vprodForecast1 = [P_B1_Vprod[i+1 + x] for x in range(mpc)]
    B1_vProd1_PowerFC.set_value(vprodForecast1)
    B1_vProd1_CrtPower.set_value(P_B1_Vprod[i])
    
    vprodForecast2 = [P_B2_Vprod[i+1 + x] for x in range(mpc)]
    B2_vProd1_PowerFC.set_value(vprodForecast2)
    B2_vProd1_CrtPower.set_value(P_B2_Vprod[i])
    
    
    # Update SOC
    
    if (B1_MemapActive.get_value()):
        B1_Stor1_In.set_value(B1_Stor1_setpointChgFC.get_value()[0])
        B1_Stor1_Out.set_value(B1_Stor1_setpointDisChgFC.get_value()[0])
    else:
        B1_Stor1_In.set_value(P_B1_Strge[i,1])
        B1_Stor1_Out.set_value(P_B1_Strge[i,0])
    
    if (B2_MemapActive.get_value()):    
        B2_Stor1_In.set_value(B2_Stor1_setpointChgFC.get_value()[0])
        B2_Stor1_Out.set_value(B2_Stor1_setpointDisChgFC.get_value()[0])
    else:
        B2_Stor1_In.set_value(P_B2_Strge[i,1])
        B2_Stor1_Out.set_value(P_B2_Strge[i,0])

    B2_Stor1_losses.set_value(list(np.ones(5) * 0.05))

    # ToDo : Losses berücksichtigen
    B1_StorChange = time_factor * (B1_Stor1_In.get_value() - B1_Stor1_Out.get_value()) / B1_Cap_Stor1 # Änderung in Prozent der Capazität
    B2_StorChange = time_factor * (B2_Stor1_In.get_value() - B2_Stor1_Out.get_value()) / B2_Cap_Stor1 # Änderung in Prozent der Capazität
    # SOC in Prozent
    B1_Stor1_SOC.set_value(B1_Stor1_SOC.get_value() + B1_StorChange)
    B2_Stor1_SOC.set_value(B2_Stor1_SOC.get_value() + B2_StorChange)
    

    print(i+1, "B1 strge: ", B1_Stor1_In.get_value(), B1_Stor1_Out.get_value(), B1_Stor1_SOC.get_value(), " demnd: ", demForecast1[0], demForecast3[0])
    print(i+1, "B2 strge: " ,B2_Stor1_In.get_value(), B2_Stor1_Out.get_value(), B2_Stor1_SOC.get_value(), " demnd: ", demForecast2[0], demForecast4[0])
    print(" ")
    
    # We cut away 5 timesteps from the day here for the MPC
    if i < size-mpc-1:
        i += 1
    else:
        i = 0
        
    time.sleep(15)    
    
    
def BuildingModel(ArrayIn):
    
    losses = np.ones(5) * 5
    return losses
    
    
'''
OLD VERSION
    
   
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
 '''
