@echo off
REM ===============================================================
REM プロジェクト管理システム - Windows実行スクリプト
REM Version: 1.0.0
REM Created: 2025-08-11
REM Encoding: UTF-8
REM 
REM 機能:
REM - Python環境チェック・依存関係自動インストール
REM - GUI/CLIモード選択・エラー処理・ユーザーガイダンス
REM - 設定ファイル確認・データディレクトリ準備
REM ===============================================================

REM === 文字化け対策 ===
REM UTF-8コードページに変更（日本語文字化け防止）
chcp 65001 >nul 2>&1
if errorlevel 1 (
    REM UTF-8が使えない場合はSJISを試行
    chcp 932 >nul 2>&1
)

title プロジェクト管理システム v1.0.0
color 0F

echo.
echo ================================================
echo   プロジェクト管理システム v1.0.0
echo   エンタープライズレベル プロジェクト管理
echo ================================================
echo.

REM === 管理者権限チェック ===
net session >nul 2>&1
if %errorlevel% == 0 (
    echo [管理者権限] 検出 - 管理者モードで実行中
) else (
    echo [注意] 一般ユーザーモードで実行中
    echo        依存関係のインストールで権限エラーが発生する可能性があります
)
echo.

REM === Python環境チェック ===
echo [チェック] Python環境を確認しています...
python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Pythonがインストールされていません
    echo.
    echo 解決方法:
    echo 1. https://python.org からPython 3.7以上をダウンロード
    echo 2. インストール時に「Add Python to PATH」をチェック
    echo 3. インストール後、このスクリプトを再実行
    echo.
    echo 何かキーを押すとブラウザでPythonダウンロードページを開きます...
    pause >nul
    start https://python.org/downloads/
    echo.
    echo Pythonをインストール後、このファイルを再実行してください。
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [成功] Python %PYTHON_VERSION% を検出

REM Pythonバージョンチェック（3.7以上）
python -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [エラー] Python 3.7以上が必要です（現在: %PYTHON_VERSION%）
    echo         Python をアップデートしてください
    pause
    exit /b 1
)

echo [成功] Pythonバージョン要件を満たしています
echo.

REM === プロジェクトディレクトリチェック ===
echo [チェック] プロジェクト構成を確認しています...
if not exist "main.py" (
    echo [エラー] main.py が見つかりません
    echo          正しいプロジェクトディレクトリで実行してください
    echo.
    echo 確認項目:
    echo 1. ファイル一式が正しく展開されているか
    echo 2. main.py ファイルが同じフォルダにあるか
    echo 3. 正しいフォルダでこのスクリプトを実行しているか
    echo.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo [警告] requirements.txt が見つかりません
    echo         手動で依存関係をインストールします
    echo         pip install PyQt6 openpyxl xlsxwriter
    echo.
) else (
    echo [成功] プロジェクト構成を確認
)
echo.

REM === 依存関係チェック・インストール ===
echo [チェック] 依存関係を確認しています...
echo           初回実行時は数分かかる場合があります

REM PyQt6チェック
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo [インストール] PyQt6 が見つかりません - インストール中...
    echo                しばらくお待ちください（数分かかる場合があります）
    pip install "PyQt6>=6.4.0" --quiet
    if errorlevel 1 (
        echo [エラー] PyQt6 のインストールに失敗しました
        echo.
        echo 解決方法を試してください:
        echo 1. 管理者権限でこのスクリプトを実行
        echo 2. 手動インストール: pip install PyQt6
        echo 3. インターネット接続を確認
        echo.
        pause
        exit /b 1
    )
    echo [成功] PyQt6 インストール完了
) else (
    echo [成功] PyQt6 検出済み
)

REM openpyxlチェック
python -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo [インストール] openpyxl が見つかりません - インストール中...
    pip install "openpyxl>=3.0.9" --quiet
    if errorlevel 1 (
        echo [エラー] openpyxl のインストールに失敗しました
        echo          手動でインストールしてください: pip install openpyxl
        pause
        exit /b 1
    )
    echo [成功] openpyxl インストール完了
) else (
    echo [成功] openpyxl 検出済み
)

REM xlsxwriterチェック
python -c "import xlsxwriter" >nul 2>&1
if errorlevel 1 (
    echo [インストール] xlsxwriter が見つかりません - インストール中...
    pip install "xlsxwriter>=3.0.3" --quiet
    if errorlevel 1 (
        echo [エラー] xlsxwriter のインストールに失敗しました
        echo          手動でインストールしてください: pip install xlsxwriter
        pause
        exit /b 1
    )
    echo [成功] xlsxwriter インストール完了
) else (
    echo [成功] xlsxwriter 検出済み
)

