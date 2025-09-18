import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from .base_module import BaseModule
from database import DB_NAME
from utils.formatters import format_cnpj, format_phone, validate_cnpj, validate_email

class ClientesModule(BaseModule):
    def setup_ui(self):
        # Inicializar variáveis primeiro
        self.current_cliente_id = None
        self.contatos_data = []
        
        # Container principal - usando toda a tela
        container = tk.Frame(self.frame, bg='#f8fafc')
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        self.create_header(container)

        # Layout principal em 2 colunas: esquerda (formulário) e direita (lista)
        main_frame = tk.Frame(container, bg='#f8fafc')
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1, uniform="cols")
        main_frame.grid_columnconfigure(1, weight=1, uniform="cols")
        main_frame.grid_rowconfigure(0, weight=1)

        # Painel de dados do cliente (esquerda)
        form_panel = tk.Frame(main_frame, bg='#f8fafc')
        form_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=(10, 10))
        form_panel.grid_columnconfigure(0, weight=1)

        # Reservar rodapé com botões do cliente ANTES de adicionar os cards
        self.create_cliente_buttons(form_panel)

        # Área rolável para os cards do formulário
        scroll_container = tk.Frame(form_panel, bg='#f8fafc')
        scroll_container.pack(side="top", fill="both", expand=True)

        form_canvas = tk.Canvas(scroll_container, bg='#f8fafc', highlightthickness=0)
        form_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=form_canvas.yview)
        form_canvas.configure(yscrollcommand=form_scrollbar.set)

        form_scrollbar.pack(side="right", fill="y")
        form_canvas.pack(side="left", fill="both", expand=True)

        form_inner = tk.Frame(form_canvas, bg='#f8fafc')
        form_window = form_canvas.create_window((0, 0), window=form_inner, anchor="nw")

        def _on_inner_configure(event):
            form_canvas.configure(scrollregion=form_canvas.bbox("all"))
        form_inner.bind("<Configure>", _on_inner_configure)

        def _on_canvas_configure(event):
            form_canvas.itemconfigure(form_window, width=event.width)
        form_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            delta = 0
            if hasattr(event, 'delta') and event.delta:
                delta = int(-event.delta / 120)
            elif getattr(event, 'num', None) in (4, 5):
                delta = -1 if event.num == 5 else 1
            if delta:
                form_canvas.yview_scroll(delta, "units")

        def _bind_mousewheel(_):
            form_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            form_canvas.bind_all("<Button-4>", _on_mousewheel)
            form_canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(_):
            form_canvas.unbind_all("<MouseWheel>")
            form_canvas.unbind_all("<Button-4>")
            form_canvas.unbind_all("<Button-5>")

        form_canvas.bind("<Enter>", _bind_mousewheel)
        form_canvas.bind("<Leave>", _unbind_mousewheel)

        # Cards/seções do formulário
        card1 = tk.Frame(form_inner, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card1.pack(fill="x", pady=(0, 8))
        tk.Label(card1, text="🧑‍💼 Dados Básicos", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_dados_basicos_section(card1)

        card2 = tk.Frame(form_inner, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card2.pack(fill="x", pady=(0, 8))
        tk.Label(card2, text="🏠 Endereço", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_endereco_section(card2)

        card3 = tk.Frame(form_inner, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card3.pack(fill="x", pady=(0, 8))
        tk.Label(card3, text="💼 Informações Comerciais", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_comercial_section(card3)

        card4 = tk.Frame(form_inner, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card4.pack(fill="x", pady=(0, 8))
        tk.Label(card4, text="⏳ Prazo de Pagamento", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_prazo_pagamento_section(card4)

        card5 = tk.Frame(form_inner, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card5.pack(fill="both", expand=True)
        tk.Label(card5, text="📇 Contatos do Cliente", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_contatos_integrados_section(card5)

        # Botões já reservados no rodapé

        # Painel da lista (direita)
        lista_panel = tk.Frame(main_frame, bg='#f8fafc')
        lista_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 10), pady=(10, 10))
        lista_panel.grid_columnconfigure(0, weight=1)
        lista_panel.grid_rowconfigure(2, weight=1)

        lista_card = tk.Frame(lista_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
        lista_card.pack(fill="both", expand=True)

        tk.Label(lista_card, text="📋 Lista de Clientes", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(fill="x", padx=12, pady=(12, 8))

        lista_inner = tk.Frame(lista_card, bg='white')
        lista_inner.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        search_frame, self.search_var = self.create_search_frame(lista_inner, placeholder="Buscar clientes...", command=self.buscar_clientes)
        search_frame.pack(fill="x", pady=(0, 10))

        # Reservar rodapé dos botões da lista ANTES de empacotar a Treeview
        lista_buttons = tk.Frame(lista_inner, bg='white')
        lista_buttons.pack(side="bottom", fill="x", pady=(10, 0))

        columns = ("nome", "cnpj", "cidade", "telefone", "email")
        self.clientes_tree = ttk.Treeview(lista_inner, columns=columns, show="headings")

        self.clientes_tree.heading("nome", text="Nome/Razão Social")
        self.clientes_tree.heading("cnpj", text="CNPJ")
        self.clientes_tree.heading("cidade", text="Cidade")
        self.clientes_tree.heading("telefone", text="Telefone")
        self.clientes_tree.heading("email", text="Email")

        self.clientes_tree.column("nome", width=280)
        self.clientes_tree.column("cnpj", width=160)
        self.clientes_tree.column("cidade", width=140)
        self.clientes_tree.column("telefone", width=140)
        self.clientes_tree.column("email", width=220)

        lista_scrollbar = ttk.Scrollbar(lista_inner, orient="vertical", command=self.clientes_tree.yview)
        self.clientes_tree.configure(yscrollcommand=lista_scrollbar.set)

        self.clientes_tree.pack(side="left", fill="both", expand=True)
        lista_scrollbar.pack(side="right", fill="y")
        
        # Adicionar evento de duplo clique para visualização/edição
        self.clientes_tree.bind("<Double-1>", self.on_cliente_double_click)

        # Botões da lista (fixos ao rodapé)
        # (Já reservado no topo deste bloco)

        # Botões da lista (fixos ao rodapé)
        editar_btn = self.create_button(lista_buttons, "Editar", self.editar_cliente)
        editar_btn.pack(side="left", padx=(0, 10))

        excluir_btn = self.create_button(lista_buttons, "Excluir", self.excluir_cliente, bg='#dc2626')
        excluir_btn.pack(side="left")

        # Carregar dados
        self.carregar_clientes()
        
    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg='#f8fafc')
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = tk.Label(header_frame, text="Gestão de Clientes", 
                               font=('Arial', 16, 'bold'),
                               bg='#f8fafc',
                               fg='#1e293b')
        title_label.pack(side="left")
        
    # Layout antigo baseado em abas removido; agora a tela usa um layout único com formulário e lista lado a lado
        
    # Layout antigo de conteúdo removido; consolidado no novo setup_ui
    def create_cliente_content(self, parent):
        import tkinter.font as tkfont
        try:
            import matplotlib
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            has_matplotlib = True
        except ImportError:
            has_matplotlib = False

        # Frame principal com grid 2 colunas, 1 linha, ambas expandem
        main_frame = tk.Frame(parent, bg='#f5f6fa')
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1, uniform="col")
        main_frame.grid_columnconfigure(1, weight=1, uniform="col")
        main_frame.grid_rowconfigure(0, weight=1)

        # Painel de dados (esquerda)
        data_panel = tk.Frame(main_frame, bg='#f5f6fa')
        data_panel.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        data_panel.grid_rowconfigure((0,1,2,3,4), weight=1)
        data_panel.grid_columnconfigure(0, weight=1)

        # Card: Dados Básicos
        card1 = tk.Frame(data_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card1.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(card1, text="🧑‍💼 Dados Básicos", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_dados_basicos_section(card1)

        # Card: Endereço
        card2 = tk.Frame(data_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card2.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        tk.Label(card2, text="🏠 Endereço", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_endereco_section(card2)

        # Card: Informações Comerciais
        card3 = tk.Frame(data_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card3.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        tk.Label(card3, text="💼 Informações Comerciais", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_comercial_section(card3)

        # Card: Prazo de Pagamento
        card4 = tk.Frame(data_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card4.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        tk.Label(card4, text="⏳ Prazo de Pagamento", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_prazo_pagamento_section(card4)

        # Card: Contatos do Cliente
        card5 = tk.Frame(data_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
        card5.grid(row=4, column=0, sticky="nsew", pady=(0, 0))
        tk.Label(card5, text="📇 Contatos do Cliente", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(anchor="w", padx=12, pady=(8, 0))
        self.create_contatos_integrados_section(card5)

        # Painel da Lista de Clientes (direita)
        lista_panel = tk.Frame(main_frame, bg='#f5f6fa')
        lista_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        lista_panel.grid_rowconfigure(2, weight=1)
        lista_panel.grid_columnconfigure(0, weight=1)

        # Card principal
        lista_card = tk.Frame(lista_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
        lista_card.pack(fill="both", expand=True)

        # Título
        tk.Label(lista_card, text="📋 Lista de Clientes", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(fill="x", padx=12, pady=(12, 8))

        # Container interno
        lista_inner = tk.Frame(lista_card, bg='white')
        lista_inner.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Frame de busca
        search_frame, self.search_var = self.create_search_frame(lista_inner, placeholder="Buscar clientes...", command=self.buscar_clientes)
        search_frame.pack(fill="x", pady=(0, 10))

        # Treeview de clientes
        columns = ("nome", "cnpj", "cidade", "telefone", "email")
        self.clientes_tree = ttk.Treeview(lista_inner, columns=columns, show="headings", height=18)

        # Cabeçalhos
        self.clientes_tree.heading("nome", text="Nome/Razão Social")
        self.clientes_tree.heading("cnpj", text="CNPJ")
        self.clientes_tree.heading("cidade", text="Cidade")
        self.clientes_tree.heading("telefone", text="Telefone")
        self.clientes_tree.heading("email", text="Email")

        # Larguras
        self.clientes_tree.column("nome", width=250)
        self.clientes_tree.column("cnpj", width=150)
        self.clientes_tree.column("cidade", width=120)
        self.clientes_tree.column("telefone", width=120)
        self.clientes_tree.column("email", width=200)

        # Scrollbar
        lista_scrollbar = ttk.Scrollbar(lista_inner, orient="vertical", command=self.clientes_tree.yview)
        self.clientes_tree.configure(yscrollcommand=lista_scrollbar.set)

        # Layout
        self.clientes_tree.pack(side="left", fill="both", expand=True)
        lista_scrollbar.pack(side="right", fill="y")

        # Botões da lista (fixos ao rodapé)
        # (Já reservado no topo deste bloco)

        # Botões da lista (fixos ao rodapé)
        editar_btn = self.create_button(lista_buttons, "Editar", self.editar_cliente)
        editar_btn.pack(side="left", padx=(0, 10))

        excluir_btn = self.create_button(lista_buttons, "Excluir", self.excluir_cliente, bg='#dc2626')
        excluir_btn.pack(side="left")

        # Botões de ação no topo
        self.create_cliente_buttons(parent)

    def create_dados_basicos_section(self, parent):
        section_frame = self.create_section_frame(parent, "Dados Básicos")
        section_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        # Grid de campos
        fields_frame = tk.Frame(section_frame, bg='white')
        fields_frame.pack(fill="both", expand=True)
        
        # Configurar grid para usar todo o espaço
        fields_frame.grid_columnconfigure(1, weight=1)
        fields_frame.grid_columnconfigure(3, weight=1)
        
        # Variáveis
        self.nome_var = tk.StringVar()
        self.nome_fantasia_var = tk.StringVar()
        self.cnpj_var = tk.StringVar()
        self.inscricao_estadual_var = tk.StringVar()
        self.inscricao_municipal_var = tk.StringVar()
        
        row = 0
        
        # Nome
        tk.Label(fields_frame, text="Nome/Razão Social *:", 
                 font=('Arial', 9, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=3)
        tk.Entry(fields_frame, textvariable=self.nome_var, 
                 font=('Arial', 9), width=50).grid(row=row, column=1, columnspan=3, sticky="ew", padx=(10, 0), pady=3)
        row += 1
        
        # Nome Fantasia
        tk.Label(fields_frame, text="Nome Fantasia:", 
                 font=('Arial', 9, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=3)
        tk.Entry(fields_frame, textvariable=self.nome_fantasia_var, 
                 font=('Arial', 9), width=50).grid(row=row, column=1, columnspan=3, sticky="ew", padx=(10, 0), pady=3)
        row += 1
        
        # CNPJ
        tk.Label(fields_frame, text="CNPJ:", 
                 font=('Arial', 9, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=3)
        cnpj_entry = tk.Entry(fields_frame, textvariable=self.cnpj_var, 
                              font=('Arial', 9), width=20)
        cnpj_entry.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)
        cnpj_entry.bind('<FocusOut>', self.format_cnpj)
        
        # Inscrição Estadual
        tk.Label(fields_frame, text="Inscrição Estadual:", 
                 font=('Arial', 9, 'bold'), bg='white').grid(row=row, column=2, sticky="w", pady=3, padx=(20, 0))
        tk.Entry(fields_frame, textvariable=self.inscricao_estadual_var, 
                 font=('Arial', 9), width=20).grid(row=row, column=3, sticky="ew", padx=(10, 0), pady=3)
        row += 1
        
        # Inscrição Municipal
        tk.Label(fields_frame, text="Inscrição Municipal:", 
                 font=('Arial', 9, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=3)
        tk.Entry(fields_frame, textvariable=self.inscricao_municipal_var, 
                 font=('Arial', 9), width=20).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)
        
        # Configurar colunas
        fields_frame.grid_columnconfigure(3, weight=1)
        
    def create_prazo_pagamento_section(self, parent):
        """Criar seção para prazo de pagamento"""
        section_frame = self.create_section_frame(parent, "Prazo de Pagamento")
        section_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        # Grid de campos
        fields_frame = tk.Frame(section_frame, bg='white')
        fields_frame.pack(fill="x")
        
        # Variáveis
        self.prazo_pagamento_var = tk.StringVar()
        
        row = 0
        
        # Prazo de Pagamento
        tk.Label(fields_frame, text="Prazo de Pagamento:", 
                 font=('Arial', 9, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=3)
        prazo_combo = ttk.Combobox(fields_frame, textvariable=self.prazo_pagamento_var, 
                                  values=["À vista", "15 dias", "30 dias", "45 dias", "60 dias", "90 dias"], 
                                  width=15)
        prazo_combo.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)
        
        fields_frame.grid_columnconfigure(1, weight=1)
        
    def create_endereco_section(self, parent):
        section_frame = self.create_section_frame(parent, "Endereço")
        section_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        fields_frame = tk.Frame(section_frame, bg='white')
        fields_frame.pack(fill="x")
        
        # Variáveis
        self.cep_var = tk.StringVar()
        self.endereco_var = tk.StringVar()
        self.numero_var = tk.StringVar()
        self.complemento_var = tk.StringVar()
        self.bairro_var = tk.StringVar()
        self.cidade_var = tk.StringVar()
        self.estado_var = tk.StringVar()
        
        row = 0
        
        # CEP
        tk.Label(fields_frame, text="CEP:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        cep_entry = tk.Entry(fields_frame, textvariable=self.cep_var, 
                             font=('Arial', 10), width=15)
        cep_entry.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=5)
        cep_entry.bind('<FocusOut>', self.buscar_cep)
        
        row += 1
        
        # Endereço
        tk.Label(fields_frame, text="Endereço:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.endereco_var, 
                 font=('Arial', 10), width=40).grid(row=row, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=5)
        
        # Número
        tk.Label(fields_frame, text="Número:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=3, sticky="w", pady=5, padx=(20, 0))
        tk.Entry(fields_frame, textvariable=self.numero_var, 
                 font=('Arial', 10), width=10).grid(row=row, column=4, sticky="w", padx=(10, 0), pady=5)
        row += 1
        
        # Complemento
        tk.Label(fields_frame, text="Complemento:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.complemento_var, 
                 font=('Arial', 10), width=25).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        
        # Bairro
        tk.Label(fields_frame, text="Bairro:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=2, sticky="w", pady=5, padx=(20, 0))
        tk.Entry(fields_frame, textvariable=self.bairro_var, 
                 font=('Arial', 10), width=20).grid(row=row, column=3, columnspan=2, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Cidade
        tk.Label(fields_frame, text="Cidade:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.cidade_var, 
                 font=('Arial', 10), width=25).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        
        # Estado
        tk.Label(fields_frame, text="Estado:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=2, sticky="w", pady=5, padx=(20, 0))
        estado_combo = ttk.Combobox(fields_frame, textvariable=self.estado_var,
                                   values=["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", 
                                          "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", 
                                          "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"],
                                   width=5)
        estado_combo.grid(row=row, column=3, sticky="w", padx=(10, 0), pady=5)
        
        # Configurar colunas
        fields_frame.grid_columnconfigure(1, weight=1)
        fields_frame.grid_columnconfigure(3, weight=1)
        
    def create_comercial_section(self, parent):
        section_frame = self.create_section_frame(parent, "Informações Comerciais")
        section_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        fields_frame = tk.Frame(section_frame, bg='white')
        fields_frame.pack(fill="x")
        
        # Variáveis
        self.telefone_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.site_var = tk.StringVar()
        
        row = 0
        
        # Telefone
        tk.Label(fields_frame, text="Telefone Principal:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        telefone_entry = tk.Entry(fields_frame, textvariable=self.telefone_var, 
                                  font=('Arial', 10), width=20)
        telefone_entry.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=5)
        telefone_entry.bind('<FocusOut>', self.format_telefone)
        
        # Email
        tk.Label(fields_frame, text="Email Principal:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=2, sticky="w", pady=5, padx=(20, 0))
        tk.Entry(fields_frame, textvariable=self.email_var, 
                 font=('Arial', 10), width=25).grid(row=row, column=3, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Site
        tk.Label(fields_frame, text="Site:", 
                 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.site_var, 
                 font=('Arial', 10), width=30).grid(row=row, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=5)
        
        # Configurar colunas
        fields_frame.grid_columnconfigure(3, weight=1)
        

    def create_cliente_dashboard(self, parent):
        """Criar dashboard com informações úteis do cliente"""
        # Frame do dashboard
        dashboard_frame = tk.Frame(parent, bg='white', relief='solid', bd=1)
        dashboard_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = tk.Label(dashboard_frame, text="📊 Dashboard do Cliente", 
                               font=('Arial', 12, 'bold'), bg='#f8fafc', fg='#1e293b')
        title_label.pack(fill="x", pady=(10, 15))
        
        # Container para cards
        cards_container = tk.Frame(dashboard_frame, bg='white')
        cards_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Card 1 - Estatísticas
        stats_card = tk.Frame(cards_container, bg='#f1f5f9', relief='solid', bd=1)
        stats_card.pack(fill="x", pady=(0, 10))
        
        tk.Label(stats_card, text="📈 Estatísticas", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', fg='#475569').pack(anchor="w", padx=10, pady=(10, 5))
        
        self.stats_text = tk.Text(stats_card, height=6, width=30, font=('Arial', 9),
                                 bg='white', relief='solid', bd=1, wrap=tk.WORD)
        self.stats_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Card 2 - Histórico
        history_card = tk.Frame(cards_container, bg='#f1f5f9', relief='solid', bd=1)
        history_card.pack(fill="both", expand=True)
        
        tk.Label(history_card, text="🕒 Histórico Recente", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', fg='#475569').pack(anchor="w", padx=10, pady=(10, 5))
        
        self.history_text = tk.Text(history_card, height=8, width=30, font=('Arial', 9),
                                   bg='white', relief='solid', bd=1, wrap=tk.WORD)
        self.history_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Inicializar dados do dashboard
        self.update_cliente_dashboard()
        
    def create_cliente_dashboard_expandido(self, parent):
        """Criar dashboard expandido com mais informações úteis"""
        # Frame do dashboard
        dashboard_frame = tk.Frame(parent, bg='white', relief='solid', bd=1)
        dashboard_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = tk.Label(dashboard_frame, text="📊 Dashboard Completo do Cliente", 
                               font=('Arial', 12, 'bold'), bg='#f8fafc', fg='#1e293b')
        title_label.pack(fill="x", pady=(8, 12))
        
        # Container para cards com scroll
        canvas = tk.Canvas(dashboard_frame, bg='white')
        scrollbar = ttk.Scrollbar(dashboard_frame, orient="vertical", command=canvas.yview)
        cards_container = tk.Frame(canvas, bg='white')
        
        cards_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=cards_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=(0, 5))
        scrollbar.pack(side="right", fill="y")
        
        # Card 1 - Estatísticas Detalhadas
        stats_card = tk.Frame(cards_container, bg='#f1f5f9', relief='solid', bd=1)
        stats_card.pack(fill="x", pady=(0, 8))
        
        tk.Label(stats_card, text="📈 Estatísticas Detalhadas", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', fg='#475569').pack(anchor="w", padx=8, pady=(8, 4))
        
        self.stats_detalhadas_text = tk.Text(stats_card, height=8, width=35, font=('Arial', 9),
                                            bg='white', relief='solid', bd=1, wrap=tk.WORD)
        self.stats_detalhadas_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Card 2 - Histórico Completo
        history_card = tk.Frame(cards_container, bg='#f1f5f9', relief='solid', bd=1)
        history_card.pack(fill="x", pady=(0, 8))
        
        tk.Label(history_card, text="🕒 Histórico Completo", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', fg='#475569').pack(anchor="w", padx=8, pady=(8, 4))
        
        self.history_completo_text = tk.Text(history_card, height=10, width=35, font=('Arial', 9),
                                            bg='white', relief='solid', bd=1, wrap=tk.WORD)
        self.history_completo_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Card 3 - Análise Financeira
        finance_card = tk.Frame(cards_container, bg='#f1f5f9', relief='solid', bd=1)
        finance_card.pack(fill="x", pady=(0, 8))
        
        tk.Label(finance_card, text="💰 Análise Financeira", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', fg='#475569').pack(anchor="w", padx=8, pady=(8, 4))
        
        self.finance_text = tk.Text(finance_card, height=6, width=35, font=('Arial', 9),
                                   bg='white', relief='solid', bd=1, wrap=tk.WORD)
        self.finance_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Card 4 - Produtos Mais Vendidos
        produtos_card = tk.Frame(cards_container, bg='#f1f5f9', relief='solid', bd=1)
        produtos_card.pack(fill="x", pady=(0, 8))
        
        tk.Label(produtos_card, text="📦 Produtos Mais Vendidos", font=('Arial', 10, 'bold'), 
                bg='#f1f5f9', fg='#475569').pack(anchor="w", padx=8, pady=(8, 4))
        
        self.produtos_text = tk.Text(produtos_card, height=6, width=35, font=('Arial', 9),
                                    bg='white', relief='solid', bd=1, wrap=tk.WORD)
        self.produtos_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Inicializar dados do dashboard expandido
        self.update_cliente_dashboard_expandido()
        
    def update_cliente_dashboard_expandido(self):
        """Atualizar dados do dashboard expandido"""
        if not hasattr(self, 'stats_detalhadas_text'):
            return
            
        # Limpar textos
        self.stats_detalhadas_text.delete('1.0', tk.END)
        self.history_completo_text.delete('1.0', tk.END)
        self.finance_text.delete('1.0', tk.END)
        self.produtos_text.delete('1.0', tk.END)
        
        if self.current_cliente_id:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            try:
                # Estatísticas detalhadas
                c.execute("SELECT COUNT(*) FROM cotacoes WHERE cliente_id = ?", (self.current_cliente_id,))
                total_cotacoes = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM cotacoes WHERE cliente_id = ? AND status = 'Aprovada'", (self.current_cliente_id,))
                cotacoes_aprovadas = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM cotacoes WHERE cliente_id = ? AND status = 'Rejeitada'", (self.current_cliente_id,))
                cotacoes_rejeitadas = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM cotacoes WHERE cliente_id = ? AND status = 'Em Aberto'", (self.current_cliente_id,))
                cotacoes_aberto = c.fetchone()[0]
                
                c.execute("SELECT SUM(valor_total) FROM cotacoes WHERE cliente_id = ? AND status = 'Aprovada'", (self.current_cliente_id,))
                faturamento = c.fetchone()[0] or 0
                
                c.execute("SELECT AVG(valor_total) FROM cotacoes WHERE cliente_id = ? AND valor_total > 0", (self.current_cliente_id,))
                media_valor = c.fetchone()[0] or 0
                
                # Tratar valores None
                faturamento = faturamento or 0
                media_valor = media_valor or 0
                
                c.execute("SELECT COUNT(*) FROM contatos WHERE cliente_id = ?", (self.current_cliente_id,))
                total_contatos = c.fetchone()[0]
                
                # Taxa de conversão
                taxa_conversao = (cotacoes_aprovadas / total_cotacoes * 100) if total_cotacoes > 0 else 0
                
                stats_info = f"""Total de Cotações: {total_cotacoes}
Aprovadas: {cotacoes_aprovadas} ({taxa_conversao:.1f}%)
Rejeitadas: {cotacoes_rejeitadas}
Em Aberto: {cotacoes_aberto}
Faturamento Total: R$ {faturamento:,.2f}
Média por Cotação: R$ {media_valor:,.2f}
Contatos Cadastrados: {total_contatos}"""
                
                self.stats_detalhadas_text.insert('1.0', stats_info)
                
                # Histórico completo
                c.execute("""
                    SELECT numero_proposta, data_criacao, status, valor_total, 
                           responsavel_id, data_validade
                    FROM cotacoes 
                    WHERE cliente_id = ? 
                    ORDER BY data_criacao DESC 
                    LIMIT 10
                """, (self.current_cliente_id,))
                
                historico = c.fetchall()
                if historico:
                    history_info = ""
                    for cotacao in historico:
                        numero, data, status, valor, resp_id, validade = cotacao
                        
                        # Buscar nome do responsável
                        c.execute("SELECT nome_completo FROM usuarios WHERE id = ?", (resp_id,))
                        resp_nome = c.fetchone()
                        resp_nome = resp_nome[0] if resp_nome else "N/A"
                        
                        valor = valor or 0  # Tratar valor None
                        history_info += f"📋 {numero}\n"
                        history_info += f"   Data: {data}\n"
                        history_info += f"   Status: {status}\n"
                        history_info += f"   Valor: R$ {valor:,.2f}\n"
                        history_info += f"   Responsável: {resp_nome}\n"
                        history_info += f"   Validade: {validade}\n\n"
                else:
                    history_info = "Nenhuma cotação encontrada."
                
                self.history_completo_text.insert('1.0', history_info)
                
                # Análise financeira
                c.execute("""
                    SELECT 
                        SUM(CASE WHEN status = 'Aprovada' THEN valor_total ELSE 0 END) as aprovado,
                        SUM(CASE WHEN status = 'Em Aberto' THEN valor_total ELSE 0 END) as em_aberto,
                        SUM(CASE WHEN status = 'Rejeitada' THEN valor_total ELSE 0 END) as rejeitado
                    FROM cotacoes 
                    WHERE cliente_id = ?
                """, (self.current_cliente_id,))
                
                finance_data = c.fetchone()
                if finance_data:
                    aprovado, em_aberto, rejeitado = finance_data
                    aprovado = aprovado or 0
                    em_aberto = em_aberto or 0
                    rejeitado = rejeitado or 0
                    
                    # Garantir que são números
                    aprovado = float(aprovado) if aprovado is not None else 0
                    em_aberto = float(em_aberto) if em_aberto is not None else 0
                    rejeitado = float(rejeitado) if rejeitado is not None else 0
                    
                    finance_info = f"""Valor Aprovado: R$ {aprovado:,.2f}
Valor em Aberto: R$ {em_aberto:,.2f}
Valor Rejeitado: R$ {rejeitado:,.2f}
Total Movimentado: R$ {aprovado + em_aberto + rejeitado:,.2f}

Potencial de Faturamento:
- Em Aberto: R$ {em_aberto:,.2f}"""
                    
                    self.finance_text.insert('1.0', finance_info)
                
                # Produtos mais vendidos
                c.execute("""
                    SELECT ic.item_nome, COUNT(*) as quantidade, SUM(ic.valor_total_item) as valor_total
                    FROM itens_cotacao ic
                    JOIN cotacoes c ON ic.cotacao_id = c.id
                    WHERE c.cliente_id = ? AND c.status = 'Aprovada'
                    GROUP BY ic.item_nome
                    ORDER BY quantidade DESC, valor_total DESC
                    LIMIT 5
                """, (self.current_cliente_id,))
                
                produtos = c.fetchall()
                if produtos:
                    produtos_info = ""
                    for produto in produtos:
                        nome, qtd, valor = produto
                        produtos_info += f"📦 {nome}\n"
                        produtos_info += f"   Qtd: {qtd}\n"
                        produtos_info += f"   Valor: R$ {valor:,.2f}\n\n"
                else:
                    produtos_info = "Nenhum produto vendido ainda."
                
                self.produtos_text.insert('1.0', produtos_info)
                
            except sqlite3.Error as e:
                self.stats_detalhadas_text.insert('1.0', f"Erro ao carregar dados: {e}")
            finally:
                conn.close()
        else:
            self.stats_detalhadas_text.insert('1.0', "Selecione um cliente para ver as estatísticas.")
            self.history_completo_text.insert('1.0', "Selecione um cliente para ver o histórico.")
            self.finance_text.insert('1.0', "Selecione um cliente para ver a análise financeira.")
            self.produtos_text.insert('1.0', "Selecione um cliente para ver os produtos.")
        
    def update_cliente_dashboard(self):
        """Atualizar dados do dashboard"""
        if not hasattr(self, 'stats_text') or not hasattr(self, 'history_text'):
            return
            
        # Limpar textos
        self.stats_text.delete('1.0', tk.END)
        self.history_text.delete('1.0', tk.END)
        
        if self.current_cliente_id:
            # Buscar estatísticas do cliente
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            try:
                # Estatísticas
                c.execute("SELECT COUNT(*) FROM cotacoes WHERE cliente_id = ?", (self.current_cliente_id,))
                total_cotacoes = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM cotacoes WHERE cliente_id = ? AND status = 'Aprovada'", (self.current_cliente_id,))
                cotacoes_aprovadas = c.fetchone()[0]
                
                c.execute("SELECT SUM(valor_total) FROM cotacoes WHERE cliente_id = ? AND status = 'Aprovada'", (self.current_cliente_id,))
                faturamento = c.fetchone()[0] or 0
                
                c.execute("SELECT COUNT(*) FROM contatos WHERE cliente_id = ?", (self.current_cliente_id,))
                total_contatos = c.fetchone()[0]
                
                # Atualizar estatísticas
                stats_info = f"""Total de Cotações: {total_cotacoes}
Cotações Aprovadas: {cotacoes_aprovadas}
Faturamento Total: R$ {faturamento:,.2f}
Contatos Cadastrados: {total_contatos}"""
                
                self.stats_text.insert('1.0', stats_info)
                
                # Histórico recente
                c.execute("""
                    SELECT numero_proposta, data_criacao, status, valor_total 
                    FROM cotacoes 
                    WHERE cliente_id = ? 
                    ORDER BY data_criacao DESC 
                    LIMIT 5
                """, (self.current_cliente_id,))
                
                historico = c.fetchall()
                if historico:
                    history_info = ""
                    for cotacao in historico:
                        numero, data, status, valor = cotacao
                        history_info += f"📋 {numero}\n"
                        history_info += f"   Data: {data}\n"
                        history_info += f"   Status: {status}\n"
                        history_info += f"   Valor: R$ {valor:,.2f}\n\n"
                else:
                    history_info = "Nenhuma cotação encontrada."
                
                self.history_text.insert('1.0', history_info)
                
            except sqlite3.Error as e:
                self.stats_text.insert('1.0', f"Erro ao carregar dados: {e}")
                self.history_text.insert('1.0', "Erro ao carregar histórico.")
            finally:
                conn.close()
        else:
            self.stats_text.insert('1.0', "Selecione um cliente para ver as estatísticas.")
            self.history_text.insert('1.0', "Selecione um cliente para ver o histórico.")
        
    def create_contatos_integrados_section(self, parent):
        """Seção de contatos integrada na aba de dados do cliente"""
        section_frame = self.create_section_frame(parent, "Contatos do Cliente")
        section_frame.pack(fill="both", expand=True, pady=(5, 0))

        # Container principal (apenas 1 coluna, sem dashboard)
        contatos_container = tk.Frame(section_frame, bg='white')
        contatos_container.pack(fill="both", expand=True)

        # Frame para adicionar contato
        add_contato_frame = tk.Frame(contatos_container, bg='white')
        add_contato_frame.pack(fill="x", pady=(0, 10))

        # Variáveis do contato (se não existirem ainda)
        if not hasattr(self, 'contato_nome_var'):
            self.contato_nome_var = tk.StringVar()
            self.contato_cargo_var = tk.StringVar()
            self.contato_telefone_var = tk.StringVar()
            self.contato_email_var = tk.StringVar()
            self.contato_observacoes_var = tk.StringVar()

        # Campos para novo contato
        fields_frame = tk.Frame(add_contato_frame, bg='white')
        fields_frame.pack(fill="x")

        row = 0
        # Nome e Cargo na primeira linha
        tk.Label(fields_frame, text="Nome:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.contato_nome_var, font=('Arial', 10), width=25).grid(row=row, column=1, sticky="ew", padx=(5, 10), pady=5)

        tk.Label(fields_frame, text="Cargo:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=2, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.contato_cargo_var, font=('Arial', 10), width=20).grid(row=row, column=3, sticky="ew", padx=(5, 0), pady=5)
        row += 1

        # Telefone e Email na segunda linha
        tk.Label(fields_frame, text="Telefone:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        contato_telefone_entry = tk.Entry(fields_frame, textvariable=self.contato_telefone_var, font=('Arial', 10), width=20)
        contato_telefone_entry.grid(row=row, column=1, sticky="w", padx=(5, 10), pady=5)
        contato_telefone_entry.bind('<FocusOut>', self.format_contato_telefone)

        tk.Label(fields_frame, text="Email:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=2, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.contato_email_var, font=('Arial', 10), width=25).grid(row=row, column=3, sticky="ew", padx=(5, 0), pady=5)
        row += 1

        # Observações na terceira linha
        tk.Label(fields_frame, text="Observações:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.contato_observacoes_var, font=('Arial', 10), width=60).grid(row=row, column=1, columnspan=3, sticky="ew", padx=(5, 0), pady=5)

        # Configurar expansão das colunas
        fields_frame.grid_columnconfigure(1, weight=1)
        fields_frame.grid_columnconfigure(3, weight=1)

        # Botões para contatos
        contatos_buttons = tk.Frame(add_contato_frame, bg='white')
        contatos_buttons.pack(fill="x", pady=(10, 0))

        adicionar_contato_btn = self.create_button(contatos_buttons, "Salvar Contato", self.adicionar_contato)
        adicionar_contato_btn.pack(side="left", padx=(0, 10))

        limpar_contato_btn = self.create_button(contatos_buttons, "Limpar Campos", self.limpar_contato, bg='#e2e8f0', fg='#475569')
        limpar_contato_btn.pack(side="left")

        # Lista de contatos
        lista_frame = tk.Frame(contatos_container, bg='white')
        lista_frame.pack(fill="both", expand=True)

        # Reservar rodapé dos botões de contatos ANTES da Treeview
        lista_buttons = tk.Frame(lista_frame, bg='white')
        lista_buttons.pack(side="bottom", fill="x", pady=(5, 0))

        # Treeview para contatos
        columns = ("nome", "cargo", "telefone", "email", "observacoes")
        self.contatos_tree = ttk.Treeview(lista_frame, columns=columns, show="headings")

        # Cabeçalhos
        self.contatos_tree.heading("nome", text="Nome")
        self.contatos_tree.heading("cargo", text="Cargo")
        self.contatos_tree.heading("telefone", text="Telefone")
        self.contatos_tree.heading("email", text="Email")
        self.contatos_tree.heading("observacoes", text="Observações")

        # Larguras
        self.contatos_tree.column("nome", width=150)
        self.contatos_tree.column("cargo", width=120)
        self.contatos_tree.column("telefone", width=120)
        self.contatos_tree.column("email", width=180)
        self.contatos_tree.column("observacoes", width=200)

        # Scrollbar
        contatos_scrollbar = ttk.Scrollbar(lista_frame, orient="vertical", command=self.contatos_tree.yview)
        self.contatos_tree.configure(yscrollcommand=contatos_scrollbar.set)

        # Pack
        self.contatos_tree.pack(side="left", fill="both", expand=True)
        contatos_scrollbar.pack(side="right", fill="y")

        # Botões da lista (fixos ao rodapé)
        # (Já reservado no topo deste bloco)

        # Botões da lista (fixos ao rodapé)
        editar_contato_btn = self.create_button(lista_buttons, "Editar Contato", self.editar_contato_selecionado)
        editar_contato_btn.pack(side="left", padx=(0, 10))

        excluir_contato_btn = self.create_button(lista_buttons, "Excluir Contato", self.excluir_contato_selecionado, bg='#dc2626')
        excluir_contato_btn.pack(side="left")

    def create_cliente_buttons(self, parent):
        buttons_frame = tk.Frame(parent, bg='white')
        # Fixar os botões ao rodapé do painel de formulário
        buttons_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        # Botões
        novo_btn = self.create_button(buttons_frame, "Novo Cliente", self.novo_cliente, bg='#e2e8f0', fg='#475569')
        novo_btn.pack(side="left", padx=(0, 10))
        
        salvar_btn = self.create_button(buttons_frame, "Salvar Cliente", self.salvar_cliente)
        salvar_btn.pack(side="left", padx=(0, 10))
        
        excluir_btn = self.create_button(buttons_frame, "Excluir Cliente", self.excluir_cliente, bg='#dc2626')
        excluir_btn.pack(side="left")

    def format_cnpj(self, event=None):
        """Formatar CNPJ automaticamente"""
        cnpj = self.cnpj_var.get()
        if cnpj:
            self.cnpj_var.set(format_cnpj(cnpj))
            
    def format_telefone(self, event=None):
        """Formatar telefone automaticamente"""
        telefone = self.telefone_var.get()
        if telefone:
            self.telefone_var.set(format_phone(telefone))
            
    def format_cep(self, event=None):
        """Formatar CEP automaticamente"""
        from utils.formatters import format_cep
        cep = self.cep_var.get()
        if cep:
            self.cep_var.set(format_cep(cep))
            
    def novo_cliente(self):
        """Limpar formulário para novo cliente"""
        self.current_cliente_id = None
        
        # Limpar todos os campos
        self.nome_var.set("")
        self.nome_fantasia_var.set("")
        self.cnpj_var.set("")
        self.inscricao_estadual_var.set("")
        self.inscricao_municipal_var.set("")
        self.endereco_var.set("")
        self.numero_var.set("")
        self.complemento_var.set("")
        self.bairro_var.set("")
        self.cidade_var.set("")
        self.estado_var.set("")
        self.cep_var.set("")
        self.telefone_var.set("")
        self.email_var.set("")
        self.site_var.set("")
        self.prazo_pagamento_var.set("")
        self.contatos_data = [] # Limpar contatos
        self.contatos_tree.delete(*self.contatos_tree.get_children()) # Limpar treeview de contatos
        
    def salvar_cliente(self):
        """Salvar cliente no banco de dados"""
        if not self.can_edit('clientes'):
            self.show_warning("Você não tem permissão para salvar clientes.")
            return
            
        # Validações
        nome = self.nome_var.get().strip()
        if not nome:
            self.show_warning("O nome/razão social é obrigatório.")
            return
            
        cnpj = self.cnpj_var.get().strip()
        if cnpj and not validate_cnpj(cnpj):
            self.show_warning("CNPJ inválido.")
            return
            
        email = self.email_var.get().strip()
        if email and not validate_email(email):
            self.show_warning("Email inválido.")
            return
            
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            # Verificar CNPJ duplicado antes de salvar
            if cnpj:
                if self.current_cliente_id:
                    # Verificar se existe outro cliente com o mesmo CNPJ (excluindo o atual)
                    c.execute("SELECT id FROM clientes WHERE cnpj = ? AND id != ?", (cnpj, self.current_cliente_id))
                else:
                    # Verificar se existe cliente com o mesmo CNPJ
                    c.execute("SELECT id FROM clientes WHERE cnpj = ?", (cnpj,))
                
                if c.fetchone():
                    self.show_error("CNPJ já cadastrado no sistema. Não é possível salvar um CNPJ duplicado.")
                    return
            
            # Preparar dados
            dados = (
                nome,
                self.nome_fantasia_var.get().strip(),
                cnpj if cnpj else None,
                self.inscricao_estadual_var.get().strip(),
                self.inscricao_municipal_var.get().strip(),
                self.endereco_var.get().strip(),
                self.numero_var.get().strip(),
                self.complemento_var.get().strip(),
                self.bairro_var.get().strip(),
                self.cidade_var.get().strip(),
                self.estado_var.get().strip(),
                self.cep_var.get().strip(),
                self.telefone_var.get().strip(),
                email if email else None,
                self.site_var.get().strip(),
                self.prazo_pagamento_var.get().strip()
            )
            
            if self.current_cliente_id:
                # Atualizar cliente existente
                c.execute("""
                    UPDATE clientes SET
                        nome = ?, nome_fantasia = ?, cnpj = ?, inscricao_estadual = ?,
                        inscricao_municipal = ?, endereco = ?, numero = ?, complemento = ?,
                        bairro = ?, cidade = ?, estado = ?, cep = ?, telefone = ?, email = ?,
                        site = ?, prazo_pagamento = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, dados + (self.current_cliente_id,))
            else:
                # Inserir novo cliente
                c.execute("""
                    INSERT INTO clientes (nome, nome_fantasia, cnpj, inscricao_estadual,
                                        inscricao_municipal, endereco, numero, complemento,
                                        bairro, cidade, estado, cep, telefone, email,
                                        site, prazo_pagamento)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, dados)
                
                self.current_cliente_id = c.lastrowid
            
            conn.commit()
            self.show_success("Cliente salvo com sucesso!")
            
            # Emitir evento para atualizar outros módulos
            self.emit_event('cliente_created')
            
            # Recarregar lista
            self.carregar_clientes()
            
        except sqlite3.IntegrityError as e:
            if "cnpj" in str(e).lower():
                self.show_error("CNPJ já cadastrado no sistema.")
            else:
                self.show_error(f"Erro de integridade: {e}")
        except sqlite3.Error as e:
            self.show_error(f"Erro ao salvar cliente: {e}")
        finally:
            conn.close()
            
    def carregar_clientes(self):
        """Carregar lista de clientes"""
        # Limpar lista atual
        for item in self.clientes_tree.get_children():
            self.clientes_tree.delete(item)
            
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            c.execute("""
                SELECT id, nome, cnpj, cidade, telefone, email
                FROM clientes
                ORDER BY nome
            """)
            
            for row in c.fetchall():
                cliente_id, nome, cnpj, cidade, telefone, email = row
                self.clientes_tree.insert("", "end", values=(
                    nome,
                    format_cnpj(cnpj) if cnpj else "",
                    cidade or "",
                    format_phone(telefone) if telefone else "",
                    email or ""
                ), tags=(cliente_id,))
                
        except sqlite3.Error as e:
            self.show_error(f"Erro ao carregar clientes: {e}")
        finally:
            conn.close()
            
    def buscar_clientes(self):
        """Buscar clientes com filtro"""
        termo = self.search_var.get().strip()
        
        # Limpar lista atual
        for item in self.clientes_tree.get_children():
            self.clientes_tree.delete(item)
            
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            if termo:
                c.execute("""
                    SELECT id, nome, cnpj, cidade, telefone, email
                    FROM clientes
                    WHERE nome LIKE ? OR cnpj LIKE ? OR cidade LIKE ?
                    ORDER BY nome
                """, (f"%{termo}%", f"%{termo}%", f"%{termo}%"))
            else:
                c.execute("""
                    SELECT id, nome, cnpj, cidade, telefone, email
                    FROM clientes
                    ORDER BY nome
                """)
            
            for row in c.fetchall():
                cliente_id, nome, cnpj, cidade, telefone, email = row
                self.clientes_tree.insert("", "end", values=(
                    nome,
                    format_cnpj(cnpj) if cnpj else "",
                    cidade or "",
                    format_phone(telefone) if telefone else "",
                    email or ""
                ), tags=(cliente_id,))
                
        except sqlite3.Error as e:
            self.show_error(f"Erro ao buscar clientes: {e}")
        finally:
            conn.close()
            
    def editar_cliente(self):
        """Editar/Visualizar cliente selecionado baseado nas permissões"""
        selected = self.clientes_tree.selection()
        if not selected:
            self.show_warning("Selecione um cliente para editar/visualizar.")
            return
            
        # Obter ID do cliente
        tags = self.clientes_tree.item(selected[0])['tags']
        if not tags:
            return
            
        cliente_id = tags[0]
        
        if self.can_edit('clientes'):
            # Usuário pode editar - carregar normalmente
            self.carregar_cliente_para_edicao(cliente_id)
        else:
            # Usuário só pode visualizar - usar função de visualização
            self.visualizar_cliente(cliente_id)
        
    def on_cliente_double_click(self, event):
        """Duplo clique na treeview - visualizar ou editar cliente baseado nas permissões"""
        selected = self.clientes_tree.selection()
        if not selected:
            return
            
        # Obter ID do cliente
        tags = self.clientes_tree.item(selected[0])['tags']
        if not tags:
            return
            
        cliente_id = tags[0]
        
        if self.can_edit('clientes'):
            # Usuário pode editar - carregar para edição
            self.carregar_cliente_para_edicao(cliente_id)
        else:
            # Usuário só pode visualizar - carregar dados em modo readonly
            self.visualizar_cliente(cliente_id)
    
    def carregar_cliente_para_edicao(self, cliente_id):
        """Carregar dados do cliente para edição"""
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            # Buscar dados do cliente
            c.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
            cliente = c.fetchone()
            
            if not cliente:
                self.show_error("Cliente não encontrado.")
                return
                
            # Preencher campos
            self.current_cliente_id = cliente_id
            self.nome_var.set(cliente[1] or "")  # nome
            self.nome_fantasia_var.set(cliente[2] or "")  # nome_fantasia
            self.cnpj_var.set(format_cnpj(cliente[3]) if cliente[3] else "")  # cnpj
            self.inscricao_estadual_var.set(cliente[4] or "")  # inscricao_estadual
            self.inscricao_municipal_var.set(cliente[5] or "")  # inscricao_municipal
            self.endereco_var.set(cliente[6] or "")  # endereco
            self.numero_var.set(cliente[7] or "")  # numero
            self.complemento_var.set(cliente[8] or "")  # complemento
            self.bairro_var.set(cliente[9] or "")  # bairro
            self.cidade_var.set(cliente[10] or "")  # cidade
            self.estado_var.set(cliente[11] or "")  # estado
            self.cep_var.set(cliente[12] or "")  # cep
            self.telefone_var.set(format_phone(cliente[13]) if cliente[13] else "")  # telefone
            self.email_var.set(cliente[14] or "")  # email
            self.site_var.set(cliente[15] or "")  # site
            self.prazo_pagamento_var.set(cliente[16] or "")  # prazo_pagamento
            
            # Carregar contatos
            self.contatos_data = []
            self.contatos_tree.delete(*self.contatos_tree.get_children())
            c.execute("SELECT * FROM contatos WHERE cliente_id = ? ORDER BY nome", (cliente_id,))
            for contato in c.fetchall():
                self.contatos_data.append({
                    'id': contato[0],
                    'nome': contato[2],
                    'cargo': contato[3],
                    'telefone': contato[4],
                    'email': contato[5],
                    'observacoes': contato[6]
                })
                self.contatos_tree.insert("", "end", values=(
                    contato[2], contato[3], format_phone(contato[4]) if contato[4] else "",
                    contato[5] or "", contato[6] or ""
                ), tags=(contato[0],))
            
            # Layout único: permanecer na mesma tela
            
            # Atualizar dados derivados (se aplicável)
            self.update_cliente_dashboard()
            self.update_cliente_dashboard_expandido()
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao carregar cliente: {e}")
        finally:
            conn.close()
            
    def excluir_cliente(self):
        """Excluir cliente selecionado"""
        if not self.can_edit('clientes'):
            self.show_warning("Você não tem permissão para excluir clientes.")
            return
            
        # Confirmar exclusão
        if not messagebox.askyesno("Confirmar Exclusão", 
                                   "Tem certeza que deseja excluir este cliente?\n"
                                   "Esta ação não pode ser desfeita."):
            return
            
        # Obter ID do cliente
        tags = self.clientes_tree.item(selected[0])['tags']
        if not tags:
            return
            
        cliente_id = tags[0]
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            # Excluir contatos primeiro
            c.execute("DELETE FROM contatos WHERE cliente_id = ?", (cliente_id,))
            
            # Excluir cliente
            c.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
            conn.commit()
            
            self.show_success("Cliente excluído com sucesso!")
            
            # Emitir evento para atualizar outros módulos
            self.emit_event('cliente_deleted')
            
            # Recarregar lista
            self.carregar_clientes()
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao excluir cliente: {e}")
        finally:
            conn.close()

    def adicionar_contato(self):
        """Adicionar novo contato ao cliente (sem salvar o cliente automaticamente)"""
        if not self.can_edit('clientes'):
            self.show_warning("Você não tem permissão para adicionar contatos.")
            return
            
        # Exigir cliente previamente salvo para associar contato
        if not self.current_cliente_id:
            self.show_warning("Salve o cliente antes de salvar um contato (use 'Salvar Cliente').")
            return
         
        nome = self.contato_nome_var.get().strip()
        if not nome:
            self.show_warning("O nome do contato é obrigatório.")
            return
            
        telefone = self.contato_telefone_var.get().strip()
        email = self.contato_email_var.get().strip()
        
        if not telefone and not email:
            self.show_warning("O contato deve ter pelo menos um telefone ou email.")
            return
            
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            dados_contato = (
                self.current_cliente_id,
                nome,
                self.contato_cargo_var.get().strip(),
                telefone,
                email,
                self.contato_observacoes_var.get().strip()
            )
            
            c.execute("""
                INSERT INTO contatos (cliente_id, nome, cargo, telefone, email, observacoes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, dados_contato)
            conn.commit()
            
            self.show_success("Contato salvo com sucesso!")
            self.limpar_contato() # Limpar campos do novo contato
            self.carregar_cliente_para_edicao(self.current_cliente_id) # Recarregar cliente com novo contato
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao salvar contato: {e}")
        finally:
            conn.close()
            
    def limpar_contato(self):
        """Limpar campos do novo contato"""
        self.contato_nome_var.set("")
        self.contato_cargo_var.set("")
        self.contato_telefone_var.set("")
        self.contato_email_var.set("")
        self.contato_observacoes_var.set("")
        
    def editar_contato_selecionado(self):
        """Editar contato selecionado"""
        if not self.can_edit('clientes'):
            self.show_warning("Você não tem permissão para editar contatos.")
            return
            
        selected = self.contatos_tree.selection()
        if not selected:
            self.show_warning("Selecione um contato para editar.")
            return
            
        # Obter ID do contato
        tags = self.contatos_tree.item(selected[0])['tags']
        if not tags:
            return
            
        contato_id = tags[0]
        
        contato_to_edit = next((c for c in self.contatos_data if c['id'] == contato_id), None)
        if not contato_to_edit:
            self.show_error("Contato não encontrado.")
            return
            
        self.contato_nome_var.set(contato_to_edit['nome'])
        self.contato_cargo_var.set(contato_to_edit['cargo'])
        self.contato_telefone_var.set(contato_to_edit['telefone'])
        self.contato_email_var.set(contato_to_edit['email'])
        self.contato_observacoes_var.set(contato_to_edit['observacoes'])
        
        # Layout único: permanecer na mesma tela
        
    def excluir_contato_selecionado(self):
        """Excluir contato selecionado"""
        if not self.can_edit('clientes'):
            self.show_warning("Você não tem permissão para excluir contatos.")
            return
            
        selected = self.contatos_tree.selection()
        if not selected:
            self.show_warning("Selecione um contato para excluir.")
            return
            
        # Confirmar exclusão
        if not messagebox.askyesno("Confirmar Exclusão", 
                                   "Tem certeza que deseja excluir este contato?\n"
                                   "Esta ação não pode ser desfeita."):
            return
            
        # Obter ID do contato
        tags = self.contatos_tree.item(selected[0])['tags']
        if not tags:
            return
            
        contato_id = tags[0]
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            c.execute("DELETE FROM contatos WHERE id = ?", (contato_id,))
            conn.commit()
            
            self.show_success("Contato excluído com sucesso!")
            self.carregar_cliente_para_edicao(self.current_cliente_id) # Recarregar cliente sem o contato excluído
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao excluir contato: {e}")
        finally:
            conn.close()

    def format_contato_telefone(self, event=None):
        """Formatar telefone do contato automaticamente"""
        telefone = self.contato_telefone_var.get()
        if telefone:
            self.contato_telefone_var.set(format_phone(telefone))

    def buscar_cep(self, event=None):
        """Buscar CEP e preencher endereço"""
        cep = self.cep_var.get().strip()
        if not cep:
            return
            
        try:
            from utils.correios import buscar_cep
            endereco = buscar_cep(cep)
            if endereco:
                self.endereco_var.set(endereco['logradouro'])
                self.bairro_var.set(endereco['bairro'])
                self.cidade_var.set(endereco['cidade'])
                self.estado_var.set(endereco['uf'])
            else:
                self.show_warning("CEP não encontrado.")
        except ImportError:
            # Se não tiver o módulo de correios, apenas formatar o CEP
            from utils.formatters import format_cep
            self.cep_var.set(format_cep(cep))
        except Exception as e:
            self.show_error(f"Erro ao buscar CEP: {e}")
            
    def visualizar_cliente(self, cliente_id):
        """Visualizar dados do cliente em modo readonly"""
        # Carregar os dados do cliente primeiro
        self.carregar_cliente_para_edicao(cliente_id)
        
        # Aguardar um momento para garantir que os dados sejam carregados
        self.frame.after(100, lambda: self._aplicar_readonly_visualizacao())
        
        # Mostrar mensagem informativa
        self.show_info("Visualizando cliente em modo consulta. Os dados não podem ser editados.")
        
    def _aplicar_readonly_visualizacao(self):
        """Aplica readonly após os dados serem carregados"""
        if not self.can_edit('clientes'):
            self.apply_readonly_for_visualization()