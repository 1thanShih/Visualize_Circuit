import tkinter as tk
from tkinter import ttk  # 引入 ttk 用於下拉選單
from tkinter import simpledialog
from circuit_utils import snap, transform_coords

class Terminal:
    def __init__(self, name, x, y):
        self.name = name
        self.rel_x = x
        self.rel_y = y
        self.custom_net_name = ""

class Component:
    _counts = {}

    def __init__(self, canvas, x, y, prefix):
        self.canvas = canvas
        self.x = snap(x)
        self.y = snap(y)
        self.rotation = 0
        self.mirror = False
        self.id = id(self)
        self.tags = f"comp_{self.id}"
        
        if prefix not in Component._counts:
            Component._counts[prefix] = 0
        Component._counts[prefix] += 1
        self.name = f"{prefix}{Component._counts[prefix]}"
        
        self.value = "1k"
        self.shape_lines = []
        self.terminals = [] 
        self.hitbox_size = (40, 40)
        
        # 用於儲存電源的詳細參數 (一般元件用不到，但電源元件會用到)
        self.source_params = {} 

    def setup_terminals(self):
        pass

    def get_abs_terminals(self):
        abs_terms = []
        for term in self.terminals:
            pts = transform_coords([(term.rel_x, term.rel_y)], self.x, self.y, self.rotation, self.mirror)
            abs_terms.append((term, pts[0][0], pts[0][1]))
        return abs_terms

    def update_visuals(self):
        self.canvas.delete(self.tags)
        self.draw()

    def draw(self):
        # 1. Hitbox
        hw, hh = self.hitbox_size[0]/2, self.hitbox_size[1]/2
        self.canvas.create_rectangle(self.x - hw, self.y - hh, self.x + hw, self.y + hh, 
                                     fill="white", outline="", tags=self.tags)

        # 2. Shape
        for p1, p2 in self.shape_lines:
            t_points = transform_coords([p1, p2], self.x, self.y, self.rotation, self.mirror)
            (x1, y1), (x2, y2) = t_points
            self.canvas.create_line(x1, y1, x2, y2, tags=self.tags, width=2, fill="black")
        
        # 3. Terminals
        for term_obj, tx, ty in self.get_abs_terminals():
            r = 3
            self.canvas.create_oval(tx-r, ty-r, tx+r, ty+r, fill="red", outline="red", tags=self.tags)
            if term_obj.custom_net_name:
                self.canvas.create_text(tx, ty-10, text=term_obj.custom_net_name, fill="brown", font=("Arial", 6), tags=self.tags)

        # 4. Extra Drawing (給子類別擴充圖形，如 + - 號)
        self.draw_extra()

        self.draw_text()
        self.canvas.tag_raise(self.tags)

    def draw_extra(self):
        pass # 子類別實作

    def draw_text(self):
        self.canvas.create_text(self.x, self.y + 35, text=f"{self.name}\n{self.value}", tags=self.tags, font=("Arial", 8))

    def rotate(self):
        self.rotation = (self.rotation + 90) % 360
        self.update_visuals()

    def flip(self):
        self.mirror = not self.mirror
        self.update_visuals()

    def edit_properties(self):
        # 預設的一般屬性編輯
        labels = ["Name", "Value"]
        defaults = [self.name, self.value]
        for term in self.terminals:
            labels.append(f"Node ({term.name})")
            defaults.append(term.custom_net_name)
        self.open_property_dialog(labels, defaults, self.apply_properties)

    def apply_properties(self, values):
        if values[0]: self.name = values[0]
        if values[1]: self.value = values[1]
        for i, term in enumerate(self.terminals):
            if i + 2 < len(values):
                term.custom_net_name = values[i+2]
        self.update_visuals()

    def open_property_dialog(self, labels, defaults, callback):
        dialog = tk.Toplevel(self.canvas.winfo_toplevel())
        dialog.title("Edit Properties")
        entries = []
        for i, label_text in enumerate(labels):
            tk.Label(dialog, text=label_text).grid(row=i, column=0, padx=10, pady=5, sticky="e")
            entry = tk.Entry(dialog)
            entry.insert(0, str(defaults[i]))
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="w")
            entries.append(entry)
            
        def on_ok(event=None):
            result = [e.get() for e in entries]
            callback(result)
            dialog.destroy()
            
        btn = tk.Button(dialog, text="OK", command=on_ok, bg="lightblue", width=10)
        btn.grid(row=len(labels), column=0, columnspan=2, pady=20)
        dialog.bind('<Return>', on_ok)
        dialog.transient(self.canvas.winfo_toplevel())
        dialog.grab_set()
        self.canvas.wait_window(dialog)


