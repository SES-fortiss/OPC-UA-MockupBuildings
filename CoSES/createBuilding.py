# -*- coding: utf-8 -*-
"""
Created on Mon Jul  8 09:41:18 2019

@author: mayer
"""

from opcua import Server

# __init__

def create_Server_Basics(name, port):
    
    url = 'opc.tcp://0.0.0.0:' + port
    gebName = 'CoSES' + name
    server = Server()
    server.set_endpoint(url)
    server.set_server_name('CoSES_OPCUA_Server_' + name)
    idx = server.register_namespace(gebName)

    # Root node
    objects = server.get_objects_node()    
    return (server, url, idx, objects)
    

def create_Namespace(server, idx, objects):
    General = objects.add_object(idx, "General")
    Demand = objects.add_object(idx, "Demand")

    Systems = objects.add_object(idx, "Systems")
    # Untersysteme
    Producer = Systems.add_folder(idx, "Producer")
    VolatilePruducer = Systems.add_folder(idx, "VolatileProducer")
    Coupler = Systems.add_folder(idx, "Coupler")
    Storage = Systems.add_folder(idx, "Storage")
    
    return (General, Demand, Systems, Producer, VolatilePruducer, Coupler, Storage)

    


def add_General(idx, General, url, ConnectionStat, EMSname, InMEMAP, BuildCat):
    
    EndPoint = General.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_0_FM__EndPoint", url)
    ConnStat = General.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_0_FM__ConnStat", ConnectionStat)
    MEMAPflag = General.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_0_FM__MEMAPflag", InMEMAP)
    MEMAPflag.set_writable()
    EMSnameID = General.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_0_FM__EMSnameID", EMSname)
    BCategory = General.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM__BCategory", BuildCat)

    #return (only writables?)
    return (EndPoint, ConnStat, MEMAPflag, EMSnameID, BCategory)



def add_Demand(idx, Demand, DemName, FC_Step, FC_Size, H_minT, C_maxT, E_cost, H_cost, C_cost):

    nameID = Demand.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM__nameID", DemName)
    PrimarySector = Demand.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM__PrimSect", "heat")
    SecondarySecrot = Demand.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM__SecdSect", "electricity")
    TertiarySector = Demand.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM__TertSect", "cold")
    
    # Forecast
    NumberDFCSteps = Demand.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM__NumDFCstp", FC_Step)
    SizeDFCSteps = Demand.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM__SizeDFCstp", FC_Size)
    
    
    
    Heat = Demand.add_folder(idx, "Heat")
    # Forecast
    HtDemdFC = []
    HtCostFC = []
    HtForecast = Heat.add_folder(idx, "Forecasts")
    for i in range(FC_Step):
        HtDemdFC.append(HtForecast.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM_HT_DemFcHeat" + str(i+1), 0.0))
        HtDemdFC[i].set_writable()
        HtCostFC.append( HtForecast.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM_HT_HeatBuyC" + str(i+1), H_cost))
        HtCostFC[i].set_writable()
    
    HeatPowerDemand =  Heat.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_3_FM_HT_HtDemSet", 0)
    HeatPowerDemand.set_writable()
    # Auch als Forecast ?
    HtTempDemand = Heat.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM_HT_MinTempDH", H_minT)
    HtTempDemand.set_writable()
    
    Elec = Demand.add_folder(idx, "Electricity")
    # Forecast
    ElDemdFC = []
    ElCostFC = []
    ElForecast = Elec.add_folder(idx, "Forecasts")
    for i in range(FC_Step):
        ElDemdFC.append(ElForecast.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM_EL_DemFcElec" + str(i+1), 0.0))
        ElDemdFC[i].set_writable()
        ElCostFC.append(ElForecast.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM_EL_ElecSellC" , E_cost))
        ElCostFC[i].set_writable()
    
    ElecPowerDemand =  Elec.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_2_TM_EL_curDemElec", 0)
    ElecPowerDemand.set_writable()

    
    Cold = Demand.add_folder(idx, "Cold")
    # Forecast
    CdDemdFC = []
    CdCostFC = []
    CdForecast = Cold.add_folder(idx, "Forecasts")
    for i in range(FC_Step):
        CdDemdFC.append(CdForecast.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM_CD_DemFcCold" + str(i+1), 0.0))
        CdDemdFC[i].set_writable()
        CdCostFC.append(CdForecast.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM_CD_ColdSellC" , C_cost))
        CdCostFC[i].set_writable()
    # Auch als Forecast ? 
    CdTempDemand = Cold.add_variable(idx, "CoSESEMS01OBJ02_DEMND01_1_FM_CD_MaxTempDC", C_maxT)
    CdTempDemand.set_writable()
    #return writables
    return (HeatPowerDemand, HtCostFC, HtDemdFC, ElecPowerDemand, ElDemdFC, ElCostFC)
  
    
    
def add_Coupler(idx, name, Coupler, Medium1, Medium2, Eff_p, Eff_s, P_min, P_max1, Temp):
    # MOCKUP-SERVER-VERSION    
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



def add_Producer(idx, name, Producer, PrimSect, EffPrim, P_min, P_max, Temp_min, Temp_max, PrimEnCost, GenCosts, PrimCO2Cost):
    
    Prod = Producer.add_folder(idx, "Producers")
    ProdNaming = "CoSESEMS{02.}.format(1)OBJ{02.}.format(1)_CPROD{02.}.format(1)"
    print(ProdNaming)
    
    ID_Prod = Prod.add_property(idx, "CoSESEMS01OBJ01_CPROD01_1_FM__nameID", name)
    PrimarySector = Prod.add_property(idx, "CoSESEMS01OBJ01_CPROD01_1_FM_HT_PrimSect", PrimSect)
    PrimaryEff = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_1_FM_HT_EffPrim", EffPrim)
    MinP = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_1_FM_HT_minPwrPrim", P_min)
    MinP.set_writable()
    MaxP = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_1_FM_HT_maxPwrPrim", P_max)
    MaxP.set_writable()
    
    MinTemp = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_1_FM_HT_minTemp", Temp_min)
    MaxTemp = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_1_FM_HT_maxTemp", Temp_max)
    
    EnergyCosts = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_1_FM_HT_PrimEnCost", PrimEnCost)
    EnergyCosts.set_writable()
    GenerationCosts = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_1_FM_HT_GenCosts", GenCosts)
    GenerationCosts.set_writable()
    CO2Costs = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_1_FM__PrimCO2Costs", PrimCO2Cost)
    CO2Costs.set_writable()
    
    Setpoint = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_3_FM_HT_SPDevPwr", 0) 
    Setpoint.set_writable()
    Production = Prod.add_variable(idx, "CoSESEMS01OBJ01_CPROD01_2_TM_HT_curPwrPrim", 0)
    Production.set_writable()
    
    
    
    return(Production, PrimaryEff, P_min, P_max, MinTemp, MaxTemp, Setpoint, Production)
    
    
 
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