@echo off
echo ===================================================
echo TurniApp Build Script (Nuitka)
echo ===================================================
echo Installing requirements...
python.exe -m pip install --upgrade pip
pip install -r requirements.txt nuitka ordered-set

echo.
echo Running Nuitka Compiler...
python -m nuitka --standalone --onefile --windows-console-mode=disable --enable-plugin=pyside6 --mingw64 --windows-icon-from-ico=icon.ico main.py

echo.
echo Build completed. Standalone folder is located under 'build_nuitka/main.dist/'
pause
