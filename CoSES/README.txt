1. Start Python Interface Servers for House 1 and House 2 using pycharm
2. Start UA Expert for Monitoring
2. Start VeriStand via VI using API
3. Start MEMAP-platform jar via command line
	3.1. cd <working directory>
	3.2 java -jar MEMAP_CoSES.jar jetty <horizont steps> <time step length in seconds>
4. Start Data logging via API
5. Start Experiment in Python Interface Servers for House 1 and House 2
6. Use postman to send .json file with configuration to the running MEMAP platform

...
experiment
...

7. Stop Data Logging via API
8. Undeploy via API
9. Stop MEMAP-platform
10. Stop Python Interface Servers
11. Close UA Expert