# --- 特殊電源元件設定視窗邏輯 ---
class SourceMixin:
    """用於 VoltageSource 和 CurrentSource 的共用邏輯"""
    def init_params(self):
        # 預設參數
        self.source_type = "DC"  # DC, AC, PULSE, SIN
        self.params = {
            "DC": {"dc_val": "5"},
            "AC": {"mag": "1", "phase": "0"},
            "PULSE": {"v1": "0", "v2": "5", "td": "0", "tr": "1n", "tf": "1n", "pw": "10n", "per": "20n"},
            "SIN": {"vo": "0", "va": "1", "freq": "1k", "td": "0", "theta": "0"}
        }
        self.update_display_value()

    def update_display_value(self):
        # 更新顯示在圖上的文字
        if self.source_type == "DC":
            self.value = f"DC {self.params['DC']['dc_val']}"
        elif self.source_type == "AC":
            self.value = f"AC {self.params['AC']['mag']}"
        elif self.source_type == "PULSE":
            self.value = "PULSE"
        elif self.source_type == "SIN":
            self.value = "SIN"

    def edit_source_properties(self):
        """進階電源設定視窗"""
        dialog = tk.Toplevel(self.canvas.winfo_toplevel())
        dialog.title(f"Edit Source: {self.name}")
        
        # 1. 名字與端點設定 (上半部)
        tk.Label(dialog, text="Name:").grid(row=0, column=0, sticky="e")
        name_entry = tk.Entry(dialog)
        name_entry.insert(0, self.name)
        name_entry.grid(row=0, column=1)

        term_entries = []
        for i, term in enumerate(self.terminals):
            tk.Label(dialog, text=f"Node ({term.name}):").grid(row=1+i, column=0, sticky="e")
            e = tk.Entry(dialog)
            e.insert(0, term.custom_net_name)
            e.grid(row=1+i, column=1)
            term_entries.append(e)

        # 分隔線
        tk.Frame(dialog, height=2, bd=1, relief=tk.SUNKEN).grid(row=10, column=0, columnspan=2, sticky="ew", pady=10)

        # 2. 電源類型選擇 (Combobox)
        tk.Label(dialog, text="Source Function:").grid(row=11, column=0, sticky="e")
        type_var = tk.StringVar(value=self.source_type)
        type_combo = ttk.Combobox(dialog, textvariable=type_var, values=["DC", "AC", "PULSE", "SIN"], state="readonly")
        type_combo.grid(row=11, column=1)

        # 參數輸入區 (Frame)
        param_frame = tk.Frame(dialog)
        param_frame.grid(row=12, column=0, columnspan=2, pady=10)
        
        # 儲存輸入框的字典
        current_entries = {}

        def update_param_fields(event=None):
            # 清空舊欄位
            for widget in param_frame.winfo_children():
                widget.destroy()
            current_entries.clear()
            
            stype = type_var.get()
            params = self.params.get(stype, {})
            
            r = 0
            for key, val in params.items():
                tk.Label(param_frame, text=f"{key}:").grid(row=r, column=0, sticky="e")
                e = tk.Entry(param_frame)
                e.insert(0, val)
                e.grid(row=r, column=1, sticky="w")
                current_entries[key] = e
                r += 1
            
            # 若是 PULSE，顯示提示 (Triange wave 提示)
            if stype == "PULSE":
                tk.Label(param_frame, text="(Tip: For Triangle, set PW small, TR+TF=PER)", fg="gray").grid(row=r, column=0, columnspan=2)

        type_combo.bind("<<ComboboxSelected>>", update_param_fields)
        update_param_fields() # 初始化顯示

        def on_ok():
            # 1. 儲存名字與端點
            if name_entry.get(): self.name = name_entry.get()
            for i, term in enumerate(self.terminals):
                term.custom_net_name = term_entries[i].get()
            
            # 2. 儲存參數
            stype = type_var.get()
            self.source_type = stype
            for key, entry in current_entries.items():
                self.params[stype][key] = entry.get()
            
            self.update_display_value()
            self.update_visuals()
            dialog.destroy()

        tk.Button(dialog, text="OK", command=on_ok, bg="lightblue", width=10).grid(row=20, column=0, columnspan=2, pady=10)
        dialog.transient(self.canvas.winfo_toplevel())
        dialog.grab_set()
        self.canvas.wait_window(dialog)


