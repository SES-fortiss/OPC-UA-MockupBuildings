# Installation

1) Extract `timescaledb` from the zip
2) Stop any running PostgreSQL processes
3) Run `setup.exe` inside of the extracted folder
4) A `cmd.exe` window will open and if successful will end with:
"TimescaleDB installation completed successfully.
Press ENTER/Return key to close..."
5) Restart PostgreSQL
6) Run `ALTER EXTENSION timescaledb UPDATE;` in each database that needs to be updated