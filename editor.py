import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import json
import os

# 引入元件與工具
from components import Resistor, Inductor, Capacitor, CMOS, Pin, VoltageSource, CurrentSource
from circuit_utils import snap, dist, is_point_on_segment, get_closest_point_on_segment

class Wire:
    def __init__(self, canvas, p1, p2, scale=1.0, pan_x=0, pan_y=0):
        self.canvas = canvas
        self.start_p = p1 # 邏輯座標 (Logical Coordinate)
        self.end_p = p2   # 邏輯座標
        self.id = id(self)
        self.tags = f"wire_{self.id}"
        self.draw(scale, pan_x, pan_y)

    def draw(self, scale, pan_x, pan_y):
        self.canvas.delete(self.tags)
        # 將邏輯座標轉換為螢幕座標進行繪製
        sx1 = (self.start_p[0] * scale) + pan_x
        sy1 = (self.start_p[1] * scale) + pan_y
        sx2 = (self.end_p[0] * scale) + pan_x
        sy2 = (self.end_p[1] * scale) + pan_y
        
        lw = max(2, int(2 * scale))
        hit_w = max(10, int(10 * scale))
        
        self.canvas.create_line(sx1, sy1, sx2, sy2, fill="blue", width=lw, tags=self.tags)
        # 隱形加粗線 (Hitbox)
        self.canvas.create_line(sx1, sy1, sx2, sy2, width=hit_w, tags=(self.tags, "wire_hitbox"), stipple="gray25", fill="")

