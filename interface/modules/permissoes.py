import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from .base_module import BaseModule
from database import DB_NAME

class PermissoesModule(BaseModule):
    def setup_ui(self):
        container = tk.Frame(self.frame, bg='#f8fafc')
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        self.create_header(container)
        
        # Frame principal
        main_frame = tk.Frame(container, bg='white', relief='solid', bd=1)
        main_frame.pack(fill="both", expand=True, pady=(20, 0))
        
        # Seleção de usuário
        self.create_user_selection(main_frame)
        
        # Grid de permissões
        self.create_permissions_grid(main_frame)
        
        # Botões
        self.create_buttons(main_frame)
        
        # Inicializar dados
        self.carregar_usuarios()
        
    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg='#f8fafc')
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = tk.Label(header_frame, text="Gerenciamento de Permissões", 
                               font=('Arial', 18, 'bold'), bg='#f8fafc', fg='#1e293b')
        title_label.pack(side="left")
        
        description_label = tk.Label(header_frame, 
                                    text="Configure as permissões de acesso por módulo para cada usuário",
                                    font=('Arial', 10), bg='#f8fafc', fg='#64748b')
        description_label.pack(side="left", padx=(20, 0))
        
    def create_user_selection(self, parent):
        user_frame = tk.Frame(parent, bg='white', padx=20, pady=15)
        user_frame.pack(fill="x")
        
        tk.Label(user_frame, text="Usuário:", font=('Arial', 12, 'bold'), 
                bg='white').pack(side="left")
        
        self.usuario_var = tk.StringVar()
        self.usuario_combo = ttk.Combobox(user_frame, textvariable=self.usuario_var, 
                                         width=40, state="readonly")
        self.usuario_combo.pack(side="left", padx=(10, 0))
        self.usuario_combo.bind("<<ComboboxSelected>>", self.on_usuario_changed)
        
    def create_permissions_grid(self, parent):
        # Frame com scrollbar
        canvas_frame = tk.Frame(parent, bg='white')
        canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg='white')
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg='white')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Título da grid
        title_frame = tk.Frame(self.scrollable_frame, bg='white')
        title_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(title_frame, text="Módulos do Sistema", font=('Arial', 14, 'bold'), 
                bg='white').pack()
        
        # Cabeçalho da grid
        header_frame = tk.Frame(self.scrollable_frame, bg='#f1f5f9', relief='solid', bd=1)
        header_frame.pack(fill="x", pady=(0, 5))
        
        tk.Label(header_frame, text="Módulo", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', width=25, anchor='w').grid(row=0, column=0, padx=10, pady=8, sticky='w')
        tk.Label(header_frame, text="Sem Acesso", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', width=15).grid(row=0, column=1, padx=5, pady=8)
        tk.Label(header_frame, text="Consulta", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', width=15).grid(row=0, column=2, padx=5, pady=8)
        tk.Label(header_frame, text="Controle Total", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', width=15).grid(row=0, column=3, padx=5, pady=8)
        
        # Módulos disponíveis
        self.modulos = [
            ("dashboard", "📊 Dashboard"),
            ("clientes", "👥 Clientes"),
            ("produtos", "📦 Cadastros"),
            ("orcamento_servicos", "🔧 Orçamento de Serviços"),
            ("orcamento_produtos", "📦 Orçamento de Produtos"),
            ("locacoes", "📄 Orçamento de Locações"),
            ("relatorios", "📋 Relatórios"),
            ("usuarios", "👤 Usuários"),
            ("permissoes", "🔐 Permissões")
        ]
        
        self.permission_vars = {}
        
        for i, (modulo_key, modulo_nome) in enumerate(self.modulos):
            row_frame = tk.Frame(self.scrollable_frame, bg='white', relief='solid', bd=1)
            row_frame.pack(fill="x", pady=1)
            
            # Nome do módulo
            tk.Label(row_frame, text=modulo_nome, font=('Arial', 10), 
                    bg='white', width=25, anchor='w').grid(row=0, column=0, padx=10, pady=8, sticky='w')
            
            # Radio buttons para permissões
            var = tk.StringVar(value="sem_acesso")
            self.permission_vars[modulo_key] = var
            
            tk.Radiobutton(row_frame, text="", variable=var, value="sem_acesso", 
                          bg='white', width=15).grid(row=0, column=1, padx=5, pady=5)
            tk.Radiobutton(row_frame, text="", variable=var, value="consulta", 
                          bg='white', width=15).grid(row=0, column=2, padx=5, pady=5)
            tk.Radiobutton(row_frame, text="", variable=var, value="controle_total", 
                          bg='white', width=15).grid(row=0, column=3, padx=5, pady=5)
        
    def create_buttons(self, parent):
        buttons_frame = tk.Frame(parent, bg='white', pady=15)
        buttons_frame.pack(fill="x", side="bottom")
        
        # Botão Salvar
        save_btn = self.create_button(buttons_frame, "💾 Salvar Permissões", 
                                     self.salvar_permissoes, bg='#10b981')
        save_btn.pack(side="left", padx=(20, 10))
        
        # Botão Limpar
        clear_btn = self.create_button(buttons_frame, "🗑️ Limpar Tudo", 
                                      self.limpar_permissoes, bg='#ef4444')
        clear_btn.pack(side="left", padx=10)
        
        # Botão Aplicar Template
        template_frame = tk.Frame(buttons_frame, bg='white')
        template_frame.pack(side="right", padx=20)
        
        tk.Label(template_frame, text="Template:", font=('Arial', 10), 
                bg='white').pack(side="left")
        
        template_btn1 = self.create_button(template_frame, "Operador Padrão", 
                                          lambda: self.aplicar_template('operador'), bg='#3b82f6')
        template_btn1.pack(side="left", padx=(5, 0))
        
        template_btn2 = self.create_button(template_frame, "Administrador", 
                                          lambda: self.aplicar_template('admin'), bg='#7c3aed')
        template_btn2.pack(side="left", padx=(5, 0))
        
    def carregar_usuarios(self):
        """Carregar lista de usuários"""
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            c.execute("SELECT id, username, nome_completo, role FROM usuarios ORDER BY nome_completo")
            usuarios = c.fetchall()
            
            usuarios_list = []
            self.usuarios_dict = {}
            
            for user_id, username, nome_completo, role in usuarios:
                display_name = f"{nome_completo} ({username}) - {role}"
                usuarios_list.append(display_name)
                self.usuarios_dict[display_name] = user_id
                
            self.usuario_combo['values'] = usuarios_list
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao carregar usuários: {e}")
        finally:
            conn.close()
            
    def on_usuario_changed(self, event=None):
        """Carregar permissões do usuário selecionado"""
        usuario_str = self.usuario_var.get()
        if not usuario_str:
            return
            
        usuario_id = self.usuarios_dict.get(usuario_str)
        if not usuario_id:
            return
            
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            # Buscar permissões existentes
            c.execute("SELECT modulo, nivel_acesso FROM permissoes_usuarios WHERE usuario_id = ?", 
                     (usuario_id,))
            permissoes = dict(c.fetchall())
            
            # Aplicar permissões aos controles
            for modulo_key in self.permission_vars:
                if modulo_key in permissoes:
                    self.permission_vars[modulo_key].set(permissoes[modulo_key])
                else:
                    self.permission_vars[modulo_key].set("sem_acesso")
                    
        except sqlite3.Error as e:
            self.show_error(f"Erro ao carregar permissões: {e}")
        finally:
            conn.close()
            
    def salvar_permissoes(self):
        """Salvar permissões do usuário"""
        if not self.can_edit('permissoes'):
            self.show_warning("Você não tem permissão para salvar permissões.")
            return
            
        usuario_str = self.usuario_var.get()
        if not usuario_str:
            self.show_warning("Selecione um usuário.")
            return
            
        usuario_id = self.usuarios_dict.get(usuario_str)
        if not usuario_id:
            self.show_warning("Usuário selecionado inválido.")
            return
            
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            # Remover permissões existentes
            c.execute("DELETE FROM permissoes_usuarios WHERE usuario_id = ?", (usuario_id,))
            
            # Inserir novas permissões
            for modulo_key, var in self.permission_vars.items():
                nivel_acesso = var.get()
                if nivel_acesso != "sem_acesso":
                    c.execute("""
                        INSERT INTO permissoes_usuarios (usuario_id, modulo, nivel_acesso)
                        VALUES (?, ?, ?)
                    """, (usuario_id, modulo_key, nivel_acesso))
            
            conn.commit()
            self.show_success("Permissões salvas com sucesso!")
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao salvar permissões: {e}")
        finally:
            conn.close()
            
    def limpar_permissoes(self):
        """Limpar todas as permissões"""
        if messagebox.askyesno("Confirmar", "Deseja remover todas as permissões do usuário selecionado?"):
            for var in self.permission_vars.values():
                var.set("sem_acesso")
                
    def aplicar_template(self, template_type):
        """Aplicar template de permissões"""
        if template_type == 'operador':
            # Operador padrão: consulta em todos, controle total em orçamentos
            permissoes_template = {
                'dashboard': 'consulta',
                'clientes': 'consulta',
                'produtos': 'consulta', 
                'orcamento_servicos': 'controle_total',
                'orcamento_produtos': 'controle_total',
                'locacoes': 'controle_total',
                'relatorios': 'controle_total',
                'usuarios': 'sem_acesso',
                'permissoes': 'sem_acesso'
            }
        elif template_type == 'admin':
            # Administrador: controle total em tudo
            permissoes_template = {
                'dashboard': 'controle_total',
                'clientes': 'controle_total',
                'produtos': 'controle_total',
                'orcamento_servicos': 'controle_total', 
                'orcamento_produtos': 'controle_total',
                'locacoes': 'controle_total',
                'relatorios': 'controle_total',
                'usuarios': 'controle_total',
                'permissoes': 'controle_total'
            }
        else:
            return
            
        # Aplicar template
        for modulo, nivel in permissoes_template.items():
            if modulo in self.permission_vars:
                self.permission_vars[modulo].set(nivel)
                
        self.show_success(f"Template '{template_type}' aplicado com sucesso!")

    def get_user_permissions(self, user_id):
        """Obter permissões de um usuário específico"""
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            c.execute("SELECT modulo, nivel_acesso FROM permissoes_usuarios WHERE usuario_id = ?", 
                     (user_id,))
            return dict(c.fetchall())
            
        except sqlite3.Error:
            return {}
        finally:
            conn.close()
            
    def user_has_permission(self, user_id, module, required_level='consulta'):
        """Verificar se usuário tem permissão específica"""
        permissions = self.get_user_permissions(user_id)
        user_level = permissions.get(module, 'sem_acesso')
        
        if required_level == 'consulta':
            return user_level in ['consulta', 'controle_total']
        elif required_level == 'controle_total':
            return user_level == 'controle_total'
            
        return False

    def handle_event(self, event_type, data=None):
        """Atualizações reativas para a aba de permissões"""
        if event_type == 'usuario_created':
            try:
                self.carregar_usuarios()
                print("DEBUG: Permissões - lista de usuários atualizada após criação de usuário")
            except Exception as e:
                print(f"Aviso: falha ao atualizar usuários nas permissões: {e}")