
這是一個基於 Python Tkinter 開發的輕量級電路繪製工具，專注於快速繪製電路圖並生成 HSPICE Netlist。無需安裝龐大的 EDA 軟體，即可進行基礎的電路設計與網表導出。

## 主要功能 (Main Features)

*   **輕量級且跨平台**：基於 Python 標準庫 Tkinter，啟動迅速。
*   **HSPICE 支援**：可直接導出相容於 HSPICE 的 Netlist 檔案。
*   **常用元件支援**：內建電阻 (R)、電感 (L)、電容 (C)、NMOS、PMOS 等元件。
*   **便捷操作**：支援快捷鍵生成元件、旋轉、鏡像與連線。
*   **自動環境配置**：提供 Windows 批次檔自動建立 Conda 環境並修復常見的 Tcl/Tk 問題。

##  快速開始 (Quick Start)

### Windows 使用者 (推薦)

本專案包含一個自動化腳本，可自動處理環境依賴。

1.  找到資料夾中的 **`run.bat`** 檔案。
2.  直接雙擊執行。
    *   腳本會自動檢查是否已安裝 Conda 環境 `circuit_cad`。
    *   若無，將自動建立環境並安裝 Python 3.11 與 Tkinter。
    *   最後自動啟動程式。

### 手動安裝 (Manual Installation)

如果您熟悉命令列操作，也可以手動建立環境：

```bash
# 1. 建立 Conda 環境 (指定 python 3.11 和 tk 以避免 GUI 錯誤)
conda create -n circuit_cad python=3.11 tk -y

# 2. 啟用環境
conda activate circuit_cad

# 3. 執行程式
python main.py
```

## 快捷鍵列表 (Shortcuts)

為了提高繪圖效率，本工具高度依賴鍵盤快捷鍵：

| 按鍵 | 功能 | 說明 |
| :--- | :--- | :--- |
| **R** | 新增電阻 (Resistor) | |
| **L** | 新增電感 (Inductor) | |
| **C** | 新增電容 (Capacitor) | |
| **N** | 新增 NMOS | |
| **P** | 新增 PMOS | |
| **W** | 切換連線模式 (Wire) | 再次按下可退出 |
| **Del** | 切換刪除模式 (Delete) | 點擊元件以刪除 |
| **M** | 鏡像元件 (Mirror) | 水平翻轉選中的元件 |
| **O** | 旋轉元件 (Rotate) | 順時針旋轉選中的元件 |
| **Esc** | 選擇模式 (Select) | 回到預設游標模式 |
| **F1** | 顯示說明 (Help) | 查看幫助視窗 |

## 專案結構

*   `main.py`: 程式入口點，負責視窗初始化與快捷鍵綁定。
*   `editor.py`: 核心編輯器邏輯，處理畫布操作與事件。
*   `components.py`: 定義電路元件的屬性與繪製方法。
*   `circuit_utils.py`: 電路網表生成與輔助工具。
*   `env.yaml`: Conda 環境設定檔。
*   `run.bat`: Windows 自動啟動腳本。

## 系統需求

*   Anaconda 或 Miniconda
*   Python 3.11+
*   Tkinter (通常隨 Python 安裝，但在 Conda 中建議顯式安裝 `tk` 包)

