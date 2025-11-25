import tkinter as tk
from tkinter import ttk, simpledialog
from editor import SchematicEditor

class CircuitApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Circuit CAD v6.0 (Tabs & Renaming)")
        self.root.geometry("1200x800")

        # 1. Top Menu (Global Application Menu)
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Application", menu=file_menu)
        file_menu.add_command(label="New Tab", command=self.add_tab)
        file_menu.add_command(label="Close Tab", command=self.close_current_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)

        # 2. Notebook (Tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # [新增] 綁定分頁操作事件
        # Windows/Linux 右鍵通常是 Button-3, Mac 有時是 Button-2，這裡綁定 Button-3
        self.notebook.bind("<Button-3>", self.on_tab_right_click)
        # 雙擊左鍵也可以改名
        self.notebook.bind("<Double-Button-1>", self.on_tab_double_click)

        # 初始分頁
        self.add_tab()

        # 綁定全域快捷鍵
        root.bind("<Control-t>", lambda e: self.add_tab())
        root.bind("<Control-w>", lambda e: self.close_current_tab())
        
        # 綁定操作快捷鍵 (轉發給當前 Active Tab)
        keys = ["<r>", "<R>", "<l>", "<L>", "<c>", "<C>", 
                "<n>", "<N>", "<p>", "<P>", "<v>", "<V>", "<i>", "<I>", 
                "<m>", "<M>", "<Delete>", "<w>", "<W>", "<F1>"]
        for key in keys:
            root.bind(key, self.dispatch_event)

    def add_tab(self):
        tab_count = len(self.notebook.tabs()) + 1
        # [修改] 將 self.add_tab 作為 callback 傳入 Editor
        # 這樣 Editor 內部的 File 選單就能呼叫這個函數來開新分頁
        new_tab = SchematicEditor(self.notebook, on_new_file_callback=self.add_tab)
        self.notebook.add(new_tab, text=f"Untitled {tab_count}")
        self.notebook.select(new_tab)

    def close_current_tab(self):
        if not self.notebook.tabs(): return
        current_tab_id = self.notebook.select()
        self.notebook.forget(current_tab_id)
        self.root.nametowidget(current_tab_id).destroy()

    # --- [新增] 分頁重新命名邏輯 ---
    def rename_tab(self, event):
        try:
            # 透過滑鼠座標找出點擊的是哪一個 Tab 的 index
            tab_index = self.notebook.index(f"@{event.x},{event.y}")
            current_text = self.notebook.tab(tab_index, "text")
            
            # 彈出視窗詢問新名稱
            new_name = simpledialog.askstring("Rename Tab", "Enter new name:", initialvalue=current_text)
            
            if new_name:
                self.notebook.tab(tab_index, text=new_name)
        except tk.TclError:
            # 如果點擊的地方不是分頁標籤 (例如點到右邊空白處)，忽略錯誤
            pass

    def on_tab_right_click(self, event):
        self.rename_tab(event)

    def on_tab_double_click(self, event):
        self.rename_tab(event)

    def dispatch_event(self, event):
        if not self.notebook.tabs(): return
        current_tab_id = self.notebook.select()
        editor = self.root.nametowidget(current_tab_id)
        
        char = event.keysym.lower()
        if char == 'r': editor.add_comp("R")
        elif char == 'l': editor.add_comp("L")
        elif char == 'c': editor.add_comp("C")
        elif char == 'n': editor.add_comp("NMOS")
        elif char == 'p': editor.add_comp("PMOS")
        elif char == 'v': editor.add_comp("V")
        elif char == 'i': editor.add_comp("I")
        elif char == 'm': editor.mirror_selection()
        elif event.keysym == 'Delete': editor.toggle_delete_mode()
        elif char == 'w': editor.toggle_wire_mode()
        elif event.keysym == 'F1': editor.show_help()

def main():
    root = tk.Tk()
    app = CircuitApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()