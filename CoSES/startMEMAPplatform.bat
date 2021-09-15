@echo off
cd %~dp0\01_Platform\CoSES-MEMAP-JAR
set /p MPChorizon= Enter Enter the number of steps in the MPC horizon: 
set /p PauseinSecs= Enter the duration of one time step in seconds (only simulation purposes):
echo There are %MPChorizon% steps in the MPC horizon.
echo Optimzation is performed every %PauseinSecs% seconds.
java -jar MEMAP_CoSES.jar jetty %MPChorizon% %PauseinSecs%
