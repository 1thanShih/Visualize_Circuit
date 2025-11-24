import tkinter as tk
from tkinter import messagebox
from components import Resistor, Inductor, Capacitor, CMOS, Pin, VoltageSource, CurrentSource
from circuit_utils import snap, dist, is_point_on_segment, get_closest_point_on_segment

class Wire:
    def __init__(self, canvas, p1, p2):
        self.canvas = canvas
        self.start_p = p1
        self.end_p = p2
        self.id = id(self)
        self.tags = f"wire_{self.id}"
        self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="blue", width=2, tags=self.tags)
        self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], width=10, tags=(self.tags, "wire_hitbox"), stipple="gray25", fill="") 

class CircuitEditor:
    def __init__(self, root):
        self.root = root
        self.mode = "SELECT"
        self.components = []
        self.wires = []
        self.selected_item = None
        self.temp_wire_start = None
        self.drag_data = {}
        self.del_style = tk.StringVar(value="CLICK") 
        
        # --- [新增] 模擬參數預設值 ---
        # 格式: Key: { 'active': Boolean, 'params': String, 'hint': String }
        self.sim_settings = {
            ".OP":   {"active": False, "params": "", "hint": "(Operating Point - No params)"},
            ".TRAN": {"active": True,  "params": "1n 100n", "hint": "step stop [start]"},
            ".DC":   {"active": False, "params": "VIN 0 3.3 0.1", "hint": "src start stop step"},
            ".AC":   {"active": False, "params": "DEC 10 1 10k", "hint": "type np start stop"},
            ".TF":   {"active": False, "params": "V(out) VIN", "hint": "out_var src"},
            ".NOISE":{"active": False, "params": "V(out) VIN 10", "hint": "out_var src interval"}
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # --- 下拉選單區 ---
        def create_dropdown(parent, text, items):
            mb = tk.Menubutton(parent, text=text, relief=tk.RAISED, padx=10)
            menu = tk.Menu(mb, tearoff=0)
            mb.config(menu=menu)
            for label, cmd_code in items:
                menu.add_command(label=label, command=lambda c=cmd_code: self.add_comp(c))
            mb.pack(side=tk.LEFT, padx=2)
            return mb

        create_dropdown(toolbar, "Passives", [("Resistor (R)", "R"), ("Inductor (L)", "L"), ("Capacitor (C)", "C")])
        create_dropdown(toolbar, "MOSFETs", [("NMOS (N)", "NMOS"), ("PMOS (P)", "PMOS")])
        create_dropdown(toolbar, "Sources", [("Voltage (V)", "V"), ("Current (I)", "I")])
        
        tk.Button(toolbar, text="PIN", bg="#ffcccc", command=lambda: self.add_comp("PIN")).pack(side=tk.LEFT, padx=5)
        
        tk.Label(toolbar, text="|", fg="gray").pack(side=tk.LEFT, padx=5)
        self.mode_label = tk.Label(toolbar, text="Mode: SELECT", fg="blue", font=("Arial", 10, "bold"))
        self.mode_label.pack(side=tk.LEFT, padx=5)

        # --- 右側功能區 ---
        tk.Button(toolbar, text="Help(F1)", bg="lightblue", command=self.show_help).pack(side=tk.RIGHT)
        
        # [修改] 輸出按鈕旁增加模擬設定按鈕
        tk.Button(toolbar, text="Generate Netlist", bg="yellow", command=self.export_netlist).pack(side=tk.RIGHT, padx=5)
        tk.Button(toolbar, text="Sim Settings", bg="#ccffcc", command=self.open_sim_settings).pack(side=tk.RIGHT, padx=5)
        
        del_frame = tk.Frame(toolbar, bd=1, relief=tk.SUNKEN)
        del_frame.pack(side=tk.RIGHT, padx=10)
        self.del_btn = tk.Button(del_frame, text="Del Mode", bg="#ffaaaa", command=self.toggle_delete_mode)
        self.del_btn.pack(side=tk.LEFT)
        tk.Radiobutton(del_frame, text="Click", variable=self.del_style, value="CLICK", indicatoron=0, width=5).pack(side=tk.LEFT)
        tk.Radiobutton(del_frame, text="Box", variable=self.del_style, value="BOX", indicatoron=0, width=5).pack(side=tk.LEFT)

        self.canvas = tk.Canvas(self.root, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.focus_set()
        self.draw_grid()

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)

    def draw_grid(self):
        self.canvas.delete("grid")
        for i in range(0, 2000, 20):
            self.canvas.create_line(i, 0, i, 2000, fill="#f0f0f0", tags="grid")
            self.canvas.create_line(0, i, 2000, i, fill="#f0f0f0", tags="grid")
        self.canvas.tag_lower("grid")

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
        x, y = 300, 300
        comp = None
        if c_type == "R": comp = Resistor(self.canvas, x, y)
        elif c_type == "L": comp = Inductor(self.canvas, x, y)
        elif c_type == "C": comp = Capacitor(self.canvas, x, y)
        elif c_type == "V": comp = VoltageSource(self.canvas, x, y)
        elif c_type == "I": comp = CurrentSource(self.canvas, x, y)
        elif c_type == "NMOS": comp = CMOS(self.canvas, x, y, False)
        elif c_type == "PMOS": comp = CMOS(self.canvas, x, y, True)
        elif c_type == "PIN": comp = Pin(self.canvas, x, y)
        if comp: self.components.append(comp)
        self.canvas.focus_set()

    # --- [新增] 模擬設定視窗邏輯 ---
    def open_sim_settings(self):
        win = tk.Toplevel(self.root)
        win.title("HSPICE Analysis Setup")
        win.geometry("500x350")
        
        # 暫存變數 (BooleanVar 和 StringVar 需要綁定到 UI)
        vars_store = {}
        
        # 標題列
        tk.Label(win, text="Enable", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
        tk.Label(win, text="Command", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        tk.Label(win, text="Parameters", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # 動態生成控制項
        row = 1
        # 定義順序
        order = [".TRAN", ".DC", ".AC", ".OP", ".TF", ".NOISE"]
        
        for cmd in order:
            settings = self.sim_settings[cmd]
            
            # 1. Checkbox
            var_active = tk.BooleanVar(value=settings["active"])
            chk = tk.Checkbutton(win, variable=var_active)
            chk.grid(row=row, column=0)
            
            # 2. Label
            tk.Label(win, text=cmd, fg="blue").grid(row=row, column=1, sticky="w")
            
            # 3. Entry
            var_params = tk.StringVar(value=settings["params"])
            entry = tk.Entry(win, textvariable=var_params, width=30)
            entry.grid(row=row, column=2, padx=5, sticky="w")
            
            # 4. Hint
            tk.Label(win, text=settings["hint"], fg="gray", font=("Arial", 8)).grid(row=row, column=3, sticky="w")
            
            vars_store[cmd] = (var_active, var_params)
            row += 1
            
        def on_save():
            # 將 UI 的值寫回 self.sim_settings
            for cmd, (v_act, v_param) in vars_store.items():
                self.sim_settings[cmd]["active"] = v_act.get()
                self.sim_settings[cmd]["params"] = v_param.get()
            win.destroy()
            
        tk.Button(win, text="Save & Close", command=on_save, bg="lightgreen", width=15).grid(row=row+1, column=0, columnspan=4, pady=15)
        
        win.transient(self.root)
        win.grab_set()
        self.root.wait_window(win)

    # --- 其餘編輯功能 (select_item ... on_double_click) 保持不變 ---
    # 請保留這些函數:
    # select_item, deselect_all, toggle_delete_mode, toggle_wire_mode, delete_target,
    # get_best_snap_point, on_click, on_mouse_move, on_drag, on_release, on_double_click,
    # rotate_selection, mirror_selection, show_help
    # solve_connectivity (務必保留上一版支援 T-Junction 的版本)
    
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
                item.update_visuals() 
            elif i_type == "wire":
                self.canvas.itemconfig(item.tags, fill="blue")
        self.selected_item = None

    def toggle_delete_mode(self):
        self.set_mode("SELECT" if self.mode == "DELETE" else "DELETE")

    def toggle_wire_mode(self):
        self.set_mode("SELECT" if self.mode == "WIRE" else "WIRE")

    def delete_target(self, item, i_type):
        if i_type == "comp":
            self.canvas.delete(item.tags)
            if item in self.components: self.components.remove(item)
        elif i_type == "wire":
            self.canvas.delete(item.tags)
            if item in self.wires: self.wires.remove(item)
        self.selected_item = None

    def get_best_snap_point(self, x, y, threshold=15):
        best_pt = None
        min_dist = float('inf')
        for comp in self.components:
            for term, tx, ty in comp.get_abs_terminals():
                d = dist((x, y), (tx, ty))
                if d < min_dist and d < threshold:
                    min_dist = d
                    best_pt = (tx, ty)
        for wire in self.wires:
            for pt in [wire.start_p, wire.end_p]:
                d = dist((x, y), pt)
                if d < min_dist and d < threshold:
                    min_dist = d
                    best_pt = pt
        if min_dist > 5: 
            for wire in self.wires:
                px, py = get_closest_point_on_segment(x, y, wire.start_p[0], wire.start_p[1], wire.end_p[0], wire.end_p[1])
                d = dist((x, y), (px, py))
                if d < min_dist and d < threshold:
                    min_dist = d
                    best_pt = (px, py)
        return best_pt 

    def on_click(self, event):
        self.canvas.focus_set()
        if self.mode == "DELETE":
            if self.del_style.get() == "CLICK":
                item_id = self.canvas.find_closest(event.x, event.y)
                tags = self.canvas.gettags(item_id)
                for comp in self.components:
                    if comp.tags in tags:
                        self.delete_target(comp, "comp")
                        return
                for wire in self.wires:
                    if wire.tags in tags:
                        self.delete_target(wire, "wire")
                        return
            elif self.del_style.get() == "BOX":
                self.drag_data["box_start_x"] = event.x
                self.drag_data["box_start_y"] = event.y
            return

        cx, cy = snap(event.x), snap(event.y)
        if self.mode == "WIRE":
            snap_pt = self.get_best_snap_point(event.x, event.y)
            target_pt = snap_pt if snap_pt else (cx, cy)
            if not self.temp_wire_start:
                self.temp_wire_start = target_pt
            else:
                new_wire = Wire(self.canvas, self.temp_wire_start, target_pt)
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
                if wire.tags in tags:
                    self.select_item(wire, "wire")
                    return
            self.deselect_all()

    def on_mouse_move(self, event):
        if self.mode == "WIRE" and self.temp_wire_start:
            sx, sy = self.temp_wire_start
            snap_pt = self.get_best_snap_point(event.x, event.y)
            ex, ey = snap_pt if snap_pt else (snap(event.x), snap(event.y))
            self.canvas.delete("preview_wire")
            self.canvas.create_line(sx, sy, ex, ey, fill="gray", dash=(4, 4), tags="preview_wire")

    def on_drag(self, event):
        if self.mode == "DELETE" and self.del_style.get() == "BOX":
            start_x = self.drag_data.get("box_start_x")
            start_y = self.drag_data.get("box_start_y")
            if start_x is not None:
                self.canvas.delete("selection_box")
                self.canvas.create_rectangle(start_x, start_y, event.x, event.y, 
                                             outline="red", dash=(4, 4), width=2, tags="selection_box")
            return

        if self.mode == "SELECT" and self.selected_item and self.selected_item[1] == "comp":
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            comp = self.drag_data["comp"]
            self.canvas.move(comp.tags, dx, dy)
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

    def on_release(self, event):
        if self.mode == "DELETE" and self.del_style.get() == "BOX":
            start_x = self.drag_data.get("box_start_x")
            start_y = self.drag_data.get("box_start_y")
            if start_x is not None:
                x1, x2 = sorted([start_x, event.x])
                y1, y2 = sorted([start_y, event.y])
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

        if self.mode == "SELECT" and self.selected_item and self.selected_item[1] == "comp":
            comp = self.selected_item[0]
            total_dx = event.x - self.drag_data["start_x"]
            total_dy = event.y - self.drag_data["start_y"]
            raw_target_x = self.drag_data["comp_start_x"] + total_dx
            raw_target_y = self.drag_data["comp_start_y"] + total_dy
            target_x = snap(raw_target_x)
            target_y = snap(raw_target_y)
            threshold = 20 
            snap_candidates = [] 
            original_x, original_y = comp.x, comp.y
            comp.x, comp.y = raw_target_x, raw_target_y
            my_terms = comp.get_abs_terminals()
            comp.x, comp.y = original_x, original_y
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
            comp.update_visuals()

    def on_double_click(self, event):
        if self.selected_item and self.selected_item[1] == "comp":
            self.selected_item[0].edit_properties()

    def rotate_selection(self):
        if self.selected_item and self.selected_item[1] == "comp": self.selected_item[0].rotate()
    
    def mirror_selection(self):
        if self.selected_item and self.selected_item[1] == "comp": self.selected_item[0].flip()
            
    def show_help(self):
        messagebox.showinfo("Help", "Shortcuts:\nW: Wire Mode\nR/M: Rotate/Mirror\nDel: Delete Mode\nDouble Click: Property")

    def solve_connectivity(self):
        adj_list = {} 
        def add_edge(p1, p2):
            s1 = f"{p1[0]},{p1[1]}"
            s2 = f"{p2[0]},{p2[1]}"
            if s1 not in adj_list: adj_list[s1] = []
            if s2 not in adj_list: adj_list[s2] = []
            adj_list[s1].append(s2)
            adj_list[s2].append(s1)
        for wire in self.wires:
            add_edge(wire.start_p, wire.end_p)
        for w1 in self.wires:
            for w2 in self.wires:
                if w1 == w2: continue
                if is_point_on_segment(w1.start_p[0], w1.start_p[1], w2.start_p[0], w2.start_p[1], w2.end_p[0], w2.end_p[1]):
                    add_edge(w1.start_p, w2.start_p)
                if is_point_on_segment(w1.end_p[0], w1.end_p[1], w2.start_p[0], w2.start_p[1], w2.end_p[0], w2.end_p[1]):
                    add_edge(w1.end_p, w2.start_p)
        all_terminals = [] 
        for comp in self.components:
            for term, tx, ty in comp.get_abs_terminals():
                all_terminals.append((comp, term, tx, ty))
                for wire in self.wires:
                    if is_point_on_segment(tx, ty, wire.start_p[0], wire.start_p[1], wire.end_p[0], wire.end_p[1]):
                        add_edge((tx, ty), wire.start_p)
        connection_tolerance = 15.0 
        for i in range(len(all_terminals)):
            for j in range(i + 1, len(all_terminals)):
                t1 = all_terminals[i]
                t2 = all_terminals[j]
                if dist((t1[2], t1[3]), (t2[2], t2[3])) < connection_tolerance:
                    add_edge((t1[2], t1[3]), (t2[2], t2[3]))
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

    def export_netlist(self):
        node_map = self.solve_connectivity()
        lines = ["* Generated by Python Circuit CAD", ".OPTIONS POST"]
        
        for comp in self.components:
            if isinstance(comp, Pin): continue 
            abs_terms = comp.get_abs_terminals()
            node_names = []
            for term, tx, ty in abs_terms:
                key = f"{tx},{ty}"
                if key in node_map:
                    node_names.append(node_map[key])
                else:
                    node_names.append(f"NC_{comp.name}_{term.name}")
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
        
        # [修改] 增加模擬指令的輸出
        lines.append("\n* --- Simulation Settings ---")
        for cmd, settings in self.sim_settings.items():
            if settings["active"]:
                # 例如: .TRAN 1n 100n
                lines.append(f"{cmd} {settings['params']}")
        
        lines.append(".END")
        
        win = tk.Toplevel(self.root)
        t = tk.Text(win, width=80, height=20)
        t.pack()
        t.insert(tk.END, "\n".join(lines))