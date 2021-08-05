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
    

def create_Namespace(idx, objects):
    General = objects.add_folder(idx, "0_EMS")
    Demand = objects.add_folder(idx, "1_Demand")

    Devices = objects.add_folder(idx, "2_Devices")
    # Untersysteme
    Producer = Devices.add_folder(idx, "21_Producer")
    VolatileProducer = Devices.add_folder(idx, "22_VolatileProducer")
    Coupler = Devices.add_folder(idx, "23_Coupler")
    Storage = Devices.add_folder(idx, "24_Storage")
    #HeatConnection = Devices.add_folder(idx, "25_HeatConnection")
    #ElecMarket = Devices.add_folder(idx, "26_ElecMarket")
    
    return (General, Demand, Devices, Producer, VolatileProducer, Coupler, Storage) # HeatConnection, ElecMarket

    


def add_General(idx, myNodeIDcntr, naming, General, EMSname):

    k=myNodeIDcntr

    EMSnameID = General.add_variable(mynsid(idx, k), naming + "_NONE_0_ZM_XX_nameID", EMSname)
    EMSnameID.set_writable()
    k+=1

    Trigger = General.add_variable(mynsid(idx, k), naming + "_NONE_0_ZM_XX_trigger", 0)
    Trigger.set_writable()
    k+=1

    efficiency = General.add_variable(mynsid(idx, k),
                                      naming + "_NONE_1_ZM_HT" + "_EffHtNetReceive", 0.0)
    efficiency.set_writable()
    k += 1

    SPFwrdPwr = General.add_variable(mynsid(idx, k),
                                     naming + "NONE_3_VM_HT_SPHeatFrwd", 0.0)
    SPFwrdPwr.set_writable()
    k += 1

    SPBackPwr = General.add_variable(mynsid(idx, k),
                                     naming + "NONE_3_VM_HT_SPHeatBack", 0.0)
    SPBackPwr.set_writable()
    k += 1

    myNodeIDcntr = k
    return (myNodeIDcntr, EMSnameID, Trigger)



