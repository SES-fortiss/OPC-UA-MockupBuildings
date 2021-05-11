siehe auch https://github.com/SES-fortiss/OPC-UA-MockupBuildings/CoSES

Zum Starten:
1.	Auf dem CoSES OPC UA Server die MPC-Horizontschrittweite einstellen (mpc = 5 z.B), dann Server starten: python CoSES_Server.py
2.	cmd cd zum Ordner der MEMAP-JAR, dann: java -jar MEMAP_CoSES.jar jetty 5 15 
3.	unter http://localhost:8013 wird der jetty Server gestartet
4.	CoSES-Server Adresse: opc.tcp://0.0.0.0:4850 , Config-File:  CoSESBuilding1Nodes.json
5.	Add Building, dann Submit Data
6.	MEMAP ist gestartet und simuliert alle 15 Sekunden mit den Daten vom OPC UA Server
7.	Unter opc.tcp://0.0.0.0:4850 liegen die daraus folgenden Setpoints
