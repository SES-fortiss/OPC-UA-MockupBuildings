# Example OPC UA server for local Energy Management Systems (EMS)

### Description
This code can be used to create any OPC UA Server, that emulates a local Energy Management System according to the MEMAP data model (https://memap-project.de). Therefore the file `createBuildings_MemapDatamodel.py` contains the following general methods
* `create_Server_Basics`
* `create_Namespace`  

as well as the follwoing methods according to the device classes defined in the data model:   

* `add_General` (EMS)
* `add_Demand` (DEMND)
* `add_Producer` (CPROD)
* `add_VolatileProducer` (VPROD)
* `add_Coupler` (COUPL)
* `add_Storage` (STRGE)  
 
These functions will add the according devices with all necessary input parameters to the namespace of the OPC UA Server of this mocked EMS.

### 2 building example
By starting `2Houses_MinimalMemapDatamodel.py` two example Mock-EMS are parametrized and two OPC UA servers launched at `opc.tcp://localhost:4880` and `opc.tcp://localhost:4890`. The Servers are simulating current demand and generation according to standard load profiles (CSV-files in data folder), which is updated at the respective node (demand/generation forecasts) every 15 seconds.


![alt text](https://github.com/JanAxelMayer/Building_OPCUA_Server/blob/master/Old%20Versions/2Houses_NoMemap.png)

The code can run on any device like e.g. raspberry pi, to test or browse the OPC UA Servers with any client - or to simulate any building and virtually connected it to a [MEMAP](https://git.fortiss.org/ASCI-public/memap/-/tree/main/projects) instance (click below).

<details>
<summary> 2 building example with MEMAP </summary>
  
![alt text](https://github.com/JanAxelMayer/Building_OPCUA_Server/blob/master/Old%20Versions/2Houses.png)

![JSON File for the 2 Building example](https://github.com/JanAxelMayer/Building_OPCUA_Server/blob/master/Old%20Versions/2HOUSES_DM_local.json)
  
</details>

