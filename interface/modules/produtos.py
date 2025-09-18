import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from .base_module import BaseModule
from database import DB_NAME
from utils.formatters import format_currency, clean_number

class ProdutosModule(BaseModule):
    def setup_ui(self):
        container = tk.Frame(self.frame, bg='#f8fafc')
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        self.create_header(container)
        
        # Notebook
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True, pady=(20, 0))
        
        # Abas
        self.create_produto_unificado_tab()
        self.create_lista_produtos_tab()
        
        self.current_produto_id = None
        self.loaded_tipo_atual = None  # Tipo do registro atualmente carregado (para prevenir conversões indesejadas)
        self.kit_items = []  # Lista de itens do kit
        self.carregar_produtos()
        
    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg='#f8fafc')
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = tk.Label(header_frame, text="Gestão de Produtos/Serviços", 
                               font=('Arial', 18, 'bold'), bg='#f8fafc', fg='#1e293b')
        title_label.pack(side="left")
        
    def create_produto_unificado_tab(self):
        produto_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(produto_frame, text="Produto/Serviços")
        
        content_frame = tk.Frame(produto_frame, bg='white', padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        # Seção principal
        section_frame = self.create_section_frame(content_frame, "Dados do Produto/Serviços")
        section_frame.pack(fill="x", pady=(0, 15))
        
        fields_frame = tk.Frame(section_frame, bg='white')
        fields_frame.pack(fill="x")
        
        # Variáveis
        self.nome_var = tk.StringVar()
        self.tipo_var = tk.StringVar(value="Produto")
        self.ncm_var = tk.StringVar()
        self.valor_var = tk.StringVar(value="0.00")
        self.descricao_var = tk.StringVar()
        self.ativo_var = tk.BooleanVar(value=True)
        
        row = 0
        
        # Nome
        tk.Label(fields_frame, text="Nome *:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.nome_var, font=('Arial', 10), width=40).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Tipo
        tk.Label(fields_frame, text="Tipo *:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tipo_combo = ttk.Combobox(fields_frame, textvariable=self.tipo_var, 
                                 values=["Produto", "Serviços", "Compressores"], width=37, state="readonly")
        tipo_combo.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        tipo_combo.bind('<<ComboboxSelected>>', self.on_tipo_changed)
        row += 1
        
        # NCM (só para produtos)
        tk.Label(fields_frame, text="NCM:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        self.ncm_entry = tk.Entry(fields_frame, textvariable=self.ncm_var, font=('Arial', 10), width=40)
        self.ncm_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Valor Unitário
        tk.Label(fields_frame, text="Valor Unitário:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        valor_entry = tk.Entry(fields_frame, textvariable=self.valor_var, font=('Arial', 10), width=40)
        valor_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        valor_entry.bind('<FocusOut>', self.format_valor)
        row += 1
        
        # Descrição
        tk.Label(fields_frame, text="Descrição:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.descricao_var, font=('Arial', 10), width=40).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1

        # Esboço do Serviço (somente para Serviços)
        esboco_label = tk.Label(fields_frame, text="Esboço do Serviço:", font=('Arial', 10, 'bold'), bg='white')
        esboco_label.grid(row=row, column=0, sticky="nw", pady=5)
        self.esboco_servico_text = tk.Text(fields_frame, height=4, width=40)
        self.esboco_servico_text.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Ativo
        tk.Label(fields_frame, text="Ativo:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Checkbutton(fields_frame, variable=self.ativo_var, bg='white').grid(row=row, column=1, sticky="w", padx=(10, 0), pady=5)
        
        fields_frame.grid_columnconfigure(1, weight=1)
        
        # Botões
        buttons_frame = tk.Frame(content_frame, bg='white')
        buttons_frame.pack(fill="x", pady=(20, 0))
        
        novo_btn = self.create_button(buttons_frame, "Novo Produto", self.novo_produto, bg='#e2e8f0', fg='#475569')
        novo_btn.pack(side="left", padx=(0, 10))
        
        salvar_btn = self.create_button(buttons_frame, "Salvar Produto", self.salvar_produto)
        salvar_btn.pack(side="left")
        
        # Seção de Kit (visível apenas quando tipo for "Kit")
        self.create_kit_integrado_section(content_frame)
        
    def create_kit_integrado_section(self, parent):
        """Seção de kit integrada na aba de produtos"""
        self.kit_section_frame = self.create_section_frame(parent, "Composição de Serviços")
        self.kit_section_frame.pack(fill="both", expand=True, pady=(15, 0))
        
        # Inicialmente oculto
        self.kit_section_frame.pack_forget()
        
        # Container principal
        kit_container = tk.Frame(self.kit_section_frame, bg='white')
        kit_container.pack(fill="both", expand=True)
        
        # Frame para adicionar itens ao kit
        add_item_frame = tk.Frame(kit_container, bg='white')
        add_item_frame.pack(fill="x", pady=(0, 10))
        
        # Variáveis para adicionar itens ao kit
        if not hasattr(self, 'item_produto_var'):
            self.item_produto_var = tk.StringVar()
            self.item_quantidade_var = tk.StringVar(value="1")
        
        # Campos para adicionar item
        fields_frame = tk.Frame(add_item_frame, bg='white')
        fields_frame.pack(fill="x")
        
        # Produto/Serviço
        tk.Label(fields_frame, text="Produto:", font=('Arial', 10, 'bold'), bg='white').grid(row=0, column=0, sticky="w", pady=5)
        self.produto_kit_combo = ttk.Combobox(fields_frame, textvariable=self.item_produto_var, width=40, state="readonly")
        self.produto_kit_combo.grid(row=0, column=1, sticky="ew", padx=(5, 10), pady=5)
        
        # Quantidade
        tk.Label(fields_frame, text="Quantidade:", font=('Arial', 10, 'bold'), bg='white').grid(row=0, column=2, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.item_quantidade_var, font=('Arial', 10), width=10).grid(row=0, column=3, sticky="w", padx=(5, 0), pady=5)
        
        # Configurar expansão das colunas
        fields_frame.grid_columnconfigure(1, weight=1)
        
        # Botões para itens do kit
        kit_buttons = tk.Frame(add_item_frame, bg='white')
        kit_buttons.pack(fill="x", pady=(10, 0))
        
        adicionar_item_btn = self.create_button(kit_buttons, "Adicionar Item", self.adicionar_item_kit)
        adicionar_item_btn.pack(side="left", padx=(0, 10))
        
        limpar_item_btn = self.create_button(kit_buttons, "Limpar", self.limpar_item_kit, bg='#e2e8f0', fg='#475569')
        limpar_item_btn.pack(side="left")
        
        # Lista de itens do kit
        lista_frame = tk.Frame(kit_container, bg='white')
        lista_frame.pack(fill="both", expand=True)
        
        # Treeview para itens do kit
        columns = ("produto", "tipo", "quantidade")
        self.kit_items_tree = ttk.Treeview(lista_frame, columns=columns, show="headings", height=6)
        
        # Cabeçalhos
        self.kit_items_tree.heading("produto", text="Produto")
        self.kit_items_tree.heading("tipo", text="Tipo")
        self.kit_items_tree.heading("quantidade", text="Quantidade")
        
        # Larguras
        self.kit_items_tree.column("produto", width=300)
        self.kit_items_tree.column("tipo", width=100)
        self.kit_items_tree.column("quantidade", width=100)
        
        # Scrollbar
        kit_scrollbar = ttk.Scrollbar(lista_frame, orient="vertical", command=self.kit_items_tree.yview)
        self.kit_items_tree.configure(yscrollcommand=kit_scrollbar.set)
        
        # Pack
        self.kit_items_tree.pack(side="left", fill="both", expand=True)
        kit_scrollbar.pack(side="right", fill="y")
        
        # Botões da lista
        lista_buttons = tk.Frame(lista_frame, bg='white')
        lista_buttons.pack(fill="x", pady=(5, 0))
        
        remover_item_btn = self.create_button(lista_buttons, "Remover Item", self.remover_item_kit, bg='#dc2626')
        remover_item_btn.pack(side="left")
        
        # Inicializar lista vazia de itens do kit
        self.kit_items = []
        
        # Carregar produtos/serviços para o combobox
        self.carregar_produtos_para_kit()
        
    def create_kit_tab(self):
        kit_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(kit_frame, text="Serviços")
        
        content_frame = tk.Frame(kit_frame, bg='white', padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        # Seção: Dados do Kit
        section_frame = self.create_section_frame(content_frame, "Dados de Serviços")
        section_frame.pack(fill="x", pady=(0, 15))
        
        fields_frame = tk.Frame(section_frame, bg='white')
        fields_frame.pack(fill="x")
        
        # Variáveis do kit
        self.kit_nome_var = tk.StringVar()
        self.kit_descricao_var = tk.StringVar()
        self.kit_ativo_var = tk.BooleanVar(value=True)
        
        row = 0
        
        # Nome do Kit
        tk.Label(fields_frame, text="Nome dos Serviços *:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.kit_nome_var, font=('Arial', 10), width=40).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Descrição do Kit
        tk.Label(fields_frame, text="Descrição:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Entry(fields_frame, textvariable=self.kit_descricao_var, font=('Arial', 10), width=40).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Ativo
        tk.Label(fields_frame, text="Ativo:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        tk.Checkbutton(fields_frame, variable=self.kit_ativo_var, bg='white').grid(row=row, column=1, sticky="w", padx=(10, 0), pady=5)
        
        fields_frame.grid_columnconfigure(1, weight=1)
        
        # Seção: Adicionar Itens ao Kit
        add_section = self.create_section_frame(content_frame, "Adicionar Itens aos Serviços")
        add_section.pack(fill="x", pady=(15, 0))
        
        add_frame = tk.Frame(add_section, bg='white')
        add_frame.pack(fill="x")
        
        # Variáveis para adicionar itens
        self.item_tipo_var = tk.StringVar(value="Produto")
        self.item_produto_var = tk.StringVar()
        self.item_quantidade_var = tk.StringVar(value="1")
        
        row = 0
        
        # Tipo de Item
        tk.Label(add_frame, text="Tipo:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
        item_tipo_combo = ttk.Combobox(add_frame, textvariable=self.item_tipo_var, 
                                      values=["Produto"], width=15, state="readonly")
        item_tipo_combo.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=5)
        item_tipo_combo.bind('<<ComboboxSelected>>', self.on_item_tipo_changed)
        
        # Produto/Serviço
        tk.Label(add_frame, text="Item:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=2, sticky="w", pady=5, padx=(20, 0))
        self.item_combo = ttk.Combobox(add_frame, textvariable=self.item_produto_var, width=30, state="readonly")
        self.item_combo.grid(row=row, column=3, sticky="ew", padx=(10, 0), pady=5)
        
        # Quantidade
        tk.Label(add_frame, text="Qtd:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=4, sticky="w", pady=5, padx=(20, 0))
        tk.Entry(add_frame, textvariable=self.item_quantidade_var, font=('Arial', 10), width=8).grid(row=row, column=5, sticky="w", padx=(10, 0), pady=5)
        
        add_frame.grid_columnconfigure(3, weight=1)
        
        # Botão adicionar item
        add_item_btn = self.create_button(add_frame, "Adicionar Item", self.adicionar_item_kit)
        add_item_btn.grid(row=row, column=6, padx=(20, 0), pady=5)
        
        # Lista de itens do kit
        lista_section = self.create_section_frame(content_frame, "Itens dos Serviços")
        lista_section.pack(fill="both", expand=True, pady=(15, 0))
        
        # Treeview para itens do kit
        kit_container = tk.Frame(lista_section, bg='white')
        kit_container.pack(fill="both", expand=True)
        
        columns = ("tipo", "nome", "quantidade", "valor_unitario", "valor_total")
        self.kit_tree = ttk.Treeview(kit_container, columns=columns, show="headings", height=8)
        
        # Cabeçalhos
        self.kit_tree.heading("tipo", text="Tipo")
        self.kit_tree.heading("nome", text="Nome")
        self.kit_tree.heading("quantidade", text="Qtd")
        self.kit_tree.heading("valor_unitario", text="Valor Unit.")
        self.kit_tree.heading("valor_total", text="Valor Total")
        
        # Larguras
        self.kit_tree.column("tipo", width=80)
        self.kit_tree.column("nome", width=250)
        self.kit_tree.column("quantidade", width=60)
        self.kit_tree.column("valor_unitario", width=100)
        self.kit_tree.column("valor_total", width=100)
        
        # Scrollbar para kit
        kit_scrollbar = ttk.Scrollbar(kit_container, orient="vertical", command=self.kit_tree.yview)
        self.kit_tree.configure(yscrollcommand=kit_scrollbar.set)
        
        # Pack
        self.kit_tree.pack(side="left", fill="both", expand=True)
        kit_scrollbar.pack(side="right", fill="y")
        
        # Label para valor total do kit
        self.kit_total_label = tk.Label(lista_section, text="Valor Total do Kit: R$ 0,00", 
                                       font=('Arial', 12, 'bold'), bg='white', fg='#1e293b')
        self.kit_total_label.pack(pady=(10, 0))
        
        # Botões do kit
        kit_buttons = tk.Frame(lista_section, bg='white')
        kit_buttons.pack(fill="x", pady=(10, 0))
        
        remover_item_btn = self.create_button(kit_buttons, "Remover Item", self.remover_item_kit, bg='#dc2626')
        remover_item_btn.pack(side="left", padx=(0, 10))
        
        novo_kit_btn = self.create_button(kit_buttons, "Novo Kit", self.novo_kit, bg='#e2e8f0', fg='#475569')
        novo_kit_btn.pack(side="left", padx=(0, 10))
        
        salvar_kit_btn = self.create_button(kit_buttons, "Salvar Kit", self.salvar_kit)
        salvar_kit_btn.pack(side="left")
        
        # Carregar produtos e serviços para os combos
        self.atualizar_combo_items()
        
    def create_lista_produtos_tab(self):
        lista_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(lista_frame, text="Lista de Produtos")
        
        container = tk.Frame(lista_frame, bg='white', padx=20, pady=20)
        container.pack(fill="both", expand=True)
        
        # Busca compartilhada
        search_frame, self.search_var = self.create_search_frame(container, command=self.buscar_produtos)
        search_frame.pack(fill="x", pady=(0, 15))
        
        # Notebook interno com três abas por tipo
        tipos_notebook = ttk.Notebook(container)
        tipos_notebook.pack(fill="both", expand=True)
        
        self.trees_por_tipo = {}
        for tipo in ["Produto", "Kit", "Compressores"]:
            tab = tk.Frame(tipos_notebook, bg='white')
            tipos_notebook.add(tab, text=("Serviços" if tipo=="Kit" else tipo))
            
            inner = tk.Frame(tab, bg='white')
            inner.pack(fill="both", expand=True)
            
            columns = ("nome", "valor", "ativo")
            tree = ttk.Treeview(inner, columns=columns, show="headings", height=15)
            tree.heading("nome", text="Nome")
            tree.heading("valor", text="Valor")
            tree.heading("ativo", text="Ativo")
            tree.column("nome", width=300)
            tree.column("valor", width=120)
            tree.column("ativo", width=80)
            scrollbar = ttk.Scrollbar(inner, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Adicionar evento de duplo clique para visualização
            tree.bind("<Double-1>", self.on_produto_double_click)
            
            self.trees_por_tipo["Serviços" if tipo=="Kit" else tipo] = tree
        
        # Botões
        lista_buttons = tk.Frame(container, bg='white')
        lista_buttons.pack(fill="x", pady=(15, 0))
        
        editar_btn = self.create_button(lista_buttons, "Editar", self.editar_produto)
        editar_btn.pack(side="left", padx=(0, 10))
        
        ativar_btn = self.create_button(lista_buttons, "Ativar/Desativar", self.toggle_ativo, bg='#f59e0b')
        ativar_btn.pack(side="left")

        excluir_btn = self.create_button(lista_buttons, "Excluir", self.excluir_produto, bg='#dc2626')
        excluir_btn.pack(side="left", padx=(10, 0))

    def on_tipo_changed(self, event):
        """Controla visibilidade do campo NCM e seção de kit baseado no tipo"""
        # Evitar interferência durante carregamento
        if hasattr(self, '_carregando') and self._carregando:
            return
            
        current_tipo = self.tipo_var.get()
        
        # Controlar campo NCM
        if True:
            self.ncm_entry.config(state='normal')
        
        # Controlar campo Esboço do Serviço
        if current_tipo == "Serviços":
            self.esboco_servico_text.config(state='normal')
        else:
            self.esboco_servico_text.config(state='disabled')

        # Se o usuário mudar o tipo para um diferente do carregado e houver um registro em edição,
        # evitar converter o registro original (ex.: Produto -> Kit). Criar um novo registro.
        try:
            # Tratar "Serviços" (UI) como equivalente a "Kit" (DB) para comparação
            def _normalize_tipo(t):
                return "Kit" if t == "Serviços" else t
            # Só resetar se realmente for uma mudança de tipo (não apenas nomenclatura)
            if (self.current_produto_id and self.loaded_tipo_atual and 
                _normalize_tipo(current_tipo) != self.loaded_tipo_atual and
                not (_normalize_tipo(current_tipo) == "Kit" and self.loaded_tipo_atual == "Kit")):
                # Resetar ID para forçar INSERT em vez de UPDATE
                self.current_produto_id = None
                # Para segurança, quando destino for Kit, iniciar composição vazia
                if current_tipo == "Serviços":
                    self.kit_items = []
                    if hasattr(self, 'kit_items_tree'):
                        self.atualizar_kit_tree()
                # Informar usuário (opcional)
                try:
                    self.show_info("Novo cadastro", f"Alterar o tipo de {self.loaded_tipo_atual} para {current_tipo} criará um novo cadastro.")
                except Exception:
                    pass
        except Exception:
            pass

        # Controlar seção de kit
        if hasattr(self, 'kit_section_frame'):
            if current_tipo == "Serviços":
                self.kit_section_frame.pack(fill="both", expand=True, pady=(15, 0))
                # Se estamos iniciando um novo cadastro (sem ID), garantir que a composição do kit comece vazia
                if not self.current_produto_id:
                    self.kit_items = []
                    if hasattr(self, 'kit_items_tree'):
                        self.atualizar_kit_tree()
            else:
                self.kit_section_frame.pack_forget()
        
            
    def format_valor(self, event):
        """Formatar valor monetário"""
        valor_str = self.valor_var.get()
        try:
            valor_float = clean_number(valor_str)
            # Só formatar se o valor for diferente de 0 ou se não estiver vazio
            if valor_float != 0 or valor_str.strip():
                self.valor_var.set(f"{valor_float:.2f}")
        except ValueError:
            # Só definir como 0.00 se o usuário realmente digitou algo inválido
            if valor_str.strip() and valor_str.strip() != "0.00":
                self.valor_var.set("0.00")
    
    def carregar_produtos_para_kit(self):
        """Carregar produtos e serviços disponíveis para o kit"""
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            # Buscar apenas produtos (itens que compõem Serviços)
            c.execute("SELECT id, nome, tipo FROM produtos WHERE tipo IN ('Produto') AND ativo = 1 ORDER BY nome")
            produtos = c.fetchall()
            
            # Limpar e popular combobox
            if hasattr(self, 'produto_kit_combo'):
                valores = [f"{row[1]} (Produto)" for row in produtos]
                self.produto_kit_combo['values'] = valores
                
                # Armazenar mapeamento id -> index
                self.produtos_kit_map = {i: row[0] for i, row in enumerate(produtos)}
                self.produtos_kit_data = produtos
                
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro ao carregar produtos: {e}")
        finally:
            conn.close()
    
    def adicionar_item_kit(self):
        """Adicionar item à composição do kit"""
        if not self.can_edit('produtos'):
            self.show_warning("Você não tem permissão para adicionar itens ao kit.")
            return
            
        if not self.item_produto_var.get():
            messagebox.showwarning("Aviso", "Selecione um produto/serviço!")
            return
            
        try:
            quantidade = float(self.item_quantidade_var.get())
            if quantidade <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Erro", "Quantidade deve ser um número positivo!")
            return
        
        # Obter dados do produto selecionado
        index = self.produto_kit_combo.current()
        if index < 0:
            messagebox.showwarning("Aviso", "Produto não selecionado corretamente!")
            return
            
        produto_id = self.produtos_kit_map[index]
        produto_nome, produto_tipo = self.produtos_kit_data[index][1], 'Produto'
        
        # Verificar se já existe
        for item in self.kit_items:
            if item['produto_id'] == produto_id:
                messagebox.showwarning("Aviso", "Este produto já está no kit!")
                return
        
        # Adicionar à lista
        item = {
            'produto_id': produto_id,
            'nome': produto_nome,
            'tipo': produto_tipo,
            'quantidade': quantidade
        }
        self.kit_items.append(item)
        
        # Atualizar treeview
        self.atualizar_kit_tree()
        
        # Limpar campos
        self.limpar_item_kit()
    
    def limpar_item_kit(self):
        """Limpar campos de item do kit"""
        self.item_produto_var.set("")
        self.item_quantidade_var.set("1")
    
    def remover_item_kit(self):
        """Remover item selecionado do kit"""
        if not self.can_edit('produtos'):
            self.show_warning("Você não tem permissão para modificar kits.")
            return
            
        if not hasattr(self, 'kit_items_tree'):
            return
            
        selection = self.kit_items_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um item para remover!")
            return
        
        # Obter índice do item
        item_id = self.kit_items_tree.item(selection[0])['text']
        try:
            index = int(item_id)
            if 0 <= index < len(self.kit_items):
                del self.kit_items[index]
                self.atualizar_kit_tree()
        except (ValueError, IndexError):
            messagebox.showerror("Erro", "Erro ao remover item!")
    
    def atualizar_kit_tree(self):
        """Atualizar a treeview de itens do kit"""
        # Limpar treeview
        for item in self.kit_items_tree.get_children():
            self.kit_items_tree.delete(item)
        
        # Adicionar itens
        for i, item in enumerate(self.kit_items):
            self.kit_items_tree.insert("", "end", text=str(i), values=(
                item['nome'],
                item['tipo'],
                f"{item['quantidade']:.2f}"
            ))
            
    def novo_produto(self):
        if not self.can_edit('produtos'):
            self.show_warning("Você não tem permissão para criar novos produtos.")
            return
            
        self.current_produto_id = None
        self.loaded_tipo_atual = None
        self.nome_var.set("")
        self.tipo_var.set("Produto")
        self.ncm_var.set("")
        self.valor_var.set("0.00")
        self.descricao_var.set("")
        self.ativo_var.set(True)
        self.ncm_entry.config(state='normal') # Habilita o campo NCM para produtos
        try:
            if hasattr(self, 'esboco_servico_text'):
                self.esboco_servico_text.delete("1.0", tk.END)
            self.on_tipo_changed(None)
        except Exception:
            pass
        
    def salvar_produto(self):
        if not self.can_edit('produtos'):
            self.show_warning("Você não tem permissão para salvar produtos.")
            return
            
        nome = self.nome_var.get().strip()
        tipo = self.tipo_var.get()
        # Mapear UI para DB: Serviços -> Kit; Compressores -> Produto + categoria
        if tipo == "Serviços":
            tipo_db = "Kit"
        elif tipo == "Compressores":
            tipo_db = "Produto"
        else:
            tipo_db = tipo
        categoria_db = "Compressores" if tipo == "Compressores" else "Geral"
        
        if not nome:
            self.show_warning("O nome é obrigatório.")
            return
            
        if not tipo:
            self.show_warning("Selecione o tipo.")
            return
        
        # Validação específica para kit
        if tipo == "Serviços" and not self.kit_items:
            self.show_warning("Um kit deve ter pelo menos um item!")
            return
            
        try:
            valor = clean_number(self.valor_var.get())
        except ValueError:
            self.show_warning("Valor inválido.")
            return

        # Ler esboço do serviço (apenas se Serviços)
        esboco_texto = None
        try:
            if hasattr(self, 'esboco_servico_text') and self.tipo_var.get() == 'Serviços':
                esboco_texto = self.esboco_servico_text.get("1.0", tk.END).strip()
        except Exception:
            esboco_texto = None

        # Prevenir que um produto vire kit sem intenção: caso um registro existente de Produto/Serviço
        # esteja com tipo alterado para "Kit", forçar novo cadastro (não UPDATE)
        # Permitir editar normalmente um item Serviços (Kit), sem forçar novo cadastro
        try:
            if self.current_produto_id and self.loaded_tipo_atual and tipo == "Serviços" and self.loaded_tipo_atual == "Kit":
                pass
        except Exception:
            pass
            
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            if self.current_produto_id:
                # Atualizar produto
                c.execute("""
                    UPDATE produtos SET nome = ?, tipo = ?, ncm = ?, valor_unitario = ?,
                                      descricao = ?, esboco_servico = ?, categoria = ?, ativo = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    nome, tipo_db, self.ncm_var.get().strip(),
                    valor, self.descricao_var.get().strip(),
                    esboco_texto, categoria_db,
                    1 if self.ativo_var.get() else 0,
                    self.current_produto_id
                ))
                
                # Se for kit, limpar itens existentes
                if tipo == "Serviços":
                    c.execute("DELETE FROM kit_items WHERE kit_id = ?", (self.current_produto_id,))
            else:
                # Inserir novo produto
                c.execute("""
                    INSERT INTO produtos (nome, tipo, ncm, valor_unitario, descricao, esboco_servico, categoria, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nome, tipo_db, self.ncm_var.get().strip(),
                    valor, self.descricao_var.get().strip(),
                    esboco_texto, categoria_db,
                    1 if self.ativo_var.get() else 0
                ))
                self.current_produto_id = c.lastrowid
            
            # Se for kit, salvar itens
            if tipo == "Serviços":
                for item in self.kit_items:
                    c.execute("""
                        INSERT INTO kit_items (kit_id, produto_id, quantidade)
                        VALUES (?, ?, ?)
                    """, (self.current_produto_id, item['produto_id'], item['quantidade']))
            
            conn.commit()
            
            tipo_nome = "Serviços" if tipo == "Serviços" else ("Compressores" if tipo == "Compressores" else "Produto")
            self.show_success(f"{tipo_nome} salvo com sucesso!")
            
            # Emitir evento
            print(f"DEBUG PRODUTOS: Emitindo evento 'produto_created' para tipo: {tipo}")
            self.emit_event('produto_created')
            print("DEBUG PRODUTOS: Evento emitido com sucesso!")
            
            # Teste: emitir evento de teste
            print("DEBUG PRODUTOS: Emitindo evento de teste...")
            self.emit_event('test_event')
            print("DEBUG PRODUTOS: Evento de teste emitido!")
            
            self.carregar_produtos()
            self.carregar_produtos_para_kit()  # Atualizar lista para kits
            # Atualizar tipo carregado atual para refletir o registro em edição
            self.loaded_tipo_atual = ("Kit" if tipo == "Serviços" else tipo_db)
            # Evitar reaproveitar composição anterior em um novo kit
            if tipo == "Serviços":
                self.kit_items = []
                if hasattr(self, 'kit_items_tree'):
                    self.atualizar_kit_tree()
                # opcional: limpar campos de item
                self.item_produto_var.set("")
                self.item_quantidade_var.set("1")
                # manter dados do kit na tela para revisão, ou usar self.novo_kit() se desejar limpar tudo
                # self.novo_kit()
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao salvar {tipo.lower()}: {e}")
        finally:
            conn.close()
            
    def carregar_produtos(self):
        """Carregar lista de produtos em três abas por tipo"""
        # Limpar listas atuais
        if hasattr(self, 'trees_por_tipo'):
            for tipo, tree in self.trees_por_tipo.items():
                for item in tree.get_children():
                    tree.delete(item)
         
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
         
        try:
            # Buscar produtos
            c.execute("""
                SELECT id, nome, tipo, valor_unitario, ativo, COALESCE(categoria,'Geral')
                FROM produtos
                ORDER BY nome
            """)
            for row in c.fetchall():
                produto_id, nome, tipo, valor, ativo, categoria = row
                display_tipo = ("Serviços" if tipo == "Kit" else ("Compressores" if (tipo == "Produto" and (categoria or "") == "Compressores") else "Produto"))
                tree = self.trees_por_tipo.get(display_tipo)
                if tree is None:
                    continue
                tree.insert("", "end", values=(
                    nome,
                    format_currency(valor),
                    "Sim" if ativo else "Não"
                ), tags=(produto_id,))
         
        except sqlite3.Error as e:
            self.show_error(f"Erro ao carregar produtos: {e}")
        finally:
            conn.close()
             
    def buscar_produtos(self):
        """Buscar produtos com filtro nas três abas"""
        termo = self.search_var.get().strip()
         
        # Limpar listas atuais
        if hasattr(self, 'trees_por_tipo'):
            for tipo, tree in self.trees_por_tipo.items():
                for item in tree.get_children():
                    tree.delete(item)
         
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
         
        try:
            if termo:
                c.execute("""
                    SELECT id, nome, tipo, valor_unitario, ativo, COALESCE(categoria,'Geral')
                    FROM produtos
                    WHERE nome LIKE ? OR tipo LIKE ? OR descricao LIKE ? OR COALESCE(categoria,'Geral') LIKE ?
                    ORDER BY nome
                """, (f"%{termo}%", f"%{termo}%", f"%{termo}%", f"%{termo}%"))
            else:
                c.execute("""
                    SELECT id, nome, tipo, valor_unitario, ativo, COALESCE(categoria,'Geral')
                    FROM produtos
                    ORDER BY nome
                """)
             
            for row in c.fetchall():
                produto_id, nome, tipo, valor, ativo, categoria = row
                display_tipo = ("Serviços" if tipo == "Kit" else ("Compressores" if (tipo == "Produto" and (categoria or "") == "Compressores") else "Produto"))
                tree = self.trees_por_tipo.get(display_tipo)
                if tree is None:
                    continue
                tree.insert("", "end", values=(
                    nome,
                    format_currency(valor),
                    "Sim" if ativo else "Não"
                ), tags=(produto_id,))
         
        except sqlite3.Error as e:
            self.show_error(f"Erro ao buscar produtos: {e}")
        finally:
            conn.close()
            
    def on_produto_double_click(self, event):
        """Duplo clique na treeview - visualizar ou editar produto baseado nas permissões"""
        produto_id, _tree = self._get_selected_produto_id()
        if not produto_id:
            return
            
        if self.can_edit('produtos'):
            # Usuário pode editar - carregar para edição
            self.carregar_produto_para_edicao(produto_id)
            # Ir para a aba de criação/edição
            try:
                self.notebook.select(0)
            except Exception:
                pass
        else:
            # Usuário só pode visualizar - carregar dados em modo readonly
            self.visualizar_produto(produto_id)

    def editar_produto(self):
        """Editar/Visualizar produto selecionado baseado nas permissões"""
        produto_id, _tree = self._get_selected_produto_id()
        if not produto_id:
            self.show_warning("Selecione um produto/serviço/kit para editar/visualizar.")
            return
            
        if self.can_edit('produtos'):
            # Usuário pode editar - carregar normalmente
            self.carregar_produto_para_edicao(produto_id)
            # Ir imediatamente para a aba de criação/edição
            try:
                self.notebook.select(0)
            except Exception:
                pass
        else:
            # Usuário só pode visualizar - usar função de visualização
            self.visualizar_produto(produto_id)

    def excluir_produto(self):
        """Excluir produto/serviço/kit selecionado."""
        if not self.can_edit('produtos'):
            self.show_warning("Você não tem permissão para excluir produtos.")
            return
            
        produto_id, tree = self._get_selected_produto_id()
        if not produto_id:
            self.show_warning("Selecione um registro para excluir.")
            return
        if not messagebox.askyesno("Confirmar Exclusão", "Deseja realmente excluir este registro?\n(Itens de kit vinculados serão removidos.)"):
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            # Remover composições de kit onde este registro seja kit_id (se for kit)
            c.execute("DELETE FROM kit_items WHERE kit_id = ?", (produto_id,))
            # Remover referências onde este registro seja um item de kit
            c.execute("DELETE FROM kit_items WHERE produto_id = ?", (produto_id,))
            # Remover o próprio produto
            c.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
            conn.commit()
            self.show_success("Registro excluído com sucesso!")
            # Atualizar listas
            self.carregar_produtos()
            self.carregar_produtos_para_kit()
        except sqlite3.Error as e:
            self.show_error(f"Erro ao excluir: {e}")
        finally:
            conn.close()
        
    def carregar_produto_para_edicao(self, produto_id):
        """Carregar dados do produto para edição"""
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            c.execute("""
                SELECT id, nome, tipo, ncm, valor_unitario, descricao, esboco_servico, COALESCE(categoria,'Geral'), ativo
                FROM produtos WHERE id = ?
            """, (produto_id,))
            produto = c.fetchone()
            
            if not produto:
                self.show_error("Produto não encontrado.")
                return
                
            self.current_produto_id = produto_id
            # Flag para evitar interferência do on_tipo_changed durante carregamento
            self._carregando = True
            
            if produto[2] == "Kit":
                # Carregar kit - usar as variáveis padrão
                self.nome_var.set(produto[1] or "")  # nome
                self.tipo_var.set("Serviços")
                self.descricao_var.set(produto[5] or "")  # descricao
                # Garantir que o Valor Unitário também seja carregado para Serviços (Kit)
                try:
                    valor_unitario = produto[4] or 0
                    self.valor_var.set(f"{valor_unitario:.2f}")
                except Exception:
                    pass
                try:
                    if hasattr(self, 'esboco_servico_text'):
                        # Garantir que o campo esteja habilitado para escrever
                        try:
                            self.esboco_servico_text.config(state='normal')
                        except Exception:
                            pass
                        self.esboco_servico_text.delete("1.0", tk.END)
                        if produto[6]:
                            self.esboco_servico_text.insert("1.0", produto[6])
                except Exception:
                    pass
                self.ativo_var.set(bool(produto[8]))  # ativo
                self.loaded_tipo_atual = "Kit"
                
                # Garantir estado da UI
                self.on_tipo_changed(None)
                self.notebook.select(0)
                
                # Carregar itens do kit
                self.kit_items = []
                c.execute("""
                    SELECT p.id, p.nome, p.tipo, p.valor_unitario, ki.quantidade
                    FROM kit_items ki
                    JOIN produtos p ON ki.produto_id = p.id
                    WHERE ki.kit_id = ?
                """, (produto_id,))
                
                kit_items_data = c.fetchall()
                
                for item_row in kit_items_data:
                    item_id, nome, tipo, valor_unitario, quantidade = item_row
                    self.kit_items.append({
                        'produto_id': item_id,
                        'tipo': tipo,
                        'nome': nome,
                        'quantidade': quantidade
                    })
                
                # Atualizar interface do kit
                self.atualizar_kit_tree()
                
                # Garantir que a seção de kit seja exibida
                if hasattr(self, 'kit_section_frame'):
                    self.kit_section_frame.pack(fill="both", expand=True, pady=(15, 0))
                    
                # Recarregar produtos para o combobox
                self.carregar_produtos_para_kit()
                
            else:
                # Carregar produto/serviço/compressores
                self.nome_var.set(produto[1] or "")  # nome
                tipo_db = produto[2] or "Produto"
                categoria_db = produto[7] or "Geral"
                if tipo_db == "Produto" and categoria_db == "Compressores":
                    self.tipo_var.set("Compressores")
                else:
                    self.tipo_var.set(("Serviços" if tipo_db == "Kit" else tipo_db))
                self.ncm_var.set(produto[3] or "")  # ncm
                valor_unitario = produto[4] or 0
                self.valor_var.set(f"{valor_unitario:.2f}")  # valor_unitario
                self.descricao_var.set(produto[5] or "")  # descricao
                try:
                    if hasattr(self, 'esboco_servico_text'):
                        # Garantir que o campo esteja habilitado para receber o texto
                        try:
                            self.esboco_servico_text.config(state='normal')
                        except Exception:
                            pass
                        self.esboco_servico_text.delete("1.0", tk.END)
                        if produto[6]:
                            self.esboco_servico_text.insert("1.0", produto[6])
                except Exception:
                    pass
                self.ativo_var.set(bool(produto[8]))  # ativo
                self.loaded_tipo_atual = (tipo_db)
                
                # Garantir estado da UI (NCM/Kit)
                self.on_tipo_changed(None)
                self.notebook.select(0)  # Ir para aba de produto/serviço
                # Se não for kit, ocultar a seção de kit
                if hasattr(self, 'kit_section_frame'):
                    self.kit_section_frame.pack_forget()
                
        except sqlite3.Error as e:
            self.show_error(f"Erro ao carregar produto: {e}")
        finally:
            conn.close()
            # Remover flag de carregamento
            self._carregando = False
            
    def toggle_ativo(self):
        """Ativar/desativar produto selecionado (qualquer aba)."""
        if not self.can_edit('produtos'):
            self.show_warning("Você não tem permissão para alterar status de produtos.")
            return
            
        produto_id, tree = self._get_selected_produto_id()
        if not produto_id:
            self.show_warning("Selecione um produto para ativar/desativar.")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            c.execute("UPDATE produtos SET ativo = NOT ativo WHERE id = ?", (produto_id,))
            conn.commit()
            
            self.show_success("Status do produto alterado com sucesso!")
            self.carregar_produtos()
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao alterar status: {e}")
        finally:
            conn.close()

    def atualizar_combo_items(self):
        """Atualizar combo com produtos e serviços disponíveis"""
        self.on_item_tipo_changed()
        
    def on_item_tipo_changed(self, event=None):
        """Atualizar combo de itens baseado no tipo selecionado"""
        tipo = self.item_tipo_var.get()
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            c.execute("SELECT id, nome, valor_unitario FROM produtos WHERE tipo = ? AND ativo = 1 ORDER BY nome", (tipo,))
            items = c.fetchall()
            
            values = [f"{item[1]} - R$ {item[2]:.2f}" for item in items]
            self.item_combo['values'] = values
            self.item_combo.set("")
            
            # Armazenar dados para uso posterior
            self.items_data = {f"{item[1]} - R$ {item[2]:.2f}": item for item in items}
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao carregar itens: {e}")
        finally:
            conn.close()
            
    def adicionar_item_kit(self):
        """Adicionar item à composição do kit"""
        if not self.can_edit('produtos'):
            self.show_warning("Você não tem permissão para adicionar itens ao kit.")
            return
            
        if not self.item_produto_var.get():
            self.show_warning("Selecione um produto/serviço!")
            return
            
        try:
            quantidade = float(self.item_quantidade_var.get())
            if quantidade <= 0:
                raise ValueError()
        except ValueError:
            self.show_error("Quantidade deve ser um número positivo!")
            return
        
        # Obter dados do produto selecionado
        index = self.produto_kit_combo.current()
        if index < 0:
            self.show_warning("Produto não selecionado corretamente!")
            return
            
        if not hasattr(self, 'produtos_kit_map') or index not in self.produtos_kit_map:
            self.show_warning("Erro ao obter dados do produto!")
            return
            
        produto_id = self.produtos_kit_map[index]
        produto_nome, produto_tipo = self.produtos_kit_data[index][1], 'Produto'
        
        # Verificar se já existe
        for item in self.kit_items:
            if item['produto_id'] == produto_id:
                self.show_warning("Este produto já está no kit!")
                return
        
        # Adicionar à lista
        item = {
            'produto_id': produto_id,
            'nome': produto_nome,
            'tipo': produto_tipo,
            'quantidade': quantidade
        }
        self.kit_items.append(item)
        
        # Atualizar treeview
        self.atualizar_kit_tree()
        
        # Limpar campos
        self.item_produto_var.set("")
        self.item_quantidade_var.set("1")
        
    def atualizar_kit_tree(self):
        """Atualizar a treeview de itens do kit"""
        if not hasattr(self, 'kit_items_tree'):
            print("DEBUG: ERRO - kit_items_tree não encontrado")  # Debug
            return
            
        print(f"DEBUG: Atualizando kit tree com {len(self.kit_items)} itens")  # Debug
        
        # Limpar treeview
        for item in self.kit_items_tree.get_children():
            self.kit_items_tree.delete(item)
        
        # Adicionar itens
        for i, item in enumerate(self.kit_items):
            print(f"DEBUG: Inserindo item {i}: {item['nome']} - {item['tipo']} - Qtd: {item['quantidade']}")  # Debug
            self.kit_items_tree.insert("", "end", text=str(i), values=(
                item['nome'],
                item['tipo'],
                f"{item['quantidade']:.2f}"
            ))
        
        print(f"DEBUG: Kit tree atualizada com {len(self.kit_items_tree.get_children())} itens visíveis")  # Debug
        
    def remover_item_kit(self):
        """Remover item selecionado do kit"""
        if not self.can_edit('produtos'):
            self.show_warning("Você não tem permissão para modificar kits.")
            return
            
        if not hasattr(self, 'kit_items_tree'):
            return
            
        selection = self.kit_items_tree.selection()
        if not selection:
            self.show_warning("Selecione um item para remover!")
            return
        
        # Obter índice do item
        item_id = self.kit_items_tree.item(selection[0])['text']
        try:
            index = int(item_id)
            if 0 <= index < len(self.kit_items):
                del self.kit_items[index]
                self.atualizar_kit_tree()
        except (ValueError, IndexError):
            self.show_error("Erro ao remover item!")
        
    def novo_kit(self):
        """Limpar formulário para novo kit"""
        self.current_produto_id = None
        self.nome_var.set("")
        self.tipo_var.set("Kit")
        self.descricao_var.set("")
        self.ativo_var.set(True)
        self.kit_items = []
        if hasattr(self, 'kit_items_tree'):
            self.atualizar_kit_tree()
        
    def _get_selected_produto_id(self):
        """Retorna (produto_id, tree_obj) da primeira aba com seleção."""
        if not hasattr(self, 'trees_por_tipo'):
            return None, None
        for tipo, tree in self.trees_por_tipo.items():
            try:
                selected = tree.selection()
                if selected:
                    tags = tree.item(selected[0]).get('tags')
                    if tags:
                        return tags[0], tree
            except Exception:
                continue
        return None, None
        
    def visualizar_produto(self, produto_id):
        """Visualizar dados do produto em modo readonly"""
        # Carregar os dados do produto primeiro
        self.carregar_produto_para_edicao(produto_id)
        
        # Ir para a aba de criação/edição para mostrar os dados
        try:
            self.notebook.select(0)
        except Exception:
            pass
            
        # Aguardar um momento para garantir que os dados sejam carregados
        self.frame.after(100, lambda: self._aplicar_readonly_visualizacao())
        
        # Mostrar mensagem informativa
        self.show_info("Visualizando produto em modo consulta. Os dados não podem ser editados.")
        
    def _aplicar_readonly_visualizacao(self):
        """Aplica readonly após os dados serem carregados"""
        if not self.can_edit('produtos'):
            self.apply_readonly_for_visualization()
        
