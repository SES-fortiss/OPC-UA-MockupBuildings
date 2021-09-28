1. Start Python Interface Servers for House 1 and House 2 using pycharm
1a. connect Holsten portal to server
2. Start UA Expert for Monitoring
3. Start VeriStand via VI using API
	3.1 choose the right targets
4. Start MEMAP-platform jar via command line
	4.1. cd C:\Users\Public\A_MEMAPinCoSES_Arbeitsordner\01_MEMAP_platform_servers\CoSES\01_Platform\CoSES-MEMAP-JAR
	4.2 java -jar MEMAP_CoSES.jar jetty <horizont steps> <time step length in seconds>
5. Start Data logging via API
6. Start Experiment in Python Interface Servers for House 1 and House 2
7. Go to the equipment and write down the gas meter counts.
8. Use postman to send .json file with configuration to the running MEMAP platform

...
experiment
...

9. Stop Data Logging via API
10. Undeploy via API
11. Stop MEMAP-platform
12. Stop Python Interface Servers
13. Close UA Expert
14. Go to the equipment and write down the gas meter counts.