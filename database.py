import sqlite3
import os
import hashlib

DB_NAME = "crm_compressores.db"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def criar_banco():
	conn = sqlite3.connect(DB_NAME)
	c = conn.cursor()

	# Tabela Usuários
	c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT NOT NULL UNIQUE,
		password TEXT NOT NULL,
		role TEXT NOT NULL DEFAULT 'operador',
		nome_completo TEXT,
		email TEXT,
		telefone TEXT,
		template_personalizado BOOLEAN DEFAULT 0,
		template_image_path TEXT,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)''')
	
	# Migração: Adicionar colunas se não existirem
	try:
		c.execute("ALTER TABLE usuarios ADD COLUMN template_personalizado BOOLEAN DEFAULT 0")
	except sqlite3.OperationalError:
		pass  # Coluna já existe
		
	try:
		c.execute("ALTER TABLE usuarios ADD COLUMN template_image_path TEXT")
	except sqlite3.OperationalError:
		pass  # Coluna já existe
		
	# Migração: Adicionar colunas para cotações se não existirem
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN esboco_servico TEXT")
	except sqlite3.OperationalError:
		pass  # Coluna já existe
		
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN relacao_pecas_substituir TEXT")
	except sqlite3.OperationalError:
		pass  # Coluna já existe
		
	# Migração: Adicionar coluna para tipo de operação nos itens
	try:
		c.execute("ALTER TABLE itens_cotacao ADD COLUMN tipo_operacao TEXT DEFAULT 'Compra'")
	except sqlite3.OperationalError:
		pass  # Coluna já existe

	# Migração: Adicionar colunas para Locação nas cotações
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN tipo_cotacao TEXT DEFAULT 'Compra'")
	except sqlite3.OperationalError:
		pass
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN locacao_valor_mensal REAL")
	except sqlite3.OperationalError:
		pass
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN locacao_data_inicio DATE")
	except sqlite3.OperationalError:
		pass
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN locacao_data_fim DATE")
	except sqlite3.OperationalError:
		pass
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN locacao_qtd_meses INTEGER")
	except sqlite3.OperationalError:
		pass
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN locacao_nome_equipamento TEXT")
	except sqlite3.OperationalError:
		pass

	# Migração: Adicionar coluna para imagem da locação
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN locacao_imagem_path TEXT")
	except sqlite3.OperationalError:
		pass  # Coluna já existe

	# Migração: Adicionar coluna para contato do cliente na cotação
	try:
		c.execute("ALTER TABLE cotacoes ADD COLUMN contato_nome TEXT")
	except sqlite3.OperationalError:
		pass  # Coluna já existe

	# Migração: Adicionar colunas de locação por item em itens_cotacao
	try:
		c.execute("ALTER TABLE itens_cotacao ADD COLUMN locacao_data_inicio DATE")
	except sqlite3.OperationalError:
		pass
	try:
		c.execute("ALTER TABLE itens_cotacao ADD COLUMN locacao_data_fim DATE")
	except sqlite3.OperationalError:
		pass
	try:
		c.execute("ALTER TABLE itens_cotacao ADD COLUMN locacao_qtd_meses INTEGER")
	except sqlite3.OperationalError:
		pass
	# Migração: Imagem por item de locação
	try:
		c.execute("ALTER TABLE itens_cotacao ADD COLUMN locacao_imagem_path TEXT")
	except sqlite3.OperationalError:
		pass

	# Tabela Clientes - ATUALIZADA
	c.execute('''CREATE TABLE IF NOT EXISTS clientes (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		nome TEXT NOT NULL,
		nome_fantasia TEXT,
		cnpj TEXT UNIQUE,
		inscricao_estadual TEXT,
		inscricao_municipal TEXT,
		endereco TEXT,
		numero TEXT,
		complemento TEXT,
		bairro TEXT,
		cidade TEXT,
		estado TEXT,
		cep TEXT,
		telefone TEXT,
		email TEXT,
		site TEXT,
		prazo_pagamento TEXT,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)''')

	# Tabela Contatos do Cliente - NOVA
	c.execute('''CREATE TABLE IF NOT EXISTS contatos (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		cliente_id INTEGER NOT NULL,
		nome TEXT NOT NULL,
		cargo TEXT,
		telefone TEXT,
		email TEXT,
		observacoes TEXT,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
	)''')

	# Tabela Técnicos
	c.execute('''CREATE TABLE IF NOT EXISTS tecnicos (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		nome TEXT NOT NULL,
		especialidade TEXT,
		telefone TEXT,
		email TEXT,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)''')

	# Tabela Produtos/Serviços/Kits
	c.execute('''CREATE TABLE IF NOT EXISTS produtos (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		nome TEXT NOT NULL,
		tipo TEXT NOT NULL CHECK (tipo IN ('Serviço', 'Produto', 'Kit')),
		ncm TEXT,
		valor_unitario REAL DEFAULT 0,
		descricao TEXT,
		esboco_servico TEXT,
		categoria TEXT DEFAULT 'Geral',
		ativo BOOLEAN DEFAULT 1,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)''')

	# Migração: Adicionar coluna esboco_servico em produtos
	try:
		c.execute("ALTER TABLE produtos ADD COLUMN esboco_servico TEXT")
	except sqlite3.OperationalError:
		pass

	# Migração: Adicionar coluna categoria em produtos
	try:
		c.execute("ALTER TABLE produtos ADD COLUMN categoria TEXT DEFAULT 'Geral'")
	except sqlite3.OperationalError:
		pass

	# Tabela Itens do Kit - RENOMEADA
	c.execute('''CREATE TABLE IF NOT EXISTS kit_items (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		kit_id INTEGER NOT NULL,
		produto_id INTEGER NOT NULL,
		quantidade REAL NOT NULL DEFAULT 1,
		FOREIGN KEY (kit_id) REFERENCES produtos(id) ON DELETE CASCADE,
		FOREIGN KEY (produto_id) REFERENCES produtos(id)
	)''')

	# Tabela Cotações
	c.execute('''CREATE TABLE IF NOT EXISTS cotacoes (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		numero_proposta TEXT NOT NULL UNIQUE,
		cliente_id INTEGER NOT NULL,
		responsavel_id INTEGER NOT NULL,
		filial_id INTEGER DEFAULT 2,
		data_criacao DATE NOT NULL,
		data_validade DATE,
		modelo_compressor TEXT,
		numero_serie_compressor TEXT,
		descricao_atividade TEXT,
		observacoes TEXT,
		valor_total REAL DEFAULT 0,
		tipo_frete TEXT DEFAULT 'FOB',
		condicao_pagamento TEXT,
		contato_nome TEXT,
		prazo_entrega TEXT,
		moeda TEXT DEFAULT 'BRL',
		status TEXT DEFAULT 'Em Aberto',
		caminho_arquivo_pdf TEXT,
		relacao_pecas TEXT,
		esboco_servico TEXT,
		relacao_pecas_substituir TEXT,
		tipo_cotacao TEXT DEFAULT 'Compra',
		locacao_valor_mensal REAL,
		locacao_data_inicio DATE,
		locacao_data_fim DATE,
		locacao_qtd_meses INTEGER,
		locacao_nome_equipamento TEXT,
		locacao_imagem_path TEXT,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (cliente_id) REFERENCES clientes(id),
		FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
	)''')

	# Tabela Itens da Cotação
	c.execute('''CREATE TABLE IF NOT EXISTS itens_cotacao (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		cotacao_id INTEGER NOT NULL,
		produto_id INTEGER,
		tipo TEXT NOT NULL,
		item_nome TEXT NOT NULL,
		quantidade REAL NOT NULL,
		descricao TEXT,
		valor_unitario REAL NOT NULL,
		valor_total_item REAL NOT NULL,
		eh_kit BOOLEAN DEFAULT 0,
		kit_id INTEGER,
		mao_obra REAL DEFAULT 0,
		deslocamento REAL DEFAULT 0,
		estadia REAL DEFAULT 0,
		icms REAL DEFAULT 0,
		tipo_operacao TEXT DEFAULT 'Compra',
		locacao_data_inicio DATE,
		locacao_data_fim DATE,
		locacao_qtd_meses INTEGER,
		locacao_imagem_path TEXT,
		FOREIGN KEY (cotacao_id) REFERENCES cotacoes(id),
		FOREIGN KEY (produto_id) REFERENCES produtos(id),
		FOREIGN KEY (kit_id) REFERENCES itens_cotacao(id)
	)''')

	# Migração: Adicionar coluna ICMS em itens_cotacao
	try:
		c.execute("ALTER TABLE itens_cotacao ADD COLUMN icms REAL DEFAULT 0")
	except sqlite3.OperationalError:
		pass
		
	# Migração: Adicionar coluna ISS em itens_cotacao
	try:
		c.execute("ALTER TABLE itens_cotacao ADD COLUMN iss REAL DEFAULT 0")
	except sqlite3.OperationalError:
		pass

	# Tabela Relatórios Técnicos - ATUALIZADA com campos das abas 2 e 3
	c.execute('''CREATE TABLE IF NOT EXISTS relatorios_tecnicos (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		numero_relatorio TEXT NOT NULL UNIQUE,
		cliente_id INTEGER NOT NULL,
		responsavel_id INTEGER NOT NULL,
		data_criacao DATE NOT NULL,
		formulario_servico TEXT,
		tipo_servico TEXT,
		descricao_servico TEXT,
		data_recebimento DATE,
		
		-- Aba 1: Condição Inicial
		condicao_encontrada TEXT,
		placa_identificacao TEXT,
		acoplamento TEXT,
		aspectos_rotores TEXT,
		valvulas_acopladas TEXT,
		data_recebimento_equip TEXT,
		
		-- Aba 2: Peritagem do Subconjunto
		parafusos_pinos TEXT,
		superficie_vedacao TEXT,
		engrenagens TEXT,
		bico_injetor TEXT,
		rolamentos TEXT,
		aspecto_oleo TEXT,
		data_peritagem TEXT,
		
		-- Aba 3: Desmembrando Unidade Compressora
		interf_desmontagem TEXT,
		aspecto_rotores_aba3 TEXT,
		aspecto_carcaca TEXT,
		interf_mancais TEXT,
		galeria_hidraulica TEXT,
		data_desmembracao TEXT,
		
		-- Aba 4: Relação de Peças e Serviços
		servicos_propostos TEXT,
		pecas_recomendadas TEXT,
		data_pecas TEXT,
		
		-- Outros campos
		cotacao_id INTEGER,
		tempo_trabalho_total TEXT,
		tempo_deslocamento_total TEXT,
		fotos TEXT,
		assinaturas TEXT,
		anexos_aba1 TEXT,
		anexos_aba2 TEXT,
		anexos_aba3 TEXT,
		anexos_aba4 TEXT,
		filial_id INTEGER DEFAULT 2,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (cliente_id) REFERENCES clientes(id),
		FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
	)''')

	# Tabela de Permissões de Usuários
	c.execute('''CREATE TABLE IF NOT EXISTS permissoes_usuarios (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		usuario_id INTEGER NOT NULL,
		modulo TEXT NOT NULL,
		nivel_acesso TEXT NOT NULL DEFAULT 'sem_acesso',
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
		UNIQUE(usuario_id, modulo)
	)''')

	# Tabela de Eventos de Campo
	c.execute('''CREATE TABLE IF NOT EXISTS eventos_campo (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		relatorio_id INTEGER NOT NULL,
		tecnico_id INTEGER NOT NULL,
		data_hora TEXT NOT NULL,
		evento TEXT NOT NULL,
		tipo TEXT NOT NULL,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (relatorio_id) REFERENCES relatorios_tecnicos(id),
		FOREIGN KEY (tecnico_id) REFERENCES usuarios(id)
	)''')

	conn.commit()
	conn.close()
	
	# Criar usuário master se não existir
	criar_usuario_master()

def criar_usuario_master():
	"""Criar usuário master padrão se não existir"""
	conn = sqlite3.connect(DB_NAME)
	c = conn.cursor()
	
	try:
		# Verificar se já existe um usuário admin
		c.execute("SELECT COUNT(*) FROM usuarios WHERE role LIKE '%admin%'")
		count = c.fetchone()[0]
		if count == 0:
			# Criar usuário master
			import hashlib
			password_hash = hashlib.sha256("admin123".encode()).hexdigest()
			
			c.execute("""
				INSERT INTO usuarios (username, password, role, nome_completo, email, telefone)
				VALUES (?, ?, ?, ?, ?, ?)
			""", ("admin", password_hash, "admin", "Administrador", "admin@sistema.com", ""))
			
			conn.commit()
		else:
			pass  # Usuário admin já existe
			
	except sqlite3.Error as e:
		print(f"Erro ao criar usuário master: {e}")
	finally:
		conn.close()

if __name__ == "__main__":
	criar_banco()
	print("Banco de dados criado com sucesso!")
