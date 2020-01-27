# -*- coding: utf-8 -*-
"""
Created on Tue Oct 16 17:20:59 2018

@author: mayer
"""

from opcua import Server
import time
import numpy as np
#import requests, json
import random
#from numpy import genfromtxt


# ============================== Building 1 ==============================
Geb = "Building1_"
server1 = Server()
url1 = "opc.tcp://0.0.0.0:4880"
server1.set_endpoint(url1)
server1.set_server_name("MEMAP fortiss Server 1")

name = "MEMAP_Building1"
idx = server1.register_namespace(name)

# Root node
objects = server1.get_objects_node()


# ================= Defining the Namespace Building 1 =====================

#General = objects.add_object(idx, "General")
#Classification = General.add_folder(idx, "Classification")
BuildingClass =  General.add_variable(idx, "BuildingClass", 0)

### Demand
Demand = objects.add_object(idx, "Demand")

Heat = Demand.add_folder(idx, "Heat")
#
HeatPower_B1 =  Heat.add_variable(idx, "Power", 5.3)
HeatPower_B1.set_writable()
H_Temp_demand = Heat.add_variable(idx, "min_Temperature_demand", 75)
H_Costs =  Heat.add_variable(idx, "max_cost_EUR_per_kWh", 8)

Elec = Demand.add_folder(idx, "Electricity")
#
ElecPower_B1 =  Elec.add_variable(idx, "Power", 2.1)
ElecPower_B1.set_writable()
El_Costs =  Heat.add_variable(idx, "max_cost_EUR_per_kWh", 12)

Cold = Demand.add_folder(idx, "Cold")
#
ColdPower =  Heat.add_variable(idx, "Power", 1.6)
ColdPower.set_writable()
H_Temp_demand = Cold.add_variable(idx, "max_Temperature_demand", 20)

"""
Management = Demand.add_folder(idx,"DemandManagement")
#
HeatMgmt = Management.add_folder(idx, "Heat")
HeatReduction = HeatMgmt.add_variable(idx, "PossiblePowerReduction", 2)
HeatAbsorption = HeatMgmt.add_variable(idx, "PossiblePowerAbsorption", 2)
HeatTemperature = HeatMgmt.add_variable(idx, "Temperature", 50)

ElecMgmt = Management.add_folder(idx, "Electricity")
HeatReduction = ElecMgmt.add_variable(idx, "PossiblePowerReduction", 0.2)
HeatAbsorption = ElecMgmt.add_variable(idx, "PossiblePowerAbsorption", 0.2)
"""

### Anlagen
Systems = objects.add_object(idx, "Systems")

Pruducer = Systems.add_folder(idx, "Producer")
#Producer
"""
Prod1 = Pruducer.add_folder(idx, "Producer_1")
ID_Prod1 = Prod1.add_property(idx, "ID", Geb+"Producer_1")
Medium = Prod1.add_property(idx, "Medium", "Heat")
MinP = Prod1.add_variable(idx, "MinPower", 30)
MaxP = Prod1.add_variable(idx, "MaxPower", 80)
temp_req = Prod1.add_variable(idx, "required_Temp", 80)

Prod2 = Pruducer.add_folder(idx, "Producer_2")
ID_Prod2 = Prod2.add_property(idx, "ID", Geb+"Producer_2")
Medium = Prod2.add_property(idx, "Medium", "Electricity")
MinP = Prod2.add_variable(idx, "MinPower", 3)
MaxP = Prod2.add_variable(idx, "MaxPower", 12)
"""

VolatilePruducer = Systems.add_folder(idx, "VolatileProducer")
#VolatileProducer
VProd1 = VolatilePruducer.add_folder(idx, "Volatile_Producer_1")
ID_VProd1 = VProd1.add_property(idx, "nameID", Geb+"Photovoltaik")
Med_VProd1 = VProd1.add_property(idx, "Medium", "Electricity")
Eff_VProd1 = VProd1.add_variable(idx, "Efficiency", 0.18)
A_VProd1 = VProd1.add_variable(idx, "Area_m2", 18)
Pwr_VProd1 = VProd1.add_variable(idx, "installed_Power", 3.24)
MinP_VProd1 = VProd1.add_variable(idx, "MinPower", 0)
MaxP_VProd1 = VProd1.add_variable(idx, "MaxPower", 3.24)
#writable
B1_P_VProd1 = VProd1.add_variable(idx, "current production", 2.4789)
B1_P_VProd1.set_writable()


