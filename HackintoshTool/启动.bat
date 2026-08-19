@echo off
chcp 65001 >nul
title 黑苹果一键辅助工具
echo 正在启动黑苹果一键辅助工具...

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 使用你的 Python 完整路径启动
"C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe" main.py

:: 如果上面的路径不对，可以改为以下方式（自动寻找 python）：
:: python main.py
:: 如果提示找不到 python，请修改为你的实际 python.exe 路径

pause