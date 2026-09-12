@echo off
title Despliegue saas_small (Docker)
chcp 65001 >nul

echo ========================================
echo  Gestión Comercial - Despliegue Docker
echo ========================================
echo.

:: Verificar Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker no está instalado o no está en el PATH.
    echo         Ve a https://www.docker.com/products/docker-desktop e instálalo.
    pause
    exit /b 1
)

:: Verificar que Docker está corriendo
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker no está corriendo. Abre Docker Desktop e inténtalo de nuevo.
    pause
    exit /b 1
)

:: Verificar archivos
if not exist "docker-compose.yml" (
    echo [ERROR] No se encuentra docker-compose.yml en el directorio actual.
    echo         Ejecuta este script desde la raíz del proyecto saas_small.
    pause
    exit /b 1
)

echo [1/6] Deteniendo contenedores anteriores (si existen)...
docker compose down 2>nul

echo [2/6] Construyendo imágenes desde cero...
docker compose build --no-cache
if %errorlevel% neq 0 (
    echo [ERROR] Falló la construcción de imágenes. Revisa los logs arriba.
    pause
    exit /b 1
)

echo [3/6] Iniciando servicios...
docker compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Falló al iniciar los servicios.
    pause
    exit /b 1
)

echo [4/6] Esperando a que el backend esté listo...
:wait_loop
timeout /t 3 /nobreak >nul
docker compose exec backend curl -sf http://localhost:8000/api/health >nul 2>&1
if %errorlevel% neq 0 (
    echo        Esperando...
    goto wait_loop
)
echo        Backend listo.

echo [5/6] Sembrando datos de ejemplo...
docker compose exec backend python scripts/seed_demo_data.py
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] El seed de datos de ejemplo falló. Puedes ejecutarlo manualmente después.
)

echo [6/6] Abriendo navegador...
start http://localhost:3000

echo.
echo ========================================
echo  ¡Despliegue completado con éxito!
echo ========================================
echo.
echo  Frontend:        http://localhost:3000
echo  API:             http://localhost:8000
echo  Documentación:   http://localhost:8000/api/docs
echo.
echo  Usuario admin:   admin@negocio.com / admin123
echo  Usuario vendedor: vendedor1@negocio.com / vendedor123
echo.
echo  Para ver logs en tiempo real:
echo    docker compose logs -f
echo.
pause
