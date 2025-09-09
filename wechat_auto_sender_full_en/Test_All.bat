@echo off
call 0_Test_Reset_DB.bat
call 1_Test_Seed_Demo.bat
call 2_Test_Print_State.bat
echo.
echo ==== 等待 15 秒让 demo 任务到期 ====
timeout /t 15 >nul
call 5_Test_Scheduler_Tick.bat
call 2_Test_Print_State.bat
echo.
echo 你也可以單獨測試：hooks 或 sender 的乾跑
echo - hooks: 4_Test_Hooks_Once.bat
echo - sender dry-run: 3_Test_Sender_DRY_RUN.bat  (需 DRY_RUN=True)
pause
