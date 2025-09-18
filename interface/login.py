import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib

from database import DB_NAME, criar_banco
from utils.theme import apply_theme, PALETTE, FONTS
from interface.main_window import MainWindow


class LoginWindow:
    def __init__(self, root):
        self.root = root

        # Garantir banco criado e usuário admin padrão
        try:
            criar_banco()
            self._ensure_default_admin()
        except Exception as e:
            print(f"Erro ao preparar banco de dados: {e}")

        # Janela de login como Toplevel
        self.window = tk.Toplevel(self.root)
        self.window.title("Login - Proposta Comercial")
        self.window.configure(bg=PALETTE["bg_app"]) 
        # Janela em tamanho fixo suficiente para exibir o cartão de login, centralizada
        self.window.geometry("520x520")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        # In fullscreen, centering is not needed

        # Variáveis
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        # Apply theme once the window is created
        try:
            apply_theme(self.window)
        except Exception:
            pass

        self._build_ui()

        # Foco inicial
        self.window.after(50, lambda: self.username_entry.focus_set())

    def _build_ui(self):
        container = tk.Frame(self.window, bg=PALETTE["bg_app"]) 
        container.pack(fill="both", expand=True, padx=24, pady=24)

        title = tk.Label(
            container,
            text="Proposta Comercial",
            font=FONTS["title"],
            bg=PALETTE["bg_app"],
            fg=PALETTE["text_primary"],
        )
        title.pack(anchor="n", pady=(8, 16))

        form_card = tk.Frame(container, bg='#ffffff', highlightthickness=1, highlightbackground=PALETTE["border"]) 
        form_card.pack(fill="x", padx=4, pady=4)
        form = tk.Frame(form_card, bg='#ffffff')
        form.pack(fill="both", expand=True, padx=24, pady=24)

        # Usuário
        tk.Label(form, text="Usuário", font=FONTS["base"], bg=PALETTE["bg_app"]).pack(
            anchor="w"
        )
        self.username_entry = ttk.Entry(
            form, textvariable=self.username_var, font=FONTS["base"],
        )
        self.username_entry.pack(fill="x", ipady=10, pady=(2, 12))

        # Senha
        tk.Label(form, text="Senha", font=FONTS["base"], bg=PALETTE["bg_app"]).pack(anchor="w")
        self.password_entry = ttk.Entry(
            form,
            textvariable=self.password_var,
            font=FONTS["base"],
            show="*",
        )
        self.password_entry.pack(fill="x", ipady=10, pady=(2, 4))

        # Bind Enter
        self.window.bind("<Return>", lambda _e: self._attempt_login())

        # Ações
        actions = tk.Frame(form, bg='#ffffff') 
        actions.pack(fill="x", pady=(16, 0))

        login_btn = ttk.Button(
            actions,
            text="Entrar",
            style="Primary.TButton",
            command=self._attempt_login,
        )
        login_btn.pack(side="left")

        # Removido texto de dica de senha para maior profissionalismo

    def _on_close(self):
        try:
            # Encerrar toda a aplicação se fechar a tela de login
            self.root.destroy()
        except Exception:
            pass

    def _ensure_default_admin(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM usuarios")
            count = c.fetchone()[0] or 0
            if count == 0:
                password_hash = hashlib.sha256("admin123".encode()).hexdigest()
                c.execute(
                    """
                    INSERT INTO usuarios (username, password, role, nome_completo, email)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("admin", password_hash, "admin", "Administrador", "admin@empresa.com"),
                )
                conn.commit()
                print("Usuário admin padrão criado: admin / admin123")
        finally:
            conn.close()

    def _attempt_login(self):
        username = (self.username_var.get() or "").strip()
        password = self.password_var.get() or ""

        if not username or not password:
            messagebox.showwarning("Login", "Informe usuário e senha.")
            return

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute(
                "SELECT id, role, COALESCE(nome_completo, username) FROM usuarios WHERE username = ? AND password = ?",
                (username, password_hash),
            )
            row = c.fetchone()
        finally:
            conn.close()

        if not row:
            messagebox.showerror("Login", "Usuário ou senha inválidos.")
            return

        user_id, role, nome_completo = row

        # Fechar janela de login e abrir a principal
        try:
            self.window.destroy()
        except Exception:
            pass

        MainWindow(self.root, user_id, role, nome_completo)

    def _quick_login_admin(self):
        self.username_var.set("admin")
        self.password_var.set("admin123")
        self._attempt_login()