Coupler = Systems.add_folder(idx, "Coupler")
# Coupler
Coup1 = Coupler.add_folder(idx, "Coupler_1")
ID_Coup1 = Coup1.add_property(idx, "nameID", Geb+"Heatpump")
Med1_Coup1 = Coup1.add_property(idx, "prim_Medium", "Heat")
Med2_Coup1 = Coup1.add_property(idx, "sec_Medium", "Electricity")
Eff1_Coup1 = Coup1.add_variable(idx, "prim_Efficiency", 3.8)
Eff2_Coup1 = Coup1.add_variable(idx, "sec_Efficiency", -1)
MinP_Coup1 = Coup1.add_variable(idx, "MinPower", 0)
MaxP_Coup1 = Coup1.add_variable(idx, "MaxPower", 10)
#writable
B1_P_Coup1 = Coup1.add_variable(idx, "current production", 0.78)
B1_P_Coup1.set_writable()

Storage = Systems.add_folder(idx, "Storage")
#
Stor1 = Storage.add_folder(idx, "Storage_1")
ID_Stor1 = Stor1.add_property(idx,"nameID", Geb+"Battery")
Med_Stor1 = Stor1.add_property(idx, "Medium", "Electricity")
Eff_Stor1 = Stor1.add_variable(idx, "prim_Efficiency", 0.98)
B1_Cap_Stor1 = Stor1.add_variable(idx, "Capacity", 12)
MinP_Stor1 = Stor1.add_variable(idx, "MinPower", 0)
B1_MaxP_in_Stor1 = Stor1.add_variable(idx, "MaxPower_charge", 3.3)
B1_MaxP_out_Stor1 = Stor1.add_variable(idx, "MaxPower_discharge", 3.3)
#writables
B1_P_in_Stor1 = Stor1.add_variable(idx, "current charge", 1.6)
B1_P_in_Stor1.set_writable()
B1_P_out_Stor1 = Stor1.add_variable(idx, "current discharge", 0)
B1_P_out_Stor1.set_writable()
B1_SOC_Stor1 = Stor1.add_variable(idx, "State of charge", 0.67)
B1_SOC_Stor1.set_writable()


# ============================== Building 2 ==============================
Geb = "Building2_"
server2 = Server()
url2 = "opc.tcp://0.0.0.0:4890"
server2.set_endpoint(url2)
server2.set_server_name("MEMAP fortiss Server 2")

name = "MEMAP_Building2"
idx = server2.register_namespace(name)

# Root node
objects = server2.get_objects_node()


# ================= Defining the Namespace Building 2 =====================

General = objects.add_object(idx, "General")
#Classification = General.add_folder(idx, "Classification")
BuildingClass =  General.add_variable(idx, "BuildingClass", 0)

### Demand
Demand = objects.add_object(idx, "Demand")

Heat = Demand.add_folder(idx, "Heat")
#
HeatPower_B2 =  Heat.add_variable(idx, "Power", 13.1)
HeatPower_B2.set_writable()
H_Temp_demand = Heat.add_variable(idx, "min_Temperature_demand", 40)
H_Costs =  Heat.add_variable(idx, "max_cost_EUR_per_kWh", 7.7)

Elec = Demand.add_folder(idx, "Electricity")
#
ElecPower_B2 =  Elec.add_variable(idx, "Power", 5.9)
ElecPower_B2.set_writable()
El_Costs =  Heat.add_variable(idx, "max_cost_EUR_per_kWh", 12.4)

Cold = Demand.add_folder(idx, "Cold")
#
ColdPower =  Heat.add_variable(idx, "Power", 0.8)
ColdPower.set_writable()
H_Temp_demand = Cold.add_variable(idx, "max_Temperature_demand", 22)

"""
Management = Demand.add_folder(idx,"DemandManagement")
#
HeatMgmt = Management.add_folder(idx, "Heat")
HeatReduction = HeatMgmt.add_variable(idx, "PossiblePowerReduction", 2)
HeatAbsorption = HeatMgmt.add_variable(idx, "PossiblePowerAbsorption", 2)
HeatTemperature = HeatMgmt.add_variable(idx, "Temperature", 50)

ElecMgmt = Management.add_folder(idx, "Electricity")
HeatReduction = ElecMgmt.add_variable(idx, "PossiblePowerReduction", 0.2)
HeatAbsorption = ElecMgmt.add_variable(idx, "PossiblePowerAbsorption", 0.2)
"""

