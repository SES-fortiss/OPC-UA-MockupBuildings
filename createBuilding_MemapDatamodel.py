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
    
    k = range(500, 550, 2)
    
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
    trigger = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, 5000)), naming+"_NONE_0_ZM_XX_trigger", 0)
    trigger.set_writable()
    
    SPFwrdPwr = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[5])), naming + "NONE_3_VM_HT_SPPwrFrwd",0.0)
    SPFwrdPwr.set_writable()
    SPBackPwr = General.add_variable(ua.NodeId.from_string('ns={};i={}'.format(idx, k[6])), naming + "NONE_3_VM_HT_SPPwrBack", 0.0)
    SPBackPwr.set_writable()

    #return (only writables?)
    return (endPoint, connStat, EMSnameID, trigger)



def add_Demand(counter, naming, idx, Demand, sector, demName, FC_step, buyCost, sellCost, PrimCO2Cost, MaxBuyLimit):
    
    Demnd = Demand.add_folder(idx, "DEMND{:02d}".format(int(counter[0,0]+1)))
    demdNaming = naming+"_DEMND{:02d}".format(int(counter[0,0]+1))
    print(demdNaming + " added...")
    short = sector_to_short(sector)
    
    nameID = Demnd.add_variable(idx, demdNaming+"_0_ZM_XX_nameID", demName)
    nameID.set_writable()
    
    # static values - device
    Parameters = Demnd.add_folder(idx, short+"_Parameters")
    demandSector = Parameters.add_variable(idx, demdNaming+"_1_ZM_" + short + "_PrimSect", sector)
    demandSector.set_writable()
    
    
    # Forecasts
    Forecast = Demnd.add_folder(idx, short+"_Forecast")
    
    demandArray = Forecast.add_variable(idx, demdNaming + "_2_ZM_" + short + "_DemandFC", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    demandArray.set_writable()

    gridBuyAr = Forecast.add_variable(idx, demdNaming + "_2_ZM_" + short + "_GrdBuyCost", list(buyCost*np.ones(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    gridBuyAr.set_writable()
    gridSellAr = Forecast.add_variable(idx, demdNaming + "_2_ZM_" + short + "_GrdSellCost", list(sellCost*np.ones(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    gridSellAr.set_writable()

    CO2Costs = Forecast.add_variable(idx, demdNaming + "_2_ZM_" + short + "_CO2PerKWh", list(PrimCO2Cost*np.ones(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    CO2Costs.set_writable()
    
    MaxElecBuylimit = Forecast.add_variable(idx, demdNaming + "_2_ZM_" + short + "_MaxBuyLimit", list(MaxBuyLimit*np.ones(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    MaxElecBuylimit.set_writable()



    Setpoint = Demnd.add_folder(idx, "Setpoints_DEMND{:02d}".format(int(counter[0,1]+1)))
    
    SPGrdBuyAr = Setpoint.add_variable(idx, demdNaming + "_3_VM_" + short + "_SPGrdBuy", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    SPGrdBuyAr.set_writable()
    SPGrdSellAr = Setpoint.add_variable(idx, demdNaming + "_3_VM_" + short + "_SPGrdSell", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    SPGrdSellAr.set_writable()

    counter[0,0]+=1

    return (demandArray, gridBuyAr, gridSellAr)




def add_Producer(counter, naming, FC_step, idx, name, Producer, inMEMAP, 
                 PrimSect, EffPrim, P_min, P_max, GenCosts, PrimCO2Cost):
    
    Prod = Producer.add_folder(idx, "CPROD{:02d}".format(int(counter[0,1]+1)))
    prodNaming = naming + "_CPROD{:02d}".format(int(counter[0,1]+1))
    print(prodNaming + " added...")
    short = sector_to_short(PrimSect)
    
    nameID = Prod.add_property(idx, prodNaming + "_0_ZM_XX_nameID", name)
    nameID.set_writable()
    MEMAPflag = Prod.add_variable(idx, prodNaming + "_0_ZM_" + short + "_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()
    
    
    Parameters = Prod.add_folder(idx, short+"_Parameters")
    
    primarySector = Parameters.add_property(idx, prodNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    primaryEff = Parameters.add_variable(idx, prodNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    primaryEff.set_writable()
    MinP = Parameters.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MinPower", P_min)
    MinP.set_writable()
    MaxP = Parameters.add_variable(idx, prodNaming + "_1_ZM_" + short + "_MaxPower", P_max)
    MaxP.set_writable()
    CO2Costs = Parameters.add_variable(idx, prodNaming + "_1_ZM_" + short + "_CO2PerKWh", PrimCO2Cost)
    CO2Costs.set_writable()

    # Forecasts
    Forecast = Prod.add_folder(idx, short+"_Forecast")

    generationCosts = Forecast.add_variable(idx, prodNaming + "_1_ZM_" + short + "_GenCosts", list(GenCosts*np.ones(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    generationCosts.set_writable()
    

    Setpoint = Prod.add_folder(idx, "Setpoints_CPROD{:02d}".format(int(counter[0,1]+1)))
    SPDevPwrAr = Setpoint.add_variable(idx, prodNaming + "_3_VM_" + short + "_SPDevPwr", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    SPDevPwrAr.set_writable()

    counter[0,1]+=1
    
    return(generationCosts, SPDevPwrAr)
    
    
 
def add_VolatileProducer(counter, naming, idx, name, VolatileProducer, inMEMAP, 
                         PrimSect, installedPwr, FC_step, GenCosts, PrimCO2Cost):
    
    VProd = VolatileProducer.add_folder(idx, "VPROD{:02d}".format(int(counter[0,2]+1)))
    vProdNaming = naming+"_VPROD{:02d}".format(int(counter[0,2]+1))
    print(vProdNaming + " added...")
    short = sector_to_short(PrimSect)

    nameID = VProd.add_property(idx, vProdNaming + "_0_ZM_XX_nameID", name)
    nameID.set_writable()
    MEMAPflag = VProd.add_variable(idx, vProdNaming + "_0_ZM_" + short + "_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()
    
    
    # Parameters
    Parameters = VProd.add_folder(idx, short+"_Parameters")
    
    primarySector = Parameters.add_property(idx, vProdNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    MaxP = Parameters.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_MaxPower", installedPwr)
    MaxP.set_writable()
    generationCosts = Parameters.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_GenCosts", GenCosts)
    generationCosts.set_writable()
    CO2Costs = Parameters.add_variable(idx, vProdNaming + "_1_ZM_" + short + "_CO2PerKWh", PrimCO2Cost)
    CO2Costs.set_writable()
    
    # Forecasts
    Forecast = VProd.add_folder(idx, short+"_Forecast")

    productionFC = Forecast.add_variable(idx, vProdNaming + "_2_ZM_" + short + "_ProdFC", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    productionFC.set_writable()
    
    
    counter[0,2]+=1
    
    return(productionFC)
    
   
def add_Coupler(counter, naming, idx, name, Coupler, inMEMAP, 
                PrimSect, SecdSect, EffPrim, EffSec, P_min, P_max1, FC_step, GenCosts, PrimCO2Cost):
    
    Coup = Coupler.add_folder(idx, "COUPL{:02d}".format(int(counter[0,3]+1)))
    coupNaming = naming +"_COUPL{:02d}".format(int(counter[0,3]+1))
    print(coupNaming + " added...")
    short = sector_to_short(PrimSect)
    
    nameID = Coup.add_property(idx, coupNaming + "_0_ZM_XX_nameID", name)
    nameID.set_writable()
    MEMAPflag = Coup.add_variable(idx, coupNaming + "_0_ZM_" + short + "_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()

    # Parameters
    Parameters = Coup.add_folder(idx, short+"_Parameters")
    
    primarySector = Parameters.add_property(idx, coupNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    secondarySector = Parameters.add_property(idx, coupNaming + "_1_ZM_" + short + "_SecdSect", SecdSect)
    secondarySector.set_writable()
    primaryEff = Parameters.add_variable(idx, coupNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    primaryEff.set_writable()
    primaryEff = Parameters.add_variable(idx, coupNaming + "_1_ZM_" + short + "_EffSec", EffSec)
    primaryEff.set_writable()
    MinP = Parameters.add_variable(idx, coupNaming + "_1_ZM_" + short + "_MinPower", P_min)
    MinP.set_writable()
    MaxP = Parameters.add_variable(idx, coupNaming + "_1_ZM_" + short + "_MaxPower", P_max1)
    MaxP.set_writable()
    CO2Costs = Parameters.add_variable(idx, coupNaming + "_1_ZM_" + short + "_CO2PerKWh", PrimCO2Cost)
    CO2Costs.set_writable()
    
    # Forecasts
    Forecast = Coup.add_folder(idx, short+"_Forecast")

    generationCosts = Forecast.add_variable(idx, coupNaming + "_2_ZM_" + short + "_GenCosts", list(GenCosts*np.ones(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    generationCosts.set_writable()


    # Setpoints
    Setpoint = Coup.add_folder(idx, "Setpoints_COUPL{:02d}".format(int(counter[0,3]+1)))
    SPDevPwrAr = Setpoint.add_variable(idx, coupNaming + "_3_VM_" + short + "_SPDevPwr", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    SPDevPwrAr.set_writable()
    
    
    counter[0,3]+=1
    
    return(generationCosts, SPDevPwrAr)
    

    
def add_Storage(counter, naming, FC_step, idx, name, Storage, inMEMAP, 
                PrimSect, CEffPrim, DisCEffPrim, Capacity, loss, Pmax_in, Pmax_Out,
                SOC_init, GenCosts, PrimCO2Cost):

    
    Stor = Storage.add_folder(idx, "STRGE{:02d}".format(int(counter[0,4]+1)))
    storNaming = naming+"_STRGE{:02d}".format(int(counter[0,4]+1))
    print(storNaming + " added...")
    short = sector_to_short(PrimSect)
    
    nameID = Stor.add_property(idx, storNaming + "_0_ZM_XX_nameID", name)
    nameID.set_writable()
    MEMAPflag = Stor.add_variable(idx, storNaming + "_0_ZM_" + short + "_MEMAPflag", inMEMAP)
    MEMAPflag.set_writable()
    
   # Parameters
    Parameters = Stor.add_folder(idx, short+"_Parameters")
    
    primarySector = Parameters.add_property(idx, storNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    chargingEff = Parameters.add_variable(idx, storNaming + "_1_ZM_" + short + "_EffPrim", CEffPrim)
    chargingEff.set_writable()
    dischargingEff = Parameters.add_variable(idx, storNaming + "_1_ZM_" + short + "_DisEffPrim", DisCEffPrim)
    dischargingEff.set_writable()
    maxP_out = Parameters.add_variable(idx, storNaming + "_1_ZM_" + short + "_MaxPower", Pmax_Out)
    maxP_out.set_writable()
    maxP_in = Parameters.add_variable(idx, storNaming + "_1_ZM_" + short + "_MaxPowerIn", Pmax_in)
    maxP_in.set_writable()
    storageCap = Parameters.add_variable(idx, storNaming + "_1_ZM_" + short + "_Capacity", Capacity)
    storageCap.set_writable()
    storageLosses = Parameters.add_variable(idx, storNaming + "_1_ZM_" + short + "_StorLossPD", loss)
    storageLosses.set_writable()    
    generationCosts = Parameters.add_variable(idx, storNaming + "_1_ZM_" + short + "_GenCosts", GenCosts)
    generationCosts.set_writable()
    CO2Costs = Parameters.add_variable(idx, storNaming + "_1_ZM_" + short + "_CO2PerKWh", PrimCO2Cost)
    CO2Costs.set_writable()

    # Setpoints
    Setpoint = Stor.add_folder(idx, "Setpoints_STRGE{:02d}".format(int(counter[0,4]+1)))
    setpointChgAr = Setpoint.add_variable(idx, storNaming + "_3_VM_" + short + "_SPCharge", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointChgAr.set_writable()
    setpointDisChgAr = Setpoint.add_variable(idx, storNaming + "_3_VM_" + short + "_SPDisChrg", list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointDisChgAr.set_writable()
    
    # Measurementss
    Measurement = Stor.add_folder(idx, short+"_Measurement")
    SOC = Measurement.add_variable(idx, storNaming + "_4_ZM_" + short + "_curSOC", SOC_init)
    SOC.set_writable()
	
    counter[0,4]+=1
    
    return(storageLosses, setpointChgAr, setpointDisChgAr, SOC)
    


# ======================== Helper Funktions ======================
    
def sector_to_short(sec):
    switcher = {
            "heat": "HT",
            "electricity" : "EL",
            "elec" : "EL",
            "cold" : "CD"
            }
    return switcher.get(sec, "XX")    

