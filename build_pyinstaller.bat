@echo off
echo ===================================================
echo TurniApp Build Script (PyInstaller)
echo ===================================================
echo Installing requirements...
python.exe -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Running PyInstaller...
pyinstaller --noconfirm --onedir --windowed --name="TurniApp" main.py

echo.
echo Build completed. Executable folder can be found under 'dist/TurniApp/'
pause
