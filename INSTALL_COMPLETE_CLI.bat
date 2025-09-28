@echo off
chcp 65001 >nul
echo ========================================================
echo AION Creator - Instalacion Completa CLI GoDaddy
echo ========================================================
echo.

echo [1/4] Verificando Python y dependencias...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python no encontrado. Instala Python 3.11+
    pause
    exit /b 1
)

python -c "import requests" 2>nul || (
    echo Instalando requests...
    pip install requests
)

echo ✅ Python y dependencias OK
echo.

echo [2/4] Configurando CLI tools...
echo.

echo Archivos disponibles:
echo   ✅ GODADDY_AUTO_SETUP.py - CLI completo como wrangler
echo   ✅ GODADDY_CLI_DEMO.py - Demo sin API keys
echo   ✅ aion_enterprise_config.json - Config enterprise
echo.

echo [3/4] Probando demo...
echo.
echo ¿Quieres ver el demo del CLI? (s/n)
set /p demo="Respuesta: "

if /i "%demo%"=="s" (
    echo.
    echo Ejecutando demo...
    python GODADDY_CLI_DEMO.py
)

echo.
echo [4/4] Configuracion de credenciales API...
echo.

echo Para usar el CLI real necesitas:
echo.
echo 1. Ve a: https://developer.godaddy.com
echo 2. Crea cuenta/login
echo 3. Ve a "API Keys"
echo 4. Crea nueva key (Production recomendado)
echo 5. Copia API Key y Secret
echo.

echo ¿Quieres configurar las credenciales ahora? (s/n)
set /p config="Respuesta: "

if /i "%config%"=="s" (
    echo.
    set /p api_key="Pega tu GoDaddy API Key: "
    set /p api_secret="Pega tu GoDaddy API Secret: "

    echo.
    echo Configurando variables de entorno...
    setx GODADDY_API_KEY "%api_key%"
    setx GODADDY_API_SECRET "%api_secret%"

    echo ✅ Credenciales configuradas
    echo.
    echo Probando conexion...
    python GODADDY_AUTO_SETUP.py info avermex.com
)

echo.
echo ========================================================
echo INSTALACION COMPLETA
echo ========================================================
echo.

echo 🛠️ CLI Instalado - Comandos disponibles:
echo.

echo   python GODADDY_AUTO_SETUP.py setup-creator
echo   python GODADDY_AUTO_SETUP.py setup-aion-complete
echo   python GODADDY_AUTO_SETUP.py cname DOMAIN SUB TARGET
echo   python GODADDY_AUTO_SETUP.py list DOMAIN
echo   python GODADDY_AUTO_SETUP.py backup DOMAIN
echo   python GODADDY_AUTO_SETUP.py monitor DOMAIN
echo.

echo 🎬 Demo disponible:
echo   python GODADDY_CLI_DEMO.py
echo.

echo 📋 Para configurar creator.avermex.com:
echo   python GODADDY_AUTO_SETUP.py setup-creator
echo.

echo 🏢 Para setup enterprise completo:
echo   python GODADDY_AUTO_SETUP.py setup-aion-complete
echo.

echo ========================================================
echo.

echo ¿Quieres configurar creator.avermex.com ahora? (s/n)
set /p setup="Respuesta: "

if /i "%setup%"=="s" (
    echo.
    echo Configurando creator.avermex.com...
    python GODADDY_AUTO_SETUP.py setup-creator
)

echo.
echo 🎉 ¡Instalacion completa!
echo.
echo URLs funcionando:
echo   Frontend: https://master.aion-creator.pages.dev
echo   API:      https://aion-creator-api.pako-molina.workers.dev
echo.

pause