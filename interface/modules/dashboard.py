import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime, timedelta
from .base_module import BaseModule
from database import DB_NAME
from utils.formatters import format_currency

class DashboardModule(BaseModule):
    def setup_ui(self):
        # Container principal
        container = tk.Frame(self.frame, bg='#f8fafc')
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(container, text="Dashboard - Visão Geral", 
                               font=('Arial', 18, 'bold'),
                               bg='#f8fafc',
                               fg='#1e293b')
        title_label.pack(pady=(0, 30))
        
        # Frame dos cards de estatísticas
        stats_frame = tk.Frame(container, bg='#f8fafc')
        stats_frame.pack(fill="x", pady=(0, 30))
        
        # Criar cards de estatísticas
        self.create_stats_cards(stats_frame)
        
        # Frame dos gráficos/listas
        content_frame = tk.Frame(container, bg='#f8fafc')
        content_frame.pack(fill="both", expand=True)
        
        # Criar seções de conteúdo
        self.create_recent_activities(content_frame)
        
        # Carregar dados
        self.load_dashboard_data()
        
    def create_stats_cards(self, parent):
        """Criar cards com estatísticas"""
        # Grid para os cards
        cards_frame = tk.Frame(parent, bg='#f8fafc')
        cards_frame.pack(fill="x")
        
        # Card Clientes
        self.clients_card = self.create_stat_card(cards_frame, "👥 Clientes", "0", "#3b82f6")
        self.clients_card.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        # Card Produtos
        self.products_card = self.create_stat_card(cards_frame, "📦 Produtos", "0", "#10b981")
        self.products_card.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Card Cotações
        self.quotes_card = self.create_stat_card(cards_frame, "💰 Cotações", "0", "#f59e0b")
        self.quotes_card.grid(row=0, column=2, padx=10, pady=5, sticky="ew")
        
        # Card Relatórios
        self.reports_card = self.create_stat_card(cards_frame, "📋 Relatórios", "0", "#ef4444")
        self.reports_card.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
        
        # Configurar grid
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)
            
    def create_stat_card(self, parent, title, value, color):
        """Criar um card de estatística"""
        card = tk.Frame(parent, bg='white', relief='solid', bd=1)
        
        # Título
        title_label = tk.Label(card, text=title, 
                              font=('Arial', 12, 'bold'),
                              bg='white',
                              fg=color)
        title_label.pack(pady=(15, 5))
        
        # Valor
        value_label = tk.Label(card, text=value,
                              font=('Arial', 24, 'bold'),
                              bg='white',
                              fg='#1e293b')
        value_label.pack(pady=(0, 15))
        
        # Armazenar referência do label do valor
        card.value_label = value_label
        
        return card
        
    def create_recent_activities(self, parent):
        """Criar seção de atividades recentes"""
        # Frame principal
        activities_frame = self.create_section_frame(parent, "Atividades Recentes")
        activities_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Criar notebook para diferentes tipos de atividades
        activities_notebook = ttk.Notebook(activities_frame)
        activities_notebook.pack(fill="both", expand=True, pady=10)
        
        # Aba Cotações Recentes
        quotes_frame = tk.Frame(activities_notebook, bg='white')
        activities_notebook.add(quotes_frame, text="Cotações Recentes")
        self.create_recent_quotes_list(quotes_frame)
        
        # Aba Relatórios Recentes
        reports_frame = tk.Frame(activities_notebook, bg='white')
        activities_notebook.add(reports_frame, text="Relatórios Recentes")
        self.create_recent_reports_list(reports_frame)
        
    def create_recent_quotes_list(self, parent):
        """Criar lista de cotações recentes"""
        # Treeview
        columns = ("numero", "cliente", "data", "valor", "status")
        self.quotes_tree = ttk.Treeview(parent, columns=columns, show="headings", height=8)
        
        # Cabeçalhos
        self.quotes_tree.heading("numero", text="Número")
        self.quotes_tree.heading("cliente", text="Cliente")
        self.quotes_tree.heading("data", text="Data")
        self.quotes_tree.heading("valor", text="Valor")
        self.quotes_tree.heading("status", text="Status")
        
        # Larguras
        self.quotes_tree.column("numero", width=120)
        self.quotes_tree.column("cliente", width=200)
        self.quotes_tree.column("data", width=100)
        self.quotes_tree.column("valor", width=120)
        self.quotes_tree.column("status", width=100)
        
        # Scrollbar
        quotes_scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.quotes_tree.yview)
        self.quotes_tree.configure(yscrollcommand=quotes_scrollbar.set)
        
        # Pack
        self.quotes_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        quotes_scrollbar.pack(side="right", fill="y", pady=5)
        
    def create_recent_reports_list(self, parent):
        """Criar lista de relatórios recentes"""
        # Treeview
        columns = ("numero", "cliente", "data", "responsavel", "tipo")
        self.reports_tree = ttk.Treeview(parent, columns=columns, show="headings", height=8)
        
        # Cabeçalhos
        self.reports_tree.heading("numero", text="Número")
        self.reports_tree.heading("cliente", text="Cliente")
        self.reports_tree.heading("data", text="Data")
        self.reports_tree.heading("responsavel", text="Responsável")
        self.reports_tree.heading("tipo", text="Tipo")
        
        # Larguras
        self.reports_tree.column("numero", width=120)
        self.reports_tree.column("cliente", width=200)
        self.reports_tree.column("data", width=100)
        self.reports_tree.column("responsavel", width=150)
        self.reports_tree.column("tipo", width=100)
        
        # Scrollbar
        reports_scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.reports_tree.yview)
        self.reports_tree.configure(yscrollcommand=reports_scrollbar.set)
        
        # Pack
        self.reports_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        reports_scrollbar.pack(side="right", fill="y", pady=5)
        
    def load_dashboard_data(self):
        """Carregar dados do dashboard"""
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        try:
            # Verificar se usuário pode ver dados gerais (admin ou com permissão de consulta no dashboard)
            can_view_general_data = (self.has_role('admin') or 
                                   (hasattr(self.main_window, 'has_access') and 
                                    self.main_window.has_access('dashboard')))
            
            if can_view_general_data:
                # Admin ou usuários com permissão de consulta veem dados gerais
                # Clientes
                c.execute("SELECT COUNT(*) FROM clientes")
                clients_count = c.fetchone()[0]
                self.clients_card.value_label.config(text=str(clients_count))
                
                # Produtos
                c.execute("SELECT COUNT(*) FROM produtos WHERE ativo = 1")
                products_count = c.fetchone()[0]
                self.products_card.value_label.config(text=str(products_count))
                
                # Cotações
                c.execute("SELECT COUNT(*) FROM cotacoes")
                quotes_count = c.fetchone()[0]
                self.quotes_card.value_label.config(text=str(quotes_count))
                
                # Relatórios
                c.execute("SELECT COUNT(*) FROM relatorios_tecnicos")
                reports_count = c.fetchone()[0]
                self.reports_card.value_label.config(text=str(reports_count))
            else:
                # Usuários sem permissão veem apenas seus dados
                # Cotações do usuário
                c.execute("SELECT COUNT(*) FROM cotacoes WHERE responsavel_id = ?", (self.user_id,))
                quotes_count = c.fetchone()[0]
                self.quotes_card.value_label.config(text=str(quotes_count))
                
                # Relatórios do usuário
                c.execute("SELECT COUNT(*) FROM relatorios_tecnicos WHERE responsavel_id = ?", (self.user_id,))
                reports_count = c.fetchone()[0]
                self.reports_card.value_label.config(text=str(reports_count))
                
                # Faturamento do usuário (cotações aprovadas)
                c.execute("SELECT SUM(valor_total) FROM cotacoes WHERE responsavel_id = ? AND status = 'Aprovada'", (self.user_id,))
                faturamento = c.fetchone()[0] or 0
                self.clients_card.value_label.config(text=format_currency(faturamento))
                
                # Quantidade de propostas feitas
                c.execute("SELECT COUNT(*) FROM cotacoes WHERE responsavel_id = ?", (self.user_id,))
                propostas_count = c.fetchone()[0]
                self.products_card.value_label.config(text=str(propostas_count))
            
            # Carregar cotações recentes
            self.load_recent_quotes(c)
            
            # Carregar relatórios recentes
            self.load_recent_reports(c)
            
        except sqlite3.Error as e:
            self.show_error(f"Erro ao carregar dados: {e}")
        finally:
            conn.close()
            
    def load_recent_quotes(self, cursor):
        """Carregar cotações recentes"""
        # Limpar lista atual
        for item in self.quotes_tree.get_children():
            self.quotes_tree.delete(item)
            
        # Verificar se usuário pode ver dados gerais (admin ou com permissão de consulta)
        can_view_general_data = (self.has_role('admin') or 
                               (hasattr(self.main_window, 'has_access') and 
                                self.main_window.has_access('dashboard')))
            
        # Buscar cotações recentes baseadas no perfil
        if can_view_general_data:
            cursor.execute("""
                SELECT c.numero_proposta, cl.nome, c.data_criacao, c.valor_total, c.status
                FROM cotacoes c
                JOIN clientes cl ON c.cliente_id = cl.id
                ORDER BY c.created_at DESC
                LIMIT 10
            """)
        else:
            cursor.execute("""
                SELECT c.numero_proposta, cl.nome, c.data_criacao, c.valor_total, c.status
                FROM cotacoes c
                JOIN clientes cl ON c.cliente_id = cl.id
                WHERE c.responsavel_id = ?
                ORDER BY c.created_at DESC
                LIMIT 10
            """, (self.user_id,))
        
        for row in cursor.fetchall():
            numero, cliente, data, valor, status = row
            self.quotes_tree.insert("", "end", values=(
                numero,
                cliente,
                data,
                format_currency(valor) if valor else "R$ 0,00",
                status
            ))
            
    def load_recent_reports(self, cursor):
        """Carregar relatórios recentes"""
        # Limpar lista atual
        for item in self.reports_tree.get_children():
            self.reports_tree.delete(item)
            
        # Verificar se usuário pode ver dados gerais (admin ou com permissão de consulta)
        can_view_general_data = (self.has_role('admin') or 
                               (hasattr(self.main_window, 'has_access') and 
                                self.main_window.has_access('dashboard')))
            
        # Buscar relatórios recentes baseadas no perfil
        if can_view_general_data:
            cursor.execute("""
                SELECT r.numero_relatorio, cl.nome, r.data_criacao, u.nome_completo, r.tipo_servico
                FROM relatorios_tecnicos r
                JOIN clientes cl ON r.cliente_id = cl.id
                JOIN usuarios u ON r.responsavel_id = u.id
                ORDER BY r.created_at DESC
                LIMIT 10
            """)
        else:
            cursor.execute("""
                SELECT r.numero_relatorio, cl.nome, r.data_criacao, u.nome_completo, r.tipo_servico
                FROM relatorios_tecnicos r
                JOIN clientes cl ON r.cliente_id = cl.id
                JOIN usuarios u ON r.responsavel_id = u.id
                WHERE r.responsavel_id = ?
                ORDER BY r.created_at DESC
                LIMIT 10
            """, (self.user_id,))
        
        for row in cursor.fetchall():
            numero, cliente, data, responsavel, tipo = row
            self.reports_tree.insert("", "end", values=(
                numero,
                cliente,
                data,
                responsavel,
                tipo or "N/A"
            ))
            
    def handle_event(self, event_type, data=None):
        """Manipular eventos do sistema"""
        # Recarregar dados quando houver mudanças
        if event_type in ['cliente_created', 'produto_created', 'cotacao_created', 'relatorio_created']:
            self.load_dashboard_data()