# --- 具體元件定義 ---

class VoltageSource(Component, SourceMixin):
    def __init__(self, canvas, x, y):
        super().__init__(canvas, x, y, "V")
        self.hitbox_size = (40, 40)
        # 繪製圓形
        # 我們用 shape_lines 畫圓比較困難，所以在 draw_extra 畫
        self.shape_lines = [] 
        # 端點：上正下負
        self.setup_terminals()
        self.init_params() # 初始化電源參數
        self.draw()

    def setup_terminals(self):
        self.terminals = [Terminal("+", 0, -20), Terminal("-", 0, 20)]

    def draw_extra(self):
        # 畫圓
        cx, cy = self.x, self.y
        r = 15
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, tags=self.tags, width=2)
        # 畫線連接到端點
        self.canvas.create_line(cx, cy-r, cx, cy-20, tags=self.tags, width=2)
        self.canvas.create_line(cx, cy+r, cx, cy+20, tags=self.tags, width=2)
        # 畫 + - 號
        self.canvas.create_text(cx, cy-8, text="+", tags=self.tags, font=("Arial", 10, "bold"))
        self.canvas.create_text(cx, cy+8, text="-", tags=self.tags, font=("Arial", 10, "bold"))

    def edit_properties(self):
        self.edit_source_properties()

class CurrentSource(Component, SourceMixin):
    def __init__(self, canvas, x, y):
        super().__init__(canvas, x, y, "I")
        self.hitbox_size = (40, 40)
        self.shape_lines = []
        self.setup_terminals()
        self.init_params()
        self.draw()

    def setup_terminals(self):
        # 電流源：上進下出 (SPICE定義電流從 N1 流向 N2，我們定義 N1在上 N2在下)
        self.terminals = [Terminal("in", 0, -20), Terminal("out", 0, 20)]

    def draw_extra(self):
        cx, cy = self.x, self.y
        r = 15
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, tags=self.tags, width=2)
        self.canvas.create_line(cx, cy-r, cx, cy-20, tags=self.tags, width=2)
        self.canvas.create_line(cx, cy+r, cx, cy+20, tags=self.tags, width=2)
        
        # 畫箭頭 (向下)
        # 箭頭本體
        self.canvas.create_line(cx, cy-8, cx, cy+8, tags=self.tags, width=2)
        # 箭頭頭部
        self.canvas.create_line(cx, cy+8, cx-4, cy+4, tags=self.tags, width=2)
        self.canvas.create_line(cx, cy+8, cx+4, cy+4, tags=self.tags, width=2)

    def edit_properties(self):
        self.edit_source_properties()


# --- 其他元件 (保持不變) ---

class Pin(Component):
    def __init__(self, canvas, x, y):
        super().__init__(canvas, x, y, "PIN")
        self.shape_lines = [((-10, 0), (0, 0))]
        self.value = ""
        self.hitbox_size = (30, 30)
        self.setup_terminals()
        self.draw()
    def setup_terminals(self):
        self.terminals = [Terminal("pin", 0, 0)]
    def draw_text(self):
        self.canvas.create_text(self.x, self.y - 15, text=self.name, tags=self.tags, font=("Arial", 10, "bold"), fill="blue")
    def edit_properties(self):
        self.open_property_dialog(["Net Name"], [self.name], self.apply_pin_props)
    def apply_pin_props(self, values):
        if values[0]: self.name = values[0]
        self.update_visuals()