def add_Demand(counter, naming, idx, myNodeIDcntr, Demand, sector, demName, FC_step):
    k = myNodeIDcntr
    Demnd = Demand.add_folder(idx, "DEMND{:02d}".format(int(counter[0,0]+1)))
    demdNaming = naming+"_DEMND{:02d}".format(int(counter[0,0]+1))
    print(demdNaming + " added...")
    short = sector_to_short(sector)
    
    nameID = Demnd.add_property(mynsid(idx, k),
                                demdNaming+"_1_ZM_XX_nameID", demName)
    nameID.set_writable()
    k+=1

    # static values - device
    demandSector = Demnd.add_variable(mynsid(idx, k),
                                      demdNaming+"_1_ZM_" + short + "_PrimSect", sector)
    demandSector.set_writable()
    k+=1
    
    # dynamic values
    demandArray = Demnd.add_variable(mynsid(idx, k),
                                     demdNaming +"_2_ZM_" + short + "_DemandFC",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    demandArray.set_writable()
    k+=1

    currDemand = Demnd.add_variable(mynsid(idx, k), demdNaming + "_2_ZM_" + short + "_curDem", 0.0)
    currDemand.set_writable()
    k+=1
    
    GrdBuyCost = Demnd.add_variable(mynsid(idx, k),
                                     demdNaming + "_1_ZM_" + short + "_GrdBuyCost",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    GrdBuyCost.set_writable()
    k += 1
    
    GrdSellCost = Demnd.add_variable(mynsid(idx, k),
                                     demdNaming + "_1_ZM_" + short + "_GrdSellCost",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    GrdSellCost.set_writable()
    k += 1

    curPriceBuy = Demnd.add_variable(mynsid(idx, k),
                                    demdNaming + "_1_VM_" + short + "_curPriceBuy", 0.0)
    curPriceBuy.set_writable()
    k += 1

    curPriceSell = Demnd.add_variable(mynsid(idx, k),
                                     demdNaming + "_1_VM_" + short + "_curPriceSell", 0.0)
    curPriceSell.set_writable()
    k += 1


    GrdBuyCO2 = Demnd.add_variable(mynsid(idx, k),
                                    demdNaming + "_1_ZM_" + short + "_GrdBuyCO2",
                                    list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    GrdBuyCO2.set_writable()
    k += 1

    GrdSellCO2 = Demnd.add_variable(mynsid(idx, k),
                                     demdNaming + "_1_ZM_" + short + "_GrdSellCO2",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    GrdSellCO2.set_writable()
    k += 1

    curCO2Buy = Demnd.add_variable(mynsid(idx, k),
                                     demdNaming + "_1_VM_" + short + "_curCO2Buy", 0.0)
    curCO2Buy.set_writable()
    k += 1

    curCO2Sell = Demnd.add_variable(mynsid(idx, k),
                                      demdNaming + "_1_VM_" + short + "_curCO2Sell", 0.0)
    curCO2Sell.set_writable()
    k += 1

    GrdBuyAr = Demnd.add_variable(mynsid(idx, k), demdNaming + "_1_ZM_" + short + "_SPGrdBuyAr",
                                    list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    GrdBuyAr.set_writable()
    k += 1

    GrdSellAr = Demnd.add_variable(mynsid(idx, k), demdNaming + "_1_ZM_" + short + "_SPGrdSellAr",
                                       list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    GrdSellAr.set_writable()
    k += 1
    
    GrdBuy = Demnd.add_variable(mynsid(idx, k), demdNaming + "_3_VM_" + short + "_SPGrdBuy", 0.0)
    GrdBuy.set_writable()
    k += 1

    GrdSell = Demnd.add_variable(mynsid(idx, k), demdNaming + "_3_VM_" + short + "_SPGrdSell", 0.0)
    GrdSell.set_writable()
    k += 1

    # Only for CoSES

    DemandSetPt = Demnd.add_variable(mynsid(idx, k), demdNaming + "_1_ZM_" + short + "_DemndSetPt", 0.0)
    DemandSetPt.set_writable()
    k+=1

    '''Setpoint = Demnd.add_folder(idx, "Setpoints_DEMND{:02d}".format(int(counter[0,1]+1)))
    setpointArray = Setpoint.add_variable(idx, demdNaming +"_3_VM_" + short + "_DemndSetPt",
                                        list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointArray.set_writable()
    k+=1
    '''
    
    
    myNodeIDcntr = k
    counter[0,0]+=1

    return (myNodeIDcntr, counter, DemandSetPt, demandArray, currDemand, GrdBuyCost, GrdSellCost, GrdBuy, GrdSell,
            curPriceBuy, curPriceSell, GrdBuyCO2, GrdSellCO2, curCO2Buy, curCO2Sell)


def add_Producer(counter, naming, FC_step, idx, myNodeIDcntr, name, Producer,
                 PrimSect, EffPrim, P_min, P_max):
    k = myNodeIDcntr

    Prod = Producer.add_folder(idx, "CPROD{:02d}".format(int(counter[0,1]+1)))
    prodNaming = naming + "_CPROD{:02d}".format(int(counter[0,1]+1))
    print(prodNaming + " added...")
    short = sector_to_short(PrimSect)
    
    nameID = Prod.add_property(mynsid(idx, k), prodNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    k+=1
    
    # static values - device
    primarySector = Prod.add_variable(mynsid(idx, k), prodNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    k+=1
    MinP = Prod.add_variable(mynsid(idx, k), prodNaming + "_1_ZM_" + short + "_MinPower", P_min)
    MinP.set_writable()
    k+=1
    MaxP = Prod.add_variable(mynsid(idx, k), prodNaming + "_1_ZM_" + short + "_MaxPower", P_max)
    MaxP.set_writable()
    k+=1
    primaryEff = Prod.add_variable(mynsid(idx, k), prodNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    primaryEff.set_writable()
    k+=1

    # cost forecast
    GenCosts = Prod.add_variable(mynsid(idx, k),
                                     prodNaming + "_1_ZM_" + short + "_GenCosts",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    GenCosts.set_writable()
    k+=1
    
    CO2PerKWh = Prod.add_variable(mynsid(idx, k),
                                     prodNaming + "_1_ZM_" + short + "_CO2PerKWh",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    CO2PerKWh.set_writable()
    k+=1

    
    # dynamic values
    curPrice = Prod.add_variable(mynsid(idx, k), prodNaming + "_1_VM_" + short + "_curPrice", 0.0)
    curPrice.set_writable()
    k += 1

    curCO2costs = Prod.add_variable(mynsid(idx, k), prodNaming + "_1_VM_" + short + "_curCO2costs", 0.0)
    curCO2costs.set_writable()
    k += 1

    SPDevPwrAr = Prod.add_variable(mynsid(idx, k), prodNaming + "_3_VM_" + short + "_SPDevPwrAr",
                                   list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    SPDevPwrAr.set_writable()
    k+=1
    
    SPDevPwr = Prod.add_variable(mynsid(idx, k), prodNaming + "_3_VM_" + short + "_SPDevPwr", 0.0)
    SPDevPwr.set_writable()
    k+=1

    production = Prod.add_variable(mynsid(idx, k), prodNaming + "_2_ZM_" + short + "_curPwr", 0.0)
    production.set_writable()
    k+=1

    counter[0,1]+=1
    myNodeIDcntr = k
    return(myNodeIDcntr, production, GenCosts, CO2PerKWh, SPDevPwr, curPrice, curCO2costs)
    
    
 
def add_VolatileProducer(counter, naming, idx, myNodeIDcntr, name, VolatileProducer,
                         PrimSect, installedPwr, FC_step):
    k = myNodeIDcntr

    VProd = VolatileProducer.add_folder(mynsid(idx, k), "VPROD{:2d}".format(int(counter[0,2]+1)))
    vProdNaming = naming+"_VPROD{:2d}".format(int(counter[0,2]+1))
    print(vProdNaming + " added...")
    short = sector_to_short(PrimSect)

    nameID = VProd.add_property(mynsid(idx, k), vProdNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    k+=1
    
    
    # static values - device
    primarySector = VProd.add_variable(mynsid(idx, k), vProdNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    k+=1
    MaxP = VProd.add_variable(mynsid(idx, k), vProdNaming + "_1_ZM_" + short + "_MaxPower", installedPwr)
    MaxP.set_writable()
    k+=1
   
    # dynamic values - costs
    GenCosts = VProd.add_variable(mynsid(idx, k),
                                     vProdNaming + "_1_ZM_" + short + "_GenCosts",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    GenCosts.set_writable()
    k+=1
    
    CO2PerKWh = VProd.add_variable(mynsid(idx, k),
                                     vProdNaming + "_1_ZM_" + short + "_CO2PerKWh",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    CO2PerKWh.set_writable()
    k+=1

    curPrice = VProd.add_variable(mynsid(idx, k),
                                  vProdNaming + "_1_VM_" + short + "_curPrice", 0.0)
    curPrice.set_writable()
    k += 1

    curCO2costs = VProd.add_variable(mynsid(idx, k),
                                   vProdNaming + "_1_VM_" + short + "_curCO2costs", 0.0)
    curCO2costs.set_writable()
    k += 1
    
    
    # dynamic values - forecast
    capacityFC = VProd.add_variable(mynsid(idx, k), vProdNaming+"_1_ZM_" + short + "_capacityFC",
                                    list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    capacityFC.set_writable()
    k+=1

    SPDevPwrAr = VProd.add_variable(mynsid(idx, k), vProdNaming + "_3_VM_" + short + "_SPDevPwrAr",
                                    list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    SPDevPwrAr.set_writable()
    k+=1
    
    SPDevPwr = VProd.add_variable(mynsid(idx, k), vProdNaming + "_3_VM_" + short + "_SPDevPwr", 0.0)
    SPDevPwr.set_writable()
    k+=1

    production = VProd.add_variable(mynsid(idx, k), vProdNaming + "_2_ZM_" + short + "_curPwrPrim", 0.0)
    production.set_writable()
    k+=1

    counter[0,2]+=1
    myNodeIDcntr = k
    return(myNodeIDcntr, production, GenCosts, CO2PerKWh, SPDevPwr, curPrice, curCO2costs)
    
   
def add_Coupler(counter, naming, idx, myNodeIDcntr, name, Coupler,
                PrimSect, SecdSect, EffPrim, EffSec, P_min, P_max1, FC_step):
    k = myNodeIDcntr

    Coup = Coupler.add_folder(idx, "COUPL{:02d}".format(int(counter[0,3]+1)))
    coupNaming = naming +"_COUPL{:02d}".format(int(counter[0,3]+1))
    print(coupNaming + " added...")
    short = sector_to_short(PrimSect)
    
    nameID = Coup.add_property(mynsid(idx, k), coupNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    k+=1

    # static values - device
    primarySector = Coup.add_variable(mynsid(idx, k), coupNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    k+=1
    secondarySector = Coup.add_variable(mynsid(idx, k), coupNaming + "_1_ZM_" + short + "_SecdSect", SecdSect)
    secondarySector.set_writable()
    k+=1
    primaryEff = Coup.add_variable(mynsid(idx, k), coupNaming + "_1_ZM_" + short + "_EffPrim", EffPrim)
    primaryEff.set_writable()
    k+=1
    secondaryEff = Coup.add_variable(mynsid(idx, k), coupNaming + "_1_ZM_" + short + "_EffSec", EffSec)
    secondaryEff.set_writable()
    k+=1
    MinP = Coup.add_variable(mynsid(idx, k), coupNaming + "_1_ZM_" + short + "_MinPower", P_min)
    MinP.set_writable()
    k+=1
    MaxP = Coup.add_variable(mynsid(idx, k), coupNaming + "_1_ZM_" + short + "_MaxPower", P_max1)
    MaxP.set_writable()
    k+=1
    '''P_max2 = P_max1*EffSec/EffPrim
    MaxP2 = Coup.add_variable(idx, coupNaming + "_1_ZM_" + short + "_MaxPower2", P_max2)
    MaxP2.set_writable()
    k+=1
    '''
        
    # dynamic values
    # cost forecast
    GenCosts = Coup.add_variable(mynsid(idx, k),
                                     coupNaming + "_1_ZM_" + short + "_GenCosts",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    GenCosts.set_writable()
    k+=1
    
    CO2PerKWh = Coup.add_variable(mynsid(idx, k),
                                     coupNaming + "_1_ZM_" + short + "_CO2PerKWh",
                                     list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    CO2PerKWh.set_writable()
    k+=1

    #

    curPrice = Coup.add_variable(mynsid(idx, k),
                                 coupNaming + "_1_VM_" + short + "_curPrice", 0.0)
    curPrice.set_writable()
    k += 1

    curCO2costs = Coup.add_variable(mynsid(idx, k),
                                  coupNaming + "_1_VM_" + short + "_curCO2costs", 0.0)
    curCO2costs.set_writable()
    k += 1

    #
    
    Prod1 = Coup.add_variable(mynsid(idx, k), coupNaming + "_2_ZM_" + short + "_curPwrPrim", 0)
    Prod1.set_writable()
    k+=1
    Prod2 = Coup.add_variable(mynsid(idx, k), coupNaming + "_2_ZM_" + short + "_curPwrSec", 0)
    Prod2.set_writable()
    k+=1

    # Setpoints
    SPDevPwrAr = Coup.add_variable(mynsid(idx, k), coupNaming + "_3_VM_" + short + "_SPDevPwrAr", list(np.zeros(FC_step)),
                                       datatype=opcua.ua.ObjectIds.Double)
    SPDevPwrAr.set_writable()
    k+=1
    
    SPDevPwr = Coup.add_variable(mynsid(idx, k), coupNaming + "_3_VM_" + short + "_SPDevPwr", 0.0)
    SPDevPwr.set_writable()
    k+=1
    
    counter[0,3]+=1
    myNodeIDcntr = k
    return(myNodeIDcntr, Prod1, Prod2, GenCosts, CO2PerKWh, SPDevPwr, curPrice, curCO2costs)
    

    
def add_Storage(counter, naming, FC_step, idx, myNodeIDcntr, name, Storage,
                PrimSect, CEffPrim, DisCEffPrim, Capacity, loss, Pmax_in, Pmax_Out,
                SOC_init):
    k = myNodeIDcntr
    
    Stor = Storage.add_folder(idx, "STRGE{:02d}".format(int(counter[0,4]+1)))
    storNaming = naming+"_STRGE{:02d}".format(int(counter[0,4]+1))
    print(storNaming + " added...")
    short = sector_to_short(PrimSect)
    
    nameID = Stor.add_property(mynsid(idx, k), storNaming + "_1_ZM_XX_nameID", name)
    nameID.set_writable()
    k+=1
    
    # static values - device
    primarySector = Stor.add_variable(mynsid(idx, k), storNaming + "_1_ZM_" + short + "_PrimSect", PrimSect)
    primarySector.set_writable()
    k+=1
    chargingEff = Stor.add_variable(mynsid(idx, k), storNaming + "_1_ZM_" + short + "_EffPrim", CEffPrim)
    chargingEff.set_writable()
    k+=1
    dischargingEff = Stor.add_variable(mynsid(idx, k), storNaming + "_1_ZM_" + short + "_DisEffPrim", DisCEffPrim)
    dischargingEff.set_writable()
    k+=1
    storageLosses = Stor.add_variable(mynsid(idx, k), storNaming + "_1_ZM_" + short + "_StorLossPD", loss)
    storageLosses.set_writable()
    k+=1
    maxP_out = Stor.add_variable(mynsid(idx, k), storNaming + "_1_ZM_" + short + "_MaxPower", Pmax_Out)
    maxP_out.set_writable()
    k+=1
    maxP_in = Stor.add_variable(mynsid(idx, k), storNaming + "_1_ZM_" + short + "_MaxPowerIn", Pmax_in)
    maxP_in.set_writable()
    k+=1
    storageCap = Stor.add_variable(mynsid(idx, k), storNaming + "_1_ZM_" + short + "_Capacity", Capacity)
    storageCap.set_writable()
    k+=1
    CO2PerKWh = Stor.add_variable(mynsid(idx, k), storNaming + "_1_ZM_" + short + "_CO2PerKWh", -0.00012)
    CO2PerKWh.set_writable()
    k += 1
    
    # dynamic values
    currentP_in = Stor.add_variable(mynsid(idx, k), storNaming + "_2_ZM_" + short + "_curChrg", 0)
    currentP_in.set_writable()
    k+=1
    currentP_out = Stor.add_variable(mynsid(idx, k), storNaming + "_2_ZM_" + short + "_curDeChrg", 0)
    currentP_out.set_writable()
    k+=1
    SOC = Stor.add_variable(mynsid(idx, k), storNaming + "_2_ZM_" + short + "_curSOC", SOC_init)
    SOC.set_writable()
    k+=1
    calcSOC = Stor.add_variable(mynsid(idx, k), storNaming + "_4_VM_" + short + "_calcSOC", SOC_init)
    calcSOC.set_writable()
    k+=1
    
     # Setpoints
    setpointChgAr = Stor.add_variable(mynsid(idx, k), storNaming + "_3_VM_" + short + "_SPChargeAr",
                                      list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointChgAr.set_writable()
    k+=1
    
    setpointChg = Stor.add_variable(mynsid(idx, k), storNaming + "_3_VM_" + short + "_SPCharge", 0.0)
    setpointChg.set_writable()
    k+=1
    
    setpointDisChgAr = Stor.add_variable(mynsid(idx, k), storNaming + "_3_VM_" + short + "_SPDisChrgAr",
                                         list(np.zeros(FC_step)), datatype=opcua.ua.ObjectIds.Double)
    setpointDisChgAr.set_writable()
    k+=1
    
    setpointDisChg = Stor.add_variable(mynsid(idx, k), storNaming + "_3_VM_" + short + "_SPDisChrg", 0.0)
    setpointDisChg.set_writable()
    k+=1
    
    # static values - costs
    energyCosts = Stor.add_variable(mynsid(idx, k), storNaming + "_1_ZM_" + short + "_PrimEnCost", 0.0)
    energyCosts.set_writable()
    k+=1
    
    counter[0,4]+=1
    myNodeIDcntr = k
    return(myNodeIDcntr, SOC, calcSOC, setpointChg, setpointDisChg)
    



# ======================== Helper Funktions ======================
    
def sector_to_short(sec):
    switcher = {
            "heat": "HT",
            "electricity" : "EL",
            "elec" : "EL",
            "cold" : "CD"
            }
    return switcher.get(sec, "XX")    

def mynsid(idx, myNodeIDcntr):
    nodeID=ua.NodeId.from_string('ns={};i={}'.format(idx, myNodeIDcntr))
    return nodeID