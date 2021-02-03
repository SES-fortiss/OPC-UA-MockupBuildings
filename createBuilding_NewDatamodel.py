# -*- coding: utf-8 -*-
"""
Created on Mon Jul  8 09:41:18 2019

@author: mayer
"""
import opcua
from opcua import ua, Server
import numpy as np			  

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
    General = objects.add_folder(idx, "0_EMS")
    Demand = objects.add_folder(idx, "1_Demand")

    Systems = objects.add_folder(idx, "2_Systems")
    # Untersysteme
    Producer = Systems.add_folder(idx, "21_Producer")
    VolatilePruducer = Systems.add_folder(idx, "22_VolatileProducer")
    Coupler = Systems.add_folder(idx, "23_Coupler")
    Storage = Systems.add_folder(idx, "24_Storage")
    
    return (General, Demand, Systems, Producer, VolatilePruducer, Coupler, Storage)

    


def add_General(idx, naming, General, MemapActivated, url, connectionStat, EMSname, buildCat):
    
    k = range(100, 150, 2)
    
    endPoint = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[0])), naming+"_NONE_0_ZM_XX_EndPoint", url)
    endPoint.set_writable()
    connStat = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[1])), naming+"_NONE_0_ZM_XX_ConnStat", connectionStat)
    connStat.set_writable()
    EMSnameID = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[3])), naming+"_NONE_0_ZM_XX_nameID", EMSname)
    EMSnameID.set_writable()
    bCategory = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[4])), naming+"_NONE_1_ZM_XX_BCategory", buildCat)
    bCategory.set_writable()
    MemapActive = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, 8013)), naming+"_NONE_1_ZM_XX_MemapAct", MemapActivated)
    MemapActive.set_writable()
    trigger = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, 5000)), naming+"_NONE_1_ZM_XX_trigger", 0.0)
    trigger.set_writable()

    #return (only writables?)
    return (MemapActive, endPoint, EMSnameID, trigger)



