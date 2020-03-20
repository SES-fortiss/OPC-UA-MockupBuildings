# -*- coding: utf-8 -*-
"""
Created on Mon Jul  8 09:41:18 2019

@author: mayer
"""
from opcua import Server

# __init__

def create_Server_Basics(name, port):
    
    url = 'opc.tcp://0.0.0.0:' + port
    gebName = 'MEMAP_' + name
    server = Server()
    server.set_endpoint(url)
    server.set_server_name('MEMAP Mockup ' + name)
    idx = server.register_namespace(gebName)

    # Root node
    objects = server.get_objects_node()    
    return (server, url, idx, objects)
    

def create_Namespace(server, idx, objects):
    General = objects.add_object(idx, "General")
    Demand = objects.add_object(idx, "Demand")

    Systems = objects.add_object(idx, "Systems")
    Producer = Systems.add_folder(idx, "Producer")
    VolatilePruducer = Systems.add_folder(idx, "VolatileProducer")
    Coupler = Systems.add_folder(idx, "Coupler")
    Storage = Systems.add_folder(idx, "Storage")
    
    return (General, Demand, Systems, Producer, VolatilePruducer, Coupler, Storage)

    







def add_Demand(idx, Demand, H_minT, C_maxT, E_cost, H_cost, C_cost):

    Heat = Demand.add_folder(idx, "Heat")
#
    HeatPower =  Heat.add_variable(idx, "Power", 0)
    HeatPower.set_writable()
    H_Temp_demand = Heat.add_variable(idx, "min_Temperature_demand", H_minT)
    H_Costs =  Heat.add_variable(idx, "max_cost_EUR_per_kWh", H_cost)
    H_Costs.set_writable()
    
    Elec = Demand.add_folder(idx, "Electricity")
    #
    ElecPower =  Elec.add_variable(idx, "Power", 0)
    ElecPower.set_writable()
    E_Costs =  Elec.add_variable(idx, "max_cost_EUR_per_kWh", E_cost)
    E_Costs.set_writable()
    
    Cold = Demand.add_folder(idx, "Cold")
    #
    ColdPower =  Cold.add_variable(idx, "Power", 0)
    ColdPower.set_writable()
    C_Temp_demand = Cold.add_variable(idx, "max_Temperature_demand", C_maxT)
    C_Costs =  Cold.add_variable(idx, "max_cost_EUR_per_kWh", C_cost)
    C_Costs.set_writable()
    
    #return writables
    return (HeatPower, H_Costs, ElecPower, E_Costs, ColdPower, C_Costs)
  
    
    
def add_Coupler(idx, name, Coupler, Medium1, Medium2, Eff_p, Eff_s, P_min, P_max1, Temp):
        
    Coup = Coupler.add_folder(idx, "Coupler_1")
    ID_Coup = Coup.add_property(idx, "nameID", name)
    Med1 = Coup.add_property(idx, "prim_Medium", Medium1)
    Med2 = Coup.add_property(idx, "sec_Medium", Medium2)
    Eff1 = Coup.add_variable(idx, "prim_Efficiency", Eff_p)
    Eff2 = Coup.add_variable(idx, "sec_Efficiency", Eff_s)
    MinP = Coup.add_variable(idx, "MinPower", P_min)
    MinP.set_writable()
    MaxP1 = Coup.add_variable(idx, "prim_MaxPower", P_max1)
    MaxP1.set_writable()
    P_max2 = P_max1*Eff_s/Eff_p
    MaxP2 = Coup.add_variable(idx, "sec_MaxPower", P_max2)
    MaxP2.set_writable()
    Temp1 = Coup.add_variable(idx, "provided_Temp", Temp)
    Prod1 = Coup.add_variable(idx, "current production prim", 0)
    Prod1.set_writable()
    Prod2 = Coup.add_variable(idx, "current production sec", 0)
    Prod2.set_writable()

    return(Prod1, Eff_p, Prod2, Eff_s, P_min, P_max1, P_max2)



def add_Producer(idx, name, Producer, Medium, Eff, P_min, P_max, Temp):

    Prod = Pruducer.add_folder(idx, "Producer_1")
    ID_Prod = Prod.add_property(idx, "ID", name)
    Med = Prod.add_property(idx, "Medium", Medium)
    Eff1 = Prod.add_variable(idx, "Efficiency", Eff)
    MinP = Prod.add_variable(idx, "MinPower", P_min)
    MinP.set_writable()
    MaxP = Prod.add_variable(idx, "MaxPower", P_max)
    MaxP.set_writable()
    Temp1 = Prod.add_variable(idx, "provided_Temp", Temp)
    Prod1 = Prod.add_variable(idx, "current production", 1.1574)
    Prod1.set_writable()
    
    return(Prod1, Eff, P_min, P_max)
    
    
 
def add_VolatileProducer(idx, name, VolatilePruducer, Medium, Eff, Area, Temp):
    
    VProd = VolatilePruducer.add_folder(idx, "Volatile_Producer_1")
    ID_VProd = VProd.add_property(idx, "nameID", name)
    Med = VProd.add_property(idx, "Medium", Medium)
    Eff1 = VProd.add_variable(idx, "Efficiency", Eff)
    Area1 = VProd.add_variable(idx, "Area_m2", Area)
    P_peak = Eff*Area # kWp
    Power = VProd.add_variable(idx, "installed_Power", P_peak)
    Temp1 = VProd.add_variable(idx, "provided_Temp", Temp)
    #writable
    Prod1 = VProd.add_variable(idx, "current production", 0)
    Prod1.set_writable()
    
    return(Prod1, Eff, P_peak)
    
    
def add_Storage(idx, name, Storage, Medium, Eff, Capacity, Pmax_in, Pmax_Out, Temp, SOC_init):
    
    Stor = Storage.add_folder(idx, "Storage_1")
    ID_Stor = Stor.add_property(idx, "nameID", name)
    Med = Stor.add_property(idx, "Medium", Medium)
    Eff1 = Stor.add_variable(idx, "prim_Efficiency", Eff)
    Cap = Stor.add_variable(idx, "Capacity", Capacity)
    MinP_Stor = Stor.add_variable(idx, "MinPower", 0)
    MaxP_in = Stor.add_variable(idx, "MaxPower_charge", Pmax_in)
    MaxP_out = Stor.add_variable(idx, "MaxPower_discharge", Pmax_Out)
    Temp1 = Stor.add_variable(idx, "provided_Temp", Temp)
    
    #writables
    P_in = Stor.add_variable(idx, "current charge", 0)
    P_in.set_writable()
    P_out = Stor.add_variable(idx, "current discharge", 0)
    P_out.set_writable()
    SOC = Stor.add_variable(idx, "State of charge", SOC_init)
    SOC.set_writable()
    
    return(Eff, Capacity, P_in, P_out, SOC, Pmax_Out)