import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
from datetime import datetime, date
from .base_module import BaseModule
from database import DB_NAME
from utils.formatters import format_currency, format_date, clean_number
from utils.cotacao_validator import verificar_e_atualizar_status_cotacoes, obter_cotacoes_por_status
from pdf_generators.cotacao_nova import gerar_pdf_cotacao_nova

class OrcamentoProdutosModule(BaseModule):
	# Chave de permissão explícita
	module_key = 'orcamento_produtos'
	def setup_ui(self):
		# O listener já é registrado no BaseModule, não precisa registrar novamente
		# Inicializar variáveis primeiro
		self.current_cotacao_id = None
		self.current_cotacao_itens = []
		
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
		
		# Painel de cotação (esquerda)
		form_panel = tk.Frame(main_frame, bg='#f8fafc')
		form_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=(10, 10))
		form_panel.grid_columnconfigure(0, weight=1)
		
		# Botões fixos no rodapé do painel de formulário
		self.create_cotacao_buttons(form_panel)
		
		# Área rolável para o conteúdo do formulário
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
		
		# Suporte a rolagem pelo mouse
		def _on_mousewheel(event):
			delta = 0
			if hasattr(event, 'delta') and event.delta:
				delta = int(-event.delta / 120)
			elif getattr(event, 'num', None) in (4, 5):
				delta = -1 if event.num == 5 else 1
			if delta:
				form_canvas.yview_scroll(delta, "units")
		form_canvas.bind_all("<MouseWheel>", _on_mousewheel)
		form_canvas.bind_all("<Button-4>", _on_mousewheel)
		form_canvas.bind_all("<Button-5>", _on_mousewheel)
		
		# Conteúdo do formulário
		self.create_cotacao_content(form_inner)

		# Preencher número sequencial automaticamente ao abrir, se não houver cotação carregada
		try:
			if not self.current_cotacao_id:
				numero = self.gerar_numero_sequencial()
				self.numero_var.set(numero)
		except Exception as e:
			print(f"Aviso ao gerar número sequencial inicial de cotação: {e}")
		
		# Painel da lista (direita)
		lista_panel = tk.Frame(main_frame, bg='#f8fafc')
		lista_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 10), pady=(10, 10))
		lista_panel.grid_columnconfigure(0, weight=1)
		lista_panel.grid_rowconfigure(2, weight=1)
		
		lista_card = tk.Frame(lista_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
		lista_card.pack(fill="both", expand=True)
		
		tk.Label(lista_card, text="📋 Lista de Cotações", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(fill="x", padx=12, pady=(12, 8))
		
		lista_inner = tk.Frame(lista_card, bg='white')
		lista_inner.pack(fill="both", expand=True, padx=12, pady=(0, 12))
		
		# Busca
		search_frame, self.search_var = self.create_search_frame(lista_inner, command=self.buscar_cotacoes)
		search_frame.pack(fill="x", pady=(0, 10))
		
		# Reservar rodapé dos botões da lista antes da Treeview
		lista_buttons = tk.Frame(lista_inner, bg='white')
		lista_buttons.pack(side="bottom", fill="x", pady=(10, 0))
		
		# Treeview
		columns = ("numero", "cliente", "data", "valor", "status")
		self.cotacoes_tree = ttk.Treeview(lista_inner, columns=columns, show="headings")
		self.cotacoes_tree.heading("numero", text="Número")
		self.cotacoes_tree.heading("cliente", text="Cliente")
		self.cotacoes_tree.heading("data", text="Data")
		self.cotacoes_tree.heading("valor", text="Valor")
		self.cotacoes_tree.heading("status", text="Status")
		self.cotacoes_tree.column("numero", width=150)
		self.cotacoes_tree.column("cliente", width=250)
		self.cotacoes_tree.column("data", width=100)
		self.cotacoes_tree.column("valor", width=120)
		self.cotacoes_tree.column("status", width=100)
		
		lista_scrollbar = ttk.Scrollbar(lista_inner, orient="vertical", command=self.cotacoes_tree.yview)
		self.cotacoes_tree.configure(yscrollcommand=lista_scrollbar.set)
		
		self.cotacoes_tree.pack(side="left", fill="both", expand=True)
		lista_scrollbar.pack(side="right", fill="y")
		
		# Botões da lista
		editar_btn = self.create_button(lista_buttons, "Editar", self.editar_cotacao)
		editar_btn.pack(side="left", padx=(0, 10))
		
		duplicar_btn = self.create_button(lista_buttons, "Duplicar", self.duplicar_cotacao, bg='#f59e0b')
		duplicar_btn.pack(side="left", padx=(0, 10))
		
		gerar_pdf_lista_btn = self.create_button(lista_buttons, "Gerar PDF", self.gerar_pdf_selecionado, bg='#10b981')
		gerar_pdf_lista_btn.pack(side="right", padx=(0, 10))
		
		abrir_pdf_lista_btn = self.create_button(lista_buttons, "Abrir PDF", self.abrir_pdf_selecionado, bg='#3b82f6')
		abrir_pdf_lista_btn.pack(side="right")
		
		# Dados iniciais
		self.refresh_all_data()
		
	def create_header(self, parent):
		header_frame = tk.Frame(parent, bg='#f8fafc')
		header_frame.pack(fill="x", pady=(0, 10))
		
		title_label = tk.Label(header_frame, text="Orçamento de Produtos", 
						   font=('Arial', 16, 'bold'),
						   bg='#f8fafc',
						   fg='#1e293b')
		title_label.pack(side="left")
		
	# Estrutura antiga baseada em notebook removida; conteúdo agora no layout único
	def create_cotacao_content(self, parent):
		# Frame principal com grid 2 colunas, 100% da tela
		main_grid = tk.Frame(parent, bg='white')
		main_grid.pack(fill="both", expand=True)

		# Layout otimizado: dados compactos no topo, itens expandidos embaixo
		main_grid.grid_columnconfigure(0, weight=1)
		main_grid.grid_rowconfigure(0, weight=0)  # Dados: altura fixa
		main_grid.grid_rowconfigure(1, weight=1)  # Itens: expansível

		# Dados da cotação (altura compacta)
		dados_frame = tk.Frame(main_grid, bg='white', relief='groove', bd=2)
		dados_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
		self.create_dados_cotacao_section(dados_frame)
		
		# Itens da cotação (área expandida)
		itens_frame = tk.Frame(main_grid, bg='white', relief='groove', bd=2)
		itens_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0, 2))
		self.create_itens_cotacao_section(itens_frame)

		# Botões de ação já estão fixos no rodapé do painel de formulário (setup_ui)
		
	def create_dados_cotacao_section(self, parent):
		section_frame = self.create_section_frame(parent, "Dados da Cotação")
		section_frame.pack(fill="x", pady=(0, 5))
		
		# Grid de campos
		fields_frame = tk.Frame(section_frame, bg='white')
		fields_frame.pack(fill="x")
		
		# Variáveis
		self.numero_var = tk.StringVar()
		self.cliente_var = tk.StringVar()
		self.contato_cliente_var = tk.StringVar()
		self.filial_var = tk.StringVar(value="2")  # Default para World Comp do Brasil
		self.modelo_var = tk.StringVar()
		self.serie_var = tk.StringVar()
		self.status_var = tk.StringVar(value="Em Aberto")
		self.data_validade_var = tk.StringVar()
		self.condicao_pagamento_var = tk.StringVar()
		self.prazo_entrega_var = tk.StringVar()
		self.tipo_frete_var = tk.StringVar(value="FOB")
		self.observacoes_var = tk.StringVar()
		# Novas variáveis de cotação e locação
		self.tipo_cotacao_var = tk.StringVar(value="Compra")
		self.locacao_valor_mensal_var = tk.StringVar(value="0.00")
		self.locacao_data_inicio_var = tk.StringVar()
		self.locacao_data_fim_var = tk.StringVar()
		self.locacao_qtd_meses_var = tk.StringVar(value="0")
		self.locacao_total_var = tk.StringVar(value="R$ 0,00")
		self.locacao_equipamento_var = tk.StringVar()
		
		row = 0
		
		# Número da Proposta
		tk.Label(fields_frame, text="Número da Proposta *:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		tk.Entry(fields_frame, textvariable=self.numero_var, 
				 font=('Arial', 10), width=30).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1
		
		# Filial
		tk.Label(fields_frame, text="Filial *:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		filial_combo = ttk.Combobox(fields_frame, textvariable=self.filial_var, 
							   values=["1 - WORLD COMP COMPRESSORES LTDA", 
								  "2 - WORLD COMP DO BRASIL COMPRESSORES LTDA"], 
							   width=45, state="readonly")
		filial_combo.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		# Mostrar/ocultar ICMS conforme filial (sempre visível para Filial 2)
		def on_filial_changed(_e=None):
			try:
				filial_str = self.filial_var.get()
				filial_id = int(filial_str.split(' - ')[0]) if ' - ' in filial_str else int(filial_str)
				if filial_id == 2:
					# posicionar ICMS na linha principal de compra
					try:
						self.icms_label.grid(row=0, column=6, padx=5, sticky="w")
						self.icms_entry.grid(row=0, column=7, padx=5, sticky="w")
					except Exception:
						pass
				else:
					self.icms_label.grid_remove()
					self.icms_entry.grid_remove()
			except Exception:
				pass
		filial_combo.bind('<<ComboboxSelected>>', on_filial_changed)
		# Inicializar visibilidade
		on_filial_changed()
		row += 1
		
		# Tipo de Cotação fixo como "Compra" para Produtos
		row += 1
		
		# Cliente com busca reativa
		tk.Label(fields_frame, text="Cliente *:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		
		cliente_frame = tk.Frame(fields_frame, bg='white')
		cliente_frame.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		
		self.cliente_combo = ttk.Combobox(cliente_frame, textvariable=self.cliente_var, width=25)
		self.cliente_combo.pack(side="left", fill="x", expand=True)
		self.cliente_combo.bind("<<ComboboxSelected>>", self.on_cliente_selected)
		
		# Refresh button removed
		
		row += 1
		# Contato do Cliente
		tk.Label(fields_frame, text="Contato:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		self.contato_cliente_combo = ttk.Combobox(fields_frame, textvariable=self.contato_cliente_var, width=27, state="readonly")
		self.contato_cliente_combo.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1
		
		# Modelo e Série (ocultos para locação)
		self.modelo_label = tk.Label(fields_frame, text="Modelo do Compressor:", 
				 font=('Arial', 10, 'bold'), bg='white')
		self.modelo_label.grid(row=row, column=0, sticky="w", pady=5)
		self.modelo_entry = tk.Entry(fields_frame, textvariable=self.modelo_var, 
				 font=('Arial', 10), width=30)
		self.modelo_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1
		
		self.serie_label = tk.Label(fields_frame, text="Número de Série:", 
				 font=('Arial', 10, 'bold'), bg='white')
		self.serie_label.grid(row=row, column=0, sticky="w", pady=5)
		self.serie_entry = tk.Entry(fields_frame, textvariable=self.serie_var, 
				 font=('Arial', 10), width=30)
		self.serie_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1
		
		# Status (oculto para locação)
		self.status_label = tk.Label(fields_frame, text="Status:", 
				 font=('Arial', 10, 'bold'), bg='white')
		self.status_label.grid(row=row, column=0, sticky="w", pady=5)
		self.status_combo = ttk.Combobox(fields_frame, textvariable=self.status_var, 
							   values=["Em Aberto", "Aprovada", "Rejeitada"], 
							   width=27, state="readonly")
		self.status_combo.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1
		
		# Data de Validade (oculta para locação)
		self.data_validade_label = tk.Label(fields_frame, text="Data de Validade:", 
				 font=('Arial', 10, 'bold'), bg='white')
		self.data_validade_label.grid(row=row, column=0, sticky="w", pady=5)
		self.data_validade_entry = tk.Entry(fields_frame, textvariable=self.data_validade_var, 
				 font=('Arial', 10), width=30)
		self.data_validade_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1
		
		# Condição de Pagamento (oculta para locação)
		self.condicao_pagamento_label = tk.Label(fields_frame, text="Condição de Pagamento:", 
				 font=('Arial', 10, 'bold'), bg='white')
		self.condicao_pagamento_label.grid(row=row, column=0, sticky="w", pady=5)
		self.condicao_pagamento_entry = tk.Entry(fields_frame, textvariable=self.condicao_pagamento_var, 
				 font=('Arial', 10), width=30)
		self.condicao_pagamento_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1
		
		# Tipo de Frete (oculto para locação)
		self.tipo_frete_label = tk.Label(fields_frame, text="Tipo de Frete:", 
				 font=('Arial', 10, 'bold'), bg='white')
		self.tipo_frete_label.grid(row=row, column=0, sticky="w", pady=5)
		self.tipo_frete_combo = ttk.Combobox(fields_frame, textvariable=self.tipo_frete_var, 
				 values=["FOB", "CIF", "A combinar"], width=27, state="readonly")
		self.tipo_frete_combo.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=5)
		row += 1

		# Prazo de Entrega (oculto para locação)
		self.prazo_entrega_label = tk.Label(fields_frame, text="Prazo de Entrega:", 
				 font=('Arial', 10, 'bold'), bg='white')
		self.prazo_entrega_label.grid(row=row, column=0, sticky="w", pady=5)
		self.prazo_entrega_entry = tk.Entry(fields_frame, textvariable=self.prazo_entrega_var, 
				 font=('Arial', 10), width=30)
		self.prazo_entrega_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1
		
		# Seção de Locação (inicialmente oculta)
		self.locacao_frame = tk.Frame(section_frame, bg='white')
		self.locacao_frame.pack(fill="x", pady=(0, 10))
		loc_grid = tk.Frame(self.locacao_frame, bg='white')
		loc_grid.pack(fill="x", padx=10, pady=5)
		lrow = 0
		tk.Label(loc_grid, text="Nome do Equipamento *:", font=('Arial', 10, 'bold'), bg='white').grid(row=lrow, column=0, sticky="w", pady=5)
		tk.Entry(loc_grid, textvariable=self.locacao_equipamento_var, font=('Arial', 10), width=30).grid(row=lrow, column=1, sticky="ew", padx=(10, 0), pady=5)
		lrow += 1
		tk.Label(loc_grid, text="Valor Mensal (R$) *:", font=('Arial', 10, 'bold'), bg='white').grid(row=lrow, column=0, sticky="w", pady=5)
		tk.Entry(loc_grid, textvariable=self.locacao_valor_mensal_var, font=('Arial', 10), width=20).grid(row=lrow, column=1, sticky="w", padx=(10, 0), pady=5)
		lrow += 1
		tk.Label(loc_grid, text="Data Início (DD/MM/AAAA) *:", font=('Arial', 10, 'bold'), bg='white').grid(row=lrow, column=0, sticky="w", pady=5)
		tk.Entry(loc_grid, textvariable=self.locacao_data_inicio_var, font=('Arial', 10), width=20).grid(row=lrow, column=1, sticky="w", padx=(10, 0), pady=5)
		lrow += 1
		tk.Label(loc_grid, text="Data Fim (DD/MM/AAAA) *:", font=('Arial', 10, 'bold'), bg='white').grid(row=lrow, column=0, sticky="w", pady=5)
		tk.Entry(loc_grid, textvariable=self.locacao_data_fim_var, font=('Arial', 10), width=20).grid(row=lrow, column=1, sticky="w", padx=(10, 0), pady=5)
		lrow += 1
		tk.Label(loc_grid, text="Meses:", font=('Arial', 10, 'bold'), bg='white').grid(row=lrow, column=0, sticky="w", pady=5)
		self.locacao_meses_entry = tk.Entry(loc_grid, textvariable=self.locacao_qtd_meses_var, font=('Arial', 10), width=10, state="readonly")
		self.locacao_meses_entry.grid(row=lrow, column=1, sticky="w", padx=(10, 0), pady=5)
		lrow += 1
		tk.Label(loc_grid, text="Total Locação:", font=('Arial', 10, 'bold'), bg='white').grid(row=lrow, column=0, sticky="w", pady=5)
		self.locacao_total_entry = tk.Entry(loc_grid, textvariable=self.locacao_total_var, font=('Arial', 10), width=20, state="readonly")
		self.locacao_total_entry.grid(row=lrow, column=1, sticky="w", padx=(10, 0), pady=5)
		# Ocultar inicialmente
		self.locacao_frame.pack_forget()
		# Recalcular ao alterar campos
		self.locacao_valor_mensal_var.trace_add('write', lambda *args: self.recalcular_locacao())
		self.locacao_data_inicio_var.trace_add('write', lambda *args: self.recalcular_locacao())
		self.locacao_data_fim_var.trace_add('write', lambda *args: self.recalcular_locacao())
		
		# Observações (mais compacto)
		tk.Label(fields_frame, text="Observações:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="nw", pady=2)
		self.observacoes_text = scrolledtext.ScrolledText(fields_frame, height=2, width=30)
		self.observacoes_text.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=2)
		
		fields_frame.grid_columnconfigure(1, weight=1)
		
		# Seções específicas removidas para Orçamento de Produtos (sem esboço/peças)
		
	# Dashboards removidos deste módulo
	
	# Seções de esboço e relação de peças removidas deste módulo
		
	def create_itens_cotacao_section(self, parent):
		section_frame = self.create_section_frame(parent, "Itens da Cotação")
		section_frame.pack(fill="both", expand=True, pady=(0, 5))
		self.itens_section = section_frame
		
		# Frame para adicionar item
		add_item_frame = tk.Frame(section_frame, bg='white')
		add_item_frame.pack(fill="x", pady=(0, 10))
		
		# Campos para novo item
		self.create_item_fields(add_item_frame)
		
		# Lista de itens
		self.create_itens_list(section_frame)
		
	def create_item_fields(self, parent):
		# Variáveis
		self.item_tipo_var = tk.StringVar()
		self.item_nome_var = tk.StringVar()
		self.item_qtd_var = tk.StringVar(value="1")
		self.item_valor_var = tk.StringVar(value="0.00")
		self.item_desc_var = tk.StringVar()
		self.item_mao_obra_var = tk.StringVar(value="0.00")
		self.item_deslocamento_var = tk.StringVar(value="0.00")
		self.item_estadia_var = tk.StringVar(value="0.00")
		self.item_tipo_operacao_var = tk.StringVar(value="Compra")
		# Novos campos por item (locação)
		self.item_loc_inicio_var = tk.StringVar()
		self.item_loc_fim_var = tk.StringVar()
		self.item_loc_meses_var = tk.StringVar(value="0")
		self.item_loc_total_var = tk.StringVar(value="R$ 0,00")
		self.item_modelo_compressor_var = tk.StringVar()
		
		# Fixar tipo como Produto para este módulo
		self.item_tipo_var.set('Produto')
		# Container principal para os dois layouts
		fields_container = tk.Frame(parent, bg="white")
		fields_container.pack(padx=10, pady=(0, 10), fill="x")
		
		# ===== LAYOUT PARA COMPRA (ORIGINAL) =====
		self.compra_fields_frame = tk.Frame(fields_container, bg="white")
		
		# Grid de campos para compra (layout original)
		compra_grid = tk.Frame(self.compra_fields_frame, bg="white")
		compra_grid.pack(fill="x")
		
		# Primeira linha - layout original para compra
		self.tipo_label = tk.Label(compra_grid, text="Tipo:", font=("Arial", 10, "bold"), bg="white")
		self.tipo_label.grid(row=0, column=0, padx=5, sticky="w")
		
		# Tipo fixo como "Produto" - não é um combobox
		tipo_label = tk.Label(compra_grid, text="Produto", 
							  font=("Arial", 10), bg="white", fg='#059669')
		tipo_label.grid(row=0, column=1, padx=(2, 5), sticky="w")
		
		tk.Label(compra_grid, text="Qtd:", font=("Arial", 10, "bold"), bg="white").grid(row=0, column=2, padx=5, sticky="w")
		tk.Entry(compra_grid, textvariable=self.item_qtd_var, width=5).grid(row=0, column=3, padx=5)
		
		tk.Label(compra_grid, text="Valor Unit.:", font=("Arial", 10, "bold"), bg="white").grid(row=0, column=4, padx=5, sticky="w")
		tk.Entry(compra_grid, textvariable=self.item_valor_var, width=12).grid(row=0, column=5, padx=5)
		
		# Segunda linha - Nome e Descrição para compra
		self.nome_label_compra = tk.Label(compra_grid, text="Nome:", font=("Arial", 10, "bold"), bg="white")
		self.nome_label_compra.grid(row=1, column=0, padx=5, sticky="w")
		
		nome_frame_compra = tk.Frame(compra_grid, bg='white')
		nome_frame_compra.grid(row=1, column=1, columnspan=3, padx=5, sticky="ew")
		
		self.item_nome_combo_compra = ttk.Combobox(nome_frame_compra, textvariable=self.item_nome_var, width=30)
		self.item_nome_combo_compra.pack(side="left", fill="x", expand=True)
		self.item_nome_combo_compra.bind("<<ComboboxSelected>>", self.on_item_selected)
		
		# Terceira linha - Descrição para compra
		tk.Label(compra_grid, text="Descrição:", font=("Arial", 10, "bold"), bg="white").grid(row=2, column=0, padx=5, sticky="w")
		tk.Entry(compra_grid, textvariable=self.item_desc_var, width=60).grid(row=2, column=1, columnspan=3, padx=5, sticky="ew")
		
		# Quarta linha - Campos de serviço para compra
		# Campos específicos de serviços removidos para Produtos
		
		# ICMS (apenas quando filial = 2) - alinhado no grid principal de compra
		self.item_icms_var = tk.StringVar(value="0.00")
		self.icms_label = tk.Label(compra_grid, text="ICMS:", font=("Arial", 10, "bold"), bg="white")
		self.icms_entry = tk.Entry(compra_grid, textvariable=self.item_icms_var, width=12)
		
		# Botão adicionar para compra
		adicionar_button_compra = self.create_button(compra_grid, "Adicionar Item", self.adicionar_item)
		adicionar_button_compra.grid(row=4, column=0, columnspan=6, pady=10)
		
		# Configurar grid para compra
		compra_grid.grid_columnconfigure(1, weight=1)
		compra_grid.grid_columnconfigure(2, weight=1)
		compra_grid.grid_columnconfigure(3, weight=1)

		# Garantir que a lista de nomes esteja populada após montar a UI
		try:
			self.frame.after_idle(self._force_update_nome_compra)
		except Exception:
			pass
		
		# ===== LAYOUT PARA LOCAÇÃO (NOVO) =====
		self.locacao_fields_frame = tk.Frame(fields_container, bg="white")
		
		# Grid de campos para locação (layout novo)
		locacao_grid = tk.Frame(self.locacao_fields_frame, bg="white")
		locacao_grid.pack(fill="x")
		
		# Primeira linha - Nome do Equipamento para locação (combobox de Compressores)
		self.nome_label_locacao = tk.Label(locacao_grid, text="Nome do Equipamento:", font=("Arial", 10, "bold"), bg="white")
		self.nome_label_locacao.grid(row=0, column=0, padx=5, sticky="w")
		
		nome_frame_locacao = tk.Frame(locacao_grid, bg='white')
		nome_frame_locacao.grid(row=0, column=1, columnspan=3, padx=5, sticky="ew")
		
		self.item_nome_combo_locacao = ttk.Combobox(nome_frame_locacao, textvariable=self.item_nome_var, width=40, state="readonly")
		self.item_nome_combo_locacao.pack(side="left", fill="x", expand=True)
		self.item_nome_combo_locacao.bind("<<ComboboxSelected>>", self.on_item_selected)
		
		# Segunda linha - Descrição para locação
		tk.Label(locacao_grid, text="Descrição:", font=("Arial", 10, "bold"), bg="white").grid(row=1, column=0, padx=5, sticky="w")
		tk.Entry(locacao_grid, textvariable=self.item_desc_var, width=60).grid(row=1, column=1, columnspan=3, padx=5, sticky="ew")
		
		# Terceira linha - Data Início e Data Fim para locação
		tk.Label(locacao_grid, text="Data Início (DD/MM/AAAA):", font=("Arial", 10, "bold"), bg="white").grid(row=2, column=0, padx=5, sticky="w")
		tk.Entry(locacao_grid, textvariable=self.item_loc_inicio_var, width=15).grid(row=2, column=1, padx=5, sticky="w")
		
		tk.Label(locacao_grid, text="Data Fim (DD/MM/AAAA):", font=("Arial", 10, "bold"), bg="white").grid(row=2, column=2, padx=(30, 5), sticky="w")
		tk.Entry(locacao_grid, textvariable=self.item_loc_fim_var, width=15).grid(row=2, column=3, padx=5, sticky="w")
		
		# Quarta linha - Meses e Total Item para locação
		tk.Label(locacao_grid, text="Meses:", font=("Arial", 10, "bold"), bg="white").grid(row=3, column=0, padx=5, sticky="w")
		self.item_loc_meses_entry = tk.Entry(locacao_grid, textvariable=self.item_loc_meses_var, width=8, state="readonly")
		self.item_loc_meses_entry.grid(row=3, column=1, padx=5, sticky="w")
		
		tk.Label(locacao_grid, text="Total Item:", font=("Arial", 10, "bold"), bg="white").grid(row=3, column=2, padx=(30, 5), sticky="w")
		self.item_loc_total_entry = tk.Entry(locacao_grid, textvariable=self.item_loc_total_var, width=15, state="readonly")
		self.item_loc_total_entry.grid(row=3, column=3, padx=5, sticky="w")
		
		# Quinta linha - Modelo do Compressor para locação
		tk.Label(locacao_grid, text="Modelo do Compressor:", font=("Arial", 10, "bold"), bg="white").grid(row=4, column=0, padx=5, sticky="w")
		tk.Entry(locacao_grid, textvariable=self.item_modelo_compressor_var, width=50).grid(row=4, column=1, columnspan=3, padx=5, sticky="ew")
		
		# Sexta linha - Qtd e Valor Unit./Mensal para locação
		tk.Label(locacao_grid, text="Qtd.:", font=("Arial", 10, "bold"), bg="white").grid(row=5, column=0, padx=5, sticky="w")
		tk.Entry(locacao_grid, textvariable=self.item_qtd_var, width=8).grid(row=5, column=1, padx=5, sticky="w")
		
		tk.Label(locacao_grid, text="Valor Unit./Mensal:", font=("Arial", 10, "bold"), bg="white").grid(row=5, column=2, padx=(30, 5), sticky="w")
		tk.Entry(locacao_grid, textvariable=self.item_valor_var, width=15).grid(row=5, column=3, padx=5, sticky="w")
		
		# Sétima linha - Imagem do Equipamento para locação
		tk.Label(locacao_grid, text="Imagem do Equipamento:", font=("Arial", 10, "bold"), bg="white").grid(row=6, column=0, padx=5, sticky="w")
		
		self.locacao_imagem_var = tk.StringVar()
		img_frame = tk.Frame(locacao_grid, bg='white')
		img_frame.grid(row=6, column=1, columnspan=3, sticky="ew", padx=5, pady=5)
		
		self.locacao_imagem_entry = tk.Entry(img_frame, textvariable=self.locacao_imagem_var, font=('Arial', 10), width=35)
		self.locacao_imagem_entry.pack(side="left", fill="x", expand=True)
		
		def _pick_image():
			from tkinter import filedialog
			path = filedialog.askopenfilename(title="Selecionar Imagem do Equipamento",
											   filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.gif"), ("Todos", "*.*")])
			if path:
				self.locacao_imagem_var.set(path)
		
		picker_btn = self.create_button(img_frame, "Selecionar...", _pick_image, bg='#10b981')
		picker_btn.pack(side="right", padx=(5, 0))
		
		# Configurar grid para locação
		locacao_grid.grid_columnconfigure(1, weight=1)
		locacao_grid.grid_columnconfigure(2, weight=1)
		locacao_grid.grid_columnconfigure(3, weight=1)
		
		# Botão adicionar para locação
		adicionar_button_locacao = self.create_button(locacao_grid, "Adicionar Item", self.adicionar_item)
		adicionar_button_locacao.grid(row=7, column=0, columnspan=4, pady=15)
		
		# Bindings para calcular meses e total automaticamente
		self.item_loc_inicio_var.trace_add('write', lambda *args: self.recalcular_locacao_item())
		self.item_loc_fim_var.trace_add('write', lambda *args: self.recalcular_locacao_item())
		self.item_valor_var.trace_add('write', lambda *args: self.recalcular_locacao_item())
		
		# Inicialmente mostrar layout de compra
		self.compra_fields_frame.pack(fill="x")
		self.locacao_fields_frame.pack_forget()
		# Carregar lista de compressores para locação
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute("SELECT nome FROM produtos WHERE tipo = 'Produto' AND COALESCE(categoria,'Geral')='Compressores' AND ativo = 1 ORDER BY nome")
			comp_list = [row[0] for row in c.fetchall()]
			self.item_nome_combo_locacao['values'] = comp_list
		finally:
			try:
				conn.close()
			except Exception:
				pass
		
	def on_tipo_changed(self, event=None):
		"""Callback quando o tipo do item muda - sempre Produto"""
		# Campos de serviço já foram removidos para Produtos
		# Atualizar lista de produtos
		self.update_produtos_combo()
		
	def on_tipo_cotacao_changed(self, event=None):
		"""Alternar entre fluxo de Compra e Locação"""
		modo = self.tipo_cotacao_var.get()
		
		# Sempre manter seção de itens visível
		if hasattr(self, 'itens_section'):
			self.itens_section.pack(fill="both", expand=True, pady=(0, 10))
		
		# Mostrar/ocultar seções baseado no tipo de cotação
		if modo == "Locação":
			# Nada a ocultar além dos layouts de compra/locação
			# Ocultar seção de locação principal (não é mais necessária)
			if hasattr(self, 'locacao_frame'):
				self.locacao_frame.pack_forget()
			
			# Mostrar layout de locação, ocultar layout de compra
			self.compra_fields_frame.pack_forget()
			self.locacao_fields_frame.pack(fill="x")
			# Popular combobox de equipamentos (Compressores)
			self.update_produtos_combo()
			# Ocultar coluna de ICMS na lista (largura 0)
			try:
				self.itens_tree.heading("icms", text="")
				self.itens_tree.column("icms", width=0, minwidth=0, stretch=False)
			except Exception:
				pass
			
		else:
			# Fluxo de compra normal
			
			# Mostrar layout de compra, ocultar layout de locação
			self.locacao_fields_frame.pack_forget()
			self.compra_fields_frame.pack(fill="x")
			# Restaurar coluna de ICMS na lista
			try:
				self.itens_tree.heading("icms", text="ICMS")
				self.itens_tree.column("icms", width=80, minwidth=70, stretch=False)
			except Exception:
				pass
		
		# Ajustar campo nome baseado no tipo de cotação (garantia extra)
		if modo == "Locação":
			# Para locação, usar combobox de compressores; garantir que o entry custom não seja usado
			if hasattr(self, 'item_nome_entry'):
				try:
					self.item_nome_entry.pack_forget()
				except Exception:
					pass
			if hasattr(self, 'item_nome_combo_locacao'):
				try:
					self.item_nome_combo_locacao.pack(side="left", fill="x", expand=True)
				except Exception:
					pass
			# Limpar tipo selecionado (não usado em locação)
			self.item_tipo_var.set("")
			
			# Definir tipo de operação como Locação automaticamente
			if hasattr(self, 'item_tipo_operacao_var'):
				self.item_tipo_operacao_var.set("Locação")
		else:
			# Para compra, usar combo com produtos
			if hasattr(self, 'item_nome_entry'):
				self.item_nome_entry.pack_forget()  # Ocultar Entry
			if hasattr(self, 'item_nome_combo_locacao'):
				self.item_nome_combo_locacao.pack(side="left", fill="x", expand=True)  # Mostrar combo
			self.update_produtos_combo()
			
			# Definir tipo de operação como Compra automaticamente
			if hasattr(self, 'item_tipo_operacao_var'):
				self.item_tipo_operacao_var.set("Compra")
			# Garantir tipo 'Produto'
			self.item_tipo_var.set('Produto')
		
		# Ajustar total
		self.atualizar_total()
		
		# Ocultar/mostrar campos específicos conforme o modo de cotação
		if modo == "Locação":
			# Ocultar campos específicos de compra
			if hasattr(self, 'modelo_label'):
				self.modelo_label.grid_remove()
			if hasattr(self, 'modelo_entry'):
				self.modelo_entry.grid_remove()
			if hasattr(self, 'serie_label'):
				self.serie_label.grid_remove()
			if hasattr(self, 'serie_entry'):
				self.serie_entry.grid_remove()
			if hasattr(self, 'status_label'):
				self.status_label.grid_remove()
			if hasattr(self, 'status_combo'):
				self.status_combo.grid_remove()
			if hasattr(self, 'data_validade_label'):
				self.data_validade_label.grid_remove()
			if hasattr(self, 'data_validade_entry'):
				self.data_validade_entry.grid_remove()
			if hasattr(self, 'condicao_pagamento_label'):
				self.condicao_pagamento_label.grid_remove()
			if hasattr(self, 'condicao_pagamento_entry'):
				self.condicao_pagamento_entry.grid_remove()
			if hasattr(self, 'tipo_frete_label'):
				self.tipo_frete_label.grid_remove()
			if hasattr(self, 'tipo_frete_combo'):
				self.tipo_frete_combo.grid_remove()
			if hasattr(self, 'prazo_entrega_label'):
				self.prazo_entrega_label.grid_remove()
			if hasattr(self, 'prazo_entrega_entry'):
				self.prazo_entrega_entry.grid_remove()
			
			# Alterar label do nome para "Nome do Equipamento"
			if hasattr(self, 'nome_label'):
				self.nome_label.config(text="Nome do Equipamento:")
		else:
			# Restaurar campos para compra
			if hasattr(self, 'tipo_combo'):
				self.tipo_combo.grid(row=0, column=1, padx=5)
			if hasattr(self, 'tipo_label'):
				self.tipo_label.grid(row=0, column=0, padx=5, sticky="w")
			if hasattr(self, 'modelo_label'):
				self.modelo_label.grid()
			if hasattr(self, 'modelo_entry'):
				self.modelo_entry.grid()
			if hasattr(self, 'serie_label'):
				self.serie_label.grid()
			if hasattr(self, 'serie_entry'):
				self.serie_entry.grid()
			if hasattr(self, 'status_label'):
				self.status_label.grid()
			if hasattr(self, 'status_combo'):
				self.status_combo.grid()
			if hasattr(self, 'data_validade_label'):
				self.data_validade_label.grid()
			if hasattr(self, 'data_validade_entry'):
				self.data_validade_entry.grid()
			if hasattr(self, 'condicao_pagamento_label'):
				self.condicao_pagamento_label.grid()
			if hasattr(self, 'condicao_pagamento_entry'):
				self.condicao_pagamento_entry.grid()
			if hasattr(self, 'tipo_frete_label'):
				self.tipo_frete_label.grid()
			if hasattr(self, 'tipo_frete_combo'):
				self.tipo_frete_combo.grid()
			if hasattr(self, 'prazo_entrega_label'):
				self.prazo_entrega_label.grid()
			if hasattr(self, 'prazo_entrega_entry'):
				self.prazo_entrega_entry.grid()
			
			# Restaurar label do nome para "Nome"
			if hasattr(self, 'nome_label'):
				self.nome_label.config(text="Nome:")
		
		# Ajustar campo nome baseado no tipo de cotação
		if modo == "Locação":
			# Para locação, converter combo para Entry (texto livre) com tamanho expandido
			if hasattr(self, 'item_nome_combo') and not hasattr(self, 'item_nome_entry'):
				# Criar Entry para substituir o combo com tamanho grande
				self.item_nome_entry = tk.Entry(self.item_nome_combo.master, textvariable=self.item_nome_var, width=70, font=('Arial', 10))
				self.item_nome_entry.pack(side="left", fill="x", expand=True)
				self.item_nome_combo.pack_forget()  # Ocultar combo
			elif hasattr(self, 'item_nome_entry'):
				# Se já existe, apenas garantir que está visível com tamanho correto
				self.item_nome_entry.config(width=70)
				self.item_nome_entry.pack(side="left", fill="x", expand=True)
				if hasattr(self, 'item_nome_combo'):
					self.item_nome_combo.pack_forget()
			# Limpar tipo selecionado
			self.item_tipo_var.set("")
			
			# Definir tipo de operação como Locação automaticamente
			if hasattr(self, 'item_tipo_operacao_var'):
				self.item_tipo_operacao_var.set("Locação")
		else:
			# Para compra, usar combo com produtos
			if hasattr(self, 'item_nome_entry'):
				self.item_nome_entry.pack_forget()  # Ocultar Entry
			if hasattr(self, 'item_nome_combo'):
				self.item_nome_combo.pack(side="left", fill="x", expand=True)  # Mostrar combo
			self.update_produtos_combo()
			
			# Definir tipo de operação como Compra automaticamente
			if hasattr(self, 'item_tipo_operacao_var'):
				self.item_tipo_operacao_var.set("Compra")
		
		# Ajustar total
		self.atualizar_total()
		
	def update_produtos_combo(self):
		"""Atualizar combo de produtos - apenas Produtos (excluindo Compressores)"""
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			
			# Buscar apenas produtos (tipo 'Produto' no banco, excluindo Compressores)
			c.execute("SELECT nome FROM produtos WHERE tipo = 'Produto' AND COALESCE(categoria,'Geral') <> 'Compressores' AND ativo = 1 ORDER BY nome")
			produtos = [row[0] for row in c.fetchall()]
			
			print(f"DEBUG UPDATE_PRODUTOS: Encontrados {len(produtos)} produtos no banco")
			
			# Atualizar combobox de produtos
			if hasattr(self, 'item_nome_combo_compra'):
				try:
					self.item_nome_combo_compra.configure(state='normal')
					self.item_nome_combo_compra['values'] = produtos
					self.item_nome_combo_compra.set('')
					self.item_nome_combo_compra.configure(state='readonly')
					self.item_nome_combo_compra.update_idletasks()
					print(f"DEBUG UPDATE_PRODUTOS: Atualizados {len(produtos)} produtos")
				except Exception as e:
					print(f"Erro ao atualizar combobox de produtos: {e}")
			
			conn.close()
		except Exception as e:
			print(f"Erro ao atualizar combo de produtos: {e}")
		
		
		# Para compra, atualizar combo de produtos
		tipo = self.item_tipo_var.get()
		# Mapear para DB
		if tipo == 'Serviços':
			tipo_db = 'Kit'
		else:
			tipo_db = tipo
		if not tipo:
			if hasattr(self, 'item_nome_combo_compra'):
				self.item_nome_combo_compra['values'] = []
			return
		
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		try:
			if tipo_db == 'Produto':
				# Excluir compressores da lista de Produto
				c.execute("SELECT nome FROM produtos WHERE tipo = 'Produto' AND COALESCE(categoria,'Geral') <> 'Compressores' AND ativo = 1 ORDER BY nome")
			else:
				c.execute("SELECT nome FROM produtos WHERE tipo = ? AND ativo = 1 ORDER BY nome", (tipo_db,))
			produtos = [row[0] for row in c.fetchall()]
			
			# Atualizar combo de compra
			if hasattr(self, 'item_nome_combo_compra'):
				self.item_nome_combo_compra['values'] = produtos
				self.item_nome_var.set("")  # Limpar seleção
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar produtos: {e}")
		finally:
			conn.close()
			
	def on_item_selected(self, event=None):
		"""Callback quando um produto é selecionado"""
		nome = self.item_nome_var.get()
		modo = self.tipo_cotacao_var.get()
		
		# Para locação, não precisamos buscar dados de produto
		if modo == 'Locação':
			return
		
		# Para compra, buscar dados do produto
		tipo = self.item_tipo_var.get()
		tipo_db = 'Kit' if tipo == 'Serviços' else tipo
		if not nome or not tipo:
			return
			
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			# Para Serviços (Kit), buscar também o esboço, porém usar o valor_unitário do cadastro
			if tipo_db == 'Kit':
				c.execute("SELECT id, COALESCE(valor_unitario,0), descricao, esboco_servico FROM produtos WHERE nome = ? AND tipo = 'Kit'", (nome,))
				result = c.fetchone()
				if result:
					produto_id, valor, descricao, esboco = result
					# Usar o valor definido no cadastro do Serviço (não somar componentes)
					self.item_valor_var.set(f"{(valor or 0):.2f}")
					# Preencher esboço do serviço na seção correspondente, se existir
					try:
						if hasattr(self, 'esboco_servico_text') and esboco:
							self.esboco_servico_text.delete("1.0", tk.END)
							self.esboco_servico_text.insert("1.0", esboco)
					except Exception:
						pass
					if descricao:
						self.item_desc_var.set(descricao)
					# Preencher relação de peças automaticamente
					self.preencher_relacao_pecas_kit(produto_id)
					return
			else:
				c.execute("SELECT id, valor_unitario, descricao FROM produtos WHERE nome = ? AND tipo = ?", (nome, tipo_db))
			result = c.fetchone()
			if result:
				produto_id, valor, descricao = result
				self.item_valor_var.set(f"{valor:.2f}")
				if descricao:
					self.item_desc_var.set(descricao)
				
				# Se for Serviços (Kit), preencher automaticamente a relação de peças
				if tipo in ("Kit", "Serviços"):
					self.preencher_relacao_pecas_kit(produto_id)
				else:
					# Se não for Kit, limpar o campo de relação de peças
					if hasattr(self, 'relacao_pecas_text'):
						self.relacao_pecas_text.delete(1.0, tk.END)
		except sqlite3.Error as e:
			self.show_error(f"Erro ao buscar dados do produto: {e}")
		finally:
			conn.close()
			
	def create_itens_list(self, parent):
		# Frame para lista com scrollbars
		list_container = tk.Frame(parent, bg='white')
		list_container.pack(fill="both", expand=True)
		
		# Treeview com 14 colunas para compatibilidade total com salvar/carregar/PDF (incluindo ICMS)
		columns = ("tipo", "nome", "qtd", "valor_unit", "mao_obra", "deslocamento", "estadia", "meses", "inicio", "fim", "valor_total", "descricao", "tipo_operacao", "icms")
		self.itens_tree = ttk.Treeview(list_container, columns=columns, show="headings", height=8)
		
		# Cabeçalhos
		self.itens_tree.heading("tipo", text="Tipo")
		self.itens_tree.heading("nome", text="Nome/Equipamento")
		self.itens_tree.heading("qtd", text="Qtd")
		self.itens_tree.heading("valor_unit", text="Valor Unit./Mensal")
		self.itens_tree.heading("mao_obra", text="Mão de Obra")
		self.itens_tree.heading("deslocamento", text="Desloc.")
		self.itens_tree.heading("estadia", text="Estadia")
		self.itens_tree.heading("meses", text="Meses")
		self.itens_tree.heading("inicio", text="Início")
		self.itens_tree.heading("fim", text="Fim")
		self.itens_tree.heading("valor_total", text="Total")
		self.itens_tree.heading("descricao", text="Descrição")
		self.itens_tree.heading("tipo_operacao", text="Operação")
		self.itens_tree.heading("icms", text="ICMS")
		
		# Larguras
		self.itens_tree.column("tipo", width=80, minwidth=70)
		self.itens_tree.column("nome", width=220, minwidth=180)
		self.itens_tree.column("qtd", width=60, minwidth=50)
		self.itens_tree.column("valor_unit", width=110, minwidth=90)
		self.itens_tree.column("mao_obra", width=100, minwidth=90)
		self.itens_tree.column("deslocamento", width=90, minwidth=80)
		self.itens_tree.column("estadia", width=90, minwidth=80)
		self.itens_tree.column("meses", width=60, minwidth=50)
		self.itens_tree.column("inicio", width=90, minwidth=80)
		self.itens_tree.column("fim", width=90, minwidth=80)
		self.itens_tree.column("valor_total", width=100, minwidth=90)
		self.itens_tree.column("descricao", width=220, minwidth=160)
		self.itens_tree.column("tipo_operacao", width=90, minwidth=70)
		self.itens_tree.column("icms", width=80, minwidth=70)
		
		# Scrollbars vertical e horizontal
		v_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.itens_tree.yview)
		h_scrollbar = ttk.Scrollbar(list_container, orient="horizontal", command=self.itens_tree.xview)
		self.itens_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
		
		# Grid layout para melhor controle dos scrollbars
		self.itens_tree.grid(row=0, column=0, sticky="nsew")
		v_scrollbar.grid(row=0, column=1, sticky="ns")
		h_scrollbar.grid(row=1, column=0, sticky="ew")
		
		# Configurar grid weights para melhor distribuição
		list_container.grid_rowconfigure(0, weight=1)
		list_container.grid_columnconfigure(0, weight=1)
		
		# Configurar altura da tabela para ocupar melhor o espaço disponível
		self.itens_tree.configure(height=15)
		# Permitir edição por duplo clique
		self.itens_tree.bind("<Double-1>", self.on_item_double_click)
		
		# Botões para itens
		item_buttons = tk.Frame(parent, bg='white')
		item_buttons.pack(fill="x", pady=(10, 0))
		
		remove_btn = self.create_button(item_buttons, "Remover Item", self.remover_item, bg='#dc2626')
		remove_btn.pack(side="left", padx=5)
		
		# Label do total
		self.total_label = tk.Label(item_buttons, text="Total: R$ 0,00", font=('Arial', 12, 'bold'), bg='white', fg='#1e293b')
		self.total_label.pack(side="right")
		
	def create_cotacao_buttons(self, parent):
		buttons_frame = tk.Frame(parent, bg='white')
		buttons_frame.pack(fill="x", pady=(20, 0))
		
		# Botões
		nova_btn = self.create_button(buttons_frame, "Nova Cotação", self.nova_cotacao, bg='#e2e8f0', fg='#475569')
		nova_btn.pack(side="left", padx=(0, 10))
		
		salvar_btn = self.create_button(buttons_frame, "Salvar Cotação", self.salvar_cotacao)
		salvar_btn.pack(side="left", padx=(0, 10))
		
		gerar_pdf_btn = self.create_button(buttons_frame, "Gerar PDF", self.gerar_pdf, bg='#10b981')
		gerar_pdf_btn.pack(side="right", padx=(0, 10))
		
		abrir_pdf_btn = self.create_button(buttons_frame, "Abrir PDF", self.abrir_pdf, bg='#3b82f6')
		abrir_pdf_btn.pack(side="right")
		
	# Lista de cotações integrada no layout único
	def refresh_all_data(self):
		"""Atualizar todos os dados do módulo"""
		self.refresh_clientes()
		self.refresh_produtos()
		self.carregar_cotacoes()
		
	def refresh_clientes(self):
		"""Atualizar lista de clientes"""
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			c.execute("SELECT id, nome FROM clientes ORDER BY nome")
			clientes = c.fetchall()
			
			self.clientes_dict = {f"{nome} (ID: {id})": id for id, nome in clientes}
			cliente_values = list(self.clientes_dict.keys())
			
			self.cliente_combo['values'] = cliente_values
			
			print(f"Clientes carregados: {len(cliente_values)}")  # Debug
			
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar clientes: {e}")
		finally:
			conn.close()
			
	def refresh_produtos(self):
		"""Atualizar lista de produtos - apenas Produtos"""
		print("DEBUG ORÇAMENTO PRODUTOS: Iniciando refresh_produtos...")
		# Atualizar combo apenas para produtos
		self.update_produtos_combo()
		print("DEBUG ORÇAMENTO PRODUTOS: Refresh concluído")
		# Forçar atualização agressiva do combobox de nome
		try:
			self._force_update_nome_compra()
		except Exception as e:
			print(f"DEBUG ORÇAMENTO PRODUTOS: Falha ao forçar update do combo de nome: {e}")
		
		print("Produtos atualizados automaticamente!")  # Debug
		
	def force_update_locacao_combo(self):
		"""Forçar atualização do combobox de locação"""
		try:
			if hasattr(self, 'item_nome_combo_locacao'):
				print("DEBUG FORCE_UPDATE: Forçando atualização do combobox de locação...")
				conn = sqlite3.connect(DB_NAME)
				c = conn.cursor()
				c.execute("SELECT nome FROM produtos WHERE tipo='Produto' AND COALESCE(categoria,'Geral')='Compressores' AND ativo=1 ORDER BY nome")
				compressores = [row[0] for row in c.fetchall()]
				
				print(f"DEBUG FORCE_UPDATE: Encontrados {len(compressores)} compressores")
				
				# Forçar atualização do combobox
				self.item_nome_combo_locacao.configure(state='normal')
				self.item_nome_combo_locacao['values'] = compressores
				self.item_nome_combo_locacao.set('')
				self.item_nome_combo_locacao.configure(state='readonly')
				
				# Forçar redraw
				self.item_nome_combo_locacao.update_idletasks()
				self.frame.update_idletasks()
				
				# Verificar se os valores foram realmente atualizados
				valores_atuais = self.item_nome_combo_locacao['values']
				print(f"DEBUG FORCE_UPDATE: Combobox atualizado com {len(compressores)} compressores")
				print(f"DEBUG FORCE_UPDATE: Valores atuais no combobox: {valores_atuais}")
				print(f"DEBUG FORCE_UPDATE: Estado do combobox: {self.item_nome_combo_locacao['state']}")
			else:
				print("DEBUG FORCE_UPDATE: item_nome_combo_locacao não encontrado")
		except Exception as e:
			print(f"DEBUG FORCE_UPDATE: Erro: {e}")
		finally:
			try:
				conn.close()
			except Exception:
				pass
		
	def on_cliente_selected(self, event=None):
		"""Preencher automaticamente a condição de pagamento baseada no cliente selecionado"""
		cliente_str = self.cliente_var.get()
		if not cliente_str:
			return
			
		# Obter ID do cliente
		cliente_id = self.clientes_dict.get(cliente_str)
		if not cliente_id:
			return
			
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			
			# Buscar prazo de pagamento do cliente
			c.execute("SELECT prazo_pagamento FROM clientes WHERE id = ?", (cliente_id,))
			result = c.fetchone()
			
			if result and result[0]:
				# Preencher automaticamente a condição de pagamento
				self.condicao_pagamento_var.set(result[0])
			
			# Carregar contatos do cliente
			c.execute("SELECT nome FROM contatos WHERE cliente_id = ? ORDER BY nome", (cliente_id,))
			contatos = [row[0] for row in c.fetchall()]
			self.contato_cliente_combo['values'] = contatos
			if contatos:
				self.contato_cliente_var.set(contatos[0])
			else:
				self.contato_cliente_var.set("")
				
		except sqlite3.Error as e:
			print(f"Erro ao buscar prazo de pagamento do cliente: {e}")
		finally:
			conn.close()
			
	def gerar_numero_sequencial(self):
		"""Gerar número sequencial para cotação"""
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			
			# Buscar o maior número sequencial existente para PROD-
			c.execute("SELECT MAX(CAST(SUBSTR(numero_proposta, 6) AS INTEGER)) FROM cotacoes WHERE numero_proposta LIKE 'PROD-%'")
			result = c.fetchone()
			
			if result and result[0]:
				proximo_numero = result[0] + 1
			else:
				proximo_numero = 1
			return f"PROD-{proximo_numero:06d}"
			
		except sqlite3.Error as e:
			print(f"Erro ao gerar número sequencial: {e}")
			# Fallback para timestamp
			return f"PROD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
		finally:
			conn.close()
		
	def adicionar_item(self):
		if not self.can_edit('orcamento_produtos'):
			self.show_warning("Você não tem permissão para adicionar itens às cotações.")
			return
			
		modo = self.tipo_cotacao_var.get()
		
		if modo == 'Locação':
			# Validações para locação
			nome = self.item_nome_var.get()
			qtd_str = self.item_qtd_var.get()
			valor_str = self.item_valor_var.get()
			descricao = self.item_desc_var.get()
			inicio_str = self.item_loc_inicio_var.get()
			fim_str = self.item_loc_fim_var.get()
			modelo_compressor = self.item_modelo_compressor_var.get()
			
			# Validações
			if not nome:
				self.show_warning("Informe o nome do equipamento para locação.")
				return
		else:
			# Validações para compra
			tipo = self.item_tipo_var.get()
			nome = self.item_nome_var.get()
			qtd_str = self.item_qtd_var.get()
			valor_str = self.item_valor_var.get()
			descricao = self.item_desc_var.get()
			mao_obra_str = self.item_mao_obra_var.get()
			deslocamento_str = self.item_deslocamento_var.get()
			estadia_str = self.item_estadia_var.get()
			
			# Validações
			if not tipo or not nome:
				self.show_warning("Selecione o tipo e informe o nome do item.")
				return
		
		try:
			quantidade = float(qtd_str) if qtd_str else 1
			valor_unitario = clean_number(valor_str)
		except ValueError:
			self.show_error("Verifique os valores numéricos informados.")
			return
		
		if modo == 'Locação':
			# Processar dados de locação
			inicio_iso = self.parse_date_input(inicio_str)
			fim_iso = self.parse_date_input(fim_str)
			if not inicio_iso or not fim_iso:
				self.show_warning("Informe datas válidas de início e fim para locação.")
				return
			
			meses_int = self.calculate_months_between(inicio_iso, fim_iso)
			meses = str(meses_int)
			inicio_fmt = format_date(inicio_iso)
			fim_fmt = format_date(fim_iso)
			valor_total = quantidade * valor_unitario * meses_int
			tipo_operacao = 'Locação'
			
			# Para locação, incluir modelo do compressor na descrição
			if modelo_compressor:
				descricao_completa = f"{descricao} - Modelo: {modelo_compressor}".strip(" -")
			else:
				descricao_completa = descricao
		else:
			# Processar dados de compra
			mao_obra = clean_number(mao_obra_str)
			deslocamento = clean_number(deslocamento_str)
			estadia = clean_number(estadia_str)
			
			meses = ""
			inicio_fmt = ""
			fim_fmt = ""
			valor_total = quantidade * (valor_unitario + mao_obra + deslocamento + estadia)
			tipo_operacao = 'Compra'
			descricao_completa = descricao
		
		# Adicionar à lista no formato de 14 colunas (incluindo ICMS)
		if modo == 'Locação':
			self.itens_tree.insert("", "end", values=(
				"Produto",
				nome,
				f"{quantidade:.2f}",
				format_currency(valor_unitario),
				format_currency(0),
				format_currency(0),
				format_currency(0),
				meses,
				inicio_fmt,
				fim_fmt,
				format_currency(valor_total),
				descricao_completa,
				"Locação",
				"R$ 0,00"  # Sem ICMS para locação
			))
		else:
			# Obter ICMS baseado na filial
			icms_val = 0
			try:
				filial_str = self.filial_var.get()
				filial_id = int(filial_str.split(' - ')[0]) if ' - ' in filial_str else int(filial_str)
				if filial_id == 2:
					icms_val = clean_number(self.item_icms_var.get())
			except Exception:
				icms_val = 0
			
			self.itens_tree.insert("", "end", values=(
				tipo,
				nome,
				f"{quantidade:.2f}",
				format_currency(valor_unitario),
				format_currency(mao_obra),
				format_currency(deslocamento),
				format_currency(estadia),
				"",
				"",
				"",
				format_currency(quantidade * (valor_unitario + mao_obra + deslocamento + estadia + icms_val)),
				descricao_completa,
				"Compra",
				format_currency(icms_val)
			))
			# Guardar ICMS no último item via atributo associado (usar hidden mapping se necessário)
			if not hasattr(self, '_icms_por_item_idx'):
				self._icms_por_item_idx = {}
			try:
				last = self.itens_tree.get_children()[-1]
				self._icms_por_item_idx[last] = clean_number(self.item_icms_var.get()) if self.filial_var.get().split(' - ')[0] == '2' else 0
			except Exception:
				pass
		
		# Limpar campos baseado no modo
		if modo == 'Locação':
			# Limpar campos de locação
			self.item_nome_var.set("")
			self.item_desc_var.set("")
			self.item_qtd_var.set("1")
			self.item_valor_var.set("0.00")
			self.item_loc_inicio_var.set("")
			self.item_loc_fim_var.set("")
			self.item_loc_meses_var.set("0")
			self.item_loc_total_var.set("R$ 0,00")
			self.item_modelo_compressor_var.set("")
		else:
			# Limpar campos de compra
			# Manter tipo 'Produto' para próxima adição
			self.item_tipo_var.set('Produto')
			self.item_nome_var.set("")
			self.item_desc_var.set("")
			self.item_qtd_var.set("1")
			self.item_valor_var.set("0.00")
			self.item_mao_obra_var.set("0.00")
			self.item_deslocamento_var.set("0.00")
			self.item_estadia_var.set("0.00")
			# Limpar ICMS após adicionar item
			try:
				self.item_icms_var.set("0.00")
			except Exception:
				pass
		
		# Código de limpeza já implementado acima
		
	def remover_item(self):
		if not self.can_edit('orcamento_produtos'):
			self.show_warning("Você não tem permissão para remover itens das cotações.")
			return
			
		selected = self.itens_tree.selection()
		if not selected:
			self.show_warning("Selecione um item para remover.")
			return
			
		for item in selected:
			self.itens_tree.delete(item)
			
		self.atualizar_total()

	def on_item_double_click(self, event=None):
		"""Editar item selecionado da tabela (Compra/Locação)"""
		selected = self.itens_tree.selection()
		if not selected:
			return
		iid = selected[0]
		vals = list(self.itens_tree.item(iid)['values'])
		# Esperamos 14 colunas (inclui ICMS)
		if len(vals) != 14:
			return
		modal = tk.Toplevel(self.frame)
		modal.title("Editar Item da Proposta")
		modal.grab_set()
		labels = [
			("Tipo", 0),
			("Nome/Equipamento", 1),
			("Quantidade", 2),
			("Valor Unitário", 3),
			("Mão de Obra", 4),
			("Deslocamento", 5),
			("Estadia", 6),
			("Meses", 7),
			("Início (DD/MM/AAAA)", 8),
			("Fim (DD/MM/AAAA)", 9),
			("Valor Total", 10),
			("Descrição", 11),
			("Operação", 12),
			("ICMS", 13),
		]
		entries = {}
		row = 0
		for label, idx in labels:
			tk.Label(modal, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
			var = tk.StringVar(value=str(vals[idx]))
			ent = tk.Entry(modal, textvariable=var, width=50)
			ent.grid(row=row, column=1, padx=8, pady=4)
			entries[idx] = var
			row += 1
		def salvar_edicao():
			try:
				# Parse campos numéricos formatados
				qtd = float(entries[2].get().replace(',', '.'))
				valor_unit = clean_number(entries[3].get())
				mao_obra = clean_number(entries[4].get() or '0')
				desloc = clean_number(entries[5].get() or '0')
				estadia = clean_number(entries[6].get() or '0')
				meses = int(entries[7].get() or 0) if str(entries[7].get() or '').strip().isdigit() else 0
				icms_val = clean_number(entries[13].get() or '0')
				# Recalcular total (para locação usa meses; para compra soma custos incluindo ICMS)
				if (entries[12].get() or '').lower().startswith('loca'):
					total = (valor_unit or 0) * (meses or 0) * (qtd or 0)
				else:
					total = (qtd or 0) * ((valor_unit or 0) + (mao_obra or 0) + (desloc or 0) + (estadia or 0) + (icms_val or 0))
				# Atualizar vetor
				vals[0] = entries[0].get().strip() or 'Produto'
				vals[1] = entries[1].get().strip()
				vals[2] = f"{qtd:.2f}"
				vals[3] = format_currency(valor_unit)
				vals[4] = format_currency(mao_obra)
				vals[5] = format_currency(desloc)
				vals[6] = format_currency(estadia)
				vals[7] = str(meses or '')
				vals[8] = entries[8].get().strip()
				vals[9] = entries[9].get().strip()
				vals[10] = format_currency(total)
				vals[11] = entries[11].get().strip()
				vals[12] = entries[12].get().strip() or 'Compra'
				vals[13] = format_currency(icms_val)
				self.itens_tree.item(iid, values=tuple(vals))
				self.atualizar_total()
				modal.destroy()
			except Exception as e:
				messagebox.showerror("Erro", f"Não foi possível salvar alterações: {e}")
		btns = tk.Frame(modal)
		btns.grid(row=row, column=0, columnspan=2, pady=(8, 4))
		self.create_button(btns, "Salvar", salvar_edicao, bg='#10b981').pack(side="left", padx=6)
		self.create_button(btns, "Cancelar", modal.destroy, bg='#64748b').pack(side="left", padx=6)
		
	def parse_date_input(self, s):
		"""Converter entrada DD/MM/AAAA ou AAAA-MM-DD para AAAA-MM-DD"""
		s = (s or "").strip()
		if not s:
			return None
		try:
			# Tentar DD/MM/AAAA
			dt = datetime.strptime(s, '%d/%m/%Y').date()
			return dt.strftime('%Y-%m-%d')
		except ValueError:
			pass
		try:
			# Tentar AAAA-MM-DD
			datetime.strptime(s, '%Y-%m-%d')
			return s
		except ValueError:
			return None
		
	def calculate_months_between(self, start_iso, end_iso):
		"""Calcular meses entre duas datas (contando mês parcial como inteiro, mínimo 1)"""
		if not start_iso or not end_iso:
			return 0
		start = datetime.strptime(start_iso, '%Y-%m-%d').date()
		end = datetime.strptime(end_iso, '%Y-%m-%d').date()
		if end < start:
			return 0
		months = (end.year - start.year) * 12 + (end.month - start.month)
		# Contar parcial
		if end.day >= start.day:
			months += 1
		if months < 1:
			months = 1
		return months
		
	def recalcular_locacao(self):
		"""Recalcular meses e total da locação"""
		valor_mensal = clean_number(self.locacao_valor_mensal_var.get() or "0")
		inicio_iso = self.parse_date_input(self.locacao_data_inicio_var.get())
		fim_iso = self.parse_date_input(self.locacao_data_fim_var.get())
		meses = self.calculate_months_between(inicio_iso, fim_iso) if inicio_iso and fim_iso else 0
		self.locacao_qtd_meses_var.set(str(meses))
		total = (valor_mensal or 0) * (meses or 0)
		self.locacao_total_var.set(format_currency(total))
		# Atualizar total geral na UI
		if self.tipo_cotacao_var.get() == 'Locação':
			self.total_label.config(text=f"Total: {format_currency(total)}")
	
	def recalcular_locacao_item(self):
		"""Recalcular meses e total da locação por item"""
		if self.tipo_cotacao_var.get() != 'Locação':
			return
			
		valor_mensal = clean_number(self.item_valor_var.get() or "0")
		inicio_iso = self.parse_date_input(self.item_loc_inicio_var.get())
		fim_iso = self.parse_date_input(self.item_loc_fim_var.get())
		
		meses = self.calculate_months_between(inicio_iso, fim_iso) if inicio_iso and fim_iso else 0
		self.item_loc_meses_var.set(str(meses))
		
		quantidade = float(self.item_qtd_var.get() or "1")
		total = (valor_mensal or 0) * (meses or 0) * quantidade
		self.item_loc_total_var.set(format_currency(total))
		
		# Atualizar total geral se for locação
		if self.tipo_cotacao_var.get() == 'Locação':
			self.atualizar_total()
		
	def atualizar_total(self):
		"""Atualizar valor total da cotação"""
		total = 0
		for item in self.itens_tree.get_children():
			values = self.itens_tree.item(item)['values']
			if len(values) >= 11:
				valor_total_str = values[10].replace('R$ ', '').replace('.', '').replace(',', '.')
				try:
					total += float(valor_total_str)
				except ValueError:
					pass
		self.total_label.config(text=f"Total: {format_currency(total)}")
		
	def nova_cotacao(self):
		"""Limpar formulário para nova cotação"""
		self.current_cotacao_id = None
		
		# Limpar campos
		self.numero_var.set("")
		self.cliente_var.set("")
		self.contato_cliente_var.set("")
		try:
			self.contato_cliente_combo['values'] = []
		except Exception:
			pass
		self.modelo_var.set("")
		self.serie_var.set("")
		self.status_var.set("Em Aberto")
		self.data_validade_var.set("")
		self.condicao_pagamento_var.set("")
		self.tipo_frete_var.set("FOB")
		self.prazo_entrega_var.set("")
		self.observacoes_text.delete("1.0", tk.END)
		# Reset locação
		self.tipo_cotacao_var.set("Compra")
		self.locacao_valor_mensal_var.set("0.00")
		self.locacao_data_inicio_var.set("")
		self.locacao_data_fim_var.set("")
		self.locacao_qtd_meses_var.set("0")
		self.locacao_total_var.set("R$ 0,00")
		self.locacao_equipamento_var.set("")
		
		# Reset campos de locação por item
		if hasattr(self, 'item_loc_inicio_var'):
			self.item_loc_inicio_var.set("")
		if hasattr(self, 'item_loc_fim_var'):
			self.item_loc_fim_var.set("")
		if hasattr(self, 'item_loc_meses_var'):
			self.item_loc_meses_var.set("0")
		if hasattr(self, 'item_loc_total_var'):
			self.item_loc_total_var.set("R$ 0,00")
		if hasattr(self, 'item_modelo_compressor_var'):
			self.item_modelo_compressor_var.set("")
		if hasattr(self, 'locacao_frame'):
			self.locacao_frame.pack_forget()
		if hasattr(self, 'itens_section'):
			self.itens_section.pack(fill="both", expand=True, pady=(0, 10))
		
		# Limpar itens
		for item in self.itens_tree.get_children():
			self.itens_tree.delete(item)
			
		self.atualizar_total()
		# Limpar campos de item (compra) inclusive ICMS
		try:
			# Garantir tipo 'Produto' após nova cotação
			self.item_tipo_var.set('Produto')
			self.item_nome_var.set("")
			self.item_desc_var.set("")
			self.item_qtd_var.set("1")
			self.item_valor_var.set("0.00")
			self.item_mao_obra_var.set("0.00")
			self.item_deslocamento_var.set("0.00")
			self.item_estadia_var.set("0.00")
			self.item_icms_var.set("0.00")
		except Exception:
			pass
		
		# Gerar número sequencial automático
		numero = self.gerar_numero_sequencial()
		self.numero_var.set(numero)
		
	def salvar_cotacao(self):
		"""Salvar cotação no banco de dados"""
		if not self.can_edit('orcamento_produtos'):
			self.show_warning("Você não tem permissão para salvar cotações.")
			return
			
		# Validações
		numero = self.numero_var.get().strip()
		cliente_str = self.cliente_var.get().strip()
		modo = self.tipo_cotacao_var.get()
		
		if not numero:
			self.show_warning("Informe o número da proposta.")
			return
		if not cliente_str:
			self.show_warning("Selecione um cliente.")
			return
		cliente_id = self.clientes_dict.get(cliente_str)
		if not cliente_id:
			self.show_warning("Cliente selecionado inválido.")
			return
		if not self.itens_tree.get_children():
			self.show_warning("Adicione pelo menos um item à cotação.")
			return
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		try:
			# Calcular valor total somando itens
			valor_total = 0
			for item in self.itens_tree.get_children():
				values = self.itens_tree.item(item)['values']
				if len(values) >= 11:
					valor_total_str = values[10].replace('R$ ', '').replace('.', '').replace(',', '.')
					try:
						valor_total += float(valor_total_str)
					except ValueError:
						pass
			# Data validade
			data_validade_input = self.data_validade_var.get().strip()
			data_validade = None
			if data_validade_input:
				try:
					data_validade = datetime.strptime(data_validade_input, '%d/%m/%Y').strftime('%Y-%m-%d')
				except ValueError:
					data_validade = data_validade_input
			# Filial
			filial_str = self.filial_var.get()
			filial_id = int(filial_str.split(' - ')[0]) if ' - ' in filial_str else int(filial_str)
			# Inserir/atualizar cotação (sem usar campos globais de locação)
			if self.current_cotacao_id:
				# Preparar valores baseado no tipo de cotação
				modelo_valor = self.modelo_var.get() if modo != "Locação" else ""
				serie_valor = self.serie_var.get() if modo != "Locação" else ""
				status_valor = self.status_var.get() if modo != "Locação" else "Em Aberto"
				data_validade_valor = data_validade if modo != "Locação" else None
				condicao_pagamento_valor = self.condicao_pagamento_var.get() if modo != "Locação" else ""
				prazo_entrega_valor = self.prazo_entrega_var.get() if modo != "Locação" else ""
				
				c.execute("""
					UPDATE cotacoes SET
						numero_proposta = ?, modelo_compressor = ?, numero_serie_compressor = ?,
						observacoes = ?, valor_total = ?, status = ?, data_validade = ?,
						tipo_frete = ?, condicao_pagamento = ?, prazo_entrega = ?, filial_id = ?,
						esboco_servico = '', relacao_pecas_substituir = '',
						tipo_cotacao = ?, locacao_nome_equipamento = ?
					WHERE id = ?
				""", (numero, modelo_valor, serie_valor,
					 self.observacoes_text.get("1.0", tk.END).strip(), valor_total,
					 status_valor, data_validade_valor,
					 self.tipo_frete_var.get(), condicao_pagamento_valor, prazo_entrega_valor,
					 filial_id,
					 modo, self.locacao_equipamento_var.get(),
					 self.current_cotacao_id))
				c.execute("DELETE FROM itens_cotacao WHERE cotacao_id = ?", (self.current_cotacao_id,))
				cotacao_id = self.current_cotacao_id
			else:
				# Preparar valores baseado no tipo de cotação para INSERT
				modelo_valor = self.modelo_var.get() if modo != "Locação" else ""
				serie_valor = self.serie_var.get() if modo != "Locação" else ""
				status_valor = self.status_var.get() if modo != "Locação" else "Em Aberto"
				data_validade_valor = data_validade if modo != "Locação" else None
				condicao_pagamento_valor = self.condicao_pagamento_var.get() if modo != "Locação" else ""
				prazo_entrega_valor = self.prazo_entrega_var.get() if modo != "Locação" else ""
				
				c.execute("""
					INSERT INTO cotacoes (numero_proposta, cliente_id, responsavel_id, data_criacao,
									  modelo_compressor, numero_serie_compressor, observacoes,
									  valor_total, status, data_validade, tipo_frete, condicao_pagamento,
									  prazo_entrega, filial_id, esboco_servico, relacao_pecas_substituir,
									  tipo_cotacao, locacao_nome_equipamento)
					VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', ?, ?)
				""", (numero, cliente_id, self.user_id, datetime.now().strftime('%Y-%m-%d'),
					 modelo_valor, serie_valor, self.observacoes_text.get("1.0", tk.END).strip(), valor_total,
					 status_valor, data_validade_valor, self.tipo_frete_var.get(), condicao_pagamento_valor, prazo_entrega_valor,
					 filial_id, "Compra", self.locacao_equipamento_var.get()))
				cotacao_id = c.lastrowid
				self.current_cotacao_id = cotacao_id
			# Inserir itens
			for item in self.itens_tree.get_children():
				values = self.itens_tree.item(item)['values']
				# Esperado 14 colunas (incluindo ICMS)
				if len(values) != 14:
					continue
				tipo, nome, qtd, valor_unit, mao_obra, desloc, estadia, meses, inicio, fim, total, desc, tipo_operacao, icms = values
				quantidade = float(qtd)
				valor_unitario = clean_number(valor_unit)
				valor_mao_obra = clean_number(mao_obra)
				valor_desloc = clean_number(desloc)
				valor_estadia = clean_number(estadia)
				valor_total_item = clean_number(total)
				# Datas locação
				inicio_iso = self.parse_date_input(inicio)
				fim_iso = self.parse_date_input(fim)
				meses_int = int(meses) if str(meses).isdigit() else None
				# Forçar tipo_operacao conforme modo
				if modo == 'Locação':
					tipo_operacao = 'Locação'
				# Obter ICMS da tree
				icms_item_val = clean_number(icms)
				c.execute("""
					INSERT INTO itens_cotacao (cotacao_id, tipo, item_nome, quantidade,
										 valor_unitario, valor_total_item, descricao,
										 mao_obra, deslocamento, estadia, icms, tipo_operacao,
										 locacao_data_inicio, locacao_data_fim, locacao_qtd_meses)
					VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
				""", (cotacao_id, tipo, nome, quantidade, valor_unitario, valor_total_item, desc,
					 valor_mao_obra, valor_desloc, valor_estadia, icms_item_val, tipo_operacao,
					 inicio_iso, fim_iso, meses_int))
			conn.commit()
			self.show_success("Cotação salva com sucesso!")
			self.emit_event('cotacao_created')
			self.carregar_cotacoes()
		except sqlite3.Error as e:
			self.show_error(f"Erro ao salvar cotação: {e}")
		finally:
			conn.close()
			
	def gerar_pdf(self):
		"""Gerar PDF da cotação atual"""
		if not self.current_cotacao_id:
			self.show_warning("Salve a cotação antes de gerar o PDF.")
			return
			
		try:
			# Obter username do usuário atual para template personalizado
			current_username = self._get_current_username()
			# Passar contato selecionado para o gerador
			sucesso, resultado = gerar_pdf_cotacao_nova(
				self.current_cotacao_id,
				DB_NAME,
				current_username,
				contato_nome=self.contato_cliente_var.get()
			)
			if sucesso:
				self.show_success(f"PDF gerado com sucesso!\nLocal: {resultado}")
			else:
				self.show_error(f"Erro ao gerar PDF: {resultado}")
		except Exception as e:
			self.show_error(f"Erro ao gerar PDF: {e}")
			
	def abrir_pdf(self):
		"""Abrir PDF da cotação atual"""
		if not self.current_cotacao_id:
			self.show_warning("Salve a cotação primeiro antes de abrir o PDF.")
			return
			
		try:
			# Obter username do usuário atual para template personalizado
			current_username = self._get_current_username()
			sucesso, resultado = gerar_pdf_cotacao_nova(
				self.current_cotacao_id, 
				DB_NAME, 
				current_username, 
				contato_nome=self.contato_cliente_var.get()
			)
			
			if sucesso:
				# Abrir o PDF com o aplicativo padrão
				try:
					import os
					import sys
					if os.name == 'nt':  # Windows
						os.startfile(resultado)
					elif sys.platform == 'darwin':  # macOS
						import subprocess
						subprocess.Popen(['open', resultado])
					else:  # Linux
						import subprocess
						subprocess.Popen(['xdg-open', resultado])
				except Exception as e:
					self.show_error(f"Erro ao abrir PDF: {e}")
			else:
				self.show_error(f"Erro ao gerar PDF: {resultado}")
		except Exception as e:
			self.show_error(f"Erro ao abrir PDF: {e}")
			
	def _get_current_username(self):
		"""Obter o username do usuário atual"""
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute("SELECT username FROM usuarios WHERE id = ?", (self.user_id,))
			result = c.fetchone()
			return result[0] if result else None
		except:
			return None
		finally:
			if 'conn' in locals():
				conn.close()
			
	def carregar_cotacoes(self):
		"""Carregar lista de cotações"""
		# Verificar e atualizar cotações expiradas automaticamente
		cotações_expiradas = verificar_e_atualizar_status_cotacoes()
		
		# Limpar lista atual
		for item in self.cotacoes_tree.get_children():
			self.cotacoes_tree.delete(item)
			
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			c.execute("""
				SELECT c.id, c.numero_proposta, cl.nome, c.data_criacao, c.valor_total, c.status
				FROM cotacoes c
				JOIN clientes cl ON c.cliente_id = cl.id
				WHERE c.numero_proposta LIKE 'PROD-%'
				ORDER BY c.created_at DESC
			""")
			
			for row in c.fetchall():
				cotacao_id, numero, cliente, data, valor, status = row
				self.cotacoes_tree.insert("", "end", values=(
					numero,
					cliente,
					format_date(data),
					format_currency(valor) if valor else "R$ 0,00",
					status
				), tags=(cotacao_id,))
				
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar cotações: {e}")
		finally:
			conn.close()
			
	def buscar_cotacoes(self):
		"""Buscar cotações com filtro"""
		termo = self.search_var.get().strip()
		
		# Limpar lista atual
		for item in self.cotacoes_tree.get_children():
			self.cotacoes_tree.delete(item)
			
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			if termo:
				c.execute("""
					SELECT c.id, c.numero_proposta, cl.nome, c.data_criacao, c.valor_total, c.status
					FROM cotacoes c
					JOIN clientes cl ON c.cliente_id = cl.id
					WHERE c.numero_proposta LIKE 'PROD-%' AND (c.numero_proposta LIKE ? OR cl.nome LIKE ?)
					ORDER BY c.created_at DESC
				""", (f"%{termo}%", f"%{termo}%"))
			else:
				c.execute("""
					SELECT c.id, c.numero_proposta, cl.nome, c.data_criacao, c.valor_total, c.status
					FROM cotacoes c
					JOIN clientes cl ON c.cliente_id = cl.id
					WHERE c.numero_proposta LIKE 'PROD-%'
					ORDER BY c.created_at DESC
				""")
			
			for row in c.fetchall():
				cotacao_id, numero, cliente, data, valor, status = row
				self.cotacoes_tree.insert("", "end", values=(
					numero,
					cliente,
					format_date(data),
					format_currency(valor) if valor else "R$ 0,00",
					status
				), tags=(cotacao_id,))
				
		except sqlite3.Error as e:
			self.show_error(f"Erro ao buscar cotações: {e}")
		finally:
			conn.close()
			
	def editar_cotacao(self):
		"""Editar cotação selecionada"""
		selected = self.cotacoes_tree.selection()
		if not selected:
			self.show_warning("Selecione uma cotação para editar.")
			return
			
		# Obter ID da cotação
		tags = self.cotacoes_tree.item(selected[0])['tags']
		if not tags:
			return
			
		cotacao_id = tags[0]
		self.carregar_cotacao_para_edicao(cotacao_id)
		
		# Layout único: permanecer na mesma tela
		
	def carregar_cotacao_para_edicao(self, cotacao_id):
		"""Carregar dados da cotação para edição"""
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			# Carregar dados da cotação
			c.execute("""
				SELECT 
					c.id, c.numero_proposta, c.cliente_id, c.responsavel_id, c.filial_id,
					c.data_validade, c.modelo_compressor, c.numero_serie_compressor,
					c.descricao_atividade, c.observacoes, c.valor_total, c.tipo_frete,
					c.condicao_pagamento, c.prazo_entrega, c.moeda, c.status,
					c.caminho_arquivo_pdf, c.relacao_pecas, cl.nome AS cliente_nome,
					c.esboco_servico, c.relacao_pecas_substituir,
					c.tipo_cotacao, c.locacao_valor_mensal, c.locacao_data_inicio,
					c.locacao_data_fim, c.locacao_qtd_meses, c.locacao_nome_equipamento
				FROM cotacoes c
				JOIN clientes cl ON c.cliente_id = cl.id
				WHERE c.id = ?
			""", (cotacao_id,))
			
			cotacao = c.fetchone()
			if not cotacao:
				self.show_error("Cotação não encontrada.")
				return
				
			# Preencher campos
			self.current_cotacao_id = cotacao_id
			self.numero_var.set(cotacao[1])  # numero_proposta
			
			# Encontrar cliente no combo
			cliente_nome = cotacao[18]  # nome do cliente
			for key, value in self.clientes_dict.items():
				if value == cotacao[2]:  # cliente_id
					self.cliente_var.set(key)
					break
					
			# Campos específicos de compra (podem estar vazios para locação)
			self.modelo_var.set(cotacao[6] or "")
			self.serie_var.set(cotacao[7] or "")
			self.status_var.set(cotacao[15] or "Em Aberto")
			self.data_validade_var.set(cotacao[5] or "")
			self.condicao_pagamento_var.set(cotacao[12] or "")
			self.prazo_entrega_var.set(cotacao[13] or "")
			self.tipo_frete_var.set(cotacao[11] or "FOB")
			
			# Observações
			self.observacoes_text.delete("1.0", tk.END)
			if cotacao[9]:  # observacoes
				self.observacoes_text.insert("1.0", cotacao[9])
			
			# Campos de esboço e relação de peças não existem neste módulo
			
			# Campos de Locação
			self.tipo_cotacao_var.set(cotacao[21] or "Compra")
			self.locacao_valor_mensal_var.set(f"{cotacao[22]:.2f}" if cotacao[22] is not None else "0.00")
			self.locacao_data_inicio_var.set(format_date(cotacao[23]) if cotacao[23] else "")
			self.locacao_data_fim_var.set(format_date(cotacao[24]) if cotacao[24] else "")
			self.locacao_qtd_meses_var.set(str(cotacao[25] or 0))
			self.locacao_equipamento_var.set(cotacao[26] or "")
			
			# Recarregar caminho da imagem se existir
			try:
				self.locacao_imagem_var.set(cotacao[27] or "")
			except Exception:
				pass
				
			# Alternar UI conforme tipo de cotação
			self.on_tipo_cotacao_changed()
			
			# Carregar itens (para Compra)
			self.carregar_itens_cotacao(cotacao_id)
			
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar cotação: {e}")
		finally:
			conn.close()
			
	def carregar_itens_cotacao(self, cotacao_id):
		"""Carregar itens da cotação"""
		# Limpar lista atual
		for item in self.itens_tree.get_children():
			self.itens_tree.delete(item)
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		try:
			c.execute("""
				SELECT tipo, item_nome, quantidade, valor_unitario, valor_total_item,
				       descricao, mao_obra, deslocamento, estadia,
				       locacao_qtd_meses, locacao_data_inicio, locacao_data_fim, tipo_operacao, icms
				FROM itens_cotacao
				WHERE cotacao_id = ?
				ORDER BY id
			""", (cotacao_id,))
			for row in c.fetchall():
				(tipo, nome, qtd, valor_unit, total, desc, mao_obra, desloc, estadia, meses, inicio, fim, tipo_oper, icms) = row
				self.itens_tree.insert("", "end", values=(
					tipo or "Produto",
					nome,
					f"{qtd:.2f}",
					format_currency(valor_unit),
					format_currency(mao_obra or 0),
					format_currency(desloc or 0),
					format_currency(estadia or 0),
					str(meses or ""),
					(format_date(inicio) if inicio else ""),
					(format_date(fim) if fim else ""),
					format_currency(total),
					desc or "",
					tipo_oper or "Compra",
					format_currency(icms or 0)
				))
			self.atualizar_total()
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar itens: {e}")
		finally:
			conn.close()

	def duplicar_cotacao(self):
		"""Duplicar cotação selecionada"""
		selected = self.cotacoes_tree.selection()
		if not selected:
			self.show_warning("Selecione uma cotação para duplicar.")
			return
			
		# Obter ID da cotação
		tags = self.cotacoes_tree.item(selected[0])['tags']
		if not tags:
			return
			
		cotacao_id = tags[0]
		self.carregar_cotacao_para_edicao(cotacao_id)
		
		# Limpar ID e gerar novo número
		self.current_cotacao_id = None
		numero = f"PROP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
		self.numero_var.set(numero)
		
		# Layout único: permanecer na mesma tela
		
	def gerar_pdf_selecionado(self):
		"""Gerar PDF da cotação selecionada"""
		selected = self.cotacoes_tree.selection()
		if not selected:
			self.show_warning("Selecione uma cotação para gerar PDF.")
			return
			
		tags = self.cotacoes_tree.item(selected[0])['tags']
		if not tags:
			return
			
		cotacao_id = tags[0]
		# Obter username do usuário atual para template personalizado
		current_username = self._get_current_username()
		sucesso, resultado = gerar_pdf_cotacao_nova(cotacao_id, DB_NAME, current_username, contato_nome=self.contato_cliente_var.get())
		
		if sucesso:
			self.show_success(f"PDF gerado com sucesso!\nLocal: {resultado}")
		else:
			self.show_error(f"Erro ao gerar PDF: {resultado}")
			
	def handle_event(self, event_type, data=None):
		"""Manipular eventos do sistema"""
		print(f"DEBUG COTAÇÕES: Evento recebido: {event_type}")
		if event_type == 'cliente_created':
			self.refresh_clientes()
			print("Lista de clientes atualizada automaticamente!")
		elif event_type == 'produto_created' or event_type == 'produto_updated':
			print("DEBUG COTAÇÕES: Processando evento produto_created...")
			self.refresh_produtos()
			# Forçar atualização imediata do combobox de locação
			self.force_update_locacao_combo()
			# Forçar atualização agressiva do combobox de compra (nome)
			try:
				self._force_update_nome_compra()
			except Exception as e:
				print(f"DEBUG COTAÇÕES: Falha ao forçar update do combo de nome: {e}")
			print("Lista de produtos atualizada automaticamente!")
		elif event_type == 'test_event':
			print("DEBUG COTAÇÕES: Evento de teste recebido com sucesso!")

	def _force_update_nome_compra(self):
		"""Atualizar agressivamente o combobox de Nome (Produtos -> produtos.tipo='Produto' sem compressores)."""
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute("SELECT nome FROM produtos WHERE tipo = 'Produto' AND COALESCE(categoria,'Geral') <> 'Compressores' AND ativo = 1 ORDER BY nome")
			nomes = [row[0] for row in c.fetchall()]
			conn.close()
			print(f"DEBUG NOME_COMPRA (Produtos): {len(nomes)} itens carregados")
			if hasattr(self, 'item_nome_combo_compra'):
				self.item_nome_combo_compra.configure(state='normal')
				self.item_nome_combo_compra['values'] = nomes
				self.item_nome_combo_compra.set('')
				self.item_nome_combo_compra.configure(state='readonly')
				self.item_nome_combo_compra.update_idletasks()
		except Exception as e:
			print(f"DEBUG NOME_COMPRA (Produtos) erro: {e}")
			
	# Função de preencher relação de peças removida deste módulo
			
	def abrir_pdf_selecionado(self):
		"""Abrir PDF da cotação selecionada"""
		selected = self.cotacoes_tree.selection()
		if not selected:
			self.show_warning("Selecione uma cotação para abrir o PDF.")
			return
			
		tags = self.cotacoes_tree.item(selected[0])['tags']
		if not tags:
			return
			
		cotacao_id = tags[0]
		
		# Primeiro gerar o PDF se não existir
		current_username = self._get_current_username()
		sucesso, resultado = gerar_pdf_cotacao_nova(cotacao_id, DB_NAME, current_username, contato_nome=self.contato_cliente_var.get())
		
		if sucesso:
			# Abrir o PDF com o aplicativo padrão
			try:
				import os
				import sys
				if os.name == 'nt':  # Windows
					os.startfile(resultado)
				elif sys.platform == 'darwin':  # macOS
					import subprocess
					subprocess.Popen(['open', resultado])
				else:  # Linux
					import subprocess
					subprocess.Popen(['xdg-open', resultado])
			except Exception as e:
				self.show_error(f"Erro ao abrir PDF: {e}")
		else:
			self.show_error(f"Erro ao gerar PDF: {resultado}")