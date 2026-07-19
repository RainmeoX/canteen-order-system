@echo off
chcp 65001 >nul
echo ==============================================
echo    智能食堂预订系统 - 一键启动脚本
echo ==============================================
echo.

:: 优先使用 python，找不到再用 py 启动器，最后用写死路径
set PYTHON_PATH=
where python >nul 2>&1 && set PYTHON_PATH=python
if not defined PYTHON_PATH where py >nul 2>&1 && set PYTHON_PATH=py
if not defined PYTHON_PATH if exist "C:\Users\LENOVO\python-sdk\python3.13.2\python.exe" set PYTHON_PATH=C:\Users\LENOVO\python-sdk\python3.13.2\python.exe

if not defined PYTHON_PATH (
    echo [错误] 未找到 Python，请先安装 Python 3.8+ 并加入 PATH
    pause
    exit /b 1
)

:: 检查项目目录
if not exist "server\app.py" (
    echo [错误] 项目文件不存在
    echo    请确保本脚本放在项目根目录下
    pause
    exit /b 1
)

echo [OK] 使用 Python: %PYTHON_PATH%
echo.

:: 安装依赖（首次运行）
echo [INFO] 检查并安装依赖...
"%PYTHON_PATH%" -m pip install flask flask-cors --quiet
if %errorlevel% equ 0 (
    echo [OK] 依赖安装成功
) else (
    echo [WARN] 依赖安装可能失败，请手动安装
)
echo.

:: 初始化数据库（带示例菜品）
echo [INFO] 初始化数据库...
"%PYTHON_PATH%" database\init_db.py
echo.

:: 启动服务器
echo [INFO] 启动Flask服务器...
start "" "%PYTHON_PATH%" "server\app.py"

:: 等待服务器启动
echo [INFO] 等待服务器启动...
timeout /t 3 /nobreak >nul

:: 打开浏览器
echo [INFO] 打开浏览器...
start "" http://localhost:5000
start "" http://localhost:5000/admin

echo.
echo ==============================================
echo    服务器已启动！
echo ==============================================
echo.
echo 用户端地址: http://localhost:5000
echo 管理端地址: http://localhost:5000/admin
echo.
echo 管理端默认管理员 ID: admin_ma
echo.
echo 按 Ctrl+C 停止服务器（或关闭命令窗口）
pause