class SchematicEditor(tk.Frame):
    def __init__(self, parent, on_new_file_callback=None):
        super().__init__(parent)
        self.mode = "SELECT"
        self.components = []
        self.wires = []
        self.selected_item = None
        self.temp_wire_start = None
        self.drag_data = {}
        self.del_style = tk.StringVar(value="CLICK")
        
        # 接收來自 Main 的 callback，用於建立新分頁
        self.on_new_file_callback = on_new_file_callback
        
        # 視圖控制
        self.zoom_scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        # 全域設定
        self.global_settings = {
            "lib_path": "", "corner": "TT", "temp": "25",
            "def_n_model": "nch", "def_p_model": "pch", "options": "POST"
        }
        
        # 模擬指令設定
        self.sim_settings = {
            ".OP":   {"active": False, "params": "", "hint": "(Operating Point)"},
            ".TRAN": {"active": True,  "params": "1n 100n", "hint": "step stop"},
            ".DC":   {"active": False, "params": "VIN 0 3.3 0.1", "hint": "src start stop step"},
            ".AC":   {"active": False, "params": "DEC 10 1 10k", "hint": "type np start stop"},
            ".TF":   {"active": False, "params": "V(out) VIN", "hint": "out_var src"},
            ".NOISE":{"active": False, "params": "V(out) VIN 10", "hint": "out_var src interval"}
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        # 工具列
        toolbar = tk.Frame(self, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        def create_dropdown(parent, text, items):
            mb = tk.Menubutton(parent, text=text, relief=tk.RAISED, padx=5)
            menu = tk.Menu(mb, tearoff=0)
            mb.config(menu=menu)
            for label, cmd_code in items:
                if callable(cmd_code):
                    menu.add_command(label=label, command=cmd_code)
                else:
                    menu.add_command(label=label, command=lambda c=cmd_code: self.add_comp(c))
            mb.pack(side=tk.LEFT, padx=2)
            return mb

        # 1. File Menu
        file_items = []
        if self.on_new_file_callback:
            file_items.append(("New Schematic (Ctrl+T)", self.on_new_file_callback))
            
        file_items.extend([
            ("Open Schematic", self.load_schematic_dialog),
            ("Save Schematic", self.save_schematic_dialog),
            ("Save Netlist", self.save_netlist_dialog),
            ("Save Both", self.save_both_dialog)
        ])
        create_dropdown(toolbar, "File", file_items)
        
        tk.Label(toolbar, text="|", fg="gray").pack(side=tk.LEFT)

        # 2. Components Menus
        create_dropdown(toolbar, "Passives", [("Resistor", "R"), ("Inductor", "L"), ("Capacitor", "C")])
        create_dropdown(toolbar, "MOSFETs", [("NMOS", "NMOS"), ("PMOS", "PMOS")])
        create_dropdown(toolbar, "Sources", [("Voltage", "V"), ("Current", "I")])
        tk.Button(toolbar, text="PIN", bg="#ffcccc", command=lambda: self.add_comp("PIN")).pack(side=tk.LEFT, padx=5)
        
        tk.Label(toolbar, text="|", fg="gray").pack(side=tk.LEFT)
        self.mode_label = tk.Label(toolbar, text="Mode: SELECT", fg="blue", font=("Arial", 10, "bold"))
        self.mode_label.pack(side=tk.LEFT, padx=5)

        # 3. Function Buttons (Help Button is here)
        tk.Button(toolbar, text="Help(F1)", bg="lightblue", command=self.show_help).pack(side=tk.RIGHT, padx=5)
        tk.Button(toolbar, text="View Netlist", bg="yellow", command=self.export_netlist_window).pack(side=tk.RIGHT, padx=5)
        tk.Button(toolbar, text="Sim Settings", bg="#ccffcc", command=self.open_sim_settings).pack(side=tk.RIGHT, padx=2)
        tk.Button(toolbar, text="Config", bg="#e0e0e0", command=self.open_global_settings).pack(side=tk.RIGHT, padx=2)
        
        # 4. Delete Mode Controls
        del_frame = tk.Frame(toolbar)
        del_frame.pack(side=tk.RIGHT, padx=5)
        self.del_btn = tk.Button(del_frame, text="Del Mode", bg="#ffaaaa", command=self.toggle_delete_mode)
        self.del_btn.pack(side=tk.LEFT)
        tk.Radiobutton(del_frame, text="Click", variable=self.del_style, value="CLICK", indicatoron=0).pack(side=tk.LEFT)
        tk.Radiobutton(del_frame, text="Box", variable=self.del_style, value="BOX", indicatoron=0).pack(side=tk.LEFT)

        # Canvas setup
        self.canvas = tk.Canvas(self, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.focus_set()
        self.draw_grid()

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        
        # Zoom Bindings
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel) 
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)   
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)   
        
        # Pan Bindings
        self.canvas.bind("<ButtonPress-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.motion_pan)

    # --- Help Function (修復與優化) ---
    def show_help(self):
        help_text = (
            "【 Mouse Controls 】\n"
            "• Left Click: Select / Place / Connect\n"
            "• Right Drag: Pan View (平移視角)\n"
            "• Scroll Wheel: Zoom In/Out (縮放)\n"
            "• Double Click: Edit Component Properties\n\n"
            "【 Keyboard Shortcuts 】\n"
            "• W: Toggle Wire Mode (連線模式)\n"
            "• R: Rotate Selection (旋轉)\n"
            "• M: Mirror Selection (鏡像)\n"
            "• Delete: Toggle Delete Mode (刪除模式)\n"
            "• Ctrl+T: New Tab\n"
            "• Ctrl+W: Close Tab\n\n"
            "【 Features 】\n"
            "• Box Delete: Switch to 'Box' in Del Mode to area delete.\n"
            "• Branching: Click on existing wires to create branches.\n"
            "• Global Config: Set .LIB, .TEMP and default models."
        )
        messagebox.showinfo("Circuit CAD Help", help_text)

    # --- 繪圖、縮放、平移 ---
    def draw_grid(self):
        self.canvas.delete("grid")
        step = int(20 * self.zoom_scale)
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        # 簡單防呆
        if w < 10: w = 2000
        if h < 10: h = 2000
        
        # 計算網格起點偏移 (無限畫布錯覺)
        start_x = int(self.pan_x) % step
        start_y = int(self.pan_y) % step
        
        for i in range(start_x, w, step):
            self.canvas.create_line(i, 0, i, h, fill="#f0f0f0", tags="grid")
        for i in range(start_y, h, step):
            self.canvas.create_line(0, i, w, i, fill="#f0f0f0", tags="grid")
        self.canvas.tag_lower("grid")

    def redraw_all(self):
        self.draw_grid()
        for comp in self.components:
            comp.update_visuals(self.zoom_scale, self.pan_x, self.pan_y)
        for wire in self.wires:
            wire.draw(self.zoom_scale, self.pan_x, self.pan_y)

    def start_pan(self, event):
        self.drag_data["pan_start_x"] = event.x
        self.drag_data["pan_start_y"] = event.y

    def motion_pan(self, event):
        dx = event.x - self.drag_data["pan_start_x"]
        dy = event.y - self.drag_data["pan_start_y"]
        self.pan_x += dx
        self.pan_y += dy
        self.drag_data["pan_start_x"] = event.x
        self.drag_data["pan_start_y"] = event.y
        self.redraw_all()

    def on_mouse_wheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.zoom_scale *= 0.9
        else:
            self.zoom_scale *= 1.1
        
        if self.zoom_scale < 0.2: self.zoom_scale = 0.2
        if self.zoom_scale > 5.0: self.zoom_scale = 5.0
        self.redraw_all()

    def to_logical(self, screen_val, is_x=True):
        # Logical = (Screen - Pan) / Zoom
        pan = self.pan_x if is_x else self.pan_y
        return (screen_val - pan) / self.zoom_scale

    # --- 互動邏輯 ---
    def set_mode(self, mode):
        self.mode = mode
        self.mode_label.config(text=f"Mode: {mode}")
        if mode == "DELETE":
            self.mode_label.config(fg="red")
            self.canvas.config(cursor="X_cursor")
        elif mode == "WIRE":
            self.mode_label.config(fg="green")
            self.canvas.config(cursor="crosshair")
        else:
            self.mode_label.config(fg="blue")
            self.canvas.config(cursor="")
        self.temp_wire_start = None
        self.canvas.delete("preview_wire")
        self.canvas.delete("selection_box")
        self.deselect_all()
        self.canvas.focus_set()

    def add_comp(self, c_type):
        self.set_mode("SELECT")
        # 放置在視窗中心 (邏輯座標)
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        x = self.to_logical(w/2, True)
        y = self.to_logical(h/2, False)
        
        comp = None
        if c_type == "R": comp = Resistor(self.canvas, x, y)
        elif c_type == "L": comp = Inductor(self.canvas, x, y)
        elif c_type == "C": comp = Capacitor(self.canvas, x, y)
        elif c_type == "V": comp = VoltageSource(self.canvas, x, y)
        elif c_type == "I": comp = CurrentSource(self.canvas, x, y)
        elif c_type == "NMOS": 
            comp = CMOS(self.canvas, x, y, False)
            comp.model = self.global_settings["def_n_model"]
        elif c_type == "PMOS": 
            comp = CMOS(self.canvas, x, y, True)
            comp.model = self.global_settings["def_p_model"]
        elif c_type == "PIN": comp = Pin(self.canvas, x, y)
        
        if comp: 
            self.components.append(comp)
            comp.update_visuals(self.zoom_scale, self.pan_x, self.pan_y)
        self.canvas.focus_set()

    # --- 吸附邏輯 ---
    def get_best_snap_point(self, x, y, threshold=15):
        best_pt = None
        min_dist = float('inf')
        # 1. 元件腳位
        for comp in self.components:
            for term, tx, ty in comp.get_abs_terminals():
                d = dist((x, y), (tx, ty))
                if d < min_dist and d < threshold:
                    min_dist = d
                    best_pt = (tx, ty)
        # 2. 電線端點
        for wire in self.wires:
            for pt in [wire.start_p, wire.end_p]:
                d = dist((x, y), pt)
                if d < min_dist and d < threshold:
                    min_dist = d
                    best_pt = pt
        # 3. 電線中段 (Branching)
        if min_dist > 5: 
            for wire in self.wires:
                px, py = get_closest_point_on_segment(x, y, wire.start_p[0], wire.start_p[1], wire.end_p[0], wire.end_p[1])
                d = dist((x, y), (px, py))
                if d < min_dist and d < threshold:
                    min_dist = d
                    best_pt = (px, py)
        return best_pt 

    # --- 滑鼠事件 ---
    def on_click(self, event):
        self.canvas.focus_set()
        lx = self.to_logical(event.x, True)
        ly = self.to_logical(event.y, False)

        if self.mode == "DELETE":
            if self.del_style.get() == "CLICK":
                item_id = self.canvas.find_closest(event.x, event.y)
                tags = self.canvas.gettags(item_id)
                for comp in self.components:
                    if comp.tags in tags: self.delete_target(comp, "comp"); return
                for wire in self.wires:
                    if wire.tags in tags: self.delete_target(wire, "wire"); return
            elif self.del_style.get() == "BOX":
                self.drag_data["box_start_x"] = event.x # 框選使用螢幕座標
                self.drag_data["box_start_y"] = event.y
            return

        cx, cy = snap(lx), snap(ly)
        
        if self.mode == "WIRE":
            snap_pt = self.get_best_snap_point(lx, ly)
            target_pt = snap_pt if snap_pt else (cx, cy)
            
            if not self.temp_wire_start:
                self.temp_wire_start = target_pt
            else:
                new_wire = Wire(self.canvas, self.temp_wire_start, target_pt, self.zoom_scale, self.pan_x, self.pan_y)
                self.wires.append(new_wire)
                self.temp_wire_start = None 
                self.canvas.delete("preview_wire")

        elif self.mode == "SELECT":
            item_id = self.canvas.find_closest(event.x, event.y)
            tags = self.canvas.gettags(item_id)
            for comp in self.components:
                if comp.tags in tags:
                    self.select_item(comp, "comp")
                    self.drag_data = {
                        "x": event.x, "y": event.y,
                        "start_x": event.x, "start_y": event.y,
                        "comp_start_x": comp.x, "comp_start_y": comp.y,
                        "comp": comp
                    }
                    return
            for wire in self.wires:
                if wire.tags in tags: self.select_item(wire, "wire"); return
            self.deselect_all()

    def on_mouse_move(self, event):
        lx, ly = self.to_logical(event.x, True), self.to_logical(event.y, False)
        
        if self.mode == "WIRE" and self.temp_wire_start:
            # 預覽線繪製
            sx = (self.temp_wire_start[0] * self.zoom_scale) + self.pan_x
            sy = (self.temp_wire_start[1] * self.zoom_scale) + self.pan_y
            
            snap_pt = self.get_best_snap_point(lx, ly)
            
            dest_lx, dest_ly = snap_pt if snap_pt else (snap(lx), snap(ly))
            ex = (dest_lx * self.zoom_scale) + self.pan_x
            ey = (dest_ly * self.zoom_scale) + self.pan_y
            
            self.canvas.delete("preview_wire")
            self.canvas.create_line(sx, sy, ex, ey, fill="gray", dash=(4, 4), tags="preview_wire")

    def on_drag(self, event):
        # Box Delete Visual
        if self.mode == "DELETE" and self.del_style.get() == "BOX":
            start_x = self.drag_data.get("box_start_x")
            start_y = self.drag_data.get("box_start_y")
            if start_x is not None:
                self.canvas.delete("selection_box")
                self.canvas.create_rectangle(start_x, start_y, event.x, event.y, outline="red", dash=(4, 4), width=2, tags="selection_box")
            return

        # Comp Drag
        if self.mode == "SELECT" and self.selected_item and self.selected_item[1] == "comp":
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            comp = self.drag_data["comp"]
            self.canvas.move(comp.tags, dx, dy)
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

    def on_release(self, event):
        # Box Delete Execution
        if self.mode == "DELETE" and self.del_style.get() == "BOX":
            start_x = self.drag_data.get("box_start_x")
            start_y = self.drag_data.get("box_start_y")
            if start_x is not None:
                x1 = self.to_logical(min(start_x, event.x), True)
                x2 = self.to_logical(max(start_x, event.x), True)
                y1 = self.to_logical(min(start_y, event.y), False)
                y2 = self.to_logical(max(start_y, event.y), False)
                
                comps_to_delete = []
                wires_to_delete = []
                for comp in self.components:
                    if x1 <= comp.x <= x2 and y1 <= comp.y <= y2:
                        comps_to_delete.append(comp)
                for wire in self.wires:
                    if (x1 <= wire.start_p[0] <= x2 and y1 <= wire.start_p[1] <= y2) and \
                       (x1 <= wire.end_p[0] <= x2 and y1 <= wire.end_p[1] <= y2):
                        wires_to_delete.append(wire)
                for c in comps_to_delete: self.delete_target(c, "comp")
                for w in wires_to_delete: self.delete_target(w, "wire")
                self.canvas.delete("selection_box")
                self.drag_data["box_start_x"] = None
            return

        # Component Drop
        if self.mode == "SELECT" and self.selected_item and self.selected_item[1] == "comp":
            comp = self.selected_item[0]
            total_dx = (event.x - self.drag_data["start_x"]) / self.zoom_scale
            total_dy = (event.y - self.drag_data["start_y"]) / self.zoom_scale
            
            raw_target_x = self.drag_data["comp_start_x"] + total_dx
            raw_target_y = self.drag_data["comp_start_y"] + total_dy
            
            target_x = snap(raw_target_x)
            target_y = snap(raw_target_y)
            
            threshold = 20 
            snap_candidates = [] 
            
            orig_x, orig_y = comp.x, comp.y
            comp.x, comp.y = raw_target_x, raw_target_y
            my_terms = comp.get_abs_terminals()
            comp.x, comp.y = orig_x, orig_y

            for other in self.components:
                if other == comp: continue
                for o_term, ox, oy in other.get_abs_terminals():
                    for term, mx, my in my_terms:
                        d = dist((mx, my), (ox, oy))
                        if d < threshold:
                            snap_candidates.append((d, raw_target_x + (ox - mx), raw_target_y + (oy - my)))
            for wire in self.wires:
                for wx, wy in [wire.start_p, wire.end_p]:
                     for term, mx, my in my_terms:
                        d = dist((mx, my), (wx, wy))
                        if d < threshold:
                            snap_candidates.append((d, raw_target_x + (wx - mx), raw_target_y + (wy - my)))
            
            if snap_candidates:
                snap_candidates.sort(key=lambda x: x[0])
                target_x = snap_candidates[0][1]
                target_y = snap_candidates[0][2]
            
            comp.x = target_x
            comp.y = target_y
            comp.update_visuals(self.zoom_scale, self.pan_x, self.pan_y)

    # --- 通用功能 ---
    def on_double_click(self, event):
        if self.selected_item and self.selected_item[1] == "comp":
            self.selected_item[0].edit_properties()

    def select_item(self, item, item_type):
        self.deselect_all()
        self.selected_item = (item, item_type)
        if item_type == "comp":
            self.canvas.itemconfig(item.tags, fill="blue") 
        elif item_type == "wire":
            self.canvas.itemconfig(item.tags, fill="red")

    def deselect_all(self):
        if self.selected_item:
            item, i_type = self.selected_item
            if i_type == "comp":
                item.update_visuals(self.zoom_scale, self.pan_x, self.pan_y) 
            elif i_type == "wire":
                self.canvas.itemconfig(item.tags, fill="blue")
        self.selected_item = None

    def delete_target(self, item, i_type):
        if i_type == "comp":
            self.canvas.delete(item.tags)
            if item in self.components: self.components.remove(item)
        elif i_type == "wire":
            self.canvas.delete(item.tags)
            if item in self.wires: self.wires.remove(item)
        self.selected_item = None

    def rotate_selection(self):
        if self.selected_item and self.selected_item[1] == "comp": 
            self.selected_item[0].rotate()
            self.selected_item[0].update_visuals(self.zoom_scale, self.pan_x, self.pan_y)
    
    def mirror_selection(self):
        if self.selected_item and self.selected_item[1] == "comp": 
            self.selected_item[0].flip()
            self.selected_item[0].update_visuals(self.zoom_scale, self.pan_x, self.pan_y)

    def toggle_delete_mode(self):
        self.set_mode("SELECT" if self.mode == "DELETE" else "DELETE")

    def toggle_wire_mode(self):
        self.set_mode("SELECT" if self.mode == "WIRE" else "WIRE")

    # --- Settings Windows ---
    def open_global_settings(self):
        win = tk.Toplevel(self)
        win.title("Global Configuration")
        win.geometry("450x350")
        
        lb_frame = tk.LabelFrame(win, text="Library & Process", padx=10, pady=10)
        lb_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(lb_frame, text="Lib Path (.lib):").grid(row=0, column=0, sticky="e")
        path_var = tk.StringVar(value=self.global_settings["lib_path"])
        tk.Entry(lb_frame, textvariable=path_var, width=30).grid(row=0, column=1, padx=5)
        def browse_lib():
            filename = filedialog.askopenfilename(filetypes=[("Lib Files", "*.lib *.l"), ("All Files", "*.*")])
            if filename: path_var.set(filename)
        tk.Button(lb_frame, text="Browse", command=browse_lib).grid(row=0, column=2)
        tk.Label(lb_frame, text="Corner (e.g. TT):").grid(row=1, column=0, sticky="e")
        corn_var = tk.StringVar(value=self.global_settings["corner"])
        tk.Entry(lb_frame, textvariable=corn_var, width=10).grid(row=1, column=1, sticky="w", padx=5)

        env_frame = tk.LabelFrame(win, text="Environment", padx=10, pady=10)
        env_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(env_frame, text="Temperature (.TEMP):").grid(row=0, column=0, sticky="e")
        temp_var = tk.StringVar(value=self.global_settings["temp"])
        tk.Entry(env_frame, textvariable=temp_var, width=10).grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(env_frame, text="Options (.OPTION):").grid(row=1, column=0, sticky="e")
        opt_var = tk.StringVar(value=self.global_settings["options"])
        tk.Entry(env_frame, textvariable=opt_var, width=20).grid(row=1, column=1, sticky="w", padx=5)

        mod_frame = tk.LabelFrame(win, text="Default Component Models", padx=10, pady=10)
        mod_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(mod_frame, text="Default NMOS Model:").grid(row=0, column=0, sticky="e")
        nmod_var = tk.StringVar(value=self.global_settings["def_n_model"])
        tk.Entry(mod_frame, textvariable=nmod_var).grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(mod_frame, text="Default PMOS Model:").grid(row=1, column=0, sticky="e")
        pmod_var = tk.StringVar(value=self.global_settings["def_p_model"])
        tk.Entry(mod_frame, textvariable=pmod_var).grid(row=1, column=1, sticky="w", padx=5)

        def on_save():
            self.global_settings["lib_path"] = path_var.get()
            self.global_settings["corner"] = corn_var.get()
            self.global_settings["temp"] = temp_var.get()
            self.global_settings["options"] = opt_var.get()
            self.global_settings["def_n_model"] = nmod_var.get()
            self.global_settings["def_p_model"] = pmod_var.get()
            win.destroy()
        tk.Button(win, text="Save Settings", command=on_save, bg="lightgreen", width=15).pack(pady=10)
        win.transient(self)
        win.grab_set()
        self.wait_window(win)

    def open_sim_settings(self):
        win = tk.Toplevel(self)
        win.title("HSPICE Analysis Setup")
        win.geometry("500x350")
        vars_store = {}
        tk.Label(win, text="Enable", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
        tk.Label(win, text="Command", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        tk.Label(win, text="Parameters", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        row = 1
        order = [".TRAN", ".DC", ".AC", ".OP", ".TF", ".NOISE"]
        for cmd in order:
            settings = self.sim_settings[cmd]
            var_active = tk.BooleanVar(value=settings["active"])
            chk = tk.Checkbutton(win, variable=var_active)
            chk.grid(row=row, column=0)
            tk.Label(win, text=cmd, fg="blue").grid(row=row, column=1, sticky="w")
            var_params = tk.StringVar(value=settings["params"])
            entry = tk.Entry(win, textvariable=var_params, width=30)
            entry.grid(row=row, column=2, padx=5, sticky="w")
            tk.Label(win, text=settings["hint"], fg="gray", font=("Arial", 8)).grid(row=row, column=3, sticky="w")
            vars_store[cmd] = (var_active, var_params)
            row += 1
        def on_save():
            for cmd, (v_act, v_param) in vars_store.items():
                self.sim_settings[cmd]["active"] = v_act.get()
                self.sim_settings[cmd]["params"] = v_param.get()
            win.destroy()
        tk.Button(win, text="Save & Close", command=on_save, bg="lightgreen", width=15).grid(row=row+1, column=0, columnspan=4, pady=15)
        win.transient(self)
        win.grab_set()
        self.wait_window(win)

    # --- Netlist Generation Logic ---
    def solve_connectivity(self):
        adj_list = {} 
        def add_edge(p1, p2):
            s1 = f"{p1[0]},{p1[1]}"
            s2 = f"{p2[0]},{p2[1]}"
            if s1 not in adj_list: adj_list[s1] = []
            if s2 not in adj_list: adj_list[s2] = []
            adj_list[s1].append(s2)
            adj_list[s2].append(s1)

        # 1. Wire-Wire
        for wire in self.wires:
            add_edge(wire.start_p, wire.end_p)
        for w1 in self.wires:
            for w2 in self.wires:
                if w1 == w2: continue
                # Check if endpoints lie on other segments
                if is_point_on_segment(w1.start_p[0], w1.start_p[1], w2.start_p[0], w2.start_p[1], w2.end_p[0], w2.end_p[1]):
                    add_edge(w1.start_p, w2.start_p)
                if is_point_on_segment(w1.end_p[0], w1.end_p[1], w2.start_p[0], w2.start_p[1], w2.end_p[0], w2.end_p[1]):
                    add_edge(w1.end_p, w2.start_p)

        # 2. Terminals
        all_terminals = [] 
        for comp in self.components:
            for term, tx, ty in comp.get_abs_terminals():
                all_terminals.append((comp, term, tx, ty))
                for wire in self.wires:
                    if is_point_on_segment(tx, ty, wire.start_p[0], wire.start_p[1], wire.end_p[0], wire.end_p[1]):
                        add_edge((tx, ty), wire.start_p)

        # 3. Short
        connection_tolerance = 15.0 
        for i in range(len(all_terminals)):
            for j in range(i + 1, len(all_terminals)):
                t1 = all_terminals[i]
                t2 = all_terminals[j]
                if dist((t1[2], t1[3]), (t2[2], t2[3])) < connection_tolerance:
                    add_edge((t1[2], t1[3]), (t2[2], t2[3]))

        # 4. BFS
        visited = set()
        node_map = {} 
        net_counter = 1
        for comp, term, tx, ty in all_terminals:
            pt_key = f"{tx},{ty}"
            if pt_key not in visited:
                group_pts = []
                queue = [pt_key]
                visited.add(pt_key)
                group_pts.append(pt_key)
                while queue:
                    curr = queue.pop(0)
                    if curr in adj_list:
                        for neighbor in adj_list[curr]:
                            if neighbor not in visited:
                                visited.add(neighbor)
                                group_pts.append(neighbor)
                                queue.append(neighbor)
                final_name = None
                pin_names = []
                custom_names = []
                for c, t, ctx, cty in all_terminals:
                    c_key = f"{ctx},{cty}"
                    if c_key in group_pts:
                        if isinstance(c, Pin):
                            pin_names.append(c.name)
                        elif t.custom_net_name.strip() != "":
                            custom_names.append(t.custom_net_name)
                if pin_names: final_name = pin_names[0]
                elif custom_names: final_name = custom_names[0]
                else:
                    final_name = f"N_{net_counter}"
                    net_counter += 1
                for pt in group_pts:
                    node_map[pt] = final_name
        return node_map

    def generate_netlist_text(self):
        node_map = self.solve_connectivity()
        lines = ["* Generated by Python Circuit CAD"]
        
        if self.global_settings["options"]: lines.append(f".OPTIONS {self.global_settings['options']}")
        if self.global_settings["temp"]: lines.append(f".TEMP {self.global_settings['temp']}")
        if self.global_settings["lib_path"]:
            lines.append(".PROTECT")
            lines.append(f".LIB '{self.global_settings['lib_path']}' {self.global_settings['corner']}")
            lines.append(".UNPROTECT")
        lines.append("")

        for comp in self.components:
            if isinstance(comp, Pin): continue 
            abs_terms = comp.get_abs_terminals()
            node_names = []
            for term, tx, ty in abs_terms:
                key = f"{tx},{ty}"
                if key in node_map: node_names.append(node_map[key])
                else: node_names.append(f"NC_{comp.name}_{term.name}")
            
            line = ""
            if isinstance(comp, CMOS):
                line = f"{comp.name} {' '.join(node_names)} {comp.model} W={comp.w} L={comp.l}"
            elif isinstance(comp, (VoltageSource, CurrentSource)):
                stype = comp.source_type
                p = comp.params.get(stype, {})
                base_line = f"{comp.name} {' '.join(node_names)}"
                if stype == "DC": line = f"{base_line} DC {p.get('dc_val', '0')}"
                elif stype == "AC": line = f"{base_line} AC {p.get('mag', '1')} {p.get('phase', '0')}"
                elif stype == "PULSE": line = f"{base_line} PULSE({p.get('v1')} {p.get('v2')} {p.get('td')} {p.get('tr')} {p.get('tf')} {p.get('pw')} {p.get('per')})"
                elif stype == "SIN": line = f"{base_line} SIN({p.get('vo')} {p.get('va')} {p.get('freq')} {p.get('td')} {p.get('theta')})"
                else: line = f"{base_line} DC 0"
            else:
                line = f"{comp.name} {' '.join(node_names)} {comp.value}"
            lines.append(line)
        
        lines.append("\n* --- Simulation Settings ---")
        for cmd, settings in self.sim_settings.items():
            if settings["active"]:
                lines.append(f"{cmd} {settings['params']}")
        lines.append(".END")
        return "\n".join(lines)

    # --- File Operations ---
    def get_schematic_data(self):
        data = {"global_settings": self.global_settings, "sim_settings": self.sim_settings, "components": [], "wires": []}
        for comp in self.components:
            item = {
                "type": type(comp).__name__, "x": comp.x, "y": comp.y, 
                "rotation": comp.rotation, "mirror": comp.mirror, 
                "name": comp.name, "value": comp.value, 
                "terminals": [t.custom_net_name for t in comp.terminals]
            }
            if isinstance(comp, CMOS): item.update({"model": comp.model, "w": comp.w, "l": comp.l, "p_type": comp.p_type})
            elif isinstance(comp, (VoltageSource, CurrentSource)): item.update({"source_type": comp.source_type, "params": comp.params})
            data["components"].append(item)
        for wire in self.wires: data["wires"].append({"start": wire.start_p, "end": wire.end_p})
        return data

    def load_schematic_data(self, data):
        self.canvas.delete("all")
        self.components = []
        self.wires = []
        if "global_settings" in data: self.global_settings = data["global_settings"]
        if "sim_settings" in data: self.sim_settings = data["sim_settings"]
        
        class_map = {
            "Resistor": Resistor, "Inductor": Inductor, "Capacitor": Capacitor,
            "CMOS": CMOS, "Pin": Pin, 
            "VoltageSource": VoltageSource, "CurrentSource": CurrentSource
        }
        for item in data["components"]:
            c_type = item["type"]
            if c_type not in class_map: continue
            cls = class_map[c_type]
            if c_type == "CMOS":
                comp = cls(self.canvas, item["x"], item["y"], item.get("p_type", False))
                comp.model = item.get("model", "nch")
                comp.w = item.get("w", "1u")
                comp.l = item.get("l", "0.18u")
            else:
                comp = cls(self.canvas, item["x"], item["y"])
            
            comp.name = item["name"]
            comp.value = item["value"]
            comp.rotation = item.get("rotation", 0)
            comp.mirror = item.get("mirror", False)
            term_names = item.get("terminals", [])
            for i, t_name in enumerate(term_names):
                if i < len(comp.terminals): comp.terminals[i].custom_net_name = t_name
            if isinstance(comp, (VoltageSource, CurrentSource)):
                comp.source_type = item.get("source_type", "DC")
                comp.params = item.get("params", {})
                comp.update_display_value()
            
            self.components.append(comp)
            comp.update_visuals(self.zoom_scale, self.pan_x, self.pan_y)

        for w_data in data["wires"]:
            start = tuple(w_data["start"])
            end = tuple(w_data["end"])
            wire = Wire(self.canvas, start, end, self.zoom_scale, self.pan_x, self.pan_y)
            self.wires.append(wire)
        self.draw_grid()

    def save_schematic_dialog(self):
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if filename:
            with open(filename, "w") as f: json.dump(self.get_schematic_data(), f, indent=4)
            messagebox.showinfo("Success", "Saved!")

    def load_schematic_dialog(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if filename:
            with open(filename, "r") as f: self.load_schematic_data(json.load(f))

    def save_netlist_dialog(self):
        filename = filedialog.asksaveasfilename(defaultextension=".sp", filetypes=[("SPICE", "*.sp")])
        if filename:
            with open(filename, "w") as f: f.write(self.generate_netlist_text())
            messagebox.showinfo("Success", "Saved!")

    def save_both_dialog(self):
        base = filedialog.asksaveasfilename(title="Save Both")
        if base:
            if base.endswith(".json"): base = base[:-5]
            with open(base+".json", "w") as f: json.dump(self.get_schematic_data(), f, indent=4)
            with open(base+".sp", "w") as f: f.write(self.generate_netlist_text())
            messagebox.showinfo("Success", "Saved Both!")

    def export_netlist_window(self):
        content = self.generate_netlist_text()
        win = tk.Toplevel(self); t = tk.Text(win); t.pack(); t.insert(tk.END, content)

    def show_help(self):
        help_text = (
            "【 Mouse Controls 】\n"
            "Left Click: Select / Place / Connect\n"
            "Right Drag: Pan View \n"
            "Scroll Wheel: Zoom In/Out \n"
            "Double Click: Edit Component Properties \n \n"
            "Keyboard Shortcuts 】 \n"
            "W: Toggle Wire Mode \n"
            "R: Rotate Selection \n"
            "M: Mirror Selection \n"
            "Delete: Toggle Delete Mode \n"
            "Ctrl+T: New Tab\n"
            "Ctrl+W: Close Tab\n\n"
            "【 Features 】\n"
            "Box Delete: Switch to 'Box' in Del Mode to area delete.\n"
            "Branching: Click on existing wires to create branches.\n"
            "Global Config: Set .LIB, .TEMP and default models."
        )
        messagebox.showinfo("Circuit CAD Help", help_text)