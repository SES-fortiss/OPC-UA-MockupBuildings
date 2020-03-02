# -*- coding: utf-8 -*-
"""
Created on Mon Jul  8 09:41:18 2019

@author: mayer
"""

from opcua import ua, Server

# __init__

def create_Server_Basics(objectName, ems, port):
    
    url = 'opc.tcp://0.0.0.0:' + port
    gebName = objectName + ems
    server = Server()
    server.set_endpoint(url)
    server.set_server_name(objectName + '_OPCUA_Server_' + ems)
    idx = server.register_namespace(gebName)

    '''
    server.set_security_policy([
                ua.SecurityPolicyType.NoSecurity,
                ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
                ua.SecurityPolicyType.Basic256Sha256_Sign])
    '''

    # Root node
    objects = server.get_objects_node()    
    return (server, url, idx, objects)
    

def create_Namespace(server, idx, objects):
    General = objects.add_folder(idx, "General")
    Demand = objects.add_folder(idx, "Demand")

    Systems = objects.add_folder(idx, "Systems")
    # Untersysteme
    Producer = Systems.add_folder(idx, "Producer")
    VolatilePruducer = Systems.add_folder(idx, "VolatileProducer")
    Coupler = Systems.add_folder(idx, "Coupler")
    Storage = Systems.add_folder(idx, "Storage")
    
    return (General, Demand, Systems, Producer, VolatilePruducer, Coupler, Storage)

    


