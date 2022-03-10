# -*- coding: utf-8 -*-
"""
Created on Tue Oct 16 17:20:59 2018
Updated on Tue May 22 11:20:00 2020


@author: mayer
"""

#from opcua import Server
from createBuilding_MemapDatamodel import create_Server_Basics, create_Namespace, add_Demand, add_VolatileProducer, add_Coupler, add_Producer, add_Storage, add_General

import time
import numpy as np
#import json
#import requests, json
#import random

mpc = 5
steptime = 15

n = 96
time_factor = 24/n
size = n

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
B1_elecBuy_grid = 0.26
B1_elecSell_grid = 0.03
B1_Co2perKwh_grid = 0.474
B1_maxbuy_grid = 9999.0
																							   
(B1_htDemFCarray, B1_htBuyCostAr, B1_htSellCostAr) = add_Demand(counter, naming, idx, Demand, "heat", "Wärmebedarf_Haus1", mpc, 0.0534, 999.0, 0.0, 0.0)
(B1_elDemFCarray, B1_elBuyCostAr, B1_elSellCostAr) = add_Demand(counter, naming, idx, Demand, "elec", "Strombedarf_Haus1", mpc, B1_elecBuy_grid, B1_elecSell_grid, B1_Co2perKwh_grid, B1_maxbuy_grid)

### Anlagen

# VolatileProducer - PV-Installation
B1_Eff_VProd1 = 0.181
B1_area_VProd1 = 18.23 #m²						   
(B1_vProd1_PowerFC) = add_VolatileProducer(counter, naming, idx, "MFH1_PV", VolatileProducer, True, "elec", B1_Eff_VProd1*B1_area_VProd1, mpc, 0.0, 0.0)

# Coupler  - Heatpump
B1_Eff1_Coup1 = 3.8
B1_Eff2_Coup1 = -1
B1_P_min_Coup1 = 0
B1_P_max_Coup1 = 12				  		   
(B1_Prod1_Costs, B1_Prod1_PowerSP) = add_Coupler(counter, naming, idx, "MFH1_HP", Coupler, True, "heat", "elec", B1_Eff1_Coup1 , B1_Eff2_Coup1, B1_P_min_Coup1, B1_P_max_Coup1, mpc, 0.0, 0.0)
    
# Storage - Battery
B1_Eff_Stor1 = 0.97
B1_P_ChDisCh = 3.3				  
B1_Cap_Stor1 = 10
B1_StartSOC = 0.5				 
B1_losses = 0.05
(B1_Stor1_losses, B1_Stor1_SPChg, B1_Stor1_SPDisChg, B1_Stor1_SOC) = add_Storage(counter, naming, mpc, idx, "MFH1_Bat", Storage, True, "elec", B1_Eff_Stor1, B1_Eff_Stor1, B1_Cap_Stor1, B1_losses, B1_P_ChDisCh, B1_P_ChDisCh, B1_StartSOC, 0.0, 0.0)

# Export Namespace as XML
server1.export_xml_by_ns("NamespaceMockupServer1.xml")




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
B2_elecBuy_grid = 0.26
B2_elecSell_grid = 0.03
B2_Co2perKwh_grid = 0.474
B2_maxbuy_grid = 9999.0

(B2_htDemFCarray, B2_htBuyCostAr, B2_htSellCostAr) = add_Demand(counter, naming, idx, Demand, "heat", "Wärmebedarf_Haus2", mpc, 0.0534, 999.0, 0.0, 0.0)
(B2_elDemFCarray, B2_elBuyCostAr, B2_elSellCostAr) = add_Demand(counter, naming, idx, Demand, "elec", "Strombedarf_Haus2", mpc,B2_elecBuy_grid, B2_elecSell_grid, B2_Co2perKwh_grid, B2_maxbuy_grid)


### Anlagen

# VolatileProducer
B2_Eff_VProd1 = 0.5
B2_area_VProd1 = 8				  
(B2_vProd1_PowerFC) = add_VolatileProducer(counter, naming, idx, "MFH2_ST", VolatileProducer, True, "heat", B2_Eff_VProd1*B2_area_VProd1, mpc, 0.0, 0.0 )

