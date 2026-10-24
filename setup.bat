@echo off
REM ============================================================
REM PharmaFlow - one-click database build for XAMPP (Windows)
REM 1. Start MySQL in the XAMPP Control Panel first.
REM 2. Double-click this file (or run it from the VS Code terminal).
REM Default XAMPP: user root, empty password. If you set a password,
REM add  -p  after -u root  and type it when asked.
REM ============================================================
set MYSQL=C:\xampp\mysql\bin\mysql.exe
set SQLDIR=%~dp0sql

echo Rebuilding database...
"%MYSQL%" -u root < "%SQLDIR%\00_reset.sql"                 || goto :err
"%MYSQL%" -u root < "%SQLDIR%\01_schema.sql"                || goto :err
"%MYSQL%" -u root < "%SQLDIR%\02_triggers_procedures.sql"   || goto :err
"%MYSQL%" -u root < "%SQLDIR%\03_seed.sql"                  || goto :err
"%MYSQL%" -u root < "%SQLDIR%\03b_seed_extra.sql"            || goto :err
"%MYSQL%" -u root < "%SQLDIR%\05_roles_privileges.sql"      || goto :err
echo.
echo DONE. Database pharmacy_sales_and_inventory_db is ready.
pause
exit /b 0

:err
echo.
echo FAILED - check that MySQL is running in XAMPP and read the error above.
pause
exit /b 1