def add_General(idx, naming, General, url, connectionStat, EMSname, inMEMAP, buildCat):
    
    k = ua.NodeId.from_string('ns=%d;i=100' % idx)
    
    endPoint = General.add_variable(k, naming+"_NONE_0_ZM_XX_EndPoint", url)
    connStat = General.add_variable(idx, naming+"_NONE_0_ZM_XX_ConnStat", connectionStat)
    MEMAPflag = General.add_variable(idx, naming+"_NONE_0_ZM_XX_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()
    EMSnameID = General.add_variable(idx, naming+"_NONE_0_ZM_XX_EMSnameID", EMSname)
    bCategory = General.add_variable(idx, naming+"_NONE_1_ZM_XX_BCategory", buildCat)

    #return (only writables?)
    return (endPoint, connStat, MEMAPflag, EMSnameID, bCategory)



def add_Demand(counter, naming, idx, Demand, sector, demName, FC_step, FC_size, minT, maxT, cost):

    Demnd = Demand.add_folder(idx, "DEMND{:02d}".format(int(counter[0,0]+1)))
    demdNaming = naming+"_DEMND{:02d}".format(int(counter[0,0]+1))
    print(demdNaming + " added...")
    
    nameID = Demnd.add_variable(idx, demdNaming+"_1_ZM_XX_nameID", demName)
    demandSector = Demnd.add_variable(idx, demdNaming+"_1_ZM_XX_DemndSect", sector)
    # Forecast
    numberDFCSteps = Demnd.add_variable(idx, demdNaming+"_1_ZM_XX_NumDFCstp", FC_step)
    sizeDFCSteps = Demnd.add_variable(idx, demdNaming+"_1_ZM_XX_SizeDFCstp", FC_size)
    
    short = sector_to_short(sector)

    demdFC = []
    marketFC = []
    Forecast = Demnd.add_folder(idx, short+"_Forecast")
    for i in range(FC_step):
        demdFC.append(Forecast.add_variable(idx, demdNaming+"_2_ZM_" + short + "_DemandFC" + str(i+1), 0.0))
        demdFC[i].set_writable()
        marketFC.append(Forecast.add_variable(idx, demdNaming+"_2_ZM_" + short + "GrdBuyCost" + str(i+1), cost))
        marketFC[i].set_writable()
    
    demandJson = Forecast.add_variable(idx, demdNaming+"_1_ZM_" + short + "_DemFCjson", "" )
    demandJson.set_writable()
    marketJson = Forecast.add_variable(idx, demdNaming+"_1_ZM_" + short + "_MktFCjson", "" )
    marketJson.set_writable()
    
    # Only for CoSES
    demandSetpoint =  Demnd.add_variable(idx, demdNaming+"_3_VM_" + short + "_DemndSetPt", 0)
    demandSetpoint.set_writable()
    # Auch als Forecast ?
    minTempDemand = Demnd.add_variable(idx, demdNaming+"_1_ZM_" + short + "_MinTempDH", minT)
    minTempDemand.set_writable()
    maxTempDemand = Demnd.add_variable(idx, demdNaming+"_1_ZM_" + short + "_MaxTempDH", maxT)
    maxTempDemand.set_writable()
    
    
    counter[0,0]+=1
    #return writables ?
    return (demandSetpoint, demdFC, demandJson, marketFC, marketJson)
  



def add_Producer(counter, naming, FC_step, idx, name, Producer, PrimSect, EffPrim, P_min, P_max, Temp_min, Temp_max, PrimEnCost, GenCosts, PrimCO2Cost):
    
    Prod = Producer.add_folder(idx, "CPROD{:02d}".format(int(counter[0,1]+1)))
    prodNaming = naming+"_CPROD{:02d}".format(int(counter[0,1]+1))
    print(prodNaming + " added...")
    
    ID_Prod = Prod.add_property(idx, prodNaming + "_1_ZM_XX_nameID", name)
    
    short = sector_to_short(PrimSect)
    
    PrimarySector = Prod.add_property(idx, prodNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    PrimaryEff = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    MinP = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MinPower", P_min)
    MinP.set_writable()
    MaxP = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MaxPower", P_max)
    MaxP.set_writable()
    
    MinTemp = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_minTemp", Temp_min)
    MaxTemp = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_maxTemp", Temp_max)
    
    
    
    energyCosts = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_PrimEnCost", PrimEnCost)
    energyCosts.set_writable()
    generationCosts = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_GenCosts", GenCosts)
    generationCosts.set_writable()
    CO2Costs = Prod.add_variable(idx, prodNaming + "_1_ZM__PrimCO2Costs", PrimCO2Cost)
    CO2Costs.set_writable()
    
    Setpoint = Prod.add_folder(idx, "Setpoints_CPROD{:02d}".format(int(counter[0,1]+1)))
    setpointFC = []
    for i in range(FC_step):
        setpointFC.append(Setpoint.add_variable(idx, prodNaming + "_3_VM_" + short + "_SPDevPwr"+ str(i+1), 0.0) )
        setpointFC[i].set_writable()
    
    
    
    production = Prod.add_variable(idx, prodNaming + "_2_ZM_" + short + "_curPwrPrim", 0)
    production.set_writable()
    
    counter[0,1]+=1
    
    return(production, setpointFC)
    
    
 
def add_VolatileProducer(counter, naming, idx, name, VolatilePruducer, PrimSect, EffPrim, Area, Temp):
    
    VProd = VolatilePruducer.add_folder(idx, "VPROD{:2d}".format(int(counter[0,2]+1)))
    vProdNaming = naming+"_VPROD{:2d}".format(int(counter[0,2]+1))
    print(vProdNaming)
    

    ID_VProd = VProd.add_property(idx, vProdNaming + "_1_ZM_XX_nameID", name)
    short = sector_to_short(PrimSect)
    
    
    PrimarySector = VProd.add_property(idx, vProdNaming + "_1_ZM_" + short + "_EffPrim", PrimSect)
    PrimaryEff = VProd.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    '''
    Eff1 = VProd.add_variable(idx, "Efficiency", Eff)
    Area1 = VProd.add_variable(idx, "Area_m2", Area)
    P_peak = Eff*Area # kWp
    Power = VProd.add_variable(idx, "installed_Power", P_peak)
    Temp1 = VProd.add_variable(idx, "provided_Temp", Temp)
    #writable
    Prod1 = VProd.add_variable(idx, "current production", 0)
    Prod1.set_writable()
    '''
    counter[0,2]+=1
    
    return(PrimaryEff)
    
   
def add_Coupler(counter, naming, idx, name, Coupler, Medium1, Medium2, Eff_p, Eff_s, P_min, P_max1, Temp):
    
    
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

    
    
def add_Storage(counter, naming, FC_step, idx, name, Storage, PrimSect, CEffPrim, DisCEffPrim, Capacity, 
                loss, Pmax_in, Pmax_Out, minTemp, maxTemp, minTempOut, SOC_init, GenCosts, PrimCO2Cost):

    
    Stor = Storage.add_folder(idx, "STRGE{:02d}".format(int(counter[0,4]+1)))
    storNaming = naming+"_STRGE{:02d}".format(int(counter[0,4]+1))
    print(storNaming + " added...")
    
    ID_Stor = Stor.add_property(idx, storNaming + "_1_ZM_XX_nameID", name)
    
    short = sector_to_short(PrimSect)
    
    primarySector = Stor.add_property(idx, storNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    chargingEff = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_EffPrim", CEffPrim)
    dischargingEff = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_DisEffPrim", DisCEffPrim)
    storageCap = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_Capacity", Capacity)
    storageLosses = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_StorLossPD", loss)
    maxP_out = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_MaxPower", Pmax_Out)
    maxP_in = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_MaxChrgPwr", Pmax_in)
    
    minTempIn = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_TminStorHt", minTemp)
    maxTempIn = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_TmaxStorHt", maxTemp)
    minTempDisCh = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_TDeChrgmin", minTempOut)
    
    SOC = Stor.add_variable(idx, storNaming + "_2_ZM_" + short + "_curSOC", SOC_init)
    SOC.set_writable()
    
    
    Setpoint = Stor.add_folder(idx, "Setpoints_STRGE{:02d}".format(int(counter[0,4]+1)))
    setpointChgFC = []
    setpointDisChgFC = []
    for i in range(FC_step):
        setpointChgFC.append(Setpoint.add_variable(idx, storNaming + "_3_VM_" + short + "_SPCharge"+ str(i+1), 0.0) )
        setpointChgFC[i].set_writable()
        setpointDisChgFC.append(Setpoint.add_variable(idx, storNaming + "_3_VM_" + short + "_SPDisChrg"+ str(i+1), 0.0) )
        setpointDisChgFC[i].set_writable()
    
    
    
    #writables
    currentP_in = Stor.add_variable(idx, storNaming + "_2_ZM_" + short + "_curChrg", 0)
    currentP_in.set_writable()
    currentP_out = Stor.add_variable(idx, storNaming + "_2_ZM_" + short + "_curDeChrg", 0)
    currentP_out.set_writable()

    generationCosts = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_GenCosts", GenCosts)
    generationCosts.set_writable()
    CO2Costs = Stor.add_variable(idx, storNaming + "_1_ZM__PrimCO2Costs", PrimCO2Cost)
    CO2Costs.set_writable()
    
    
    counter[0,4]+=1
    
    return(setpointChgFC, setpointDisChgFC, SOC)
    


# ======================== Helper Funktions ======================
    
def sector_to_short(sec):
    switcher = {
            "heat": "HT",
            "electricity" : "EL",
            "elec" : "EL",
            "cold" : "CD"
            }
    return switcher.get(sec, "XX")    