def add_Demand(counter, naming, idx, Demand, sector, demName, FC_step, FC_size, minT, maxT, buyCost, sellCost):
    
    Demnd = Demand.add_folder(idx, "DEMND{:02d}".format(int(counter[0,0]+1)))
    demdNaming = naming+"_DEMND{:02d}".format(int(counter[0,0]+1))
    print(demdNaming + " added...")
    short = sector_to_short(sector)
    
    nameID = Demnd.add_variable(idx, demdNaming+"_1_ZM_XX_nameID", demName)
    nameID.set_writable()
    
    # static values - device
    demandSector = Demnd.add_variable(idx, demdNaming+"_1_ZM_" + short + "_PrimSect", sector)
    demandSector.set_writable()
    minTempDemand = Demnd.add_variable(idx, demdNaming+"_1_ZM_" + short + "_MinTempDH", minT)
    minTempDemand.set_writable()
    maxTempDemand = Demnd.add_variable(idx, demdNaming+"_1_ZM_" + short + "_MaxTempDC", maxT)
    maxTempDemand.set_writable()
    
    # static values - costs
    gridBuy = Demnd.add_variable(idx, demdNaming+"_1_ZM_" + short + "GrdBuyCost", buyCost)
    gridBuy.set_writable()
    gridSell = Demnd.add_variable(idx, demdNaming+"_1_ZM_" + short + "GrdSelCost", sellCost)
    gridSell.set_writable()
    
    # static values - forecast
    numberDFCSteps = Demnd.add_variable(idx, demdNaming+"_1_ZM_" + short + "_NumDFCstp", FC_step)
    numberDFCSteps.set_writable()
    sizeDFCSteps = Demnd.add_variable(idx, demdNaming+"_1_ZM_" + short + "_SizeDFCstp", FC_size)
    sizeDFCSteps.set_writable()

     # dynamic values
    currDemand = Demnd.add_variable(idx, demdNaming + "_2_ZM_" + short + "_currentDem", 0.0)
    currDemand.set_writable()
    
    Forecast = Demnd.add_folder(idx, short+"_Forecast")
    #ua.NodeId.from_string('ns={};i={}'.format(idx, 35))
    demandArray = Forecast.add_variable(idx, demdNaming +"_2_ZM_" + short + "_DemandFC", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    demandArray.set_writable()
    
    '''
    demdFC = []
    marketFC = []
    marketFC2 = []
    for i in range(FC_step):
        demdFC.append(Forecast.add_variable(idx, demdNaming+"_2_ZM_" + short + "_DemandFC" + str(i+1), 0.0))
        demdFC[i].set_writable()
        marketFC.append(Forecast.add_variable(idx, demdNaming+"_2_ZM_" + short + "GrdBuyCost" + str(i+1), cost))
        marketFC[i].set_writable()
        marketFC2.append(Forecast.add_variable(idx, demdNaming+"_2_ZM_" + short + "GrdSelCost" + str(i+1), 0.0))
        marketFC2[i].set_writable()
    '''
    
    # Only for CoSES
    
    Setpoint = Demnd.add_folder(idx, "Setpoints_DEMND{:02d}".format(int(counter[0,1]+1)))
    
    setpointArray = Setpoint.add_variable(idx, demdNaming +"_3_VM_" + short + "_DemndSetPt", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointArray.set_writable()

    counter[0,0]+=1

    return (setpointArray, demandArray, gridBuy, currDemand)
  



def add_Producer(counter, naming, FC_step, idx, name, Producer, inMEMAP, 
                 PrimSect, EffPrim, P_min, P_max, Temp_min, Temp_max, PrimEnCost, GenCosts, PrimCO2Cost):
    
    Prod = Producer.add_folder(idx, "CPROD{:02d}".format(int(counter[0,1]+1)))
    prodNaming = naming + "_CPROD{:02d}".format(int(counter[0,1]+1))
    print(prodNaming + " added...")
    short = sector_to_short(PrimSect)
    
    nameID = Prod.add_property(idx, prodNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    
    # static values - device
    primarySector = Prod.add_property(idx, prodNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    primaryEff = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    primaryEff.set_writable()
    MinP = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MinPower", P_min)
    MinP.set_writable()
    MaxP = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MaxPower", P_max)
    MaxP.set_writable()
    minTemp = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MinTemp", Temp_min)
    minTemp.set_writable()
    maxTemp = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MaxTemp", Temp_max)
    maxTemp.set_writable()
      
    # static values - costs
    energyCosts = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_PrimEnCost", PrimEnCost)
    energyCosts.set_writable()
    generationCosts = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_GenCosts", GenCosts)
    generationCosts.set_writable()
    CO2Costs = Prod.add_variable(idx, prodNaming + "_1_ZM_" + short + "_CO2PerKWh", PrimCO2Cost)
    CO2Costs.set_writable()
    
    # dynamic values
    MEMAPflag = Prod.add_variable(idx, prodNaming + "_0_ZM_" + short + "_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()
    production = Prod.add_variable(idx, prodNaming + "_2_ZM_" + short + "_curPwrPrim", 0.0)
    production.set_writable()
    
    Setpoint = Prod.add_folder(idx, "Setpoints_CPROD{:02d}".format(int(counter[0,1]+1)))
    setpointFC = Setpoint.add_variable(idx, prodNaming + "_3_VM_" + short + "_SPDevPwr", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointFC.set_writable()
    #for i in range(FC_step):
    #    setpointFC.append(Setpoint.add_variable(idx, prodNaming + "_3_VM_" + short + "_SPDevPwr"+ str(i+1), 0.0) )
    #    setpointFC[i].set_writable()
    

    counter[0,1]+=1
    
    return(production, setpointFC)
    
    
 
def add_VolatileProducer(counter, naming, idx, name, VolatileProducer, inMEMAP, 
                         PrimSect, installedPwr, MinTemp, MaxTemp, FC_step, FC_size, PrimEnCost, GenCosts, PrimCO2Cost):
    
    VProd = VolatileProducer.add_folder(idx, "VPROD{:02d}".format(int(counter[0,2]+1)))
    vProdNaming = naming+"_VPROD{:02d}".format(int(counter[0,2]+1))
    print(vProdNaming + " added...")
    short = sector_to_short(PrimSect)

    nameID = VProd.add_property(idx, vProdNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    
    
    # static values - device
    primarySector = VProd.add_property(idx, vProdNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    MaxP = VProd.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_MaxPower", installedPwr)
    MaxP.set_writable()
    minTemp = VProd.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_MinTemp", MinTemp)
    minTemp.set_writable()
    maxTemp = VProd.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_MaxTemp", MaxTemp)
    maxTemp.set_writable()
   
    # static values - costs
    energyCosts = VProd.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_PrimEnCost", PrimEnCost)
    energyCosts.set_writable()
    generationCosts = VProd.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_GenCosts", GenCosts)
    generationCosts.set_writable()
    CO2Costs = VProd.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_CO2PerKWh", PrimCO2Cost)
    CO2Costs.set_writable()
    
    # static values - forecast
    numberFCSteps = VProd.add_variable(idx, vProdNaming+"_1_ZM_" + short + "_NumPFCstp", FC_step)
    numberFCSteps.set_writable()
    sizeFCSteps = VProd.add_variable(idx, vProdNaming+"_1_ZM_" + short + "_SizePFCstp", FC_size)
    sizeFCSteps.set_writable()
    
    MEMAPflag = VProd.add_variable(idx, vProdNaming + "_0_ZM_" + short + "_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()
    production = VProd.add_variable(idx, vProdNaming + "_2_ZM_" + short + "_curPwrPrim", 0.0)
    production.set_writable()
    productionFC = VProd.add_variable(idx, vProdNaming + "_2_ZM_" + short + "_ProdFC", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    productionFC.set_writable()
    
    
    counter[0,2]+=1
    
    return(production, productionFC)
    
   
def add_Coupler(counter, naming, idx, name, Coupler, inMEMAP, 
                PrimSect, SecdSect, EffPrim, EffSec, P_min, P_max1, Temp_min, Temp_max, FC_step, PrimEnCost, GenCosts, PrimCO2Cost):
    
    Coup = Coupler.add_folder(idx, "COUPL{:02d}".format(int(counter[0,3]+1)))
    coupNaming = naming +"_COUPL{:02d}".format(int(counter[0,3]+1))
    print(coupNaming + " added...")
    short = sector_to_short(PrimSect)
    
    nameID = Coup.add_property(idx, coupNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()

    # static values - device
    primarySector = Coup.add_property(idx, coupNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    secondarySector = Coup.add_property(idx, coupNaming + "_1_ZM_" + short + "_SecdSect", SecdSect)
    secondarySector.set_writable()
    primaryEff = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    primaryEff.set_writable()
    primaryEff = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_EffSec", EffSec)
    primaryEff.set_writable()
    MinP = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_MinPower", P_min)
    MinP.set_writable()
    MaxP = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_MaxPower", P_max1)
    MaxP.set_writable()
    P_max2 = P_max1*EffSec/EffPrim
    MaxP2 = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_MaxPower2", P_max2)
    MaxP2.set_writable()
    minTemp = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_MinTemp", Temp_max)
    minTemp.set_writable()
    maxTemp = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_MaxTemp", Temp_min)
    maxTemp.set_writable()
    
    # static values - costs
    energyCosts = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_PrimEnCost", PrimEnCost)
    energyCosts.set_writable()
    generationCosts = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_GenCosts", GenCosts)
    generationCosts.set_writable()
    CO2Costs = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_CO2PerKWh", PrimCO2Cost)
    CO2Costs.set_writable()
    
    # dynamic values
    MEMAPflag = Coup.add_variable(idx, coupNaming + "_0_ZM_" + short + "_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()
    Prod1 = Coup.add_variable(idx, coupNaming + "_2_ZM_" + short + "_curPwrPrim", 0)
    Prod1.set_writable()
    Prod2 = Coup.add_variable(idx, coupNaming + "_2_ZM_" + short + "_curPwrSec", 0)
    Prod2.set_writable()

    # Setpoints
    Setpoint = Coup.add_folder(idx, "Setpoints_COUPL{:02d}".format(int(counter[0,3]+1)))
    setpointFC = Setpoint.add_variable(idx, coupNaming + "_3_VM_" + short + "_SPDevPwr", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointFC.set_writable()
	
    #for i in range(FC_step):
    #    setpointFC.append(Setpoint.add_variable(idx, coupNaming + "_3_VM_" + short + "_SPDevPwr"+ str(i+1), 0.0) )
    #    setpointFC[i].set_writable()
    
    
    counter[0,3]+=1
    
    return(setpointFC, Prod1, Prod2)
    

    
def add_Storage(counter, naming, FC_step, idx, name, Storage, inMEMAP, 
                PrimSect, CEffPrim, DisCEffPrim, Capacity, loss, Pmax_in, Pmax_Out, minTemp, maxTemp, minTempOut, 
                SOC_init, PrimEnCost, GenCosts, PrimCO2Cost):

    
    Stor = Storage.add_folder(idx, "STRGE{:02d}".format(int(counter[0,4]+1)))
    storNaming = naming+"_STRGE{:02d}".format(int(counter[0,4]+1))
    print(storNaming + " added...")
    short = sector_to_short(PrimSect)
    
    nameID = Stor.add_property(idx, storNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    
    # static values - device
    primarySector = Stor.add_property(idx, storNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    chargingEff = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_EffPrim", CEffPrim)
    chargingEff.set_writable()
    dischargingEff = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_DisEffPrim", DisCEffPrim)
    dischargingEff.set_writable()
    maxP_out = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_MaxPower", Pmax_Out)
    maxP_out.set_writable()
    maxP_in = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_MaxPowerIn", Pmax_in)
    maxP_in.set_writable()
    storageCap = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_Capacity", Capacity)
    storageCap.set_writable()
    storageLosses = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_StorLossPD", loss)
    storageLosses.set_writable()    
    minTempIn = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_TminStorHt", minTemp)
    minTempIn.set_writable()
    maxTempIn = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_TmaxStorHt", maxTemp)
    maxTempIn.set_writable()
    minTempDisCh = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_TDeChrgmin", minTempOut)
    minTempDisCh.set_writable()
    
    # static values - costs
    energyCosts = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_PrimEnCost", PrimEnCost)
    energyCosts.set_writable()
    generationCosts = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_GenCosts", GenCosts)
    generationCosts.set_writable()
    CO2Costs = Stor.add_variable(idx, storNaming + "_1_ZM_" + short + "_CO2PerKWh", PrimCO2Cost)
    CO2Costs.set_writable()
    
    # dynamic values
    MEMAPflag = Stor.add_variable(idx, storNaming + "_0_ZM_" + short + "_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()
    currentP_in = Stor.add_variable(idx, storNaming + "_2_ZM_" + short + "_curChrg", 0)
    currentP_in.set_writable()
    currentP_out = Stor.add_variable(idx, storNaming + "_2_ZM_" + short + "_curDeChrg", 0)
    currentP_out.set_writable()
    SOC = Stor.add_variable(idx, storNaming + "_2_ZM_" + short + "_curSOC", SOC_init)
    SOC.set_writable()
    SOCcalc = Stor.add_variable(idx, storNaming + "_2_ZM_" + short + "_calcSOC", SOC_init)
    SOCcalc.set_writable()
    
     # Setpoints
    Setpoint = Stor.add_folder(idx, "Setpoints_STRGE{:02d}".format(int(counter[0,4]+1)))
    setpointChgFC = Setpoint.add_variable(idx, storNaming + "_3_VM_" + short + "_SPCharge", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointChgFC.set_writable()
    setpointDisChgFC = Setpoint.add_variable(idx, storNaming + "_3_VM_" + short + "_SPDisChrg", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointDisChgFC.set_writable()
	
    #for i in range(FC_step):
    #    setpointChgFC.append(Setpoint.add_variable(idx, storNaming + "_3_VM_" + short + "_SPCharge"+ str(i+1), 0.0) )
    #    setpointChgFC[i].set_writable()
    #    setpointDisChgFC.append(Setpoint.add_variable(idx, storNaming + "_3_VM_" + short + "_SPDisChrg"+ str(i+1), 0.0) )
    #    setpointDisChgFC[i].set_writable()
    
    
    counter[0,4]+=1
    
    return(currentP_in, currentP_out, setpointChgFC, setpointDisChgFC, SOC)
    


# ======================== Helper Funktions ======================
    
def sector_to_short(sec):
    switcher = {
            "heat": "HT",
            "electricity" : "EL",
            "elec" : "EL",
            "cold" : "CD"
            }
    return switcher.get(sec, "XX")    

