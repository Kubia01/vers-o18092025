import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from database import DB_NAME
from utils.theme import apply_theme, style_header_frame, PALETTE, FONTS

class MainWindow:
    def __init__(self, root, user_id, role, nome_completo):
        self.root = root
        self.user_id = user_id
        self.role = role
        self.nome_completo = nome_completo
        
        # Sistema de eventos para comunicação entre módulos
        self.event_listeners = []
        
        self.setup_main_window()
        self.create_main_ui()
        
        # Mostrar janela principal
        self.root.deiconify()
        
    def setup_main_window(self):
        """Configurar janela principal"""
        self.root.title(f"Proposta Comercial - {self.nome_completo} ({self.role})")
        self.root.geometry("1400x800")
        try:
            apply_theme(self.root)
        except Exception:
            pass
        self.root.configure(bg=PALETTE["bg_app"]) 
        
        # Maximizar janela após login para ocupar a tela inteira
        try:
            self.root.state('zoomed')
        except Exception:
            try:
                self.root.attributes('-zoomed', True)
            except Exception:
                # Fallback: centralizar
                self.center_window()
        
    def center_window(self):
        """Centralizar a janela na tela"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def has_role(self, role_name: str) -> bool:
        """Verifica se o usuário possui o perfil informado (suporta múltiplos perfis separados por vírgula)."""
        try:
            roles = [r.strip().lower() for r in (self.role or '').split(',') if r.strip()]
            return role_name.lower() in roles
        except Exception:
            return self.role == role_name
        
    def register_listener(self, listener_func):
        """Registrar um listener para eventos do sistema"""
        self.event_listeners.append(listener_func)
        
    def emit_event(self, event_type, data=None):
        """Emitir um evento para todos os listeners"""
        print(f"DEBUG MAIN_WINDOW: Emitindo evento '{event_type}' para {len(self.event_listeners)} listeners")
        for i, listener in enumerate(self.event_listeners):
            try:
                print(f"DEBUG MAIN_WINDOW: Notificando listener {i}: {listener}")
                listener(event_type, data)
            except Exception as e:
                print(f"Erro ao processar evento {event_type}: {e}")
        
    def create_main_ui(self):
        # Frame superior com menu
        self.create_header()

        # Container com navegação lateral (vertical) + área principal (notebook)
        container = tk.Frame(self.root, bg=PALETTE["bg_app"]) 
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, minsize=220)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # Navegação lateral
        self.side_nav = tk.Frame(container, bg="#ffffff", highlightthickness=1, highlightbackground=PALETTE["border"]) 
        self.side_nav.grid(row=0, column=0, sticky="nswe", padx=(10, 6), pady=(10, 10))

        # Área de conteúdo com notebook (mantém a lógica e instância dos módulos)
        # Main content notebook with hidden tabs (style handled by theme)
        self.notebook = ttk.Notebook(container, style='Main.TNotebook')
        self.notebook.grid(row=0, column=1, sticky="nswe", padx=(6, 10), pady=(10, 10))

        # Criar módulos
        self._load_user_permissions()
        self.create_modules()
        
    def create_header(self):
        """Criar cabeçalho com informações do usuário e botões"""
        header_frame = tk.Frame(self.root, bg=PALETTE["bg_header"], height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        # Frame esquerdo - título
        left_frame = tk.Frame(header_frame, bg=PALETTE["bg_header"]) 
        left_frame.pack(side="left", fill="y", padx=20, pady=10)
        
        title_label = tk.Label(left_frame, 
                              text="Proposta Comercial",
                              font=FONTS["title"],
                              bg=PALETTE["bg_header"],
                              fg='white')
        title_label.pack(anchor="w")
        
        # Frame direito - informações do usuário e logout
        right_frame = tk.Frame(header_frame, bg=PALETTE["bg_header"]) 
        right_frame.pack(side="right", fill="y", padx=20, pady=10)
        
        user_label = tk.Label(right_frame,
                             text=f"Usuário: {self.nome_completo} ({self.role})",
                             font=FONTS["base"],
                             bg=PALETTE["bg_header"],
                             fg='#e2e8f0')
        user_label.pack(anchor="e")
        
        logout_btn = tk.Button(right_frame,
                              text="SAIR",
                              font=('Arial', 8, 'bold'),
                              bg='#000000',
                              fg='#ffffff',
                              bd=2,
                              relief='raised',
                              command=self.logout)
        
        # Adicionar efeito hover
        def on_enter(e):
            logout_btn['bg'] = '#1e40af'
        def on_leave(e):
            logout_btn['bg'] = '#000000'
        
        logout_btn.bind("<Enter>", on_enter)
        logout_btn.bind("<Leave>", on_leave)
        
        logout_btn.pack(anchor="e", pady=(5, 0))
        
    def create_modules(self):
        """Criar todos os módulos do sistema com importação isolada e tolerante a falhas"""
        def add_module(tab_text, module_path, class_name):
            frame = tk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_text)
            try:
                mod = __import__(module_path, fromlist=[class_name])
                cls = getattr(mod, class_name)
                instance = cls(frame, self.user_id, self.role, self)
                # Aplicar readonly automaticamente baseado nas permissões
                module_key = self._tab_text_to_key(tab_text)
                if not self.can_edit(module_key) and hasattr(instance, 'set_read_only'):
                    try:
                        instance.set_read_only(True)
                        print(f"🔒 FORÇANDO modo somente leitura para módulo {module_key} (usuário {self.user_id})")
                        # Aplicar proteção adicional após um breve delay para garantir que a UI esteja pronta
                        self.root.after(100, lambda: self._force_read_only_protection(instance, module_key))
                    except Exception as e:
                        print(f"⚠️ Erro ao aplicar modo somente leitura: {e}")
                return instance
            except Exception as e:
                messagebox.showerror("Erro ao carregar módulo", f"Falha ao carregar {tab_text}:\n\n{e}")
                return None

        # Dashboard
        if self.has_access('dashboard'):
            self.dashboard_module = add_module("📊 Dashboard", "interface.modules.dashboard", "DashboardModule")
        # Clientes
        if self.has_access('clientes'):
            self.clientes_module = add_module("👥 Clientes", "interface.modules.clientes", "ClientesModule")
        # Cadastros (antes: Produtos)
        if self.has_access('produtos'):
            self.produtos_module = add_module("📦 Cadastros", "interface.modules.produtos", "ProdutosModule")
        # Orçamento de Serviços
        if self.has_access('orcamento_servicos'):
            self.orcamento_servicos_module = add_module("🔧 Orçamento de Serviços", "interface.modules.orcamento_servicos", "OrcamentoServicosModule")
        # Orçamento de Produtos
        if self.has_access('orcamento_produtos'):
            self.orcamento_produtos_module = add_module("📦 Orçamento de Produtos", "interface.modules.orcamento_produtos", "OrcamentoProdutosModule")
        # Orçamento de Locações (aba separada - módulo independente)
        if self.has_access('relatorios') or self.has_access('cotacoes'):
            # manter lógica de locações na permissão de cotações/relatórios se necessário, ou crie chave própria
            if self.has_access('relatorios') or self.has_access('cotacoes'):
                self.locacoes_module = add_module("📄 Orçamento de Locações", "interface.modules.locacoes_full", "LocacoesModule")
        # Relatórios
        if self.has_access('relatorios'):
            self.relatorios_module = add_module("📋 Relatórios", "interface.modules.relatorios", "RelatoriosModule")
        # Usuários e Permissões
        if self.has_access('usuarios'):
            self.usuarios_module = add_module("👤 Usuários", "interface.modules.usuarios", "UsuariosModule")
        if self.has_access('permissoes'):
            self.permissoes_module = add_module("🔐 Permissões", "interface.modules.permissoes", "PermissoesModule")

        # Construir navegação lateral com botões que selecionam as abas do notebook
        self._build_side_nav()
        # Destacar item ativo ao trocar de aba
        try:
            self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        except Exception:
            pass

    def _tab_text_to_key(self, tab_text: str) -> str:
        mapping = {
            '📊 Dashboard': 'dashboard',
            '👥 Clientes': 'clientes',
            '📦 Cadastros': 'produtos',
            '🔧 Orçamento de Serviços': 'orcamento_servicos',
            '📦 Orçamento de Produtos': 'orcamento_produtos',
            '📄 Orçamento de Locações': 'locacoes',
            '📋 Relatórios': 'relatorios',
            '👤 Usuários': 'usuarios',
            '🔐 Permissões': 'permissoes',
        }
        return mapping.get(tab_text, '')
    
    def _force_read_only_protection(self, instance, module_key):
        """Força proteção adicional para garantir que nenhum campo possa ser editado"""
        try:
            if hasattr(instance, 'frame'):
                print(f"🔒🔒🔒 APLICANDO proteção TOTAL no módulo {module_key}")
                self._disable_all_widgets_completely(instance.frame)
                print(f"✅ Proteção TOTAL aplicada no módulo {module_key}")
        except Exception as e:
            print(f"⚠️ Erro ao aplicar proteção total: {e}")
    
    def _disable_all_widgets_completely(self, widget):
        """Desabilita COMPLETAMENTE todos os widgets de forma recursiva e agressiva"""
        try:
            # Desabilitar TODOS os tipos de widgets
            if hasattr(widget, 'config'):
                try:
                    if isinstance(widget, (tk.Entry, tk.Text, tk.Spinbox, ttk.Entry, ttk.Spinbox)):
                        widget.config(state='disabled')
                    elif isinstance(widget, ttk.Combobox):
                        # Permitir interação de leitura (seleção) para filtros/visualização
                        try:
                            widget.config(state='readonly')
                        except Exception:
                            pass
                    elif isinstance(widget, (tk.Checkbutton, tk.Radiobutton)):
                        widget.config(state='disabled')
                    elif isinstance(widget, tk.Listbox):
                        widget.config(state='disabled', selectmode='none')
                    elif isinstance(widget, ttk.Treeview):
                        # Manter seleção habilitada para permitir visualização de itens
                        try:
                            widget.config(selectmode='browse')
                        except Exception:
                            pass
                    elif isinstance(widget, (tk.Scale, ttk.Scale)):
                        widget.config(state='disabled')
                    elif isinstance(widget, (tk.Button, ttk.Button)):
                        # Desabilitar TODOS os botões exceto os de consulta
                        try:
                            button_text = widget.cget('text').lower()
                            allowed_buttons = ['buscar', 'pesquisar', 'filtrar', 'visualizar', 'ver', 'consultar', 'imprimir', 'exportar', 'pdf', 'voltar', 'anterior', 'próximo', 'primeiro', 'último', 'editar']
                            if not any(allowed in button_text for allowed in allowed_buttons):
                                widget.config(state='disabled')
                        except:
                            widget.config(state='disabled')
                except:
                    pass
            
            # Bloquear TODOS os bindings de eventos
            if hasattr(widget, 'bind'):
                try:
                    # Lista completa de eventos a serem bloqueados
                    events_to_block = [
                        '<Key>', '<Button-1>', '<Double-Button-1>', '<ButtonRelease-1>', '<B1-Motion>',
                        '<Return>', '<Tab>', '<Shift-Tab>', '<Control-a>', '<Control-c>', '<Control-v>',
                        '<Control-x>', '<Control-z>', '<Control-y>', '<Delete>', '<BackSpace>',
                        '<F2>', '<F5>', '<F9>', '<Button-3>', '<Button-2>', '<B2-Motion>',
                        '<ButtonRelease-2>', '<Shift-Button-1>', '<Control-Button-1>', '<Up>',
                        '<Down>', '<Left>', '<Right>', '<Home>', '<End>', '<Page_Up>',
                        '<Page_Down>', '<Insert>', '<Space>', '<Escape>', '<Alt-F4>',
                        '<Control-s>', '<Control-n>', '<Control-o>', '<Control-w>', '<Control-q>'
                    ]
                    
                    for event in events_to_block:
                        widget.unbind(event)
                        
                    # Bloquear também eventos globais
                    widget.bind('<Key>', lambda e: 'break')
                    widget.bind('<Button-1>', lambda e: 'break' if not self._is_allowed_widget(widget) else None)
                    widget.bind('<Double-Button-1>', lambda e: 'break')
                    widget.bind('<Return>', lambda e: 'break')
                    widget.bind('<Tab>', lambda e: 'break')
                    widget.bind('<Control-a>', lambda e: 'break')
                    widget.bind('<Control-c>', lambda e: 'break')
                    widget.bind('<Control-v>', lambda e: 'break')
                    widget.bind('<Control-x>', lambda e: 'break')
                    widget.bind('<Control-z>', lambda e: 'break')
                    widget.bind('<Control-y>', lambda e: 'break')
                    widget.bind('<Delete>', lambda e: 'break')
                    widget.bind('<BackSpace>', lambda e: 'break')
                    widget.bind('<F2>', lambda e: 'break')
                    widget.bind('<F5>', lambda e: 'break')
                    widget.bind('<F9>', lambda e: 'break')
                    widget.bind('<Button-3>', lambda e: 'break')  # Botão direito
                    widget.bind('<Button-2>', lambda e: 'break')  # Botão do meio
                    
                except:
                    pass
            
            # Processar filhos recursivamente
            for child in widget.winfo_children():
                self._disable_all_widgets_completely(child)
                
        except Exception as e:
            pass
    
    def _is_allowed_widget(self, widget):
        """Verifica se o widget é permitido para usuários somente leitura"""
        try:
            if isinstance(widget, (tk.Button, ttk.Button)):
                button_text = widget.cget('text').lower()
                allowed_buttons = ['buscar', 'pesquisar', 'filtrar', 'visualizar', 'ver', 'consultar', 'imprimir', 'exportar', 'pdf', 'voltar', 'anterior', 'próximo', 'primeiro', 'último', 'editar']
                return any(allowed in button_text for allowed in allowed_buttons)
            return False
        except:
            return False

    def _build_side_nav(self):
        """Cria botões verticais para navegar entre as abas do notebook."""
        try:
            self._nav_buttons = []
            for tab_id in self.notebook.tabs():
                text = self.notebook.tab(tab_id, option='text')
                btn = ttk.Button(
                    self.side_nav,
                    text=text,
                    style='Secondary.TButton',
                    command=lambda t=tab_id: self.notebook.select(t)
                )
                btn.pack(fill='x', padx=10, pady=6)
                self._nav_buttons.append((tab_id, btn))
            # Inicial: marcar selecionado
            self._on_tab_changed()
        except Exception as e:
            print(f"Aviso: falha ao construir navegação lateral: {e}")

    def _on_tab_changed(self, *_args):
        """Atualiza o estilo do botão ativo conforme a aba selecionada."""
        try:
            current = self.notebook.select()
            for tab_id, btn in getattr(self, '_nav_buttons', []):
                if tab_id == current:
                    btn.configure(style='Primary.TButton')
                else:
                    btn.configure(style='Secondary.TButton')
        except Exception:
            pass

    def _load_user_permissions(self):
        """Carrega as permissões do usuário corrente em self.user_permissions"""
        self.user_permissions = {}
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT modulo, nivel_acesso FROM permissoes_usuarios WHERE usuario_id = ?", (self.user_id,))
            self.user_permissions = dict(c.fetchall())
        except Exception as e:
            print(f"Aviso: falha ao carregar permissões: {e}")
            self.user_permissions = {}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def has_access(self, module_key: str) -> bool:
        """Retorna True se o usuário pode ver o módulo (ou se for admin)."""
        if self.has_role('admin'):
            return True
        level = (self.user_permissions or {}).get(module_key, 'sem_acesso')
        return level in ('consulta', 'controle_total')

    def can_edit(self, module_key: str) -> bool:
        """Retorna True se o usuário pode editar o módulo (ou se for admin)."""
        if self.has_role('admin'):
            return True
        level = (self.user_permissions or {}).get(module_key, 'sem_acesso')
        return level == 'controle_total'
        
    def logout(self):
        """Fazer logout e voltar para tela de login"""
        if messagebox.askyesno("Logout", "Tem certeza que deseja sair?"):
            self.root.withdraw()
            
            # Criar nova janela de login
            from interface.login import LoginWindow
            LoginWindow(self.root)