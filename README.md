
# Visualize_Circuit — 電路繪製與 Netlist 匯出

Visualize_Circuit is a lightweight circuit drawing tool built with Python and Tkinter. It focuses on quick schematic drawing and exporting HSPICE-compatible netlists (.sp).\n
這是一個基於 Python + Tkinter 的輕量級電路繪製工具，專注於快速繪製電路圖並生成 HSPICE 相容的 Netlist（.sp）。

## 主要功能 / Main Features

- 輕量且跨平台（Windows / Linux / macOS）、匯出 HSPICE Netlist、常用元件（R/L/C/NMOS/PMOS）、快捷鍵與基礎編輯。
- Lightweight and cross-platform, exports HSPICE-compatible netlists (.sp), common components (R/L/C/NMOS/PMOS), keyboard shortcuts for fast editing.

## 快速開始 / Quick Start

### 使用 Conda（推薦） / Using Conda (recommended)

建議使用 `env.yaml` 或 `Makefile` 建立 Conda 環境後執行。
Use the provided `env.yaml` to create a Conda environment, then run the app.

```bash
# create environment from env.yaml
conda env create -f env.yaml -n circuit_cad

# activate
conda activate circuit_cad

# run
python main.py
```

或使用 Makefile：

```bash
make        # runs "setup" then "run" according to the Makefile
```

Windows: you can also run `run.bat` which automates environment creation and starts the app.

## 快捷鍵 / Shortcuts (summary)

- R (電阻), L (電感), C (電容), N (NMOS), P (PMOS), W (連線), Del (刪除), M (鏡像), O (旋轉), Esc (選擇), F1 (說明)
- R (Resistor), L (Inductor), C (Capacitor), N (NMOS), P (PMOS), W (Wire mode), Del (Delete), M (Mirror), O (Rotate), Esc (Select), F1 (Help)

## 專案結構 / Project Layout

- `main.py` - 程式入口 / app entry point
- `editor.py` - 編輯器與畫布事件處理 / editor and canvas logic
- `components.py` - 元件定義與繪製 / component definitions and drawing
- `circuit_utils.py` - 網表生成 / netlist generation utilities
- `env.yaml` - Conda environment file
- `run.bat` - Windows automation script

## Makefile

`Makefile` 提供 `setup`（建立 Conda 環境）與 `run`（啟動程式）目標。直接執行 `make` 會順序執行這兩個目標。

The `Makefile` has `setup` (creates Conda env) and `run` (starts the app). `make` runs both.

## Netlist 與輸出檔案 / Netlist and Outputs

- 工具會匯出 HSPICE 相容的 Netlist（常見副檔名 `.sp` 或 `.spice`）。另外可能會產生 JSON 儲存或導出檔案。
- The tool exports HSPICE-compatible netlists (commonly `.sp`); it may also produce JSON save/export files.

注意 / Note: the repository `.gitignore` currently ignores `*.sp` and `*.json` to avoid committing exported artifacts. If you want to keep exports under version control, remove those patterns from `.gitignore`.