# Coupler
B2_Eff1_Coup1 = .6
B2_Eff2_Coup1 = .25
B2_P_min_Coup1 = .5
B2_P_max_Coup1 = 6.6					
(B2_Prod1_Costs, B2_Prod1_PowerSP) = add_Coupler(counter, naming, idx, "MFH2_uCHP", Coupler, True, "heat", "elec", B2_Eff1_Coup1, B2_Eff2_Coup1, B2_P_min_Coup1, B2_P_max_Coup1, mpc, 0.059, 0.202)

# Storage 
B2_Eff_Stor1 = 0.98
B2_P_ChDisCh = 10				 
B2_Cap_Stor1 = 20
B2_StartSOC = 0.5		
B2_losses = 0.05			 
(B2_Stor1_losses, B2_Stor1_SPChg, B2_Stor1_SPDisChg, B2_Stor1_SOC) = add_Storage(counter, naming, mpc, idx, "MFH2_TS", Storage, True, "heat", B2_Eff_Stor1, B2_Eff_Stor1 , B2_Cap_Stor1, B2_losses, B2_P_ChDisCh, B2_P_ChDisCh, B2_StartSOC, 0.0, 0.0)


# Export Namespace as XML
server2.export_xml(Systems.get_children(), "NamespaceMockupServer2.xml")




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

while B1_trigger.get_value() == 0:    
     time.sleep(0.5)    

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
      

    # Variable Strompreise
    # Aber beide Häuser gleich
    elBuyCosts1 = [E_Price[i+1 + x]/100 for x in range(mpc)]
    B1_elBuyCostAr.set_value(elBuyCosts1)
    elBuyCosts2 = [E_Price[i+1 + x]/100 for x in range(mpc)]
    B2_elBuyCostAr.set_value(elBuyCosts2)
    

    # Solare Produktion
    vprodForecast1 = [P_B1_Vprod[i+1 + x] for x in range(mpc)]
    B1_vProd1_PowerFC.set_value(vprodForecast1)
    
    vprodForecast2 = [P_B2_Vprod[i+1 + x] for x in range(mpc)]
    B2_vProd1_PowerFC.set_value(vprodForecast2)
    
    
    # Update SOC
    
    if not B1_MemapActive.get_value():
        B1_Stor1_SPChg.get_value().set_value(P_B1_Strge[i:i+mpc,1])
        B1_Stor1_SPDisChg.get_value().set_value(P_B1_Strge[i:i+mpc,0])
    
    if not B2_MemapActive.get_value():    
        B2_Stor1_SPChg.get_value().set_value(P_B2_Strge[i:i+mpc,1])
        B2_Stor1_SPDisChg.get_value().set_value(P_B2_Strge[i:i+mpc,0])

    #  Losses berücksichtigen
    B1_alpha = 1 - time_factor * B1_Stor1_losses.get_value()
    B2_alpha = 1 - time_factor * B2_Stor1_losses.get_value()
    
    B1_StorChange = time_factor * (B1_Stor1_SPChg.get_value()[0] - B1_Stor1_SPDisChg.get_value()[0]) / B1_Cap_Stor1 # Änderung in Prozent der Capazität
    B2_StorChange = time_factor * (B2_Stor1_SPChg.get_value()[0] - B2_Stor1_SPDisChg.get_value()[0]) / B2_Cap_Stor1 # Änderung in Prozent der Capazität
    # SOC in Prozent
    B1_Stor1_SOC.set_value(B1_alpha * B1_Stor1_SOC.get_value() + B1_StorChange)
    B2_Stor1_SOC.set_value(B2_alpha * B2_Stor1_SOC.get_value() + B2_StorChange)
    

    print(i+1, "B1 strge: ", B1_Stor1_SPChg.get_value()[0], B1_Stor1_SPDisChg.get_value()[0], B1_Stor1_SOC.get_value(), " demnd: ", demForecast1[0], demForecast3[0])
    print(i+1, "B2 strge: " ,B2_Stor1_SPChg.get_value()[0], B2_Stor1_SPDisChg.get_value()[0], B2_Stor1_SOC.get_value(), " demnd: ", demForecast2[0], demForecast4[0])
    print(" ")
    
    # We cut away 5 timesteps from the day here for the MPC
    if i < size-mpc-1:
        i += 1
    else:
        i = 0
        
    time.sleep(steptime)    
    
    