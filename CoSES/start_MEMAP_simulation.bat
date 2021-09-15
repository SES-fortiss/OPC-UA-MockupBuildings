cd %~dp0\01_Platform
curl -X POST 172.24.208.1:8013/memap/message -H "Content-Type: text/plain" -d "@2HOUSES_COSES_wConn_local_NewSPs_disabled.json" -v