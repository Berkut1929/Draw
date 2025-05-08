import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw, ImageGrab, ImageOps, ImageFilter
import numpy as np
import os
import json
from datetime import datetime


# ==============================================
# КЛАСС ГРАФИЧЕСКОГО РЕДАКТОРА
# ==============================================
class MicroGIMP:
    def __init__(self, root):
        self.root = root
        self.root.title("Micro GIMP Pro")
        self.root.geometry("1200x800")

        # Настройка стилей
        self.setup_styles()

        # Основные переменные
        self.brush_size = 5
        self.brush_color = "black"
        self.eraser_mode = False
        self.current_tool = "brush"
        self.fill_color = "white"
        self.image_path = None
        self.undo_stack = []
        self.redo_stack = []
        self.layers = []
        self.active_layer = None
        self.history_enabled = True
        self.last_save_path = None

        # Создание интерфейса
        self.create_menu()
        self.create_toolbar()
        self.create_canvas()
        self.create_layers_panel()
        self.create_statusbar()

        # Инициализация первого слоя
        self.add_layer("Background")

        # Привязка горячих клавиш
        self.bind_shortcuts()

    # ==============================================
    # НАСТРОЙКА СТИЛЕЙ
    # ==============================================
    def setup_styles(self):
        style = ttk.Style()
        style.configure("Toolbutton.TButton", padding=2, font=("Arial", 9))
        style.configure("Status.TLabel", background="#f0f0f0", relief=tk.SUNKEN, padding=3)
        style.configure("Layer.TFrame", background="#f5f5f5")
        style.configure("ActiveLayer.TFrame", background="#d0e0ff")

    # ==============================================
    # СОЗДАНИЕ ИНТЕРФЕЙСА
    # ==============================================
    def create_menu(self):
        menubar = tk.Menu(self.root)

        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новый", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Открыть", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Сохранить", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Сохранить как...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.exit_app)
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Меню "Правка"
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Отменить", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Повторить", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Очистить", command=self.clear_canvas)
        menubar.add_cascade(label="Правка", menu=edit_menu)

        # Меню "Инструменты"
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Кисть", command=lambda: self.set_tool("brush"))
        tools_menu.add_command(label="Ластик", command=lambda: self.set_tool("eraser"))
        tools_menu.add_command(label="Линия", command=lambda: self.set_tool("line"))
        tools_menu.add_command(label="Прямоугольник", command=lambda: self.set_tool("rectangle"))
        tools_menu.add_command(label="Овал", command=lambda: self.set_tool("oval"))
        tools_menu.add_command(label="Заливка", command=lambda: self.set_tool("fill"))
        menubar.add_cascade(label="Инструменты", menu=tools_menu)

        # Меню "Фильтры"
        filters_menu = tk.Menu(menubar, tearoff=0)
        filters_menu.add_command(label="Черно-белый", command=self.apply_grayscale)
        filters_menu.add_command(label="Размытие", command=self.apply_blur)
        filters_menu.add_command(label="Контур", command=self.apply_contour)
        filters_menu.add_command(label="Яркость", command=self.adjust_brightness)
        menubar.add_cascade(label="Фильтры", menu=filters_menu)

        # Меню "Справка"
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)

        self.root.config(menu=menubar)

    def create_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Кнопки инструментов
        tools = [
            ("brush", "Кисть", "🖌️"),
            ("eraser", "Ластик", "🧽"),
            ("line", "Линия", "─"),
            ("rectangle", "Прямоугольник", "⬛"),
            ("oval", "Овал", "🔵"),
            ("fill", "Заливка", "🎨"),
        ]

        for tool, text, icon in tools:
            btn = ttk.Button(
                toolbar,
                text=f"{icon} {text}",
                command=lambda t=tool: self.set_tool(t),
                style="Toolbutton.TButton"
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Выбор цвета
        ttk.Label(toolbar, text="Цвет:").pack(side=tk.LEFT, padx=5)
        self.color_btn = tk.Button(
            toolbar,
            bg=self.brush_color,
            width=2,
            command=self.choose_color
        )
        self.color_btn.pack(side=tk.LEFT, padx=2)

        # Размер кисти
        ttk.Label(toolbar, text="Размер:").pack(side=tk.LEFT, padx=5)
        self.size_slider = ttk.Scale(
            toolbar,
            from_=1,
            to=50,
            value=self.brush_size,
            command=self.change_brush_size
        )
        self.size_slider.pack(side=tk.LEFT, padx=2)
        self.size_label = ttk.Label(toolbar, text=str(self.brush_size))
        self.size_label.pack(side=tk.LEFT)

        # Переключатель ластика
        self.eraser_btn = ttk.Checkbutton(
            toolbar,
            text="Ластик",
            command=self.toggle_eraser
        )
        self.eraser_btn.pack(side=tk.LEFT, padx=5)

    def create_canvas(self):
        self.canvas_frame = ttk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg="white",
            width=800,
            height=600,
            cursor="cross"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Привязка событий мыши
        self.canvas.bind("<Button-1>", self.start_drawing)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drawing)

    def create_layers_panel(self):
        self.layers_frame = ttk.Frame(self.root, width=200)
        self.layers_frame.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(self.layers_frame, text="Слои").pack(pady=5)

        self.layers_listbox = tk.Listbox(self.layers_frame)
        self.layers_listbox.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(self.layers_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="+", command=lambda: self.add_layer("Новый слой")).pack(side=tk.LEFT, fill=tk.X,
                                                                                           expand=True)
        ttk.Button(btn_frame, text="-", command=self.delete_layer).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="▲", command=self.move_layer_up).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="▼", command=self.move_layer_down).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def create_statusbar(self):
        self.statusbar = ttk.Frame(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.tool_label = ttk.Label(self.statusbar, text="Инструмент: Кисть", style="Status.TLabel")
        self.tool_label.pack(side=tk.LEFT, padx=2)

        self.coord_label = ttk.Label(self.statusbar, text="X: 0, Y: 0", style="Status.TLabel")
        self.coord_label.pack(side=tk.RIGHT, padx=2)

        self.canvas.bind("<Motion>", self.update_coords)

    # ==============================================
    # ОСНОВНЫЕ ФУНКЦИИ
    # ==============================================
    def set_tool(self, tool):
        self.current_tool = tool
        self.tool_label.config(text=f"Инструмент: {tool.capitalize()}")

        if tool == "eraser":
            self.eraser_mode = True
        else:
            self.eraser_mode = False

    def choose_color(self):
        color = colorchooser.askcolor(title="Выберите цвет")[1]
        if color:
            self.brush_color = color
            self.color_btn.config(bg=color)

    def change_brush_size(self, value):
        self.brush_size = int(float(value))
        self.size_label.config(text=str(self.brush_size))

    def toggle_eraser(self):
        self.eraser_mode = not self.eraser_mode
        if self.eraser_mode:
            self.current_tool = "eraser"
            self.tool_label.config(text="Инструмент: Ластик")
        else:
            self.current_tool = "brush"
            self.tool_label.config(text="Инструмент: Кисть")

    def update_coords(self, event):
        self.coord_label.config(text=f"X: {event.x}, Y: {event.y}")

    # ==============================================
    # РИСОВАНИЕ
    # ==============================================
    def start_drawing(self, event):
        self.start_x, self.start_y = event.x, event.y

        if self.current_tool == "fill":
            self.fill(event.x, event.y)
            return

        self.last_x, self.last_y = event.x, event.y
        self.save_state()

    def draw(self, event):
        x, y = event.x, event.y

        if self.current_tool == "brush":
            self.canvas.create_line(
                self.last_x, self.last_y, x, y,
                width=self.brush_size,
                fill=self.brush_color if not self.eraser_mode else "white",
                capstyle=tk.ROUND,
                smooth=True
            )
            self.last_x, self.last_y = x, y

        elif self.current_tool == "line":
            self.canvas.delete("temp_line")
            self.canvas.create_line(
                self.start_x, self.start_y, x, y,
                width=self.brush_size,
                fill=self.brush_color,
                tags="temp_line"
            )

        elif self.current_tool in ["rectangle", "oval"]:
            self.canvas.delete("temp_shape")
            if self.current_tool == "rectangle":
                self.canvas.create_rectangle(
                    self.start_x, self.start_y, x, y,
                    width=self.brush_size,
                    outline=self.brush_color,
                    tags="temp_shape"
                )
            else:
                self.canvas.create_oval(
                    self.start_x, self.start_y, x, y,
                    width=self.brush_size,
                    outline=self.brush_color,
                    tags="temp_shape"
                )

    def stop_drawing(self, event):
        if self.current_tool == "line":
            self.canvas.create_line(
                self.start_x, self.start_y, event.x, event.y,
                width=self.brush_size,
                fill=self.brush_color
            )
            self.canvas.delete("temp_line")

        elif self.current_tool == "rectangle":
            self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                width=self.brush_size,
                outline=self.brush_color
            )
            self.canvas.delete("temp_shape")

        elif self.current_tool == "oval":
            self.canvas.create_oval(
                self.start_x, self.start_y, event.x, event.y,
                width=self.brush_size,
                outline=self.brush_color
            )
            self.canvas.delete("temp_shape")

    def fill(self, x, y):
        items = self.canvas.find_overlapping(x, y, x, y)
        if items:
            item = items[-1]
            self.canvas.itemconfig(item, fill=self.brush_color)
        else:
            self.canvas.create_rectangle(0, 0, self.canvas.winfo_width(), self.canvas.winfo_height(),
                                         fill=self.brush_color, tags="bg")

    def clear_canvas(self):
        self.canvas.delete("all")
        self.save_state()

    # ==============================================
    # РАБОТА СО СЛОЯМИ
    # ==============================================
    def add_layer(self, name):
        layer = {
            "id": len(self.layers) + 1,
            "name": name,
            "visible": True,
            "opacity": 1.0
        }
        self.layers.append(layer)
        self.update_layers_list()

    def delete_layer(self):
        if len(self.layers) > 1:
            selected = self.layers_listbox.curselection()
            if selected:
                del self.layers[selected[0]]
                self.update_layers_list()

    def move_layer_up(self):
        selected = self.layers_listbox.curselection()
        if selected and selected[0] > 0:
            self.layers[selected[0]], self.layers[selected[0] - 1] = self.layers[selected[0] - 1], self.layers[
                selected[0]]
            self.update_layers_list()
            self.layers_listbox.select_set(selected[0] - 1)

    def move_layer_down(self):
        selected = self.layers_listbox.curselection()
        if selected and selected[0] < len(self.layers) - 1:
            self.layers[selected[0]], self.layers[selected[0] + 1] = self.layers[selected[0] + 1], self.layers[
                selected[0]]
            self.update_layers_list()
            self.layers_listbox.select_set(selected[0] + 1)

    def update_layers_list(self):
        self.layers_listbox.delete(0, tk.END)
        for layer in self.layers:
            self.layers_listbox.insert(tk.END, layer["name"])

    # ==============================================
    # ФИЛЬТРЫ И ЭФФЕКТЫ
    # ==============================================
    def apply_grayscale(self):
        self.save_state()
        img = self.canvas_to_image()
        img = img.convert("L").convert("RGB")
        self.image_to_canvas(img)

    def apply_blur(self):
        self.save_state()
        img = self.canvas_to_image()
        img = img.filter(ImageFilter.BLUR)
        self.image_to_canvas(img)

    def apply_contour(self):
        self.save_state()
        img = self.canvas_to_image()
        img = img.filter(ImageFilter.CONTOUR)
        self.image_to_canvas(img)

    def adjust_brightness(self):
        brightness = tk.simpledialog.askfloat("Яркость", "Введите значение (-100..100)", initialvalue=0)
        if brightness is not None:
            self.save_state()
            img = self.canvas_to_image()
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1 + brightness / 100)
            self.image_to_canvas(img)

    # ==============================================
    # РАБОТА С ФАЙЛАМИ
    # ==============================================
    def new_file(self):
        self.canvas.delete("all")
        self.layers = []
        self.add_layer("Background")
        self.image_path = None
        self.last_save_path = None
        self.undo_stack = []
        self.redo_stack = []

    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Изображения", "*.png;*.jpg;*.jpeg;*.bmp"), ("Все файлы", "*.*")]
        )
        if file_path:
            try:
                img = Image.open(file_path)
                self.image_to_canvas(img)
                self.image_path = file_path
                self.last_save_path = file_path
                self.save_state()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")

    def save_file(self):
        if self.last_save_path:
            self.save_image(self.last_save_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("Все файлы", "*.*")]
        )
        if file_path:
            self.save_image(file_path)
            self.last_save_path = file_path

    def save_image(self, file_path):
        try:
            img = self.canvas_to_image()
            img.save(file_path)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

    def exit_app(self):
        if messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти?"):
            self.root.quit()

    # ==============================================
    # ИСТОРИЯ ДЕЙСТВИЙ (UNDO/REDO)
    # ==============================================
    def save_state(self):
        if self.history_enabled:
            img = self.canvas_to_image()
            self.undo_stack.append(img)
            self.redo_stack = []

    def undo(self):
        if self.undo_stack:
            img = self.undo_stack.pop()
            self.redo_stack.append(self.canvas_to_image())
            self.image_to_canvas(img)

    def redo(self):
        if self.redo_stack:
            img = self.redo_stack.pop()
            self.undo_stack.append(self.canvas_to_image())
            self.image_to_canvas(img)

    # ==============================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # ==============================================
    def canvas_to_image(self):
        x = self.root.winfo_rootx() + self.canvas.winfo_x()
        y = self.root.winfo_rooty() + self.canvas.winfo_y()
        x1 = x + self.canvas.winfo_width()
        y1 = y + self.canvas.winfo_height()
        return ImageGrab.grab((x, y, x1, y1))

    def image_to_canvas(self, img):
        self.canvas.delete("all")
        img_tk = ImageTk.PhotoImage(img)
        self.canvas.image = img_tk
        self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)

    def bind_shortcuts(self):
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())

    def show_about(self):
        messagebox.showinfo(
            "О программе",
            "Micro P\n\n"
            "Упрощенный графический редактор\n"
            "с поддержкой слоев, фильтров и истории действий.\n\n"
        )


# ==============================================
# ЗАПУСК ПРОГРАММЫ
# ==============================================
if __name__ == "__main__":
    root = tk.Tk()
    app = MicroGIMP(root)
    root.mainloop()