class Resistor(Component):
    def __init__(self, canvas, x, y):
        super().__init__(canvas, x, y, "R")
        self.shape_lines = [
            ((-30, 0), (-20, 0)), ((-20, 0), (-15, -10)), ((-15, -10), (-5, 10)),
            ((-5, 10), (5, -10)), ((5, -10), (15, 10)), ((15, 10), (20, 0)), ((20, 0), (30, 0))
        ]
        self.hitbox_size = (70, 30)
        self.setup_terminals()
        self.draw()
    def setup_terminals(self):
        self.terminals = [Terminal("n1", -30, 0), Terminal("n2", 30, 0)]

class Inductor(Component):
    def __init__(self, canvas, x, y):
        super().__init__(canvas, x, y, "L")
        self.shape_lines = [
            ((-30, 0), (-20, 0)), ((20, 0), (30, 0)),
            ((-20, 0), (-20, -10)), ((-20, -10), (-10, -10)), ((-10, -10), (-10, 0)),
            ((-10, 0), (-10, -10)), ((-10, -10), (0, -10)), ((0, -10), (0, 0)),
            ((0, 0), (0, -10)), ((0, -10), (10, -10)), ((10, -10), (10, 0)),
            ((10, 0), (10, -10)), ((10, -10), (20, -10)), ((20, -10), (20, 0))
        ]
        self.hitbox_size = (70, 30)
        self.setup_terminals()
        self.draw()
    def setup_terminals(self):
        self.terminals = [Terminal("n1", -30, 0), Terminal("n2", 30, 0)]

class Capacitor(Component):
    def __init__(self, canvas, x, y):
        super().__init__(canvas, x, y, "C")
        self.shape_lines = [
            ((-30, 0), (-5, 0)), ((5, 0), (30, 0)),
            ((-5, -15), (-5, 15)), ((5, -15), (5, 15))
        ]
        self.hitbox_size = (70, 40)
        self.setup_terminals()
        self.draw()
    def setup_terminals(self):
        self.terminals = [Terminal("n1", -30, 0), Terminal("n2", 30, 0)]

class CMOS(Component):
    def __init__(self, canvas, x, y, p_type=False):
        self.p_type = p_type
        prefix = "M_P" if p_type else "M_N"
        super().__init__(canvas, x, y, prefix)
        self.model = "pch" if p_type else "nch"
        self.w = "1u"
        self.l = "0.18u"
        self.hitbox_size = (60, 60)
        self.shape_lines = [
            ((-10, -15), (-10, 15)), ((0, -15), (0, 15)),
            ((0, -10), (20, -10)), ((20, -10), (20, -25)),
            ((0, 10), (20, 10)), ((20, 10), (20, 25)),
            ((0, 0), (20, 0))
        ]
        if self.p_type:
            self.shape_lines.append(((-30, 0), (-16, 0)))
            self.shape_lines.extend([((-16, 0), (-13, -3)), ((-13, -3), (-10, 0)),
                                     ((-10, 0), (-13, 3)), ((-13, 3), (-16, 0))])
            self.shape_lines.extend([((10, 0), (15, -5)), ((10, 0), (15, 5))])
        else:
            self.shape_lines.append(((-30, 0), (-10, 0)))
            self.shape_lines.extend([((10, 0), (5, -5)), ((10, 0), (5, 5))])
        self.setup_terminals()
        self.draw()
    def setup_terminals(self):
        self.terminals = [Terminal("D", 20, -25), Terminal("G", -30, 0), Terminal("S", 20, 25), Terminal("B", 20, 0)]
    def draw_text(self):
        info = f"{self.name}\n{self.model}\nW={self.w}\nL={self.l}"
        self.canvas.create_text(self.x, self.y + 40, text=info, tags=self.tags, font=("Arial", 7))
    def edit_properties(self):
        labels = ["Name", "Model", "Width (W)", "Length (L)"]
        defaults = [self.name, self.model, self.w, self.l]
        for term in self.terminals:
            labels.append(f"Node ({term.name})")
            defaults.append(term.custom_net_name)
        self.open_property_dialog(labels, defaults, self.apply_cmos_props)
    def apply_cmos_props(self, values):
        if values[0]: self.name = values[0]
        if values[1]: self.model = values[1]
        if values[2]: self.w = values[2]
        if values[3]: self.l = values[3]
        for i, term in enumerate(self.terminals):
            if i + 4 < len(values):
                term.custom_net_name = values[i+4]
        self.update_visuals()