### Anlagen
Systems = objects.add_object(idx, "Systems")

Pruducer = Systems.add_folder(idx, "Producer")
#Producer
"""
Prod1 = Pruducer.add_folder(idx, "Producer_1")
ID_Prod1 = Prod1.add_property(idx, "ID", Geb+"Producer_1")
Medium = Prod1.add_property(idx, "Medium", "Heat")
MinP = Prod1.add_variable(idx, "MinPower", 30)
MaxP = Prod1.add_variable(idx, "MaxPower", 80)
temp_req = Prod1.add_variable(idx, "required_Temp", 80)

Prod2 = Pruducer.add_folder(idx, "Producer_2")
ID_Prod2 = Prod2.add_property(idx, "ID", Geb+"Producer_2")
Medium = Prod2.add_property(idx, "Medium", "Electricity")
MinP = Prod2.add_variable(idx, "MinPower", 3)
MaxP = Prod2.add_variable(idx, "MaxPower", 12)
"""

VolatilePruducer = Systems.add_folder(idx, "VolatileProducer")
#VolatileProducer
VProd1 = VolatilePruducer.add_folder(idx, "Volatile_Producer_1")
ID_VProd1 = VProd1.add_property(idx, "nameID", Geb+"Solarthermic")
Med_VProd1 = VProd1.add_property(idx, "Medium", "Heat")
Eff_VProd1 = VProd1.add_variable(idx, "Efficiency", 0.5)
A_VProd1 = VProd1.add_variable(idx, "Area_m2", 3)
Pwr_VProd1 = VProd1.add_variable(idx, "installed_Power", 1.5)
MinP_VProd1 = VProd1.add_variable(idx, "MinPower", 0)
MaxP_VProd1 = VProd1.add_variable(idx, "MaxPower", 1.5)
#writable
B2_P_VProd1 = VProd1.add_variable(idx, "current production", 1.1574)
B2_P_VProd1.set_writable()


Coupler = Systems.add_folder(idx, "Coupler")
# Coupler
Coup1 = Coupler.add_folder(idx, "Coupler_1")
ID_Coup1 = Coup1.add_property(idx, "nameID", Geb+"CHP")
Med1_Coup1 = Coup1.add_property(idx, "prim_Medium", "Heat")
Med2_Coup1 = Coup1.add_property(idx, "sec_Medium", "Electricity")
Eff1_Coup1 = Coup1.add_variable(idx, "prim_Efficiency", 0.6)
Eff2_Coup1 = Coup1.add_variable(idx, "sec_Efficiency", 0.25)
MinP_Coup1 = Coup1.add_variable(idx, "MinPower", 0)
MaxP_Coup1 = Coup1.add_variable(idx, "MaxPower", 3.6)
#writable
B2_P_Coup1 = Coup1.add_variable(idx, "current production", 1.63)
B2_P_Coup1.set_writable()

Storage = Systems.add_folder(idx, "Storage")
#
Stor1 = Storage.add_folder(idx, "Storage_1")
ID_Stor1 = Stor1.add_property(idx,"nameID", Geb+"ThermalStorage")
Med_Stor1 = Stor1.add_property(idx, "Medium", "Heat")
Eff_Stor1 = Stor1.add_variable(idx, "prim_Efficiency", 0.98)
B2_Cap_Stor1 = Stor1.add_variable(idx, "Capacity", 20)
MinP_Stor1 = Stor1.add_variable(idx, "MinPower", 0)
B2_MaxP_in_Stor1 = Stor1.add_variable(idx, "MaxPower_charge", 5)
B2_MaxP_out_Stor1 = Stor1.add_variable(idx, "MaxPower_discharge", 5)
#writables
B2_P_in_Stor1 = Stor1.add_variable(idx, "current charge", 0)
B2_P_in_Stor1.set_writable()
B2_P_out_Stor1 = Stor1.add_variable(idx, "current discharge", 0.86)
B2_P_out_Stor1.set_writable()
B2_SOC_Stor1 = Stor1.add_variable(idx, "State of charge", 0.72)
B2_SOC_Stor1.set_writable()

