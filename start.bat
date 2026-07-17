@echo off
chcp 65001 >nul
echo ==============================================
echo    智能食堂预订系统 - 一键启动脚本
echo ==============================================
echo.

:: 设置Python路径
set PYTHON_PATH=C:\Users\LENOVO\python-sdk\python3.13.2\python.exe

:: 检查Python是否存在
if not exist "%PYTHON_PATH%" (
    echo [错误] Python路径不存在
    echo    %PYTHON_PATH%
    echo.
    echo 请检查Python安装路径并修改本脚本中的 PYTHON_PATH 变量
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

echo [OK] 环境检查通过
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
echo 按 Ctrl+C 停止服务器（或关闭命令窗口）
pause