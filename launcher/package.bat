:: filepath: /Users/user/Documents/OP_2/messenger-p2p/launcher/package.bat
@echo off
echo Packaging P2P Messenger for Windows...

:: Встановлюємо необхідні пакети
pip install pyinstaller pillow

:: Визначаємо директорії
set "LAUNCHER_DIR=%~dp0"
set "PROJECT_DIR=%LAUNCHER_DIR%.."
set "TEMP_DIR=%LAUNCHER_DIR%temp_build"

:: Створюємо тимчасову директорію
mkdir "%TEMP_DIR%" 2>nul
mkdir "%TEMP_DIR%\client" 2>nul
mkdir "%TEMP_DIR%\server" 2>nul

:: Копіюємо необхідні файли проекту
echo Copying project files...
xcopy /E /I "%PROJECT_DIR%\client" "%TEMP_DIR%\client"
xcopy /E /I "%PROJECT_DIR%\server" "%TEMP_DIR%\server"

:: Копіюємо launcher в тимчасову директорію
copy "%LAUNCHER_DIR%messenger_launcher.py" "%TEMP_DIR%\"

:: Переходимо в тимчасову директорію для створення пакету
cd "%TEMP_DIR%"

:: Створюємо виконуваний файл
echo Creating executable...
pyinstaller --onefile --icon="%LAUNCHER_DIR%icon.ico" --name=P2P_Messenger messenger_launcher.py

:: Копіюємо проектні файли в директорію dist
echo Preparing distribution...
xcopy /E /I client dist\client
xcopy /E /I server dist\server
copy "%PROJECT_DIR%\README.md" dist\ 2>nul

:: Створюємо ZIP-архів
cd dist
echo Creating ZIP archive...
powershell Compress-Archive -Path * -DestinationPath ..\P2P_Messenger_Windows.zip -Force

:: Переміщуємо архів у директорію завантажень
mkdir "%PROJECT_DIR%\website\downloads" 2>nul
move ..\P2P_Messenger_Windows.zip "%PROJECT_DIR%\website\downloads\"

:: Очищення тимчасової директорії
cd "%LAUNCHER_DIR%"
rmdir /S /Q "%TEMP_DIR%"

echo Packaging completed! The archive is available at website/downloads/P2P_Messenger_Windows.zip
pause