import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import sqlite3
from datetime import datetime

from .base_module import BaseModule
from database import DB_NAME
from utils.formatters import format_currency, format_date, clean_number
from pdf_generators.cotacao_nova import gerar_pdf_cotacao_nova


class LocacoesModule(BaseModule):
	def setup_ui(self):
		self.current_cotacao_id = None

		container = tk.Frame(self.frame, bg='#f8fafc')
		container.pack(fill="both", expand=True, padx=10, pady=10)

		# Header
		header = tk.Frame(container, bg='#f8fafc')
		header.pack(fill="x")
		tk.Label(header, text="Gestão de Locações", font=('Arial', 16, 'bold'), background='#f8fafc', foreground='#1e293b').pack(side="left")

		# Main split
		main_frame = tk.Frame(container, bg='#f8fafc')
		main_frame.pack(fill="both", expand=True)
		main_frame.grid_columnconfigure(0, weight=1, uniform="cols")
		main_frame.grid_columnconfigure(1, weight=1, uniform="cols")
		main_frame.grid_rowconfigure(0, weight=1)

		# Form panel
		form_panel = tk.Frame(main_frame, bg='#f8fafc')
		form_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=(10, 10))
		form_panel.grid_columnconfigure(0, weight=1)

		# Buttons footer (top)
		self._create_buttons(form_panel)

		# Scrollable form
		scroll_container = tk.Frame(form_panel, bg='#f8fafc')
		scroll_container.pack(side="top", fill="both", expand=True)
		form_canvas = tk.Canvas(scroll_container, bg='#f8fafc', highlightthickness=0)
		form_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=form_canvas.yview)
		form_canvas.configure(yscrollcommand=form_scrollbar.set)
		form_scrollbar.pack(side="right", fill="y")
		form_canvas.pack(side="left", fill="both", expand=True)
		form_inner = tk.Frame(form_canvas, bg='#f8fafc')
		form_window = form_canvas.create_window((0, 0), window=form_inner, anchor="nw")
		form_inner.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
		form_canvas.bind("<Configure>", lambda e: form_canvas.itemconfigure(form_window, width=e.width))

		# Content
		self._create_form_content(form_inner)

		# List panel (right)
		list_panel = tk.Frame(main_frame, bg='#f8fafc')
		list_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 10), pady=(10, 10))
		list_panel.grid_columnconfigure(0, weight=1)
		list_panel.grid_rowconfigure(2, weight=1)

		lista_card = tk.Frame(list_panel, bg='white', bd=0, relief='ridge', highlightthickness=0)
		lista_card.pack(fill="both", expand=True)
		ttk.Label(lista_card, text="📄 Locações", font=("Arial", 12, "bold"), background='white', anchor="w").pack(fill="x", padx=12, pady=(12, 8))
		lista_inner = tk.Frame(lista_card, bg='white')
		lista_inner.pack(fill="both", expand=True, padx=12, pady=(0, 12))

		search_frame, self.search_var = self.create_search_frame(lista_inner, command=self.buscar)
		search_frame.pack(fill="x", pady=(0, 10))

		lista_buttons = tk.Frame(lista_inner, bg='white')
		lista_buttons.pack(side="bottom", fill="x", pady=(10, 0))
		editar_btn = self.create_button(lista_buttons, "Editar", self.editar)
		editar_btn.pack(side="left", padx=(0, 10))
		# Manter apenas o botão inferior direito de PDF
		gerar_pdf_lista_btn = self.create_button(lista_buttons, "Gerar PDF", self.gerar_pdf, bg='#10b981')
		gerar_pdf_lista_btn.pack(side="right", padx=(0, 10))
		
		abrir_pdf_lista_btn = self.create_button(lista_buttons, "Abrir PDF", self.abrir_pdf, bg='#3b82f6')
		abrir_pdf_lista_btn.pack(side="right")

		columns = ("numero", "cliente", "data", "valor", "status")
		self.tree = ttk.Treeview(lista_inner, columns=columns, show="headings")
		self.tree.heading("numero", text="Número")
		self.tree.heading("cliente", text="Cliente")
		self.tree.heading("data", text="Data")
		self.tree.heading("valor", text="Valor")
		self.tree.heading("status", text="Status")
		self.tree.column("numero", width=150)
		self.tree.column("cliente", width=250)
		self.tree.column("data", width=100)
		self.tree.column("valor", width=120)
		self.tree.column("status", width=100)
		lista_scrollbar = ttk.Scrollbar(lista_inner, orient="vertical", command=self.tree.yview)
		self.tree.configure(yscrollcommand=lista_scrollbar.set)
		self.tree.pack(side="left", fill="both", expand=True)
		lista_scrollbar.pack(side="right", fill="y")

		self._refresh_clientes()
		self._carregar_lista()

	def _create_buttons(self, parent):
		buttons_frame = tk.Frame(parent, bg='white')
		buttons_frame.pack(fill="x", pady=(20, 0))
		nova_btn = self.create_button(buttons_frame, "Nova Locação", self.nova, bg='#e2e8f0', fg='#475569')
		nova_btn.pack(side="left", padx=(0, 10))
		salvar_btn = self.create_button(buttons_frame, "Salvar Locação", self.salvar)
		salvar_btn.pack(side="left", padx=(0, 10))
		# Removido botão superior de Gerar PDF (manter apenas o inferior direito)

	def _create_form_content(self, parent):
		main_grid = tk.Frame(parent, bg='white')
		main_grid.pack(fill="both", expand=True)
		main_grid.grid_columnconfigure(0, weight=1)
		main_grid.grid_rowconfigure(0, weight=0)
		main_grid.grid_rowconfigure(1, weight=1)

		# Dados (sem bloco de "Dados da Locação")
		dados = tk.LabelFrame(main_grid, text="Dados da Locação", font=('Arial', 11, 'bold'), bg='white')
		dados.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

		row = 0
		self.numero_var = tk.StringVar()
		self.cliente_var = tk.StringVar()
		self.contato_cliente_var = tk.StringVar()
		self.filial_var = tk.StringVar(value="2")
		self.modelo_var = tk.StringVar()
		self.observacoes_var = tk.StringVar()
		self.condicao_pagamento_var = tk.StringVar()
		self.tipo_frete_var = tk.StringVar(value="FOB")
		self.prazo_entrega_var = tk.StringVar()

		tk.Label(dados, text="Número da Proposta *:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		tk.Entry(dados, textvariable=self.numero_var, font=('Arial', 10), width=30).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1

		tk.Label(dados, text="Filial *:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		filial_combo = ttk.Combobox(dados, textvariable=self.filial_var, values=["1 - WORLD COMP COMPRESSORES LTDA", "2 - WORLD COMP DO BRASIL COMPRESSORES LTDA"], width=45, state="readonly")
		filial_combo.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		# ICMS não é mais utilizado em Locação
		def on_filial_changed(_e=None):
			return
		filial_combo.bind('<<ComboboxSelected>>', on_filial_changed)
		row += 1

		tk.Label(dados, text="Cliente *:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		cliente_frame = tk.Frame(dados, bg='white')
		cliente_frame.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		self.cliente_combo = ttk.Combobox(cliente_frame, textvariable=self.cliente_var, width=25)
		self.cliente_combo.pack(side="left", fill="x", expand=True)
		self.cliente_combo.bind("<<ComboboxSelected>>", self._on_cliente_selected)
		# Refresh button removed
		row += 1

		tk.Label(dados, text="Contato:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		self.contato_cliente_combo = ttk.Combobox(dados, textvariable=self.contato_cliente_var, width=27, state="readonly")
		self.contato_cliente_combo.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1

		tk.Label(dados, text="Modelo do Compressor:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		tk.Entry(dados, textvariable=self.modelo_var, font=('Arial', 10), width=50).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1

		tk.Label(dados, text="Condição de Pagamento *:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		tk.Entry(dados, textvariable=self.condicao_pagamento_var, font=('Arial', 10), width=50).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1

		# Tipo de Frete e Prazo de Entrega
		tk.Label(dados, text="Tipo de Frete:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		tipo_frete_combo = ttk.Combobox(dados, textvariable=self.tipo_frete_var, values=["FOB", "CIF", "A combinar"], width=27, state="readonly")
		tipo_frete_combo.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=5)
		row += 1

		tk.Label(dados, text="Prazo de Entrega:", font=('Arial', 10, 'bold'), bg='white').grid(row=row, column=0, sticky="w", pady=5)
		tk.Entry(dados, textvariable=self.prazo_entrega_var, font=('Arial', 10), width=50).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
		row += 1

		# Observações
		obs = tk.LabelFrame(main_grid, text="Observações", font=('Arial', 11, 'bold'), bg='white')
		obs.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0, 2))
		self.observacoes_text = scrolledtext.ScrolledText(obs, height=3, width=80, wrap=tk.WORD)
		self.observacoes_text.pack(fill="both", expand=True, padx=10, pady=5)

		# Itens
		itens_section = tk.LabelFrame(main_grid, text="Itens da Locação", font=('Arial', 11, 'bold'), bg='white')
		itens_section.grid(row=2, column=0, sticky="nsew", padx=2, pady=(0, 2))
		self._create_items_ui(itens_section)

		# Set initial number
		if not self.current_cotacao_id:
			try:
				self.numero_var.set(self._gerar_numero_sequencial())
			except Exception:
				pass

	def _create_items_ui(self, parent):
		add_frame = tk.Frame(parent, bg='white')
		add_frame.pack(fill="x", pady=(0, 10))

		self.item_nome_var = tk.StringVar()
		self.item_desc_var = tk.StringVar()
		self.item_qtd_var = tk.StringVar(value="1")
		self.item_valor_var = tk.StringVar(value="0.00")
		self.item_inicio_var = tk.StringVar()
		self.item_fim_var = tk.StringVar()
		self.item_imagem_var = tk.StringVar()
		# ICMS removido do fluxo de Locação

		row = 0
		tk.Label(add_frame, text="Nome do Equipamento:", font=("Arial", 10, "bold"), background="white").grid(row=row, column=0, padx=5, sticky="w")
		self.item_nome_combo = ttk.Combobox(add_frame, textvariable=self.item_nome_var, width=40, state="readonly")
		self.item_nome_combo.grid(row=row, column=1, padx=5, sticky="ew")
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute("SELECT nome FROM produtos WHERE tipo = 'Produto' AND COALESCE(categoria,'Geral')='Compressores' AND ativo = 1 ORDER BY nome")
			comp_list = [row[0] for row in c.fetchall()]
			self.item_nome_combo['values'] = comp_list
		finally:
			try:
				conn.close()
			except Exception:
				pass
		row += 1

		tk.Label(add_frame, text="Descrição:", font=("Arial", 10, "bold"), background="white").grid(row=row, column=0, padx=5, sticky="w")
		tk.Entry(add_frame, textvariable=self.item_desc_var, width=60).grid(row=row, column=1, padx=5, sticky="ew")
		row += 1

		tk.Label(add_frame, text="Qtd.", font=("Arial", 10, "bold"), background="white").grid(row=row, column=0, padx=5, sticky="w")
		tk.Entry(add_frame, textvariable=self.item_qtd_var, width=8).grid(row=row, column=1, padx=5, sticky="w")
		row += 1

		tk.Label(add_frame, text="Valor Unit./Mensal:", font=("Arial", 10, "bold"), background="white").grid(row=row, column=0, padx=5, sticky="w")
		tk.Entry(add_frame, textvariable=self.item_valor_var, width=15).grid(row=row, column=1, padx=5, sticky="w")
		row += 1

		tk.Label(add_frame, text="Início (DD/MM/AAAA):", font=("Arial", 10, "bold"), background="white").grid(row=row, column=0, padx=5, sticky="w")
		tk.Entry(add_frame, textvariable=self.item_inicio_var, width=15).grid(row=row, column=1, padx=5, sticky="w")
		row += 1

		tk.Label(add_frame, text="Fim (DD/MM/AAAA):", font=("Arial", 10, "bold"), background="white").grid(row=row, column=0, padx=5, sticky="w")
		tk.Entry(add_frame, textvariable=self.item_fim_var, width=15).grid(row=row, column=1, padx=5, sticky="w")
		row += 1

		tk.Label(add_frame, text="Imagem do Equipamento:", font=("Arial", 10, "bold"), background="white").grid(row=row, column=0, padx=5, sticky="w")
		img_item_frame = tk.Frame(add_frame, bg='white')
		img_item_frame.grid(row=row, column=1, sticky="ew", padx=5)
		tk.Entry(img_item_frame, textvariable=self.item_imagem_var, width=35).pack(side="left", fill="x", expand=True)
		self.create_button(img_item_frame, "Selecionar...", lambda: self._pick_image_into(self.item_imagem_var), bg='#10b981').pack(side="right", padx=(5, 0))
		row += 1

		# Campo ICMS removido

		# Ações de imagem do item selecionado
		actions_frame = tk.Frame(parent, bg='white')
		actions_frame.pack(fill="x", pady=(0, 8))
		self.create_button(actions_frame, "Usar imagem no item selecionado", self._aplicar_imagem_item_selecionado, bg='#64748b').pack(side="left", padx=(5, 5))
		self.create_button(actions_frame, "Remover imagem do item selecionado", self._remover_imagem_item_selecionado, bg='#dc2626').pack(side="left", padx=(0, 5))

		add_btn = self.create_button(add_frame, "Adicionar Item", self._adicionar_item)
		add_btn.grid(row=row, column=0, columnspan=2, pady=10)

		# Tree
		list_container = tk.Frame(parent, bg='white')
		list_container.pack(fill="both", expand=True)
		columns = ("nome", "qtd", "valor_unit", "meses", "inicio", "fim", "valor_total", "descricao", "imagem")
		self.itens_tree = ttk.Treeview(list_container, columns=columns, show="headings", height=8)
		for col, text, width in [
			("nome", "Nome/Equipamento", 250),
			("qtd", "Qtd", 60),
			("valor_unit", "Valor Unit./Mensal", 120),
			("meses", "Meses", 60),
			("inicio", "Início", 90),
			("fim", "Fim", 90),
			("valor_total", "Total", 100),
			("descricao", "Descrição", 200),
			("imagem", "Imagem", 200)
		]:
			self.itens_tree.heading(col, text=text)
			self.itens_tree.column(col, width=width, minwidth=width)
		v_scroll = ttk.Scrollbar(list_container, orient="vertical", command=self.itens_tree.yview)
		h_scroll = ttk.Scrollbar(list_container, orient="horizontal", command=self.itens_tree.xview)
		self.itens_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
		self.itens_tree.grid(row=0, column=0, sticky="nsew")
		v_scroll.grid(row=0, column=1, sticky="ns")
		h_scroll.grid(row=1, column=0, sticky="ew")
		list_container.grid_rowconfigure(0, weight=1)
		list_container.grid_columnconfigure(0, weight=1)

		# Permitir edição por duplo clique
		self.itens_tree.bind("<Double-1>", self._on_item_double_click)

		# Footer total
		item_buttons = tk.Frame(parent, bg='white')
		item_buttons.pack(fill="x", pady=(10, 0))
		remove_btn = self.create_button(item_buttons, "Remover Item", self._remover_item, bg='#dc2626')
		remove_btn.pack(side="left", padx=5)
		self.total_label = ttk.Label(item_buttons, text="Total: R$ 0,00", font=('Arial', 12, 'bold'), background='white', foreground='#1e293b')
		self.total_label.pack(side="right")

	# --- Actions ---
	def _pick_image_into(self, var):
		path = filedialog.askopenfilename(title="Selecionar Imagem do Equipamento",
										  filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.gif"), ("Todos", "*.*")])
		if path:
			var.set(path)

	def _aplicar_imagem_item_selecionado(self):
		selected = self.itens_tree.selection()
		if not selected:
			self.show_warning("Selecione um item para aplicar a imagem.")
			return
		img = self.item_imagem_var.get().strip()
		item_id = selected[0]
		vals = list(self.itens_tree.item(item_id)['values'])
		if len(vals) == 9:
			vals[8] = img
			self.itens_tree.item(item_id, values=tuple(vals))

	def _remover_imagem_item_selecionado(self):
		selected = self.itens_tree.selection()
		if not selected:
			self.show_warning("Selecione um item para remover a imagem.")
			return
		item_id = selected[0]
		vals = list(self.itens_tree.item(item_id)['values'])
		if len(vals) == 9:
			vals[8] = ""
			self.itens_tree.item(item_id, values=tuple(vals))

	def _adicionar_item(self):
		if not self.can_edit('locacoes'):
			self.show_warning("Você não tem permissão para adicionar itens.")
			return
			
		nome = self.item_nome_var.get().strip()
		qtd = self.item_qtd_var.get().strip() or "1"
		valor = self.item_valor_var.get().strip() or "0.00"
		desc = self.item_desc_var.get().strip()
		# ICMS removido
		inicio_iso = self._parse_date(self.item_inicio_var.get())
		fim_iso = self._parse_date(self.item_fim_var.get())
		if not nome:
			self.show_warning("Informe o nome do equipamento do item.")
			return
		if not (inicio_iso and fim_iso):
			self.show_warning("Informe datas início e fim válidas para o item.")
			return
		try:
			quantidade = float(qtd)
			valor_unit = clean_number(valor)
		except ValueError:
			self.show_error("Valores numéricos inválidos para item.")
			return
		meses = self._calculate_months_between(inicio_iso, fim_iso)
		# Calcular total sem ICMS
		total = ((valor_unit or 0) * (meses or 0) * quantidade)
			
		self.itens_tree.insert("", "end", values=(
			nome,
			f"{quantidade:.2f}",
			format_currency(valor_unit),
			str(meses),
			format_date(inicio_iso),
			format_date(fim_iso),
			format_currency(total),
			desc,
			self.item_imagem_var.get().strip()
		))
		self._update_total()
		# clear item inputs
		self.item_nome_var.set("")
		self.item_desc_var.set("")
		self.item_qtd_var.set("1")
		self.item_valor_var.set("0.00")
		self.item_inicio_var.set("")
		self.item_fim_var.set("")
		self.item_imagem_var.set("")
		# ICMS removido

	def _remover_item(self):
		sel = self.itens_tree.selection()
		for s in sel:
			self.itens_tree.delete(s)
		self._update_total()

	def _update_total(self):
		total = 0
		for iid in self.itens_tree.get_children():
			values = self.itens_tree.item(iid)['values']
			if len(values) >= 7:
				valor_total_str = str(values[6]).replace('R$ ', '').replace('.', '').replace(',', '.')
				try:
					total += float(valor_total_str)
				except ValueError:
					pass
		self.total_label.config(text=f"Total: {format_currency(total)}")

	# --- DB helpers ---
	def _refresh_clientes(self):
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute("SELECT id, nome FROM clientes ORDER BY nome")
			clientes = c.fetchall()
			self.clientes_dict = {f"{nome} (ID: {id})": id for id, nome in clientes}
			self.cliente_combo['values'] = list(self.clientes_dict.keys())
		except Exception as e:
			print(f"Erro ao carregar clientes: {e}")
		finally:
			try:
				conn.close()
			except Exception:
				pass

	def _on_cliente_selected(self, event=None):
		cliente_str = self.cliente_var.get().strip()
		if not cliente_str:
			return
		cliente_id = self.clientes_dict.get(cliente_str)
		if not cliente_id:
			return
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			# Carregar contatos do cliente
			c.execute("SELECT nome FROM contatos WHERE cliente_id = ? ORDER BY nome", (cliente_id,))
			contatos = [row[0] for row in c.fetchall()]
			self.contato_cliente_combo['values'] = contatos
			if contatos:
				self.contato_cliente_var.set(contatos[0])
			else:
				self.contato_cliente_var.set("")
			# Preencher condição de pagamento a partir do cadastro do cliente
			try:
				c.execute("SELECT prazo_pagamento FROM clientes WHERE id = ?", (cliente_id,))
				res = c.fetchone()
				if res and res[0]:
					self.condicao_pagamento_var.set(res[0])
			except Exception:
				pass
		except Exception as e:
			print(f"Erro ao carregar contatos: {e}")
		finally:
			try:
				conn.close()
			except Exception:
				pass

	def _gerar_numero_sequencial(self) -> str:
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute("SELECT MAX(CAST(SUBSTR(numero_proposta, 5) AS INTEGER)) FROM cotacoes WHERE tipo_cotacao='Locação' AND numero_proposta LIKE 'LOC-%'")
			result = c.fetchone()
			proximo = (result[0] + 1) if (result and result[0]) else 1
			return f"LOC-{proximo:06d}"
		except Exception:
			return f"LOC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
		finally:
			try:
				conn.close()
			except Exception:
				pass

	# --- Persistência ---
	def salvar(self):
		if not self.can_edit('locacoes'):
			self.show_warning("Você não tem permissão para salvar locações.")
			return
			
		numero = self.numero_var.get().strip()
		cliente_str = self.cliente_var.get().strip()
		cond_pgto = self.condicao_pagamento_var.get().strip()
		if not numero:
			self.show_warning("Informe o número da proposta.")
			return
		if not cliente_str:
			self.show_warning("Selecione um cliente.")
			return
		if not cond_pgto:
			self.show_warning("Informe a Condição de Pagamento.")
			return
		cliente_id = self.clientes_dict.get(cliente_str)
		if not cliente_id:
			self.show_warning("Cliente inválido.")
			return

		# Somar total
		total = 0
		for iid in self.itens_tree.get_children():
			values = self.itens_tree.item(iid)['values']
			if len(values) >= 7:
				try:
					total += float(str(values[6]).replace('R$ ', '').replace('.', '').replace(',', '.'))
				except ValueError:
					pass

		data_validade = None
		filial_str = self.filial_var.get()
		filial_id = int(filial_str.split(' - ')[0]) if ' - ' in filial_str else int(filial_str)

		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()

			if self.current_cotacao_id:
				c.execute(
					"""
					UPDATE cotacoes
					SET numero_proposta=?, cliente_id=?, responsavel_id=?, filial_id=?, data_criacao=?,
						data_validade=?, modelo_compressor=?, observacoes=?, valor_total=?, status=?,
						tipo_frete=?, condicao_pagamento=?, prazo_entrega=?, esboco_servico=?, relacao_pecas_substituir=?,
						tipo_cotacao=?, contato_nome=?
					WHERE id=?
					""",
					(
						numero, cliente_id, self.user_id, filial_id, datetime.now().strftime('%Y-%m-%d'),
						data_validade, self.modelo_var.get().strip(), self.observacoes_text.get("1.0", tk.END).strip(), total, "Em Aberto",
						self.tipo_frete_var.get().strip(), cond_pgto, self.prazo_entrega_var.get().strip(), "", "",
						"Locação", self.contato_cliente_var.get().strip(),
						self.current_cotacao_id,
					),
				)
				c.execute("DELETE FROM itens_cotacao WHERE cotacao_id = ?", (self.current_cotacao_id,))
				cotacao_id = self.current_cotacao_id
			else:
				c.execute(
					"""
					INSERT INTO cotacoes (
						numero_proposta, cliente_id, responsavel_id, data_criacao, data_validade,
						modelo_compressor, observacoes, valor_total, status, tipo_frete, condicao_pagamento, prazo_entrega,
						filial_id, esboco_servico, relacao_pecas_substituir, tipo_cotacao,
						contato_nome
					) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
					""",
					(
						numero, cliente_id, self.user_id, datetime.now().strftime('%Y-%m-%d'), None,
						self.modelo_var.get().strip(), self.observacoes_text.get("1.0", tk.END).strip(), total, "Em Aberto", self.tipo_frete_var.get().strip(), cond_pgto, self.prazo_entrega_var.get().strip(),
						filial_id, "", "", "Locação",
						self.contato_cliente_var.get().strip(),
					),
				)
				cotacao_id = c.lastrowid
				self.current_cotacao_id = cotacao_id

			# Inserir itens com imagem por item
			for iid in self.itens_tree.get_children():
				values = self.itens_tree.item(iid)['values']
				(nome, qtd, valor_unit_fmt, meses, inicio_fmt, fim_fmt, total_fmt, desc, imagem) = values
				quantidade = float(qtd)
				valor_unit = clean_number(valor_unit_fmt)
				valor_total_item = clean_number(total_fmt)
				icms_val = 0
				inicio_iso = self._parse_date(inicio_fmt)
				fim_iso = self._parse_date(fim_fmt)
				meses_int = int(meses) if str(meses).isdigit() else None
				c.execute(
					"""
					INSERT INTO itens_cotacao (
						cotacao_id, tipo, item_nome, quantidade, valor_unitario, valor_total_item, descricao,
						mao_obra, deslocamento, estadia, icms, tipo_operacao, locacao_data_inicio, locacao_data_fim, locacao_qtd_meses,
						locacao_imagem_path
					) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
					""",
					(
						cotacao_id, "Produto", nome, quantidade, valor_unit, valor_total_item, desc,
						0, 0, 0, icms_val, "Locação", inicio_iso, fim_iso, meses_int,
						imagem,
					),
				)

			conn.commit()
			self.show_success("Locação salva com sucesso!")
			self._carregar_lista()
		except sqlite3.Error as e:
			self.show_error(f"Erro ao salvar locação: {e}")
		finally:
			try:
				conn.close()
			except Exception:
				pass

	def nova(self):
		self.current_cotacao_id = None
		self.numero_var.set("")
		self.cliente_var.set("")
		self.contato_cliente_var.set("")
		self.filial_var.set("2")
		self.modelo_var.set("")
		self.condicao_pagamento_var.set("")
		self.tipo_frete_var.set("FOB")
		self.prazo_entrega_var.set("")
		self.observacoes_text.delete("1.0", tk.END)
		# Limpar contatos disponíveis
		try:
			self.contato_cliente_combo['values'] = []
		except Exception:
			pass
		for iid in self.itens_tree.get_children():
			self.itens_tree.delete(iid)
		# limpar qualquer imagem temporária
		self.item_imagem_var.set("")
		# Limpar campos de item
		self.item_nome_var.set("")
		self.item_desc_var.set("")
		self.item_qtd_var.set("1")
		self.item_valor_var.set("0.00")
		self.item_inicio_var.set("")
		self.item_fim_var.set("")
		try:
			self.numero_var.set(self._gerar_numero_sequencial())
		except Exception:
			pass

	def gerar_pdf(self):
		# Permitir gerar PDF a partir da seleção na lista, mesmo sem estado do formulário
		cotacao_id = self.current_cotacao_id
		if not cotacao_id:
			try:
				selected = self.tree.selection()
				if selected:
					cotacao_id = self.tree.item(selected[0])['tags'][0]
			except Exception:
				cotacao_id = None
		if not cotacao_id:
			self.show_warning("Selecione uma locação na lista para gerar o PDF.")
			return
		try:
			current_username = self._get_current_username()
			sucesso, resultado = gerar_pdf_cotacao_nova(
				cotacao_id,
				DB_NAME,
				current_username,
				contato_nome=self.contato_cliente_var.get(),
				locacao_pagina4_text=None,
				locacao_pagina4_image=None,
			)
			if sucesso:
				self.show_success(f"PDF gerado com sucesso!\nLocal: {resultado}")
			else:
				self.show_error(f"Erro ao gerar PDF: {resultado}")
		except Exception as e:
			self.show_error(f"Erro ao gerar PDF: {e}")
			
	def abrir_pdf(self):
		"""Abrir PDF da locação selecionada"""
		selected = self.tree.selection()
		if not selected:
			self.show_warning("Selecione uma locação para abrir o PDF.")
			return
			
		tags = self.tree.item(selected[0])['tags']
		if not tags:
			return
			
		cotacao_id = tags[0]
		
		# Primeiro gerar o PDF se não existir
		try:
			current_username = self._get_current_username()
			sucesso, resultado = gerar_pdf_cotacao_nova(
				cotacao_id, 
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
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute("SELECT username FROM usuarios WHERE id = ?", (self.user_id,))
			r = c.fetchone()
			return r[0] if r else None
		except Exception:
			return None
		finally:
			try:
				conn.close()
			except Exception:
				pass

	# --- List/Load ---
	def _carregar_lista(self):
		for iid in self.tree.get_children():
			self.tree.delete(iid)
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute(
				"""
				SELECT id, numero_proposta, (SELECT nome FROM clientes WHERE id=cliente_id) AS cliente,
				       data_criacao, valor_total, status
				FROM cotacoes
				WHERE tipo_cotacao = 'Locação'
				ORDER BY created_at DESC
				"""
			)
			for (cid, numero, cliente, data, valor, status) in c.fetchall():
				self.tree.insert("", "end", values=(
					numero,
					cliente,
					format_date(data),
					format_currency(valor) if valor else "R$ 0,00",
					status or "Em Aberto",
				), tags=(cid,))
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar locações: {e}")
		finally:
			try:
				conn.close()
			except Exception:
				pass

	def buscar(self):
		termo = self.search_var.get().strip()
		for iid in self.tree.get_children():
			self.tree.delete(iid)
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			if termo:
				c.execute(
					"""
					SELECT id, numero_proposta, (SELECT nome FROM clientes WHERE id=cliente_id) AS cliente,
					       data_criacao, valor_total, status
					FROM cotacoes
					WHERE tipo_cotacao = 'Locação' AND (numero_proposta LIKE ? OR cliente IN (
						SELECT nome FROM clientes WHERE nome LIKE ?
					))
					ORDER BY created_at DESC
					""",
					(f"%{termo}%", f"%{termo}%"),
				)
			else:
				c.execute(
					"""
					SELECT id, numero_proposta, (SELECT nome FROM clientes WHERE id=cliente_id) AS cliente,
					       data_criacao, valor_total, status
					FROM cotacoes
					WHERE tipo_cotacao = 'Locação'
					ORDER BY created_at DESC
					"""
				)
			for (cid, numero, cliente, data, valor, status) in c.fetchall():
				self.tree.insert("", "end", values=(
					numero,
					cliente,
					format_date(data),
					format_currency(valor) if valor else "R$ 0,00",
					status or "Em Aberto",
				), tags=(cid,))
		except sqlite3.Error as e:
			self.show_error(f"Erro ao buscar: {e}")
		finally:
			try:
				conn.close()
			except Exception:
				pass

	def editar(self):
		"""Editar/Visualizar locação selecionada baseado nas permissões"""
		sel = self.tree.selection()
		if not sel:
			self.show_warning("Selecione uma locação para editar/visualizar.")
			return
			
		cotacao_id = self.tree.item(sel[0])['tags'][0]
		
		if self.can_edit('locacoes'):
			# Usuário pode editar - carregar normalmente
			self._carregar_cotacao(cotacao_id)
		else:
			# Usuário só pode visualizar - carregar dados e aplicar readonly
			self._carregar_cotacao(cotacao_id)
			# Aplicar modo readonly após carregamento
			self.frame.after(100, lambda: self._aplicar_readonly_visualizacao())
			self.show_info("Visualizando locação em modo consulta. Os dados não podem ser editados.")
			
	def _aplicar_readonly_visualizacao(self):
		"""Aplica readonly após os dados serem carregados"""
		if not self.can_edit('locacoes'):
			self.apply_readonly_for_visualization()

	def _carregar_cotacao(self, cotacao_id):
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute(
				"""
				SELECT id, numero_proposta, cliente_id, responsavel_id, filial_id, data_validade, modelo_compressor,
				       observacoes, valor_total, status, contato_nome, condicao_pagamento, tipo_frete, prazo_entrega
				FROM cotacoes
				WHERE id = ? AND tipo_cotacao = 'Locação'
				""",
				(cotacao_id,),
			)
			row = c.fetchone()
			if not row:
				self.show_error("Locação não encontrada.")
				return
			(
				cid, numero, cliente_id, responsavel_id, filial_id, data_validade, modelo_compressor,
				observacoes, valor_total, status, contato_nome, cond_pgto, tipo_frete, prazo_entrega
			) = row
			self.current_cotacao_id = cid
			self.numero_var.set(numero)
			# set cliente in combo
			for display, _id in self.clientes_dict.items():
				if _id == cliente_id:
					self.cliente_var.set(display)
					break
			# contato
			self._on_cliente_selected()
			if contato_nome:
				try:
					self.contato_cliente_var.set(contato_nome)
				except Exception:
					pass
			# filial e campos
			self.filial_var.set(str(filial_id))
			self.modelo_var.set(modelo_compressor or "")
			self.condicao_pagamento_var.set(cond_pgto or "")
			self.tipo_frete_var.set(tipo_frete or "FOB")
			self.prazo_entrega_var.set(prazo_entrega or "")
			self.observacoes_text.delete("1.0", tk.END)
			if observacoes:
				self.observacoes_text.insert("1.0", observacoes)

			# itens
			for iid in self.itens_tree.get_children():
				self.itens_tree.delete(iid)
			c.execute(
				"""
				SELECT item_nome, quantidade, valor_unitario, locacao_qtd_meses, locacao_data_inicio,
				       locacao_data_fim, valor_total_item, descricao, locacao_imagem_path
				FROM itens_cotacao
				WHERE cotacao_id = ?
				ORDER BY id
				""",
				(cid,),
			)
			first_img = ""
			for (nome, qtd, valor_unit, meses, inicio, fim, total_item, desc, img) in c.fetchall():
				self.itens_tree.insert(
					"", "end",
					values=(
						nome,
						f"{qtd:.2f}",
						format_currency(valor_unit),
						str(meses or ""),
						format_date(inicio) if inicio else "",
						format_date(fim) if fim else "",
						format_currency(total_item),
						desc or "",
						img or "",
					),
				)
				if not first_img and img:
					first_img = img
			self._update_total()
			# Prefill image field with first item's image to allow keeping/changing
			if first_img:
				self.item_imagem_var.set(first_img)
		except sqlite3.Error as e:
			self.show_error(f"Erro ao carregar locação: {e}")
		finally:
			try:
				conn.close()
			except Exception:
				pass

	# --- Utils ---
	def _parse_date(self, s):
		s = (s or "").strip()
		if not s:
			return None
		try:
			return datetime.strptime(s, '%d/%m/%Y').strftime('%Y-%m-%d')
		except ValueError:
			try:
				datetime.strptime(s, '%Y-%m-%d')
				return s
			except ValueError:
				return None

	def _calculate_months_between(self, start_iso, end_iso):
		if not start_iso or not end_iso:
			return 0
		start = datetime.strptime(start_iso, '%Y-%m-%d').date()
		end = datetime.strptime(end_iso, '%Y-%m-%d').date()
		if end < start:
			return 0
		months = (end.year - start.year) * 12 + (end.month - start.month)
		if end.day >= start.day:
			months += 1
		return months if months > 0 else 1

	def handle_event(self, event_type, data=None):
		if event_type in ('cliente_created', 'cliente_updated'):
			self._refresh_clientes()
		elif event_type in ('produto_created', 'produto_updated'):
			# Atualizar imediatamente a lista de compressores do combobox de itens
			try:
				# Se a UI ainda não criou o combobox, ignore silenciosamente
				self._refresh_compressores_combo()
			except Exception:
				pass

	def _refresh_compressores_combo(self):
		"""Recarrega os nomes de compressores no combobox de itens de locação."""
		# Só procede se o combobox existir
		if not hasattr(self, 'item_nome_combo'):
			return
		try:
			conn = sqlite3.connect(DB_NAME)
			c = conn.cursor()
			c.execute("SELECT nome FROM produtos WHERE tipo = 'Produto' AND COALESCE(categoria,'Geral')='Compressores' AND ativo = 1 ORDER BY nome")
			comp_list = [row[0] for row in c.fetchall()]
			# Forçar atualização visual do combobox
			try:
				self.item_nome_combo.configure(state='normal')
				self.item_nome_combo['values'] = comp_list
				# Limpar seleção corrente para refletir novos valores
				self.item_nome_var.set("")
				self.item_nome_combo.configure(state='readonly')
				self.item_nome_combo.update_idletasks()
			except Exception:
				pass
		finally:
			try:
				conn.close()
			except Exception:
				pass

	def _on_item_double_click(self, event=None):
		selected = self.itens_tree.selection()
		if not selected:
			return
		iid = selected[0]
		vals = list(self.itens_tree.item(iid)['values'])
		# Esperamos 9 colunas (ICMS removido)
		if len(vals) != 9:
			return
		# Criar diálogo simples de edição
		dialog = tk.Toplevel(self.frame)
		dialog.title("Editar Item da Locação")
		dialog.grab_set()
		labels = [
			("Nome/Equipamento", 0),
			("Quantidade", 1),
			("Valor Unit./Mensal", 2),
			("Meses", 3),
			("Início (DD/MM/AAAA)", 4),
			("Fim (DD/MM/AAAA)", 5),
			("Descrição", 7),
			("Imagem", 8),
		]
		entries = {}
		row = 0
		for label, idx in labels:
			tk.Label(dialog, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
			var = tk.StringVar(value=str(vals[idx]))
			ent = tk.Entry(dialog, textvariable=var, width=50)
			ent.grid(row=row, column=1, padx=8, pady=4)
			entries[idx] = var
			row += 1

		def on_save():
			try:
				# ler campos
				nome = entries[0].get().strip()
				quantidade = float(entries[1].get().strip().replace(',', '.'))
				valor_unit = clean_number(entries[2].get().strip())
				meses = int(entries[3].get().strip() or 0)
				inicio = entries[4].get().strip()
				fim = entries[5].get().strip()
				descricao = entries[7].get().strip()
				imagem = entries[8].get().strip()
				# recalcular total sem ICMS
				total = ((valor_unit or 0) * (meses or 0) * (quantidade or 0))
				# formatar
				vals[0] = nome
				vals[1] = f"{quantidade:.2f}"
				vals[2] = format_currency(valor_unit)
				vals[3] = str(meses)
				vals[4] = entries[4].get().strip()
				vals[5] = entries[5].get().strip()
				vals[6] = format_currency(total)
				vals[7] = descricao
				vals[8] = imagem
				# ICMS removido
				self.itens_tree.item(iid, values=tuple(vals))
				self._update_total()
				dialog.destroy()
			except Exception as e:
				messagebox.showerror("Erro", f"Não foi possível salvar alterações: {e}")

		btns = tk.Frame(dialog)
		btns.grid(row=row, column=0, columnspan=2, pady=(8, 4))
		self.create_button(btns, "Salvar", on_save, bg='#10b981').pack(side="left", padx=6)
		self.create_button(btns, "Cancelar", dialog.destroy, bg='#64748b').pack(side="left", padx=6)