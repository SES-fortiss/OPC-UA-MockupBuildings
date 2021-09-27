cd %~dp0\01_Platform
curl -X POST 10.162.231.203:8013/memap/message -H "Content-Type: text/plain" -d "@2HOUSES_COSES_wConn_local_NewSPs_disabled.json" -v