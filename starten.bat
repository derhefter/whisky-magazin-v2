@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  ================================================
echo   WHISKY MAGAZIN - Startmenue
echo  ================================================
echo.
echo   V1 (Classic)  ->  http://localhost:8080
echo   V2 (Notebook) ->  http://localhost:8082
echo.
echo  ================================================
echo.
echo  Starte interaktives Menue...
echo  (Tipp: Optionen 11-14 fuer Newsletter und WOTM)
echo.

call venv\Scripts\activate.bat
python main.py %*
pause
