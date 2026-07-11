chcp 65001 >nul

python ue4_localization_toolkit.py import --dir ./Txts_ready --tool "C:/Users/Boking Bow/Exe/PACKCRACK/UE4localizationsTool/UE4localizationsTool.exe" --project-dir ./gohellgo --output ./PatchOutput

:: 把所有文件移入 gohellgo 子目录（PAK 需要此路径结构）
if not exist ".\PatchOutput\gohellgo" mkdir ".\PatchOutput\gohellgo"
for /f "delims=" %%i in ('dir /b /a ".\PatchOutput"') do (
    if not "%%i"=="gohellgo" (
        move ".\PatchOutput\%%i" ".\PatchOutput\gohellgo\"
    )
)

python ./list.py

del "C:\Users\Boking Bow\Game\ゴーヘルゴー業 つきおとしてゴー_ver.1.06\gohellgo\Content\Paks\ChineseTest_1_P.pak"
"E:\AAA\Epic Games\UE_4.27\Engine\Binaries\Win64\UnrealPak.exe" "C:\Users\Boking Bow\Game\ゴーヘルゴー業 つきおとしてゴー_ver.1.06\gohellgo\Content\Paks\ChineseTest_1_P.pak" -Create="F:\Reason\Origin\GO HELL GO GO 素材\FileList.txt" -compress