# ================= Start =====================


server1.start()
print("Server1 started at {}".format(url1))
server1.PublishingEnabled = True

server2.start()
print("Server2 started at {}".format(url2))
server2.PublishingEnabled = True


Elec_Consumption = np.genfromtxt("StromVerbraeuche.csv", delimiter=";")
Heat_Consumption = np.genfromtxt("WaermeVerbraeuche.csv", delimiter=";")
size = 1440
i = 0;

while True:

    ElecPower_B1.set_value(Elec_Consumption[i,1])
    ElecPower_B2.set_value(Elec_Consumption[i,2])
    
    HeatPower_B1.set_value(Heat_Consumption[i,1])
    HeatPower_B2.set_value(Heat_Consumption[i,2])
    

    # Building 1
    B1_P_VProd1.set_value(B1_P_VProd1.get_value() * (1 + float(random.randint(-20,20))/100))
    B1_P_Coup1.set_value(B1_P_Coup1.get_value() * (1 + float(random.randint(-20,20))/100))
    
    if B1_SOC_Stor1.get_value() < B1_P_out_Stor1.get_value()/B1_Cap_Stor1.get_value():
        B1_P_in_Stor1.set_value(B1_MaxP_in_Stor1.get_value()/2)
        B1_P_out_Stor1.set_value(0)
    elif B2_SOC_Stor1.get_value() > 1 - B1_P_in_Stor1.get_value()/B1_Cap_Stor1.get_value():
        B1_P_out_Stor1.set_value(B1_MaxP_out_Stor1.get_value()/2)
        B1_P_in_Stor1.set_value(0)
    else: 
        B1_P_in_Stor1.set_value(B1_P_in_Stor1.get_value() * (1 + float(random.randint(-20,20))/100))
        B1_P_out_Stor1.set_value(B1_P_out_Stor1.get_value() * (1 + float(random.randint(-20,20))/100))
    B1_SOC_Stor1.set_value(B1_SOC_Stor1.get_value()+B1_P_in_Stor1.get_value()/B1_Cap_Stor1.get_value()-B1_P_out_Stor1.get_value()/B1_Cap_Stor1.get_value())
     
     
    # Building 2
    B2_P_VProd1.set_value(B2_P_VProd1.get_value() * (1 + float(random.randint(-20,20))/100))
    B2_P_Coup1.set_value(B2_P_Coup1.get_value() * (1 + float(random.randint(-20,20))/100))
    
    if B2_SOC_Stor1.get_value() < B2_P_out_Stor1.get_value()/B2_Cap_Stor1.get_value():
        B2_P_in_Stor1.set_value(B2_MaxP_in_Stor1.get_value()/2)
        B2_P_out_Stor1.set_value(0)
    elif B2_SOC_Stor1.get_value() > 1 - B1_P_in_Stor1.get_value()/B2_Cap_Stor1.get_value():
        B2_P_out_Stor1.set_value(B2_MaxP_out_Stor1.get_value()/2)
        B2_P_in_Stor1.set_value(0)
    else: 
        B2_P_in_Stor1.set_value(B2_P_in_Stor1.get_value() * (1 + float(random.randint(-20,20))/100))
        B2_P_out_Stor1.set_value(B2_P_out_Stor1.get_value() * (1 + float(random.randint(-20,20))/100))   
    B2_SOC_Stor1.set_value(B2_SOC_Stor1.get_value()+B2_P_in_Stor1.get_value()/B2_Cap_Stor1.get_value()-B2_P_out_Stor1.get_value()/B2_Cap_Stor1.get_value())

   
    
    """
    r = requests.get("http://192.168.21.203:8080/api/v1/status")
    k = json.loads(r.text)
    P_akt_V1.set_value(k['Production_W'])
    ElecPower.set_value(k['Consumption_W']) 
    P_akt_S1.set_value(k['Pac_total_W'])
    SOC.set_value(k['USOC'])

    
    print(i, k['Consumption_W'], k['Production_W'], k['Pac_total_W'], k['USOC'])
    """
    
    print(i, ElecPower_B1.get_value(), ElecPower_B1.get_value(), ElecPower_B2.get_value(), ElecPower_B2.get_value())
    
    
    if i < size-1:
        i += 1
    else:
        i -= size
        
    time.sleep(10)
