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
    
    k = range(100, 150, 2)
    
    endPoint = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[0])), naming+"_NONE_0_ZM_XX_EndPoint", url)
    endPoint.set_writable()
    connStat = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[1])), naming+"_NONE_0_ZM_XX_ConnStat", connectionStat)
    connStat.set_writable()
    MEMAPflag = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[2])), naming+"_NONE_0_ZM_XX_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()
    EMSnameID = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[3])), naming+"_NONE_0_ZM_XX_EMSnameID", EMSname)
    EMSnameID.set_writable()
    bCategory = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[4])), naming+"_NONE_1_ZM_XX_BCategory", buildCat)
    bCategory.set_writable()

    #return (only writables?)
    return (endPoint, connStat, MEMAPflag, EMSnameID, bCategory)



def add_Demand(counter, naming, idx, Demand, sector, demName, FC_step, FC_size, minT, maxT, cost):
    
    Demnd = Demand.add_folder(idx, "DEMND{:02d}".format(int(counter[0,0]+1)))
    demdNaming = naming+"_DEMND{:02d}".format(int(counter[0,0]+1))
    print(demdNaming + " added...")
    
    nameID = Demnd.add_variable(idx, demdNaming+"_1_ZM_XX_nameID", demName)
    nameID.set_writable()
    demandSector = Demnd.add_variable(idx, demdNaming+"_1_ZM_XX_DemndSect", sector)
    demandSector.set_writable()
    # Forecast
    numberDFCSteps = Demnd.add_variable(idx, demdNaming+"_1_ZM_XX_NumDFCstp", FC_step)
    numberDFCSteps.set_writable()
    sizeDFCSteps = Demnd.add_variable(idx, demdNaming+"_1_ZM_XX_SizeDFCstp", FC_size)
    sizeDFCSteps.set_writable()

    short = sector_to_short(sector)

    demdFC = []
    marketFC = []
    Forecast = Demnd.add_folder(idx, short+"_Forecast")
    for i in range(FC_step):
        demdFC.append(Forecast.add_variable(idx, demdNaming+"_2_ZM_" + short + "_DemandFC" + str(i+1), 0.0))
        demdFC[i].set_writable()
        marketFC.append(Forecast.add_variable(idx, demdNaming+"_2_ZM_" + short + "GrdBuyCost" + str(i+1), cost))
        marketFC[i].set_writable()
    
    #ua.NodeId.from_string('ns={};i={}'.format(idx, 35))
    demandArray = Forecast.add_variable(idx, demdNaming +"_1_ZM_" + short + "_DemFCarray", [0, 0, 0, 0, 0])
    demandArray.set_writable()
    
    demandJson = Forecast.add_variable(idx, demdNaming +"_1_ZM_" + short + "_DemFCjson", "" )
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
    return (demandSetpoint, demdFC, demandJson, demandArray, marketFC, marketJson)
  



def add_Producer(counter, naming, FC_step, idx, name, Producer, PrimSect, EffPrim, P_min, P_max, Temp_min, Temp_max, PrimEnCost, GenCosts, PrimCO2Cost):
    
    Prod = Producer.add_folder(idx, "CPROD{:02d}".format(int(counter[0,1]+1)))
    prodNaming = naming+"_CPROD{:02d}".format(int(counter[0,1]+1))
    print(prodNaming + " added...")
    
    nameID = Prod.add_property(idx, prodNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    
    short = sector_to_short(PrimSect)
    
    primarySector = Prod.add_property(idx, prodNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    primaryEff = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    primaryEff.set_writable()
    MinP = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MinPower", P_min)
    MinP.set_writable()
    MaxP = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MaxPower", P_max)
    MaxP.set_writable()
    
    minTemp = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_minTemp", Temp_min)
    minTemp.set_writable()
    maxTemp = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_maxTemp", Temp_max)
    maxTemp.set_writable()
    
    
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
    

    nameID = VProd.add_property(idx, vProdNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    
    short = sector_to_short(PrimSect)
    
    
    primarySector = VProd.add_property(idx, vProdNaming + "_1_ZM_" + short + "_EffPrim", PrimSect)
    primarySector.set_writable()
    primaryEff = VProd.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    primaryEff.set_writable()
    
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
    
    return(primaryEff)
    
   
def add_Coupler(counter, naming, idx, name, Coupler, Medium1, Medium2, Eff_p, Eff_s, P_min, P_max1, Temp):
    
    
    # MOCKUP-SERVER-VERSION    
    # Has to be adapted to new CoSES-Format and Naming convention: like Producer, 
    
    Coup = Coupler.add_folder(idx, "Coupler_1")
    nameID = Coup.add_property(idx, "nameID", name)
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
    
    nameID = Stor.add_property(idx, storNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    
    short = sector_to_short(PrimSect)
    
    primarySector = Stor.add_property(idx, storNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    chargingEff = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_EffPrim", CEffPrim)
    chargingEff.set_writable()
    dischargingEff = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_DisEffPrim", DisCEffPrim)
    dischargingEff.set_writable()
    storageCap = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_Capacity", Capacity)
    storageCap.set_writable()
    storageLosses = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_StorLossPD", loss)
    storageLosses.set_writable()
    maxP_out = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_MaxPower", Pmax_Out)
    maxP_out.set_writable()
    maxP_in = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_MaxChrgPwr", Pmax_in)
    maxP_in.set_writable()
    
    minTempIn = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_TminStorHt", minTemp)
    minTempIn.set_writable()
    maxTempIn = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_TmaxStorHt", maxTemp)
    maxTempIn.set_writable()
    minTempDisCh = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_TDeChrgmin", minTempOut)
    minTempDisCh.set_writable()
    
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
    
    
    
    # Setpoints
    currentP_in = Stor.add_variable(idx, storNaming + "_2_ZM_" + short + "_curChrg", 0)
    currentP_in.set_writable()
    currentP_out = Stor.add_variable(idx, storNaming + "_2_ZM_" + short + "_curDeChrg", 0)
    currentP_out.set_writable()

    # Setpoints
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

