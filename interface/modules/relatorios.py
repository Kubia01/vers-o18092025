import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import sqlite3
import os
import json
import sys
from datetime import datetime
from .base_module import BaseModule
from database import DB_NAME
from utils.formatters import format_date
# Import adiado para evitar falhas na importação do módulo quando bibliotecas de PDF não estiverem presentes

def _lazy_gerar_pdf_relatorio():
	from pdf_generators.relatorio_tecnico import gerar_pdf_relatorio as _gpr
	return _gpr

class RelatoriosModule(BaseModule):
	def setup_ui(self):
		# Inicializar variáveis primeiro
		self.current_relatorio_id = None
		self.tecnicos_eventos = {}
		self.anexos_aba = {1: [], 2: [], 3: [], 4: []}
		
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
		
		# Painel de relatório (esquerda)
		form_panel = tk.Frame(main_frame, bg='#f8fafc')
		form_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=(10, 10))
		form_panel.grid_columnconfigure(0, weight=1)
		
		# Botões fixos no rodapé do painel de formulário
		self.create_relatorio_buttons(form_panel)
		
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
		self.create_relatorio_content(form_inner)

		# Preencher número sequencial automaticamente ao abrir, se não houver relatório carregado
		try:
			if not self.current_relatorio_id:
				numero = self.gerar_numero_sequencial_relatorio()
				self.numero_relatorio_var.set(numero)
		except Exception as e:
			print(f"Aviso ao gerar número sequencial inicial de relatório: {e}")
		
		# Painel da lista (direita)
		lista_panel = tk.Frame(main_frame, bg='#f8fafc')
		lista_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 10), pady=(10, 10))
		lista_panel.grid_columnconfigure(0, weight=1)
		lista_panel.grid_rowconfigure(2, weight=1)
		
		lista_card = tk.Frame(lista_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
		lista_card.pack(fill="both", expand=True)
		
		tk.Label(lista_card, text="📋 Lista de Relatórios", font=("Arial", 12, "bold"), bg='white', anchor="w").pack(fill="x", padx=12, pady=(12, 8))
		
		lista_inner = tk.Frame(lista_card, bg='white')
		lista_inner.pack(fill="both", expand=True, padx=12, pady=(0, 12))
		
		# Busca
		search_frame, self.search_var = self.create_search_frame(lista_inner, command=self.buscar_relatorios)
		search_frame.pack(fill="x", pady=(0, 10))
		
		# Reservar rodapé dos botões da lista antes da Treeview
		lista_buttons = tk.Frame(lista_inner, bg='white')
		lista_buttons.pack(side="bottom", fill="x", pady=(10, 0))
		
		# Treeview
		columns = ("numero", "cliente", "data", "responsavel", "tipo")
		self.relatorios_tree = ttk.Treeview(lista_inner, columns=columns, show="headings")
		self.relatorios_tree.heading("numero", text="Número")
		self.relatorios_tree.heading("cliente", text="Cliente")
		self.relatorios_tree.heading("data", text="Data")
		self.relatorios_tree.heading("responsavel", text="Responsável")
		self.relatorios_tree.heading("tipo", text="Tipo")
		self.relatorios_tree.column("numero", width=150)
		self.relatorios_tree.column("cliente", width=200)
		self.relatorios_tree.column("data", width=100)
		self.relatorios_tree.column("responsavel", width=150)
		self.relatorios_tree.column("tipo", width=120)
		
		lista_scrollbar = ttk.Scrollbar(lista_inner, orient="vertical", command=self.relatorios_tree.yview)
		self.relatorios_tree.configure(yscrollcommand=lista_scrollbar.set)
		
		self.relatorios_tree.pack(side="left", fill="both", expand=True)
		lista_scrollbar.pack(side="right", fill="y")
		
		# Botões da lista
		editar_btn = self.create_button(lista_buttons, "Editar", self.editar_relatorio)
		editar_btn.pack(side="left", padx=(0, 10))
		
		duplicar_btn = self.create_button(lista_buttons, "Duplicar", self.duplicar_relatorio, bg='#f59e0b')
		duplicar_btn.pack(side="left", padx=(0, 10))
		
		gerar_pdf_lista_btn = self.create_button(lista_buttons, "Gerar PDF", self.gerar_pdf_selecionado, bg='#10b981')
		gerar_pdf_lista_btn.pack(side="right", padx=(0, 10))
		
		abrir_pdf_lista_btn = self.create_button(lista_buttons, "Abrir PDF", self.abrir_pdf_selecionado, bg='#3b82f6')
		abrir_pdf_lista_btn.pack(side="right")
		
		excluir_btn = self.create_button(lista_buttons, "Excluir", self.excluir_relatorio, bg='#dc2626')
		excluir_btn.pack(side="right", padx=(10, 0))
		
		# Dados iniciais
		self.refresh_all_data()
		
		# Listener para eventos de usuários
		# self.bind_event('usuario_created', self.on_usuario_created)  # Removido - método não existe

	def create_header(self, parent):
		header_frame = tk.Frame(parent, bg='#f8fafc')
		header_frame.pack(fill="x", pady=(0, 10))
		
		title_label = tk.Label(header_frame, text="Relatórios Técnicos", 
							   font=('Arial', 16, 'bold'),
							   bg='#f8fafc',
							   fg='#1e293b')
		title_label.pack(side="left")
		
	# Estrutura antiga baseada em notebook removida; conteúdo agora no layout único
	def create_relatorio_content(self, parent):
		# Frame principal com grid 2 colunas, 100% da tela
		main_grid = tk.Frame(parent, bg='white')
		main_grid.pack(fill="both", expand=True)

		# 2 colunas, 1 linha
		main_grid.grid_columnconfigure(0, weight=1, uniform="col")
		main_grid.grid_columnconfigure(1, weight=1, uniform="col")
		main_grid.grid_rowconfigure(0, weight=1, uniform="row")

		# Coluna 0: Informações (stacked)
		info_frame = tk.Frame(main_grid, bg='white', relief='groove', bd=2)
		info_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=2, pady=2)
		self.create_cliente_section(info_frame)
		self.create_servico_section(info_frame)
		self.create_tecnicos_section(info_frame)
		self.create_equipamento_section(info_frame)
		self.create_vinculacao_section(info_frame)

		# Coluna 1: Dashboard (ocupa toda a altura)
		# Coluna 1 removida (dashboard)

		# Botões de ação já estão fixos no rodapé do painel de formulário (setup_ui)

	def create_cliente_section(self, parent):
		section_frame = self.create_section_frame(parent, "Identificação do Cliente")
		section_frame.pack(fill="x", pady=(0, 10))
		
		# Grid de campos
		fields_frame = tk.Frame(section_frame, bg='white')
		fields_frame.pack(fill="x")
		
		# Variáveis
		self.cliente_var = tk.StringVar()
		
		# Cliente com busca reativa
		tk.Label(fields_frame, text="Cliente *:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=0, column=0, sticky="w", pady=5, padx=(20, 0))
		
		cliente_frame = tk.Frame(fields_frame, bg='white')
		cliente_frame.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(10, 0), pady=5)
		
		self.cliente_combo = ttk.Combobox(cliente_frame, textvariable=self.cliente_var, width=40)
		self.cliente_combo.pack(side="left", fill="x", expand=True)
		self.cliente_combo.bind("<<ComboboxSelected>>", self.on_cliente_selected)
		
		# Refresh button removed
		
		# Campos removidos da seção de identificação do cliente (mantidos apenas na seção "Dados do Serviço")
		
		# Configurar colunas
		fields_frame.grid_columnconfigure(1, weight=1)
		
	def create_servico_section(self, parent):
		section_frame = self.create_section_frame(parent, "Dados do Serviço")
		section_frame.pack(fill="x", pady=(0, 10))
		
		# Grid de campos
		fields_frame = tk.Frame(section_frame, bg='white')
		fields_frame.pack(fill="x")
		
		# Variáveis
		self.numero_relatorio_var = tk.StringVar()
		self.data_criacao_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
		self.formulario_servico_var = tk.StringVar()
		self.tipo_servico_var = tk.StringVar()
		self.data_recebimento_var = tk.StringVar()
		self.filial_var = tk.StringVar(value="2 - WORLD COMP DO BRASIL COMPRESSORES LTDA")
		
		row = 0
		
		# Número do Relatório
		tk.Label(fields_frame, text="Número do Relatório:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		tk.Entry(fields_frame, textvariable=self.numero_relatorio_var, 
				 font=('Arial', 10), width=30).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		
		# Data de Criação
		tk.Label(fields_frame, text="Data de Criação:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=2, sticky="w", pady=5, padx=(20, 0))
		tk.Entry(fields_frame, textvariable=self.data_criacao_var, 
				 font=('Arial', 10), width=15).grid(row=row, column=3, sticky="w", padx=(10, 0), pady=5)
		row += 1
		
		# Formulário de Serviço
		tk.Label(fields_frame, text="Formulário de Serviço:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		tk.Entry(fields_frame, textvariable=self.formulario_servico_var, 
				 font=('Arial', 10), width=30).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		
		# Tipo de Serviço
		tk.Label(fields_frame, text="Tipo de Serviço:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=2, sticky="w", pady=5, padx=(20, 0))
		tipo_combo = ttk.Combobox(fields_frame, textvariable=self.tipo_servico_var, 
								 values=["Manutenção", "Reparo", "Instalação", "Inspeção", "Consultoria"],
								 width=12)
		tipo_combo.grid(row=row, column=3, sticky="w", padx=(10, 0), pady=5)
		row += 1
		
		# Data de Recebimento
		tk.Label(fields_frame, text="Data de Recebimento:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		tk.Entry(fields_frame, textvariable=self.data_recebimento_var, 
				 font=('Arial', 10), width=30).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1
		
		# Descrição do Serviço
		tk.Label(fields_frame, text="Descrição do Serviço:", 
				 font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="nw", pady=5)
		self.descricao_text = scrolledtext.ScrolledText(fields_frame, height=3, width=40)
		self.descricao_text.grid(row=row, column=1, columnspan=3, sticky="ew", padx=(10, 0), pady=5)
		
		# Configurar colunas
		fields_frame.grid_columnconfigure(1, weight=1)
		
	def create_tecnicos_section(self, parent):
		section_frame = self.create_section_frame(parent, "Técnicos e Eventos")
		section_frame.pack(fill="x", pady=(0, 15))
		
		# Frame para adicionar técnico
		add_tecnico_frame = tk.Frame(section_frame, bg='white')
		add_tecnico_frame.pack(fill="x", pady=(0, 10))
		
		tk.Label(add_tecnico_frame, text="Adicionar Técnico:", 
				 font=('Arial', 10, 'bold'), bg='white').pack(side="left")
		
		self.tecnico_var = tk.StringVar()
		self.tecnico_combo = ttk.Combobox(add_tecnico_frame, textvariable=self.tecnico_var, width=30)
		self.tecnico_combo.pack(side="left", padx=(10, 0))
		
		# Refresh button removed
		
		add_tecnico_btn = self.create_button(add_tecnico_frame, "Adicionar Técnico", self.adicionar_tecnico)
		add_tecnico_btn.pack(side="left", padx=(10, 0))
		
		# Refresh button removed
		
		# Notebook para técnicos
		self.tecnicos_notebook = ttk.Notebook(section_frame)
		self.tecnicos_notebook.pack(fill="both", expand=True, pady=(10, 0))
		
	def create_equipamento_section(self, parent):
		section_frame = self.create_section_frame(parent, "Condição do Equipamento")
		section_frame.pack(fill="both", expand=True, pady=(0, 15))
		
		# Notebook para as 4 abas
		self.equipamento_notebook = ttk.Notebook(section_frame)
		self.equipamento_notebook.pack(fill="both", expand=True, pady=(10, 0))
		
		# Aba 1: Condição Inicial
		self.create_aba1_condicao_inicial()
		
		# Aba 2: Peritagem do Subconjunto
		self.create_aba2_peritagem()
		
		# Aba 3: Desmembrando Unidade Compressora
		self.create_aba3_desmembrando()
		
		# Aba 4: Relação de Peças e Serviços
		self.create_aba4_pecas_servicos()
		
	def create_aba1_condicao_inicial(self):
		frame1 = tk.Frame(self.equipamento_notebook, bg='white')
		self.equipamento_notebook.add(frame1, text="1. Condição Inicial")
		
		# Título
		tk.Label(frame1, text="CONDIÇÃO ATUAL DO EQUIPAMENTO", 
				font=('Arial', 12, 'bold'), bg='white').pack(anchor="w", pady=5)
		
		# Campos da aba 1
		campos_aba1 = [
			"Cond. Encontrada",
			"Placa/N.Série",
			"Acoplamento",
			"Aspectos Rotores",
			"Válvulas Acopladas",
			"Data Recebimento"
		]
		
		self.aba1_vars = {}
		fields_frame = tk.Frame(frame1, bg='white')
		fields_frame.pack(fill="x", padx=10, pady=5)
		
		for i, campo in enumerate(campos_aba1):
			row = i // 2
			col = (i % 2) * 2
			
			tk.Label(fields_frame, text=f"{campo}:", font=('Arial', 9, 'bold'), 
					bg='white').grid(row=row, column=col, sticky="w", padx=5, pady=2)
			
			var = tk.StringVar()
			entry = tk.Entry(fields_frame, textvariable=var, font=('Arial', 9), width=25)
			entry.grid(row=row, column=col+1, sticky="ew", padx=5, pady=2)
			
			self.aba1_vars[campo] = var
		
		# Configurar grid
		for i in range(2):
			fields_frame.grid_columnconfigure(i*2+1, weight=1)
		
		# Seção de anexos
		self.create_anexos_section(frame1, 1)
		
	def create_aba2_peritagem(self):
		frame2 = tk.Frame(self.equipamento_notebook, bg='white')
		self.equipamento_notebook.add(frame2, text="2. Peritagem do Subconjunto")
		
		# Título
		tk.Label(frame2, text="DESACOPLANDO ELEMENTO COMPRESSOR DA CAIXA DE ACIONAMENTO", 
				font=('Arial', 12, 'bold'), bg='white').pack(anchor="w", pady=5)
		
		# Campos da aba 2
		campos_aba2 = [
			"Parafusos/Pinos",
			"Superfície Vedação",
			"Engrenagens",
			"Bico Injetor",
			"Rolamentos",
			"Aspecto Óleo",
			"Data"
		]
		
		self.aba2_vars = {}
		fields_frame = tk.Frame(frame2, bg='white')
		fields_frame.pack(fill="x", padx=10, pady=5)
		
		for i, campo in enumerate(campos_aba2):
			row = i // 2
			col = (i % 2) * 2
			
			tk.Label(fields_frame, text=f"{campo}:", font=('Arial', 9, 'bold'), 
					bg='white').grid(row=row, column=col, sticky="w", padx=5, pady=2)
			
			var = tk.StringVar()
			entry = tk.Entry(fields_frame, textvariable=var, font=('Arial', 9), width=25)
			entry.grid(row=row, column=col+1, sticky="ew", padx=5, pady=2)
			
			self.aba2_vars[campo] = var
		
		# Configurar grid
		for i in range(2):
			fields_frame.grid_columnconfigure(i*2+1, weight=1)
		
		# Seção de anexos
		self.create_anexos_section(frame2, 2)
		
	def create_aba3_desmembrando(self):
		frame3 = tk.Frame(self.equipamento_notebook, bg='white')
		self.equipamento_notebook.add(frame3, text="3. Desmembrando Unidade Compressora")
		
		# Título
		tk.Label(frame3, text="GRAU DE INTERFERÊNCIA NA DESMONTAGEM", 
				font=('Arial', 12, 'bold'), bg='white').pack(anchor="w", pady=5)
		
		# Campos da aba 3
		campos_aba3 = [
			"Interf. Desmontagem",
			"Aspecto Rotores",
			"Aspecto Carcaça",
			"Interf. Mancais",
			"Galeria Hidráulica",
			"Data Desmembração"
		]
		
		self.aba3_vars = {}
		fields_frame = tk.Frame(frame3, bg='white')
		fields_frame.pack(fill="x", padx=10, pady=5)
		
		for i, campo in enumerate(campos_aba3):
			row = i // 2
			col = (i % 2) * 2
			
			tk.Label(fields_frame, text=f"{campo}:", font=('Arial', 9, 'bold'), 
					bg='white').grid(row=row, column=col, sticky="w", padx=5, pady=2)
			
			var = tk.StringVar()
			entry = tk.Entry(fields_frame, textvariable=var, font=('Arial', 9), width=25)
			entry.grid(row=row, column=col+1, sticky="ew", padx=5, pady=2)
			
			self.aba3_vars[campo] = var
		
		# Configurar grid
		for i in range(2):
			fields_frame.grid_columnconfigure(i*2+1, weight=1)
		
		# Seção de anexos
		self.create_anexos_section(frame3, 3)
		
	def create_aba4_pecas_servicos(self):
		frame4 = tk.Frame(self.equipamento_notebook, bg='white')
		self.equipamento_notebook.add(frame4, text="4. Relação de Peças e Serviços")
		
		# Serviços Propostos
		tk.Label(frame4, text="SERVIÇOS PROPOSTO PARA REFORMA DO SUBCONJUNTO:", 
				font=('Arial', 10, 'bold'), bg='white').pack(anchor="w", pady=5)
		
		self.servicos_text = scrolledtext.ScrolledText(frame4, height=5, wrap=tk.WORD)
		self.servicos_text.pack(fill="x", padx=10, pady=2)
		
		# Peças Recomendadas
		tk.Label(frame4, text="PEÇAS RECOMENDADAS PARA REFORMA:", 
				font=('Arial', 10, 'bold'), bg='white').pack(anchor="w", pady=5)
		
		self.pecas_text = scrolledtext.ScrolledText(frame4, height=5, wrap=tk.WORD)
		self.pecas_text.pack(fill="x", padx=10, pady=2)
		
		# Data
		data_frame = tk.Frame(frame4, bg='white')
		data_frame.pack(fill="x", padx=10, pady=5)
		
		tk.Label(data_frame, text="DATA:", font=('Arial', 10, 'bold'), bg='white').pack(side="left")
		self.data_pecas_var = tk.StringVar()
		tk.Entry(data_frame, textvariable=self.data_pecas_var, font=('Arial', 10), width=20).pack(side="left", padx=(10, 0))
		
		# Seção de anexos
		self.create_anexos_section(frame4, 4)
		
	def create_anexos_section(self, parent, aba_numero):
		# Título da seção de anexos
		anexos_frame = tk.LabelFrame(parent, text="Anexos", font=('Arial', 10, 'bold'), bg='white')
		anexos_frame.pack(fill="both", expand=True, padx=10, pady=10)
		
		# Frame para lista de anexos
		lista_anexos_frame = tk.Frame(anexos_frame, bg='white')
		lista_anexos_frame.pack(fill="both", expand=True)
		
		# Listbox para anexos
		anexos_listbox = tk.Listbox(lista_anexos_frame, height=4)
		anexos_listbox.pack(fill="both", expand=True, padx=5, pady=5)
		
		# Armazenar referência
		setattr(self, f'anexos_listbox_aba{aba_numero}', anexos_listbox)
		
		# Botões
		btn_frame = tk.Frame(anexos_frame, bg='white')
		btn_frame.pack(fill="x", padx=5, pady=5)
		
		add_anexo_btn = self.create_button(btn_frame, "Adicionar Anexo", 
										  lambda: self.adicionar_anexo(aba_numero), bg='#10b981')
		add_anexo_btn.pack(side="left", padx=(0, 5))
		
		remove_anexo_btn = self.create_button(btn_frame, "Remover Anexo", 
											 lambda: self.remover_anexo(aba_numero), bg='#dc2626')
		remove_anexo_btn.pack(side="left")
		
		abrir_anexo_btn = self.create_button(btn_frame, "Abrir Anexo", 
											 lambda: self.abrir_anexo(aba_numero), bg='#64748b')
		abrir_anexo_btn.pack(side="left", padx=(10, 0))
		
	def create_vinculacao_section(self, parent):
		section_frame = self.create_section_frame(parent, "Vinculação com Cotação")
		section_frame.pack(fill="x", pady=(0, 15))
		
		# Campo para selecionar cotação
		vinc_frame = tk.Frame(section_frame, bg='white')
		vinc_frame.pack(fill="x")
		
		tk.Label(vinc_frame, text="Cotação Vinculada:", 
				 font=('Arial', 10, 'bold'), bg='white').pack(side="left")
		
		self.cotacao_var = tk.StringVar()
		self.cotacao_combo = ttk.Combobox(vinc_frame, textvariable=self.cotacao_var, width=40)
		self.cotacao_combo.pack(side="left", padx=(10, 0))
		
	def create_relatorio_buttons(self, parent):
		buttons_frame = tk.Frame(parent, bg='white')
		buttons_frame.pack(fill="x", pady=(20, 0))
		
		# Botões
		novo_btn = self.create_button(buttons_frame, "Novo Relatório", self.novo_relatorio, bg='#e2e8f0', fg='#475569')
		novo_btn.pack(side="left", padx=(0, 10))
		
		salvar_btn = self.create_button(buttons_frame, "Salvar Relatório", self.salvar_relatorio)
		salvar_btn.pack(side="left", padx=(0, 10))
		
		gerar_pdf_btn = self.create_button(buttons_frame, "Gerar PDF", self.gerar_pdf, bg='#10b981')
		gerar_pdf_btn.pack(side="right", padx=(0, 10))
		
		abrir_pdf_btn = self.create_button(buttons_frame, "Abrir PDF", self.abrir_pdf, bg='#3b82f6')
		abrir_pdf_btn.pack(side="right")
		
	# Lista de relatórios integrada no layout único
	def refresh_all_data(self):
		"""Atualizar todos os dados do módulo"""
		self.refresh_clientes()
		self.refresh_tecnicos()
		self.refresh_cotacoes()
		self.carregar_relatorios()
		
	def on_usuario_created(self, event_data=None):
		"""Evento disparado quando um novo usuário é criado"""
		print("DEBUG: Evento usuario_created recebido, atualizando lista de técnicos...")
		self.refresh_tecnicos()
		
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
			
			print(f"Clientes carregados no relatório: {len(cliente_values)}")  # Debug
			
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar clientes: {e}")
		finally:
			conn.close()
			
	def refresh_tecnicos(self):
		"""Atualizar lista de técnicos (agora baseado em usuários)"""
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			# Buscar usuários em vez de técnicos
			c.execute("SELECT id, nome_completo FROM usuarios WHERE nome_completo IS NOT NULL ORDER BY nome_completo")
			tecnicos = c.fetchall()
			
			self.tecnicos_dict = {f"{nome} (ID: {id})": id for id, nome in tecnicos}
			tecnico_values = list(self.tecnicos_dict.keys())
			
			self.tecnico_combo['values'] = tecnico_values
			
			print(f"Técnicos carregados: {len(tecnico_values)}")  # Debug
			
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar técnicos: {e}")
		finally:
			conn.close()
			
	def refresh_cotacoes(self):
		"""Atualizar lista de cotações"""
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			c.execute("SELECT id, numero_proposta FROM cotacoes ORDER BY numero_proposta")
			cotacoes = c.fetchall()
			
			self.cotacoes_dict = {f"{numero} (ID: {id})": id for id, numero in cotacoes}
			cotacao_values = [""] + list(self.cotacoes_dict.keys())  # Incluir opção vazia
			
			self.cotacao_combo['values'] = cotacao_values
			
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar cotações: {e}")
		finally:
			conn.close()
			
	def adicionar_tecnico(self):
		"""Adicionar técnico ao relatório"""
		if not self.can_edit('relatorios'):
			self.show_warning("Você não tem permissão para adicionar técnicos.")
			return
			
		tecnico_str = self.tecnico_var.get().strip()
		if not tecnico_str:
			self.show_warning("Selecione um técnico.")
			return
			
		tecnico_id = self.tecnicos_dict.get(tecnico_str)
		if not tecnico_id:
			self.show_warning("Técnico selecionado inválido.")
			return
			
		# Verificar se técnico já foi adicionado
		if tecnico_id in self.tecnicos_eventos:
			self.show_warning("Técnico já foi adicionado.")
			return
			
		# Criar aba para o técnico
		tecnico_nome = tecnico_str.split(' (ID:')[0]
		tecnico_frame = tk.Frame(self.tecnicos_notebook, bg='white')
		self.tecnicos_notebook.add(tecnico_frame, text=tecnico_nome)
		
		# Frame para adicionar eventos
		add_evento_frame = tk.Frame(tecnico_frame, bg='white')
		add_evento_frame.pack(fill="x", padx=10, pady=5)
		
		tk.Label(add_evento_frame, text="Data/Hora:", font=('Arial', 9, 'bold'), bg='white').grid(row=0, column=0, sticky="w")
		data_hora_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y %H:%M'))
		tk.Entry(add_evento_frame, textvariable=data_hora_var, width=15).grid(row=0, column=1, padx=5)
		
		tk.Label(add_evento_frame, text="Tipo:", font=('Arial', 9, 'bold'), bg='white').grid(row=0, column=2, sticky="w", padx=(10, 0))
		tipo_var = tk.StringVar(value="Início")
		tipo_combo = ttk.Combobox(add_evento_frame, textvariable=tipo_var, 
								 values=["Início", "Fim", "Pausa"], width=10, state="readonly")
		tipo_combo.grid(row=0, column=3, padx=5)
		
		tk.Label(add_evento_frame, text="Evento:", font=('Arial', 9, 'bold'), bg='white').grid(row=1, column=0, sticky="w")
		evento_var = tk.StringVar()
		evento_entry = tk.Entry(add_evento_frame, textvariable=evento_var, width=50)
		evento_entry.grid(row=1, column=1, columnspan=2, padx=5, sticky="ew")
		
		# Substitui botão grande por Enter para adicionar
		evento_entry.bind('<Return>', lambda e: self.adicionar_evento(tecnico_id, data_hora_var, tipo_var, evento_var, eventos_tree))
		tipo_combo.bind('<Return>', lambda e: self.adicionar_evento(tecnico_id, data_hora_var, tipo_var, evento_var, eventos_tree))
		
		# Grid de eventos
		eventos_tree = ttk.Treeview(tecnico_frame, columns=("data_hora", "tipo", "evento"), show="headings", height=8)
		eventos_tree.heading("data_hora", text="Data/Hora")
		eventos_tree.heading("tipo", text="Tipo")
		eventos_tree.heading("evento", text="Evento")
		eventos_tree.pack(fill="both", expand=True, padx=10, pady=5)
		
		# Botão para remover evento
		remove_evento_btn = self.create_button(tecnico_frame, "Remover Evento", 
											  lambda: self.remover_evento(eventos_tree), bg='#dc2626')
		remove_evento_btn.pack(pady=5)
		
		# Armazenar referências
		self.tecnicos_eventos[tecnico_id] = {
			'nome': tecnico_nome,
			'tree': eventos_tree,
			'data_hora_var': data_hora_var,
			'tipo_var': tipo_var,
			'evento_var': evento_var
		}
		
		# Limpar seleção
		self.tecnico_var.set("")
		
	def adicionar_evento(self, tecnico_id, data_hora_var, tipo_var, evento_var, tree):
		"""Adicionar evento ao técnico"""
		data_hora = data_hora_var.get().strip()
		tipo = tipo_var.get()
		evento = evento_var.get().strip()
		
		if not data_hora or not evento:
			self.show_warning("Preencha data/hora e evento.")
			return
			
		# Adicionar à lista
		tree.insert("", "end", values=(data_hora, tipo, evento))
		
		# Limpar campos
		evento_var.set("")
		data_hora_var.set(datetime.now().strftime('%d/%m/%Y %H:%M'))
		
	def remover_evento(self, tree):
		"""Remover evento selecionado"""
		selected = tree.selection()
		if not selected:
			self.show_warning("Selecione um evento para remover.")
			return
			
		for item in selected:
			tree.delete(item)
			
	def adicionar_anexo(self, aba_numero):
		"""Adicionar anexo à aba"""
		if not self.can_edit('relatorios'):
			self.show_warning("Você não tem permissão para adicionar anexos.")
			return
			
		filepaths = filedialog.askopenfilenames(
			title=f"Selecionar Anexos para Aba {aba_numero}",
			filetypes=[("Todos os arquivos", "*.*"), ("Imagens", "*.jpg *.jpeg *.png"), ("PDFs", "*.pdf")]
		)
		
		if not filepaths:
			return
		
		listbox = getattr(self, f'anexos_listbox_aba{aba_numero}')
		
		for filepath in filepaths:
			try:
				nome_arquivo = os.path.basename(filepath)
			except Exception:
				nome_arquivo = str(filepath).split('/')[-1]
			anexo_info = {
				'nome': nome_arquivo,
				'caminho': filepath,
				'descricao': f'Anexo da Aba {aba_numero}'
			}
			self.anexos_aba[aba_numero].append(anexo_info)
			listbox.insert(tk.END, nome_arquivo)
		
	def remover_anexo(self, aba_numero):
		"""Remover anexo selecionado"""
		listbox = getattr(self, f'anexos_listbox_aba{aba_numero}')
		selected = listbox.curselection()
		
		if not selected:
			self.show_warning("Selecione um anexo para remover.")
			return
			
		index = selected[0]
		
		# Remover da lista
		self.anexos_aba[aba_numero].pop(index)
		
		# Remover da listbox
		listbox.delete(index)
		
	def _debug_anexos_json(self, aba_num):
		"""Debug function para ver o que está sendo salvo nos anexos"""
		anexos = self.anexos_aba[aba_num] if self.anexos_aba[aba_num] else []
		json_result = json.dumps(anexos) if anexos else "[]"
		print(f"DEBUG: Aba {aba_num} tem {len(anexos)} anexos: {json_result}")
		return json_result
	
	def gerar_numero_sequencial_relatorio(self) -> str:
		"""Gerar número sequencial para relatório técnico (formato REL-000001)."""
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute("SELECT MAX(CAST(SUBSTR(numero_relatorio, 5) AS INTEGER)) FROM relatorios_tecnicos WHERE numero_relatorio LIKE 'REL-%'")
			result = c.fetchone()
			if result and result[0]:
				proximo = result[0] + 1
			else:
				proximo = 1
			return f"REL-{proximo:06d}"
		except sqlite3.Error as e:
			print(f"Erro ao gerar número sequencial de relatório: {e}")
			from datetime import datetime
			return f"REL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
		finally:
			try:
				conn.close()
			except Exception:
				pass

	def novo_relatorio(self):
		"""Limpar formulário para novo relatório"""
		self.current_relatorio_id = None
		
		# Limpar campos básicos
		self.cliente_var.set("")
		self.numero_relatorio_var.set("")
		self.data_criacao_var.set(datetime.now().strftime('%d/%m/%Y'))
		self.formulario_servico_var.set("")
		self.tipo_servico_var.set("")
		self.data_recebimento_var.set("")
		self.descricao_text.delete("1.0", tk.END)
		
		# Limpar abas do equipamento
		for var_dict in [self.aba1_vars, self.aba2_vars, self.aba3_vars]:
			for var in var_dict.values():
				var.set("")
				
		self.servicos_text.delete("1.0", tk.END)
		self.pecas_text.delete("1.0", tk.END)
		self.data_pecas_var.set("")
		
		# Limpar técnicos
		for tab in self.tecnicos_notebook.tabs():
			self.tecnicos_notebook.forget(tab)
		self.tecnicos_eventos = {}
		
		# Limpar anexos
		for aba_num in range(1, 5):
			self.anexos_aba[aba_num] = []
			listbox = getattr(self, f'anexos_listbox_aba{aba_num}')
			listbox.delete(0, tk.END)
		
		# Limpar cotação
		self.cotacao_var.set("")
		
		# Gerar número sequencial automático
		numero = self.gerar_numero_sequencial_relatorio()
		self.numero_relatorio_var.set(numero)
		
	def limpar_formulario_edicao(self):
		"""Limpar formulário para edição sem apagar anexos"""
		self.current_relatorio_id = None
		
		# Limpar campos básicos
		self.cliente_var.set("")
		self.numero_relatorio_var.set("")
		self.data_criacao_var.set("")
		self.formulario_servico_var.set("")
		self.tipo_servico_var.set("")
		self.data_recebimento_var.set("")
		self.descricao_text.delete("1.0", tk.END)
		
		# Limpar abas do equipamento
		for var_dict in [self.aba1_vars, self.aba2_vars, self.aba3_vars]:
			for var in var_dict.values():
				var.set("")
				
		self.servicos_text.delete("1.0", tk.END)
		self.pecas_text.delete("1.0", tk.END)
		self.data_pecas_var.set("")
		
		# Limpar técnicos
		for tab in self.tecnicos_notebook.tabs():
			self.tecnicos_notebook.forget(tab)
		self.tecnicos_eventos = {}
		
		# Limpar cotação
		self.cotacao_var.set("")
		
		# NÃO limpar anexos - eles serão carregados depois
		
	def salvar_relatorio(self):
		"""Salvar relatório no banco de dados"""
		if not self.can_edit('relatorios'):
			self.show_warning("Você não tem permissão para salvar relatórios.")
			return
			
		# Validações
		cliente_str = self.cliente_var.get().strip()
		numero = self.numero_relatorio_var.get().strip()
		
		if not cliente_str:
			self.show_warning("Selecione um cliente.")
			return
			
		if not numero:
			self.show_warning("Informe o número do relatório.")
			return
			
		# Obter ID do cliente
		cliente_id = self.clientes_dict.get(cliente_str)
		if not cliente_id:
			self.show_warning("Cliente selecionado inválido.")
			return
			
		# Obter ID da cotação (opcional)
		cotacao_str = self.cotacao_var.get().strip()
		cotacao_id = None
		if cotacao_str:
			cotacao_id = self.cotacoes_dict.get(cotacao_str)
		
		# Obter ID da filial
		filial_str = self.filial_var.get()
		filial_id = int(filial_str.split(' - ')[0]) if ' - ' in filial_str else int(filial_str or 2)
		
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			# Preparar dados do relatório
			dados_relatorio = (
				numero,
				cliente_id,
				self.user_id,
				datetime.now().strftime('%Y-%m-%d') if not self.current_relatorio_id else None,
				self.formulario_servico_var.get().strip(),
				self.tipo_servico_var.get().strip(),
				self.descricao_text.get("1.0", tk.END).strip(),
				self.data_recebimento_var.get().strip(),
				
				# Aba 1
				self.aba1_vars.get("Cond. Encontrada", tk.StringVar()).get(),
				self.aba1_vars.get("Placa/N.Série", tk.StringVar()).get(),
				self.aba1_vars.get("Acoplamento", tk.StringVar()).get(),
				self.aba1_vars.get("Aspectos Rotores", tk.StringVar()).get(),
				self.aba1_vars.get("Válvulas Acopladas", tk.StringVar()).get(),
				self.aba1_vars.get("Data Recebimento", tk.StringVar()).get(),
				
				# Aba 2
				self.aba2_vars.get("Parafusos/Pinos", tk.StringVar()).get(),
				self.aba2_vars.get("Superfície Vedação", tk.StringVar()).get(),
				self.aba2_vars.get("Engrenagens", tk.StringVar()).get(),
				self.aba2_vars.get("Bico Injetor", tk.StringVar()).get(),
				self.aba2_vars.get("Rolamentos", tk.StringVar()).get(),
				self.aba2_vars.get("Aspecto Óleo", tk.StringVar()).get(),
				self.aba2_vars.get("Data", tk.StringVar()).get(),
				
				# Aba 3
				self.aba3_vars.get("Interf. Desmontagem", tk.StringVar()).get(),
				self.aba3_vars.get("Aspecto Rotores", tk.StringVar()).get(),
				self.aba3_vars.get("Aspecto Carcaça", tk.StringVar()).get(),
				self.aba3_vars.get("Interf. Mancais", tk.StringVar()).get(),
				self.aba3_vars.get("Galeria Hidráulica", tk.StringVar()).get(),
				self.aba3_vars.get("Data Desmembração", tk.StringVar()).get(),
				
				# Aba 4
				self.servicos_text.get("1.0", tk.END).strip(),
				self.pecas_text.get("1.0", tk.END).strip(),
				self.data_pecas_var.get().strip(),
				
				# Outros
				cotacao_id,
				"",  # tempo_trabalho_total
				"",  # tempo_deslocamento_total
				"",  # fotos
				self._debug_anexos_json(1),  # anexos_aba1
				self._debug_anexos_json(2),  # anexos_aba2
				self._debug_anexos_json(3),  # anexos_aba3
				self._debug_anexos_json(4),  # anexos_aba4
				filial_id
			)
			
			if self.current_relatorio_id:
				# Atualizar relatório existente
				c.execute("""
					UPDATE relatorios_tecnicos SET
						numero_relatorio = ?, cliente_id = ?, formulario_servico = ?,
						tipo_servico = ?, descricao_servico = ?, data_recebimento = ?,
						condicao_encontrada = ?, placa_identificacao = ?, acoplamento = ?,
						aspectos_rotores = ?, valvulas_acopladas = ?, data_recebimento_equip = ?,
						parafusos_pinos = ?, superficie_vedacao = ?, engrenagens = ?,
						bico_injetor = ?, rolamentos = ?, aspecto_oleo = ?, data_peritagem = ?,
						interf_desmontagem = ?, aspecto_rotores_aba3 = ?, aspecto_carcaca = ?,
						interf_mancais = ?, galeria_hidraulica = ?, data_desmembracao = ?,
						servicos_propostos = ?, pecas_recomendadas = ?, data_pecas = ?,
						cotacao_id = ?, tempo_trabalho_total = ?, tempo_deslocamento_total = ?,
						fotos = ?, anexos_aba1 = ?, anexos_aba2 = ?, anexos_aba3 = ?, anexos_aba4 = ?,
						filial_id = ?
					WHERE id = ?
				""", (dados_relatorio[0], dados_relatorio[1]) + dados_relatorio[4:-1] + (dados_relatorio[-1], self.current_relatorio_id,))
				
				# Remover eventos antigos
				c.execute("DELETE FROM eventos_campo WHERE relatorio_id = ?", (self.current_relatorio_id,))
				relatorio_id = self.current_relatorio_id
			else:
				# Inserir novo relatório
				c.execute("""
					INSERT INTO relatorios_tecnicos (
						numero_relatorio, cliente_id, responsavel_id, data_criacao,
						formulario_servico, tipo_servico, descricao_servico, data_recebimento,
						condicao_encontrada, placa_identificacao, acoplamento, aspectos_rotores,
						valvulas_acopladas, data_recebimento_equip, parafusos_pinos, superficie_vedacao,
						engrenagens, bico_injetor, rolamentos, aspecto_oleo, data_peritagem,
						interf_desmontagem, aspecto_rotores_aba3, aspecto_carcaca, interf_mancais,
						galeria_hidraulica, data_desmembracao, servicos_propostos, pecas_recomendadas,
						data_pecas, cotacao_id, tempo_trabalho_total, tempo_deslocamento_total,
						fotos, anexos_aba1, anexos_aba2, anexos_aba3, anexos_aba4, filial_id
					) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
				""", dados_relatorio)
				
				relatorio_id = c.lastrowid
				self.current_relatorio_id = relatorio_id
			
			# Copiar anexos para pasta do relatório e atualizar caminhos
			base_dir = os.path.join('data', 'relatorios', 'anexos', str(relatorio_id))
			os.makedirs(base_dir, exist_ok=True)
			for aba_num in range(1, 5):
				new_list = []
				for anexo in self.anexos_aba.get(aba_num, []):
					if isinstance(anexo, dict):
						orig_path = anexo.get('caminho') or anexo.get('path')
						name = anexo.get('nome') or os.path.basename(str(orig_path or ''))
						try:
							if orig_path and os.path.exists(orig_path):
								dest_path = os.path.join(base_dir, name)
								if os.path.abspath(orig_path) != os.path.abspath(dest_path):
									import shutil
									shutil.copy2(orig_path, dest_path)
								anexo['caminho'] = dest_path
						except Exception:
							pass
						new_list.append(anexo)
					else:
						# string legacy
						name = os.path.basename(str(anexo))
						dest_path = os.path.join(base_dir, name)
						try:
							if os.path.exists(str(anexo)) and os.path.abspath(str(anexo)) != os.path.abspath(dest_path):
								import shutil
								shutil.copy2(str(anexo), dest_path)
						except Exception:
							pass
						new_list.append({'nome': name, 'caminho': dest_path, 'descricao': f'Anexo da Aba {aba_num}'})
				# Persistir JSON atualizado por aba
				try:
					json_updated = json.dumps(new_list)
					c.execute(f"UPDATE relatorios_tecnicos SET anexos_aba{aba_num} = ? WHERE id = ?", (json_updated, relatorio_id))
				except Exception:
					pass
			
			# Inserir eventos dos técnicos
			for tecnico_id, tecnico_data in self.tecnicos_eventos.items():
				tree = tecnico_data['tree']
				for item in tree.get_children():
					data_hora, tipo, evento = tree.item(item)['values']
					c.execute("""
						INSERT INTO eventos_campo (relatorio_id, tecnico_id, data_hora, evento, tipo)
						VALUES (?, ?, ?, ?, ?)
					""", (relatorio_id, tecnico_id, data_hora, evento, tipo))
			
			conn.commit()
			self.show_success("Relatório salvo com sucesso!")
			
			# Emitir evento para atualizar outros módulos
			self.emit_event('relatorio_created')
			
			# Recarregar lista
			self.carregar_relatorios()
			
		except sqlite3.Error as e:
			self.show_error(f"Erro ao salvar relatório: {e}")
			import traceback
			print(f"Erro completo: {traceback.format_exc()}")
		finally:
			conn.close()
			
	def carregar_relatorios(self):
		"""Carregar lista de relatórios"""
		# Limpar lista atual
		for item in self.relatorios_tree.get_children():
			self.relatorios_tree.delete(item)
			
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			c.execute("""
				SELECT r.id, r.numero_relatorio, cl.nome, r.data_criacao, 
					   u.nome_completo, r.tipo_servico
				FROM relatorios_tecnicos r
				JOIN clientes cl ON r.cliente_id = cl.id
				JOIN usuarios u ON r.responsavel_id = u.id
				ORDER BY r.created_at DESC
			""")
			
			for row in c.fetchall():
				relatorio_id, numero, cliente, data, responsavel, tipo = row
				self.relatorios_tree.insert("", "end", values=(
					numero,
					cliente,
					format_date(data),
					responsavel,
					tipo or ""
				), tags=(relatorio_id,))
				
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar relatórios: {e}")
		finally:
			conn.close()
			
	def buscar_relatorios(self):
		"""Buscar relatórios com filtro"""
		termo = self.search_var.get().strip()
		
		# Limpar lista atual
		for item in self.relatorios_tree.get_children():
			self.relatorios_tree.delete(item)
			
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			if termo:
				c.execute("""
					SELECT r.id, r.numero_relatorio, cl.nome, r.data_criacao, 
						   u.nome_completo, r.tipo_servico
					FROM relatorios_tecnicos r
					JOIN clientes cl ON r.cliente_id = cl.id
					JOIN usuarios u ON r.responsavel_id = u.id
					WHERE r.numero_relatorio LIKE ? OR cl.nome LIKE ?
					ORDER BY r.created_at DESC
				""", (f"%{termo}%", f"%{termo}%"))
			else:
				c.execute("""
					SELECT r.id, r.numero_relatorio, cl.nome, r.data_criacao, 
						   u.nome_completo, r.tipo_servico
					FROM relatorios_tecnicos r
					JOIN clientes cl ON r.cliente_id = cl.id
					JOIN usuarios u ON r.responsavel_id = u.id
					ORDER BY r.created_at DESC
				""")
			
			for row in c.fetchall():
				relatorio_id, numero, cliente, data, responsavel, tipo = row
				self.relatorios_tree.insert("", "end", values=(
					numero,
					cliente,
					format_date(data),
					responsavel,
					tipo or ""
				), tags=(relatorio_id,))
				
		except sqlite3.Error as e:
			self.show_error(f"Erro ao buscar relatórios: {e}")
		finally:
			conn.close()
			
	def editar_relatorio(self):
		"""Editar/Visualizar relatório selecionado baseado nas permissões"""
		selected = self.relatorios_tree.selection()
		if not selected:
			self.show_warning("Selecione um relatório para visualizar/editar.")
			return
			
		# Obter ID do relatório
		tags = self.relatorios_tree.item(selected[0])['tags']
		if not tags:
			return
			
		relatorio_id = tags[0]
		if self.can_edit('relatorios'):
			# Editar
			self.carregar_relatorio_para_edicao(relatorio_id)
		else:
			# Visualizar em modo somente leitura
			try:
				self.carregar_relatorio_para_edicao(relatorio_id)
				if hasattr(self, 'set_read_only'):
					self.set_read_only(True)
				try:
					self.show_info("Visualizando relatório em modo somente leitura.")
				except Exception:
					pass
			except Exception as e:
				self.show_warning(f"Não foi possível visualizar o relatório: {e}")
		
	def carregar_relatorio_para_edicao(self, relatorio_id):
		"""Carregar dados do relatório para edição"""
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			# Carregar dados do relatório
			c.execute("SELECT * FROM relatorios_tecnicos WHERE id = ?", (relatorio_id,))
			relatorio = c.fetchone()
			
			if not relatorio:
				self.show_error("Relatório não encontrado.")
				return
				
			# Primeiro, limpar formulário (mas preservar anexos se for edição)
			self.limpar_formulario_edicao()
			
			# Preencher campos básicos
			self.current_relatorio_id = relatorio_id
			self.numero_relatorio_var.set(relatorio[1] or "")  # numero_relatorio
			
			# Encontrar cliente no combo
			for key, value in self.clientes_dict.items():
				if value == relatorio[2]:  # cliente_id
					self.cliente_var.set(key)
					break
					
			self.data_criacao_var.set(format_date(relatorio[4]) if relatorio[4] else "")
			self.formulario_servico_var.set(relatorio[5] or "")
			self.tipo_servico_var.set(relatorio[6] or "")
			
			# Descrição do serviço
			if relatorio[7]:
				self.descricao_text.insert("1.0", relatorio[7])
				
			self.data_recebimento_var.set(relatorio[8] or "")
			
			# Carregar dados das abas (índices 9-30)
			# Aba 1 (índices 9-14)
			aba1_campos = ["Cond. Encontrada", "Placa/N.Série", "Acoplamento", "Aspectos Rotores", "Válvulas Acopladas", "Data Recebimento"]
			for i, campo in enumerate(aba1_campos):
				if campo in self.aba1_vars:
					self.aba1_vars[campo].set(relatorio[9 + i] or "")
			
			# Aba 2 (índices 15-21)
			aba2_campos = ["Parafusos/Pinos", "Superfície Vedação", "Engrenagens", "Bico Injetor", "Rolamentos", "Aspecto Óleo", "Data"]
			for i, campo in enumerate(aba2_campos):
				if campo in self.aba2_vars:
					self.aba2_vars[campo].set(relatorio[15 + i] or "")
			
			# Aba 3 (índices 22-27)
			aba3_campos = ["Interf. Desmontagem", "Aspecto Rotores", "Aspecto Carcaça", "Interf. Mancais", "Galeria Hidráulica", "Data Desmembração"]
			for i, campo in enumerate(aba3_campos):
				if campo in self.aba3_vars:
					self.aba3_vars[campo].set(relatorio[22 + i] or "")
			
			# Aba 4 (índices 28-30)
			if relatorio[28]:  # servicos_propostos
				self.servicos_text.insert("1.0", relatorio[28])
			if relatorio[29]:  # pecas_recomendadas
				self.pecas_text.insert("1.0", relatorio[29])
			self.data_pecas_var.set(relatorio[30] or "")
			
			# Cotação vinculada
			if relatorio[31]:  # cotacao_id
				for key, value in self.cotacoes_dict.items():
					if value == relatorio[31]:
						self.cotacao_var.set(key)
						break
			
			# Filial: buscar de forma robusta
			try:
				c.execute("SELECT filial_id FROM relatorios_tecnicos WHERE id = ?", (relatorio_id,))
				row_f = c.fetchone()
				if row_f and row_f[0] in (1, 2):
					filial_id = row_f[0]
					nome_filial = "WORLD COMP COMPRESSORES LTDA" if filial_id == 1 else "WORLD COMP DO BRASIL COMPRESSORES LTDA"
					self.filial_var.set(f"{filial_id} - {nome_filial}")
			except Exception:
				pass
			
			# Carregar anexos usando colunas por aba, para evitar erros de índice
			for aba_num in range(1, 5):
				# Limpar anexos e listbox desta aba primeiro
				self.anexos_aba[aba_num] = []
				listbox = getattr(self, f'anexos_listbox_aba{aba_num}')
				listbox.delete(0, tk.END)

				anexos_str = None
				try:
					c.execute(f"SELECT anexos_aba{aba_num} FROM relatorios_tecnicos WHERE id = ?", (relatorio_id,))
					row_anx = c.fetchone()
					anexos_str = row_anx[0] if row_anx else None
				except Exception:
					anexos_str = None

				if anexos_str:
					try:
						# Tentar carregar como JSON
						self.anexos_aba[aba_num] = json.loads(anexos_str)
					except (json.JSONDecodeError, TypeError):
						# Fallback para formato antigo (separado por ;) ou string simples
						anexos_list = anexos_str.split(';') if isinstance(anexos_str, str) else []
						self.anexos_aba[aba_num] = [anexo for anexo in anexos_list if anexo]

				# Atualizar listbox com nomes
				for anexo in self.anexos_aba[aba_num]:
					if isinstance(anexo, dict):
						nome_candidate = anexo.get('nome') or anexo.get('caminho') or anexo.get('path') or 'Arquivo sem nome'
						nome_anexo = os.path.basename(str(nome_candidate))
					else:
						nome_anexo = os.path.basename(str(anexo)) if isinstance(anexo, (str, bytes)) else str(anexo)
					listbox.insert(tk.END, nome_anexo)
			
			# Carregar eventos dos técnicos
			self.carregar_eventos_relatorio(relatorio_id)
			
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar relatório: {e}")
			import traceback
			print(f"Erro completo: {traceback.format_exc()}")
		finally:
			conn.close()
			
	def abrir_relatorio_editor_pdf(self, relatorio_id):
		"""Método descontinuado: editor de templates removido."""
		self.show_warning("O Editor de Templates foi removido do sistema.")
		# Sem ação

	def carregar_eventos_relatorio(self, relatorio_id):
		"""Carregar eventos dos técnicos do relatório"""
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		
		try:
			c.execute("""
				SELECT ec.tecnico_id, u.nome_completo, ec.data_hora, ec.evento, ec.tipo
				FROM eventos_campo ec
				JOIN usuarios u ON ec.tecnico_id = u.id
				WHERE ec.relatorio_id = ?
				ORDER BY ec.tecnico_id, ec.data_hora
			""", (relatorio_id,))
			
			eventos = c.fetchall()
			tecnicos_adicionados = set()
			
			for evento in eventos:
				tecnico_id, tecnico_nome, data_hora, descricao, tipo = evento
				
				# Adicionar técnico se ainda não foi adicionado
				if tecnico_id not in tecnicos_adicionados:
					# Simular seleção do técnico
					for key, value in self.tecnicos_dict.items():
						if value == tecnico_id:
							self.tecnico_var.set(key)
							self.adicionar_tecnico()
							break
					tecnicos_adicionados.add(tecnico_id)
				
				# Adicionar evento
				if tecnico_id in self.tecnicos_eventos:
					tree = self.tecnicos_eventos[tecnico_id]['tree']
					tree.insert("", "end", values=(data_hora, tipo, descricao))
					
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar eventos: {e}")
		finally:
			conn.close()
			
	def duplicar_relatorio(self):
		"""Duplicar relatório selecionado"""
		selected = self.relatorios_tree.selection()
		if not selected:
			self.show_warning("Selecione um relatório para duplicar.")
			return
			
		# Obter ID do relatório
		tags = self.relatorios_tree.item(selected[0])['tags']
		if not tags:
			return
			
		relatorio_id = tags[0]
		self.carregar_relatorio_para_edicao(relatorio_id)
		
		# Limpar ID e gerar novo número sequencial
		self.current_relatorio_id = None
		numero = self.gerar_numero_sequencial_relatorio()
		self.numero_relatorio_var.set(numero)
		self.data_criacao_var.set(datetime.now().strftime('%d/%m/%Y'))
		
		# Layout único: permanecer na mesma tela
		
	def gerar_pdf(self):
		"""Gerar PDF do relatório atual"""
		if not self.current_relatorio_id:
			self.show_warning("Salve o relatório antes de gerar o PDF.")
			return
			
		gerar_pdf_relatorio = _lazy_gerar_pdf_relatorio()
		sucesso, resultado = gerar_pdf_relatorio(self.current_relatorio_id, DB_NAME)
		
		if sucesso:
			self.show_success(f"PDF gerado com sucesso!\nLocal: {resultado}")
		else:
			self.show_error(f"Erro ao gerar PDF: {resultado}")
			
	def gerar_pdf_selecionado(self):
		"""Gerar PDF do relatório selecionado"""
		selected = self.relatorios_tree.selection()
		if not selected:
			self.show_warning("Selecione um relatório para gerar PDF.")
			return
			
		# Obter ID do relatório
		tags = self.relatorios_tree.item(selected[0])['tags']
		if not tags:
			return
			
		relatorio_id = tags[0]
		gerar_pdf_relatorio = _lazy_gerar_pdf_relatorio()
		sucesso, resultado = gerar_pdf_relatorio(relatorio_id, DB_NAME)
		
		if sucesso:
			self.show_success(f"PDF gerado com sucesso!\nLocal: {resultado}")
		else:
			self.show_error(f"Erro ao gerar PDF: {resultado}")
			
	def handle_event(self, event_type, data=None):
		"""Manipular eventos recebidos do sistema"""
		if event_type == 'usuario_created':
			print("DEBUG: Evento usuario_created recebido via handle_event, atualizando lista de técnicos...")
			self.refresh_tecnicos()
		elif event_type == 'cliente_created':
			print("DEBUG: Evento cliente_created recebido via handle_event, atualizando lista de clientes...")
			self.refresh_clientes()

	def excluir_relatorio(self):
		if not self.can_edit('relatorios'):
			self.show_warning("Você não tem permissão para excluir relatórios.")
			return
			
		selected = self.relatorios_tree.selection()
		if not selected:
			self.show_warning("Selecione um relatório para excluir.")
			return
		tags = self.relatorios_tree.item(selected[0])['tags']
		if not tags:
			return
		relatorio_id = tags[0]
		if not messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja excluir o relatório selecionado?"):
			return
		conn = sqlite3.connect(DB_NAME)
		c = conn.cursor()
		try:
			c.execute("DELETE FROM eventos_campo WHERE relatorio_id = ?", (relatorio_id,))
			c.execute("DELETE FROM relatorios_tecnicos WHERE id = ?", (relatorio_id,))
			conn.commit()
			self.show_success("Relatório excluído com sucesso!")
			self.carregar_relatorios()
		except sqlite3.Error as e:
			self.show_error(f"Erro ao excluir relatório: {e}")
		finally:
			conn.close()

	def abrir_anexo(self, aba_numero):
		"""Abrir o anexo selecionado da aba com o aplicativo padrão do sistema."""
		try:
			listbox = getattr(self, f'anexos_listbox_aba{aba_numero}')
		except Exception:
			self.show_warning("Lista de anexos não encontrada.")
			return
		sel = listbox.curselection()
		if not sel:
			self.show_warning("Selecione um anexo para abrir.")
			return
		index = sel[0]
		if index < 0 or index >= len(self.anexos_aba.get(aba_numero, [])):
			self.show_warning("Seleção inválida de anexo.")
			return
		anexo = self.anexos_aba[aba_numero][index]
		caminho = anexo.get('caminho') if isinstance(anexo, dict) else str(anexo)
		# Se não existir, tentar buscar pelo nome dentro da pasta do relatório
		if not (caminho and os.path.exists(caminho)):
			base = anexo.get('nome') if isinstance(anexo, dict) else os.path.basename(str(anexo))
			if self.current_relatorio_id and base:
				local_dir = os.path.join('data', 'relatorios', 'anexos', str(self.current_relatorio_id))
				alt_path = os.path.join(local_dir, base)
				if os.path.exists(alt_path):
					caminho = alt_path
		if not (caminho and os.path.exists(caminho)):
			self.show_warning("Arquivo do anexo não encontrado.")
			return
		try:
			if os.name == 'nt':
				os.startfile(caminho)
			elif sys.platform == 'darwin':
				import subprocess
				subprocess.Popen(['open', caminho])
			else:
				import subprocess
				subprocess.Popen(['xdg-open', caminho])
		except Exception as e:
			self.show_error(f"Não foi possível abrir o anexo: {e}")
			
	def on_cliente_selected(self, event=None):
		"""Evento disparado quando um cliente é selecionado"""
		cliente_str = self.cliente_var.get().strip()
		if not cliente_str:
			return
			
		cliente_id = self.clientes_dict.get(cliente_str)
		if cliente_id:
			# Aqui você pode adicionar lógica adicional quando um cliente é selecionado
			# Por exemplo, carregar dados específicos do cliente
			pass

	def abrir_pdf_selecionado(self):
		"""Abrir PDF do relatório selecionado"""
		selected = self.relatorios_tree.selection()
		if not selected:
			self.show_warning("Selecione um relatório para abrir o PDF.")
			return
			
		# Obter ID do relatório
		tags = self.relatorios_tree.item(selected[0])['tags']
		if not tags:
			return
			
		relatorio_id = tags[0]
		
		# Primeiro gerar o PDF se não existir
		gerar_pdf_relatorio = _lazy_gerar_pdf_relatorio()
		sucesso, resultado = gerar_pdf_relatorio(relatorio_id, DB_NAME)
		
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
			
	def abrir_pdf(self):
		"""Abrir PDF do relatório atual"""
		if not self.current_relatorio_id:
			self.show_warning("Salve o relatório antes de abrir o PDF.")
			return
			
		try:
			gerar_pdf_relatorio = _lazy_gerar_pdf_relatorio()
			sucesso, resultado = gerar_pdf_relatorio(self.current_relatorio_id, DB_NAME)
			
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