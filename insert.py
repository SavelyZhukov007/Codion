"""
insert.py — Codion Content Manager
===================================
GUI-приложение для добавления блоков на страницу index.html команды Codion.
Позволяет добавлять: проекты, участников команды, новости/достижения.
Поддерживает превью HTML-страницы и парсинг текущего контента.

Требования:
    pip install tkinterweb pillow

Использование:
    python insert.py
    (запускайте из корневой папки сайта — там, где лежит index.html)

    НЕ ТРОГАТЬ (пока что, оно не допилино)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import sys
import re
import shutil
import json
import datetime
from pathlib import Path

# --- tkinterweb для HTML-превью (необязательная зависимость) ---
try:
    from tkinterweb import HtmlFrame
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False

# --- Pillow для предпросмотра изображений ---
try:
    from PIL import Image, ImageTk
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# ============================
# КОНФИГУРАЦИЯ
# ============================
BASE_DIR   = Path(__file__).parent
HTML_FILE  = BASE_DIR / "index.html"
IMAGES_DIR = BASE_DIR / "images"
LOG_FILE   = BASE_DIR / "insert_log.json"

START_MARKER = "<!-- DYNAMIC_BLOCKS_START"
END_MARKER   = "<!-- DYNAMIC_BLOCKS_END"

COLORS = {
    "bg":        "#05080f",
    "bg2":       "#0a1020",
    "surface":   "#0d1528",
    "border":    "#0d2040",
    "primary":   "#00aaff",
    "accent":    "#00d4ff",
    "text":      "#c8d8f0",
    "muted":     "#5b7498",
    "success":   "#00ff88",
    "error":     "#ff4466",
    "white":     "#ffffff",
}

FONT_MONO = ("Courier New", 10)
FONT_HEAD = ("Courier New", 13, "bold")
FONT_BODY = ("Courier New", 9)

# ============================
# HTML ШАБЛОНЫ
# ============================

def tpl_project(title, tag, desc, tech_str, img_rel, link, date_str):
    tech_tags = "".join(f'<span>{t.strip()}</span>' for t in tech_str.split(",") if t.strip())
    img_block = (
        f'<div class="project-card__img-wrap">'
        f'<img src="{img_rel}" alt="{title}" class="project-card__img"/></div>\n        '
    ) if img_rel else ""
    arrow = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>'
    return f'''
      <!-- [CODION-BLOCK project "{title}" {date_str}] -->
      <div class="project-card reveal" data-added="true">
        {img_block}<div class="project-card__body">
          <p class="project-card__tag">// {tag}</p>
          <h3 class="project-card__title">{title}</h3>
          <p class="project-card__desc">{desc}</p>
          <div class="project-card__tech">{tech_tags}</div>
          <a href="{link}" class="project-card__link">Подробнее {arrow}</a>
        </div>
      </div>'''

def tpl_news(date, title, body, img_rel):
    img_block = (
        f'<img src="{img_rel}" alt="{title}" class="news-card__img"/>\n        '
    ) if img_rel else ""
    return f'''
      <!-- [CODION-BLOCK news "{title}" {date}] -->
      <div class="news-card reveal" data-added="true">
        {img_block}<p class="news-card__date">// {date}</p>
        <h3 class="news-card__title">{title}</h3>
        <p class="news-card__body">{body}</p>
      </div>'''

def tpl_member(name, role, bio, skills_str, img_rel, github, telegram):
    skills_tags = "".join(f'<span>{s.strip()}</span>' for s in skills_str.split(",") if s.strip())
    img_content = (
        f'<img src="{img_rel}" alt="{name}" class="member-card__img"/>'
    ) if img_rel else (
        '<div style="height:100%;background:linear-gradient(135deg,#0a1020,#0d1830);'
        'display:flex;align-items:center;justify-content:center;">'
        '<i class="fas fa-user" style="font-size:4rem;color:#1a3050;"></i></div>'
    )
    return f'''
      <!-- [CODION-BLOCK member "{name}"] -->
      <div class="member-card reveal" data-added="true">
        <div class="member-card__img-wrap">{img_content}</div>
        <div class="member-card__body">
          <p class="member-card__role">// {role}</p>
          <h3 class="member-card__name">{name}</h3>
          <p class="member-card__bio">{bio}</p>
          <div class="member-card__skills">{skills_tags}</div>
          <div class="member-card__socials">
            <a href="{github}" title="GitHub"><i class="fab fa-github"></i></a>
            <a href="{telegram}" title="Telegram"><i class="fab fa-telegram"></i></a>
          </div>
        </div>
      </div>'''

# ============================
# HTML ПАРСЕР
# ============================

def parse_html_blocks(html_text):
    """Находит все блоки добавленные через insert.py."""
    pattern = r'<!--\s*\[CODION-BLOCK\s+(\w+)\s+"([^"]+)"\s*([^\]]*)\]'
    blocks  = []
    for m in re.finditer(pattern, html_text):
        blocks.append({
            "type": m.group(1),
            "name": m.group(2),
            "meta": m.group(3).strip(),
            "pos":  m.start(),
        })
    return blocks

def read_html():
    if not HTML_FILE.exists():
        return None
    return HTML_FILE.read_text(encoding="utf-8")

def write_html(content):
    # Бэкап
    backup = HTML_FILE.with_suffix(".html.bak")
    shutil.copy2(HTML_FILE, backup)
    HTML_FILE.write_text(content, encoding="utf-8")

def inject_block(html_text, block_html, target_id):
    """Вставляет block_html перед END_MARKER нужного контейнера."""
    if END_MARKER not in html_text:
        return None, "Маркер DYNAMIC_BLOCKS_END не найден в HTML."
    idx = html_text.index(END_MARKER)
    new_html = html_text[:idx] + block_html + "\n\n      " + html_text[idx:]
    return new_html, None

def inject_into_container(html_text, container_id, block_html):
    """Вставляет блок в конец div с указанным id."""
    pattern = rf'(<div[^>]*\bid=["\']?{re.escape(container_id)}["\']?[^>]*>)'
    m = re.search(pattern, html_text, re.IGNORECASE)
    if not m:
        return None, f"Контейнер #{container_id} не найден в HTML."
    # Найдём закрывающий </div>
    start   = m.end()
    depth   = 1
    pos     = start
    while pos < len(html_text) and depth > 0:
        open_  = html_text.find('<div', pos)
        close_ = html_text.find('</div', pos)
        if open_ != -1 and (close_ == -1 or open_ < close_):
            depth += 1; pos = open_ + 4
        elif close_ != -1:
            depth -= 1
            if depth == 0:
                new_html = html_text[:close_] + block_html + "\n\n      " + html_text[close_:]
                return new_html, None
            pos = close_ + 6
        else:
            break
    return None, f"Не удалось определить границы #{container_id}."

def save_log(entry):
    data = []
    if LOG_FILE.exists():
        try: data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except: pass
    data.append(entry)
    LOG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def copy_image(src_path):
    """Копирует изображение в images/ и возвращает относительный путь."""
    IMAGES_DIR.mkdir(exist_ok=True)
    dst = IMAGES_DIR / Path(src_path).name
    if Path(src_path) != dst:
        shutil.copy2(src_path, dst)
    return f"images/{dst.name}"

# ============================
# GUI
# ============================

class CodionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Codion Insert — Менеджер контента")
        self.geometry("1200x780")
        self.configure(bg=COLORS["bg"])
        self.resizable(True, True)

        self._selected_image = ""  # полный путь к выбранному изображению
        self._img_tk = None        # ссылка для Pillow

        self._build_ui()
        self._refresh_blocks_list()

    # ----- UI Layout -----
    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg=COLORS["bg"], pady=8)
        top.pack(fill="x", padx=16)

        tk.Label(top, text="⚡ CODION INSERT", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=("Courier New", 16, "bold")).pack(side="left")

        tk.Label(top, text=f"  {HTML_FILE}", bg=COLORS["bg"],
                 fg=COLORS["muted"], font=FONT_BODY).pack(side="left", padx=16)

        tk.Button(top, text="🔄 Обновить список", bg=COLORS["surface"],
                  fg=COLORS["primary"], font=FONT_BODY, relief="flat", cursor="hand2",
                  command=self._refresh_blocks_list).pack(side="right")

        # Main paned window
        paned = tk.PanedWindow(self, orient="horizontal", bg=COLORS["bg"],
                                sashwidth=6, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=8, pady=4)

        # LEFT: form + list
        left = tk.Frame(paned, bg=COLORS["bg"])
        paned.add(left, minsize=480)

        self._build_form(left)
        self._build_list(left)

        # RIGHT: preview
        right = tk.Frame(paned, bg=COLORS["bg2"])
        paned.add(right, minsize=400)
        self._build_preview(right)

    def _build_form(self, parent):
        frm = tk.LabelFrame(parent, text=" Добавить блок ", bg=COLORS["bg"],
                             fg=COLORS["accent"], font=FONT_HEAD,
                             bd=1, relief="solid", labelanchor="nw")
        frm.pack(fill="x", padx=8, pady=6)

        # Module selector
        sel_row = tk.Frame(frm, bg=COLORS["bg"])
        sel_row.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(sel_row, text="Модуль:", bg=COLORS["bg"], fg=COLORS["muted"],
                 font=FONT_BODY).pack(side="left")

        self.module_var = tk.StringVar(value="project")
        for val, lbl in [("project","Проект"), ("news","Новость/Достижение"), ("member","Участник команды")]:
            rb = tk.Radiobutton(sel_row, text=lbl, variable=self.module_var, value=val,
                                bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["surface"],
                                activebackground=COLORS["bg"], font=FONT_BODY,
                                command=self._on_module_change)
            rb.pack(side="left", padx=10)

        # Dynamic fields container
        self.fields_frame = tk.Frame(frm, bg=COLORS["bg"])
        self.fields_frame.pack(fill="x", padx=10, pady=4)
        self._build_project_fields()

        # Image selector
        img_row = tk.Frame(frm, bg=COLORS["bg"])
        img_row.pack(fill="x", padx=10, pady=4)
        tk.Label(img_row, text="Изображение:", bg=COLORS["bg"],
                 fg=COLORS["muted"], font=FONT_BODY, width=16, anchor="w").pack(side="left")
        self.img_label = tk.Label(img_row, text="не выбрано", bg=COLORS["bg"],
                                   fg=COLORS["muted"], font=FONT_BODY)
        self.img_label.pack(side="left", expand=True, fill="x")
        tk.Button(img_row, text="Выбрать…", bg=COLORS["surface"], fg=COLORS["primary"],
                  font=FONT_BODY, relief="flat", cursor="hand2",
                  command=self._pick_image).pack(side="right")

        # Image thumbnail
        self.thumb_label = tk.Label(frm, bg=COLORS["bg"])
        self.thumb_label.pack(pady=4)

        # Submit
        btn_row = tk.Frame(frm, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=10, pady=(6, 10))
        tk.Button(btn_row, text="⚡ Добавить в HTML", bg=COLORS["primary"],
                  fg=COLORS["bg"], font=("Courier New", 10, "bold"),
                  relief="flat", cursor="hand2", pady=6,
                  command=self._on_submit).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="🗑 Очистить форму", bg=COLORS["surface"],
                  fg=COLORS["muted"], font=FONT_BODY, relief="flat", cursor="hand2",
                  command=self._clear_form).pack(side="left")

        # Status bar
        self.status_var = tk.StringVar(value="// Готов к работе")
        tk.Label(frm, textvariable=self.status_var, bg=COLORS["bg"],
                 fg=COLORS["success"], font=FONT_BODY, anchor="w").pack(fill="x", padx=10, pady=(0, 6))

    def _make_field(self, parent, label, var_name, height=1):
        row = tk.Frame(parent, bg=COLORS["bg"])
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=COLORS["bg"], fg=COLORS["muted"],
                 font=FONT_BODY, width=16, anchor="nw").pack(side="left", anchor="n", pady=2)
        if height == 1:
            entry = tk.Entry(row, bg=COLORS["surface"], fg=COLORS["text"],
                              insertbackground=COLORS["accent"],
                              relief="flat", font=FONT_BODY, bd=4)
            entry.pack(side="left", fill="x", expand=True)
        else:
            entry = scrolledtext.ScrolledText(row, bg=COLORS["surface"], fg=COLORS["text"],
                                               insertbackground=COLORS["accent"],
                                               relief="flat", font=FONT_BODY,
                                               height=height, bd=4,
                                               wrap="word")
            entry.pack(side="left", fill="x", expand=True)
        setattr(self, var_name, entry)
        return entry

    def _build_project_fields(self):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self._make_field(self.fields_frame, "Название:",  "f_title")
        self._make_field(self.fields_frame, "Тег/статус:", "f_tag")
        self._make_field(self.fields_frame, "Описание:",   "f_desc",  height=3)
        self._make_field(self.fields_frame, "Технологии:", "f_tech")
        tk.Label(self.fields_frame, text="  (через запятую: Python, Django, PostgreSQL)",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_BODY).pack(anchor="w")
        self._make_field(self.fields_frame, "Ссылка:",     "f_link")

    def _build_news_fields(self):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self._make_field(self.fields_frame, "Дата:",       "f_title")
        self._make_field(self.fields_frame, "Заголовок:",  "f_tag")
        self._make_field(self.fields_frame, "Текст:",      "f_desc",  height=4)

    def _build_member_fields(self):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self._make_field(self.fields_frame, "Имя Фамилия:", "f_title")
        self._make_field(self.fields_frame, "Роль:",         "f_tag")
        self._make_field(self.fields_frame, "Биография:",    "f_desc",  height=3)
        self._make_field(self.fields_frame, "Навыки:",       "f_tech")
        tk.Label(self.fields_frame, text="  (через запятую: Python, Django)",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_BODY).pack(anchor="w")
        self._make_field(self.fields_frame, "GitHub URL:",   "f_link")
        self._make_field(self.fields_frame, "Telegram URL:", "f_extra")

    def _build_list(self, parent):
        frm = tk.LabelFrame(parent, text=" Текущие блоки в HTML ", bg=COLORS["bg"],
                             fg=COLORS["accent"], font=FONT_HEAD,
                             bd=1, relief="solid", labelanchor="nw")
        frm.pack(fill="both", expand=True, padx=8, pady=6)

        cols = ("Тип", "Название", "Дата")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=8)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["surface"],
                         foreground=COLORS["text"], fieldbackground=COLORS["surface"],
                         font=FONT_BODY, rowheight=24)
        style.configure("Treeview.Heading", background=COLORS["bg2"],
                         foreground=COLORS["accent"], font=FONT_BODY)
        style.map("Treeview", background=[("selected", COLORS["primary"])],
                  foreground=[("selected", COLORS["bg"])])

        vsb = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        vsb.pack(side="right", fill="y", pady=4)

    def _build_preview(self, parent):
        tk.Label(parent, text="ПРЕВЬЮ САЙТА", bg=COLORS["bg2"],
                 fg=COLORS["accent"], font=FONT_HEAD, pady=6).pack(fill="x")

        btn_row = tk.Frame(parent, bg=COLORS["bg2"])
        btn_row.pack(fill="x", padx=8, pady=4)

        tk.Button(btn_row, text="🔄 Обновить превью", bg=COLORS["surface"],
                  fg=COLORS["primary"], font=FONT_BODY, relief="flat", cursor="hand2",
                  command=self._refresh_preview).pack(side="left")

        tk.Button(btn_row, text="📂 Открыть в браузере", bg=COLORS["surface"],
                  fg=COLORS["primary"], font=FONT_BODY, relief="flat", cursor="hand2",
                  command=self._open_browser).pack(side="left", padx=8)

        if WEBVIEW_AVAILABLE:
            self.html_frame = HtmlFrame(parent, horizontal_scrollbar="auto")
            self.html_frame.pack(fill="both", expand=True, padx=4, pady=4)
            self._refresh_preview()
        else:
            # Fallback: HTML-код в текстовом поле
            self.preview_text = scrolledtext.ScrolledText(
                parent, bg=COLORS["surface"], fg=COLORS["text"],
                font=FONT_BODY, relief="flat", wrap="none", state="disabled"
            )
            self.preview_text.pack(fill="both", expand=True, padx=4, pady=4)

            warn = tk.Label(parent,
                text="⚠ tkinterweb не установлен. Показан исходный код HTML.\n"
                     "Установите: pip install tkinterweb",
                bg=COLORS["bg2"], fg=COLORS["error"], font=FONT_BODY, justify="left")
            warn.pack(padx=8, pady=4)
            self._load_html_source()

    # ----- Handlers -----
    def _on_module_change(self):
        m = self.module_var.get()
        if m == "project":    self._build_project_fields()
        elif m == "news":     self._build_news_fields()
        elif m == "member":   self._build_member_fields()
        self._selected_image = ""
        self.img_label.config(text="не выбрано")
        self.thumb_label.config(image="", text="")

    def _pick_image(self):
        path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif"), ("All", "*.*")]
        )
        if not path: return
        self._selected_image = path
        self.img_label.config(text=Path(path).name)
        self._show_thumb(path)

    def _show_thumb(self, path):
        if not PILLOW_AVAILABLE:
            self.thumb_label.config(text="(Pillow не установлен — предпросмотр недоступен)",
                                    fg=COLORS["muted"], font=FONT_BODY)
            return
        try:
            img = Image.open(path)
            img.thumbnail((220, 120), Image.LANCZOS)
            self._img_tk = ImageTk.PhotoImage(img)
            self.thumb_label.config(image=self._img_tk, text="")
        except Exception as e:
            self.thumb_label.config(text=f"Ошибка: {e}", fg=COLORS["error"])

    def _get_text(self, widget):
        if isinstance(widget, scrolledtext.ScrolledText):
            return widget.get("1.0", "end-1c").strip()
        return widget.get().strip()

    def _clear_form(self):
        for attr in ("f_title", "f_tag", "f_desc", "f_tech", "f_link", "f_extra"):
            if hasattr(self, attr):
                w = getattr(self, attr)
                if isinstance(w, scrolledtext.ScrolledText):
                    w.delete("1.0", "end")
                else:
                    w.delete(0, "end")
        self._selected_image = ""
        self.img_label.config(text="не выбрано")
        self.thumb_label.config(image="", text="")
        self.status_var.set("// Форма очищена")

    def _on_submit(self):
        html = read_html()
        if html is None:
            messagebox.showerror("Ошибка", f"Файл не найден:\n{HTML_FILE}")
            return

        module = self.module_var.get()
        img_rel = ""
        if self._selected_image:
            try:
                img_rel = copy_image(self._selected_image)
            except Exception as e:
                messagebox.showerror("Ошибка копирования", str(e)); return

        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            if module == "project":
                title = self._get_text(self.f_title)
                tag   = self._get_text(self.f_tag)
                desc  = self._get_text(self.f_desc)
                tech  = self._get_text(self.f_tech)
                link  = self._get_text(self.f_link) or "#"
                if not title or not desc:
                    messagebox.showwarning("Заполните форму", "Название и описание обязательны."); return
                block = tpl_project(title, tag, desc, tech, img_rel, link, date_str)
                new_html, err = inject_block(html, block, "projects-grid")

            elif module == "news":
                date  = self._get_text(self.f_title)
                title = self._get_text(self.f_tag)
                body  = self._get_text(self.f_desc)
                if not title or not body:
                    messagebox.showwarning("Заполните форму", "Заголовок и текст обязательны."); return
                block = tpl_news(date, title, body, img_rel)
                new_html, err = inject_block(html, block, "dynamic-blocks")

            elif module == "member":
                name     = self._get_text(self.f_title)
                role     = self._get_text(self.f_tag)
                bio      = self._get_text(self.f_desc)
                skills   = self._get_text(self.f_tech)
                github   = self._get_text(self.f_link) or "#"
                telegram = self._get_text(self.f_extra) if hasattr(self, "f_extra") else "#"
                if not name:
                    messagebox.showwarning("Заполните форму", "Имя обязательно."); return
                block = tpl_member(name, role, bio, skills, img_rel, github, telegram)
                new_html, err = inject_into_container(html, "team-grid", block)

            else:
                return

        except AttributeError as e:
            messagebox.showerror("Ошибка формы", f"Поле не найдено: {e}"); return

        if err:
            messagebox.showerror("Ошибка вставки", err); return

        write_html(new_html)
        save_log({"module": module, "date": date_str, "image": img_rel})

        self.status_var.set(f"// ✓ Блок «{module}» добавлен — {date_str}")
        self._refresh_blocks_list()
        self._refresh_preview()
        messagebox.showinfo("Готово!", f"Блок добавлен в {HTML_FILE.name}\nРезервная копия: .html.bak")

    def _refresh_blocks_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        html = read_html()
        if not html: return
        blocks = parse_html_blocks(html)
        for b in blocks:
            self.tree.insert("", "end", values=(b["type"], b["name"], b["meta"]))
        if not blocks:
            self.tree.insert("", "end", values=("—", "Нет блоков, добавленных через insert.py", ""))

    def _refresh_preview(self):
        html = read_html()
        if not html: return
        if WEBVIEW_AVAILABLE and hasattr(self, "html_frame"):
            # Передаём абсолютный путь чтобы CSS/изображения загрузились
            file_url = HTML_FILE.as_uri()
            try:
                self.html_frame.load_url(file_url)
            except Exception as e:
                print(f"Ошибка загрузки превью: {e}")
        elif hasattr(self, "preview_text"):
            self._load_html_source(html)

    def _load_html_source(self, html=None):
        if html is None: html = read_html() or ""
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", html)
        self.preview_text.config(state="disabled")

    def _open_browser(self):
        import webbrowser
        webbrowser.open(HTML_FILE.as_uri())


# ============================
# ENTRY POINT
# ============================
if __name__ == "__main__":
    if not HTML_FILE.exists():
        print(f"[!] index.html не найден по пути {HTML_FILE}")
        print("[!] Запускайте insert.py из корневой папки сайта.")
        sys.exit(1)

    if not PILLOW_AVAILABLE:
        print("[~] Pillow не установлен. Установите: pip install Pillow")
    if not WEBVIEW_AVAILABLE:
        print("[~] tkinterweb не установлен. Установите: pip install tkinterweb")
        print("[~] Без него превью будет показывать исходный HTML.")

    print("[*] Запуск Codion Insert...")
    app = CodionApp()
    app.mainloop()