echo.
echo [成功] 全ての依存関係が正常に確認されました
echo.

REM === データディレクトリ準備 ===
if not exist "data" (
    echo [初期化] データディレクトリを作成しています...
    mkdir data
    if errorlevel 1 (
        echo [エラー] データディレクトリの作成に失敗しました
        echo          書き込み権限を確認してください
        pause
        exit /b 1
    )
    
    mkdir data\logs
    if errorlevel 1 (
        echo [警告] ログディレクトリの作成に失敗しました
    )
    
    echo [成功] データディレクトリ作成完了
    echo         - data\ フォルダ（プロジェクトデータ保存用）
    echo         - data\logs\ フォルダ（ログファイル保存用）
) else (
    echo [確認] データディレクトリは既に存在します
)
echo.

REM === 起動モード選択 ===
echo ================================================
echo   起動モードを選択してください
echo ================================================
echo.
echo 1. GUIモード（推奨）
echo    - グラフィカルな操作画面
echo    - ガントチャート・通知管理
echo    - プロジェクト階層ツリー表示
echo    - マウス操作で直感的に使用可能
echo.
echo 2. CLIモード
echo    - コマンドライン操作画面
echo    - 自動化・スクリプト処理対応
echo    - 軽量動作・リモート操作可能
echo    - キーボードのみで操作
echo.
echo 3. データ整合性チェックのみ
echo    - システム起動せず、データ検証のみ実行
echo    - トラブル時の診断に使用
echo.
echo 4. 終了
echo.

:MODE_SELECT
set /p choice="選択してください (1-4): "

if "%choice%"=="1" goto GUI_MODE
if "%choice%"=="2" goto CLI_MODE
if "%choice%"=="3" goto CHECK_MODE
if "%choice%"=="4" goto EXIT

echo.
echo [エラー] 無効な選択です。1-4の数字を入力してください。
echo.
goto MODE_SELECT

:GUI_MODE
echo.
echo [起動] GUIモードでシステムを起動しています...
echo        ※ウィンドウが表示されない場合は、CLIモードをお試しください
echo        ※初回起動時は時間がかかる場合があります
echo.
python main.py --gui
goto END

:CLI_MODE
echo.
echo [起動] CLIモードでシステムを起動しています...
echo        ※'help' コマンドで使用方法を確認できます
echo        ※'exit' コマンドで終了します
echo        ※'sample-data' コマンドでサンプル作成できます
echo.
python main.py
goto END

:CHECK_MODE
echo.
echo [チェック] データ整合性を確認しています...
python main.py --check-only
if errorlevel 1 (
    echo.
    echo [エラー] データ整合性に問題があります
    echo          詳細については data\logs\error.log をご確認ください
    echo.
    echo 対処方法:
    echo 1. CLIモードで 'cleanup' コマンドを実行
    echo 2. バックアップからの復旧を検討
    echo 3. システム管理者にお問い合わせ
) else (
    echo.
    echo [成功] データ整合性に問題ありません
    echo         システムは正常に使用できます
)
echo.
pause
goto END

:EXIT
echo.
echo システムを終了します。
echo ご利用ありがとうございました。
goto END

:END
if errorlevel 1 (
    echo.
    echo ================================================
    echo [エラー] システム実行中にエラーが発生しました
    echo         終了コード: %errorlevel%
    echo ================================================
    echo.
    echo トラブルシューティング:
    echo 1. エラーログ確認
    echo    - data\logs\error.log ファイルを確認
    echo    - 最新のエラー内容をチェック
    echo.
    echo 2. 環境再確認
    echo    - Python バージョン: python --version
    echo    - 依存関係確認: pip list ^| findstr "PyQt6"
    echo.
    echo 3. 復旧手順
    echo    - 依存関係再インストール: pip install --force-reinstall PyQt6 openpyxl xlsxwriter
    echo    - 管理者権限での実行を試行
    echo    - ウイルス対策ソフトの一時無効化
    echo    - Windows再起動後に再実行
    echo.
    echo 4. データ問題の場合
    echo    - データ整合性チェック実行（モード3を選択）
    echo    - バックアップからの復旧検討
    echo.
    echo 5. 追加サポート
    echo    - README.md のトラブルシューティング章を参照
    echo    - docs\user_manual.md の詳細ガイドを確認
    echo.
    pause
) else (
    echo.
    echo システムが正常に終了しました。
)

echo.
echo ================================================
echo プロジェクト管理システムの実行を終了しました。
echo.
echo 次回からの起動:
echo - このファイル（run_project_manager.bat）をダブルクリック
echo - または、python main.py --gui でGUI起動
echo - または、python main.py でCLI起動
echo.
echo ご利用ありがとうございました。
echo ================================================
pause