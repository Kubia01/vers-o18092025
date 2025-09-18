import sqlite3
import os
from fpdf import FPDF
from datetime import datetime
import json
from utils.formatters import format_date, format_cnpj, format_phone
from PIL import Image
import tempfile
from assets.filiais.filiais_config import obter_filial

def clean_text(text, aggressive=False):
    """Substitui tabs por espaços e remove caracteres problemáticos"""
    if text is None:
        return ""
    
    # Converter para string se não for
    text = str(text)
    
    # Substituir tabs por espaços
    text = text.replace('\t', '    ')
    
    # Remover ou substituir caracteres problemáticos
    replacements = {
        '"': '"',  # Smart quotes
        '"': '"',
        '’': "'",
        '‘': "'",
        '…': '...',
        '–': '-',
        '—': '-',
        '°': 'o',
        '®': '(R)',
        '©': '(C)',
        '™': '(TM)',
        'ª': 'a',
        'º': 'o',
        'ç': 'c',
        'Ç': 'C'
    }
    
    for old_char, new_char in replacements.items():
        text = text.replace(old_char, new_char)
    
    # Se aggressive=True, remover todos os acentos também
    if aggressive:
        accents = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
            'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
            'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
            'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A', 'Ä': 'A',
            'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
            'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
            'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O', 'Ö': 'O',
            'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U'
        }
        for old_char, new_char in accents.items():
            text = text.replace(old_char, new_char)
    
    # Remover caracteres não-ASCII restantes
    text = ''.join(char if ord(char) < 128 else '?' for char in text)
    
    return text

class RelatorioPDF(FPDF):
    def __init__(self, dados_filial=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_auto_page_break(auto=True, margin=25)
        self.baby_blue = (137, 207, 240)  # Azul bebê corporativo
        self.dark_blue = (41, 128, 185)   # Azul escuro para títulos
        self.light_gray = (245, 245, 245) # Cinza claro para backgrounds
        self.first_page = True
        self.dados_filial = dados_filial or {}
        
        # Adicionar fonte Unicode para suportar caracteres especiais
        try:
            # Tentar adicionar DejaVu Sans (comum no sistema)
            self.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
            self.add_font('DejaVu', 'B', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', uni=True)
            self.unicode_font = True
            print("Fonte Unicode DejaVu carregada com sucesso!")
        except:
            try:
                # Fallback para Arial se disponível
                self.add_font('Arial', '', 'arial.ttf', uni=True)
                self.add_font('Arial', 'B', 'arialbd.ttf', uni=True)
                self.unicode_font = True
                print("Fonte Unicode Arial carregada com sucesso!")
            except:
                # Usar fonte padrão e clean_text mais agressivo
                self.unicode_font = False
                print("Usando fonte padrão sem Unicode - texto será limpo agressivamente")
    
    def header(self):
        # Desenha a borda em todas as páginas
        self.set_line_width(0.5)
        self.set_draw_color(70, 70, 70)  # Cor cinza escura para bordas
        self.rect(5, 5, 200, 287)  # A4: 210x297, então 5mm de margem
        
        # Adicionar logo apenas na primeira página
        if self.page_no() == 1:
            try:
                # Preferir logo oficial em assets
                logo_path = "assets/logos/world_comp_brasil.jpg"
                if os.path.exists(logo_path):
                    # Adicionar logo centralizado no topo
                    with Image.open(logo_path) as img:
                        img_width, img_height = img.size
                        # Redimensionar para caber na largura da página
                        max_width = 80
                        ratio = max_width / img_width
                        new_width = img_width * ratio
                        new_height = img_height * ratio
                        
                        x_pos = (210 - new_width) / 2
                        self.image(logo_path, x=x_pos, y=10, w=new_width, h=new_height)
                        
                        # Ajustar posicionamento do conteúdo após o logo
                        self.set_y(10 + new_height + 10)
            except Exception:
                # Se der erro, continuar sem logo
                self.set_y(20)
        else:
            # Linha de separação no topo para outras páginas
            self.set_draw_color(*self.dark_blue)
            self.set_line_width(0.8)
            self.line(10, 15, 200, 15)
            
            # Posicionamento do conteúdo
            try:
                self.set_top_margin(20)
            except Exception:
                pass
            if self.get_y() < 20:
                self.set_y(20)
        
        self.first_page = False
        self.set_text_color(0, 0, 0)  # Resetar cor do texto
    
    def footer(self):
        self.set_y(-20)
        self.set_draw_color(*self.dark_blue)
        self.line(10, self.get_y() - 5, 200, self.get_y() - 5)
        
        self.set_pdf_font('', 8)
        self.set_text_color(*self.dark_blue)
        endereco = self.dados_filial.get('endereco', 'Rua Fernando Pessoa, 17 – Batistini – São Bernardo do Campo – SP')
        cep = self.dados_filial.get('cep', '09844-390')
        email = self.dados_filial.get('email', 'rogerio@worldcompressores.com.br')
        telefones = self.dados_filial.get('telefones', '(11) 4543-6896/4543-6857/4357-8062')
        cnpj = self.dados_filial.get('cnpj', 'N/A')
        
        self.cell(0, 4, self.clean_pdf_text(f"{endereco} - CEP {cep}"), 0, 1, 'C')
        self.cell(0, 4, self.clean_pdf_text(f"CNPJ: {cnpj} | E-mail: {email} | Fone: {telefones}"), 0, 1, 'C')
        
        # Número da página
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, f"Página {self.page_no()}", 0, 0, 'R')
        
        self.set_text_color(0, 0, 0)

    def set_pdf_font(self, style='', size=10):
        """Define fonte apropriada (Unicode se disponível)"""
        if self.unicode_font:
            self.set_font("DejaVu", style, size)
        else:
            self.set_font("Arial", style, size)
    
    def clean_pdf_text(self, text):
        """Limpa texto conforme a capacidade da fonte"""
        return clean_text(text, aggressive=not self.unicode_font)
    
    def section_title(self, title):
        """Título de seção com background e formatação profissional"""
        self.ln(3)
        
        # Background da seção
        self.set_fill_color(*self.light_gray)
        self.rect(10, self.get_y(), 190, 8, 'F')
        
        # Título
        self.set_text_color(*self.dark_blue)
        self.set_pdf_font('B', 11)
        self.cell(0, 8, self.clean_pdf_text(title), 0, 1, 'L')
        self.set_text_color(0, 0, 0)
        self.ln(2)
    
    def field_label_value(self, label, value, new_line=True):
        """Formatar campo com label e valor de forma profissional"""
        if not value:
            return
            
        self.set_pdf_font('B', 9)
        self.set_text_color(*self.dark_blue)
        label_width = self.get_string_width(label + ": ") + 5
        self.cell(label_width, 5, self.clean_pdf_text(label + ":"), 0, 0)
        
        self.set_pdf_font('', 9)
        self.set_text_color(0, 0, 0)
        if new_line:
            self.cell(0, 5, self.clean_pdf_text(str(value)), 0, 1)
        else:
            self.cell(0, 5, self.clean_pdf_text(str(value)), 0, 0)
    
    def smart_field(self, label, value):
        """Campo inteligente que decide entre linha simples ou múltiplas linhas"""
        if not value:
            return
            
        # Converter para string e verificar comprimento
        value_str = str(value).strip()
        
        # Se for muito curto (menos de 50 caracteres) e sem quebras de linha, usar field_label_value
        if len(value_str) <= 50 and '\n' not in value_str and '\r' not in value_str:
            self.field_label_value(label, value_str)
        else:
            self.multi_line_field(label, value_str)
    
    def multi_line_field(self, label, value):
        """Campo de múltiplas linhas com formatação profissional"""
        if not value:
            return
            
        self.set_pdf_font('B', 9)
        self.set_text_color(*self.dark_blue)
        self.cell(0, 5, self.clean_pdf_text(label + ":"), 0, 1)
        
        self.set_pdf_font('', 9)
        self.set_text_color(0, 0, 0)
        self.set_left_margin(15)  # Indentar o conteúdo
        self.multi_cell(0, 4, self.clean_pdf_text(str(value)))
        self.set_left_margin(10)  # Voltar margem normal
        self.ln(2)
    
    def add_image_to_pdf(self, image_path, max_width=80, max_height=60):
        """Adiciona imagem ao PDF com redimensionamento automático"""
        try:
            if not os.path.exists(image_path):
                return False
                
            # Verificar se é uma imagem suportada
            supported_formats = ['.jpg', '.jpeg', '.png']
            file_ext = os.path.splitext(image_path)[1].lower()
            
            if file_ext not in supported_formats:
                return False
            
            # Obter dimensões da imagem
            with Image.open(image_path) as img:
                img_width, img_height = img.size
                
                # Calcular proporção para redimensionamento
                width_ratio = max_width / img_width
                height_ratio = max_height / img_height
                ratio = min(width_ratio, height_ratio)
                
                new_width = img_width * ratio
                new_height = img_height * ratio
                
                # Verificar se há espaço suficiente na página
                if self.get_y() + new_height > 270:  # 270 é próximo ao fim da página
                    self.add_page()
                
                # Adicionar imagem centralizada
                x_pos = (210 - new_width) / 2
                self.image(image_path, x=x_pos, y=self.get_y(), w=new_width, h=new_height)
                self.ln(new_height + 3)
                
                return True
                
        except Exception as e:
            print(f"Erro ao adicionar imagem {image_path}: {str(e)}")
            return False
    
    def add_custom_cover(self, relatorio_data, cliente_data):
        """Adiciona capa personalizada ao relatório"""
        try:
            self.add_page()
            
            # Verificar se existe logo da empresa
            logo_path = "assets/logos/world_comp_brasil.jpg"
            if os.path.exists(logo_path):
                # Adicionar logo centralizado no topo
                with Image.open(logo_path) as img:
                    img_width, img_height = img.size
                    # Redimensionar para caber na largura da página
                    max_width = 120
                    ratio = max_width / img_width
                    new_width = img_width * ratio
                    new_height = img_height * ratio
                    
                    x_pos = (210 - new_width) / 2
                    self.image(logo_path, x=x_pos, y=30, w=new_width, h=new_height)
                    self.ln(new_height + 20)
            else:
                self.ln(40)  # Espaço onde ficaria o logo
            
            # Título principal
            self.set_pdf_font('B', 24)
            self.set_text_color(*self.dark_blue)
            self.cell(0, 15, "RELATÓRIO TÉCNICO", 0, 1, 'C')
            self.ln(5)
            
            self.set_pdf_font('B', 16)
            self.cell(0, 10, "COMPRESSORES E EQUIPAMENTOS", 0, 1, 'C')
            self.ln(20)
            
            # Informações do relatório em destaque
            self.set_fill_color(*self.light_gray)
            self.rect(20, self.get_y(), 170, 40, 'F')
            
            self.set_pdf_font('B', 14)
            self.set_text_color(0, 0, 0)
            self.ln(8)
            
            # Número do relatório
            if hasattr(self, 'numero_relatorio') and self.numero_relatorio:
                self.cell(0, 8, f"Relatório Nº: {self.numero_relatorio}", 0, 1, 'C')
            
            # Data do relatório
            if hasattr(self, 'data_relatorio') and self.data_relatorio:
                self.cell(0, 8, f"Data: {self.data_relatorio}", 0, 1, 'C')
            
            self.ln(30)
            
            # Informações do cliente
            if cliente_data and len(cliente_data) > 0:  # Verificar se tem dados do cliente
                self.set_pdf_font('B', 14)
                self.set_text_color(*self.dark_blue)
                self.cell(0, 10, "CLIENTE", 0, 1, 'C')
                
                self.set_pdf_font('B', 12)
                self.set_text_color(0, 0, 0)
                
                # Nome da empresa (índice 0 = nome, índice 1 = nome_fantasia)
                nome_cliente = cliente_data[0] if len(cliente_data) > 0 and cliente_data[0] else ""
                nome_fantasia = cliente_data[1] if len(cliente_data) > 1 and cliente_data[1] else ""
                
                # Usar nome fantasia se disponível, senão usar razão social
                nome_exibir = nome_fantasia or nome_cliente
                if nome_exibir:
                    self.cell(0, 8, str(nome_exibir), 0, 1, 'C')
                
                # CNPJ se disponível (índice 2)
                cnpj_cliente = cliente_data[2] if len(cliente_data) > 2 and cliente_data[2] else ""
                if cnpj_cliente:
                    try:
                        from utils.formatters import format_cnpj
                        self.cell(0, 6, f"CNPJ: {format_cnpj(cnpj_cliente)}", 0, 1, 'C')
                    except:
                        self.cell(0, 6, f"CNPJ: {cnpj_cliente}", 0, 1, 'C')
                
                self.ln(20)
            
            # Rodapé da capa
            self.set_y(250)  # Posicionar próximo ao final da página
            self.set_pdf_font('', 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, "World Compressores - Soluções em Compressão", 0, 1, 'C')
            self.cell(0, 5, "Relatório Técnico Especializado", 0, 1, 'C')
            
        except Exception as e:
            print(f"Erro ao criar capa personalizada: {e}")
            # Se der erro, continuar sem a capa
    
    def add_attachments_section(self, anexos, section_title, same_module=True):
        """Adiciona seção de anexos com imagens, respeitando módulos por página"""
        if not anexos:
            return
            
        self.ln(3)
        self.set_pdf_font('B', 10)
        self.set_text_color(*self.dark_blue)
        self.cell(0, 6, self.clean_pdf_text(section_title), 0, 1)
        self.set_text_color(0, 0, 0)
        
        images_in_module = []
        
        # Primeiro, contar quantas imagens existem
        for anexo in anexos:
            if isinstance(anexo, dict):
                caminho = anexo.get('caminho', '')
                if caminho and os.path.exists(caminho):
                    file_ext = os.path.splitext(caminho)[1].lower()
                    if file_ext in ['.jpg', '.jpeg', '.png']:
                        images_in_module.append(anexo)
        
        # Se há muitas imagens e não há espaço suficiente, continuar no mesmo módulo
        # mas em páginas adicionais do mesmo módulo
        for i, anexo in enumerate(anexos, 1):
            if isinstance(anexo, dict):
                nome = anexo.get('nome', f'Anexo {i}')
                caminho = anexo.get('caminho', '')
                descricao = anexo.get('descricao', '')
                
                # Verificar se há espaço suficiente para a próxima imagem (aproximadamente 80mm)
                if caminho and os.path.exists(caminho):
                    file_ext = os.path.splitext(caminho)[1].lower()
                    if file_ext in ['.jpg', '.jpeg', '.png']:
                        # Se não há espaço, adicionar nova página DENTRO do mesmo módulo
                        if self.get_y() > 200:  # Próximo ao fim da página
                            self.add_page()
                            # Repetir título do módulo (não criar novo módulo)
                            if same_module:
                                self.set_pdf_font('B', 10)
                                self.set_text_color(*self.dark_blue)
                                self.cell(0, 6, self.clean_pdf_text(f"{section_title} - Continuação"), 0, 1)
                                self.set_text_color(0, 0, 0)
                                self.ln(2)
                
                # Exibir nome do arquivo
                self.set_pdf_font('B', 9)
                self.cell(0, 5, self.clean_pdf_text(f"{i}. {nome}"), 0, 1)
                
                # Exibir descrição se existir
                if descricao:
                    self.set_pdf_font('', 8)
                    self.set_text_color(80, 80, 80)
                    self.set_left_margin(15)
                    self.multi_cell(0, 4, self.clean_pdf_text(descricao))
                    self.set_left_margin(10)
                    self.set_text_color(0, 0, 0)
                
                # Tentar exibir a imagem se for um arquivo de imagem
                if caminho and os.path.exists(caminho):
                    file_ext = os.path.splitext(caminho)[1].lower()
                    if file_ext in ['.jpg', '.jpeg', '.png']:
                        self.ln(2)
                        if self.add_image_to_pdf(caminho):
                            # Adicionar legenda
                            self.set_pdf_font('I', 8)
                            self.set_text_color(100, 100, 100)
                            self.cell(0, 4, self.clean_pdf_text(f"Figura {i}: {nome}"), 0, 1, 'C')
                            self.set_text_color(0, 0, 0)
                
                self.ln(3)

def gerar_pdf_relatorio(relatorio_id, db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    
    try:
        # Primeiro obter os nomes das colunas existentes na tabela
        c.execute("PRAGMA table_info(relatorios_tecnicos)")
        columns_info = c.fetchall()
        column_names = [column[1] for column in columns_info]
        
        # Construir a query dinamicamente com base nas colunas existentes - EXPANDIDA PARA 4 ABAS
        base_columns = ["r.numero_relatorio", "r.data_criacao", "c.nome", "c.cnpj", "c.endereco", "c.cidade", "c.estado", "r.filial_id"]
        
        # Verificar quais colunas existem na tabela para as 4 abas
        report_columns = []
        column_map = {
            # Dados básicos do serviço
            "formulario_servico": "r.formulario_servico",
            "tipo_servico": "r.tipo_servico",
            "descricao_servico": "r.descricao_servico",
            "data_recebimento": "r.data_recebimento",
            
            # ABA 1: Condição Atual do Equipamento
            "condicao_encontrada": "r.condicao_encontrada",
            "placa_identificacao": "r.placa_identificacao",
            "acoplamento": "r.acoplamento",
            "aspectos_rotores": "r.aspectos_rotores",
            "valvulas_acopladas": "r.valvulas_acopladas",
            "data_recebimento_equip": "r.data_recebimento_equip",
            
            # ABA 2: Peritagem do Subconjunto
            "parafusos_pinos": "r.parafusos_pinos",
            "superficie_vedacao": "r.superficie_vedacao",
            "engrenagens": "r.engrenagens",
            "bico_injetor": "r.bico_injetor",
            "rolamentos": "r.rolamentos",
            "aspecto_oleo": "r.aspecto_oleo",
            "data_peritagem": "r.data_peritagem",
            
            # ABA 3: Desmembrando Unidade Compressora
            "interf_desmontagem": "r.interf_desmontagem",
            "aspecto_rotores_aba3": "r.aspecto_rotores_aba3",
            "aspecto_carcaca": "r.aspecto_carcaca",
            "interf_mancais": "r.interf_mancais",
            "galeria_hidraulica": "r.galeria_hidraulica",
            "data_desmembracao": "r.data_desmembracao",
            
            # ABA 4: Relação de Peças e Serviços
            "servicos_propostos": "r.servicos_propostos",
            "pecas_recomendadas": "r.pecas_recomendadas",
            "data_pecas": "r.data_pecas",
            "tempo_trabalho_total": "r.tempo_trabalho_total",
            "tempo_deslocamento_total": "r.tempo_deslocamento_total",
            
            # Campos adicionais
            "condicao_inicial": "r.condicao_inicial",
            "condicao_atual": "r.condicao_atual"
        }
        
        for col_name, sql_col in column_map.items():
            if col_name in column_names:
                report_columns.append(sql_col)
            else:
                report_columns.append("NULL as " + col_name)
        
        # Construir a query completa
        query = f"""
            SELECT {', '.join(base_columns)}, {', '.join(report_columns)}
            FROM relatorios_tecnicos r
            JOIN clientes c ON r.cliente_id = c.id
            WHERE r.id = ?
        """
        
        c.execute(query, (relatorio_id,))
        relatorio_data = c.fetchone()
        
        if not relatorio_data:
            return False, "Relatório não encontrado"
        
        # Criar um dicionário para acessar valores por nome
        column_indices = {}
        
        # Mapear colunas base para índices
        for i, col_name in enumerate(base_columns):
            col_key = col_name.split('.')[-1]
            column_indices[col_name] = i
            column_indices[col_key] = i
            
        # Mapear colunas de relatório para índices
        for i, col_full in enumerate(report_columns):
            idx = i + len(base_columns)
            if " as " in col_full:
                col_name = col_full.split(" as ")[1]
                column_indices[col_name] = idx
            else:
                col_name = col_full.split('.')[-1]
                column_indices[col_full] = idx
                column_indices[col_name] = idx
        
        # Função auxiliar para acessar dados de forma segura
        def get_value(key, default=""):
            idx = -1
            if key in column_indices:
                idx = column_indices[key]
            elif f"r.{key}" in column_indices:
                idx = column_indices[f"r.{key}"]
            elif f"c.{key}" in column_indices:
                idx = column_indices[f"c.{key}"]
                
            if idx >= 0 and idx < len(relatorio_data):
                return relatorio_data[idx] or default
            return default
        
        # Obter eventos
        c.execute("""
            SELECT u.nome_completo, e.data_hora, e.evento, e.tipo
            FROM eventos_campo e
            JOIN usuarios u ON e.tecnico_id = u.id
            WHERE e.relatorio_id = ?
            ORDER BY e.data_hora
        """, (relatorio_id,))
        eventos = c.fetchall()
        
        # Obter anexos das 4 abas
        anexos_abas = {}
        for aba_num in range(1, 5):
            aba_col = f'anexos_aba{aba_num}'
            if aba_col in column_names:
                c.execute(f"SELECT {aba_col} FROM relatorios_tecnicos WHERE id = ?", (relatorio_id,))
                anexos_result = c.fetchone()
                if anexos_result and anexos_result[0]:
                    try:
                        anexos_data = anexos_result[0]
                        if isinstance(anexos_data, str):
                            anexos_abas[aba_num] = json.loads(anexos_data)
                        elif isinstance(anexos_data, list):
                            anexos_abas[aba_num] = anexos_data
                    except (json.JSONDecodeError, TypeError):
                        anexos_abas[aba_num] = []
        
        # Criar PDF com filial
        filial_id = get_value("filial_id") or 2
        dados_filial = obter_filial(int(filial_id)) or {}
        pdf = RelatorioPDF(dados_filial)
        
        # Configurar dados para cabeçalho
        pdf.numero_relatorio = get_value("numero_relatorio")
        pdf.data_relatorio = format_date(get_value("data_criacao"))
        
        # Iniciar com o conteúdo principal
        pdf.add_page()
        
        # === PÁGINA 1: INFORMAÇÕES GERAIS ===
        pdf.section_title("IDENTIFICAÇÃO DO CLIENTE")
        
        nome_cliente = get_value("nome")
        pdf.field_label_value("RAZÃO SOCIAL", nome_cliente)
        
        cnpj_cliente = get_value("cnpj")
        if cnpj_cliente:
            pdf.field_label_value("CNPJ", format_cnpj(cnpj_cliente))
        
        endereco_cliente = get_value("endereco")
        pdf.field_label_value("ENDEREÇO", endereco_cliente)
        
        cidade = get_value("cidade")
        estado = get_value("estado")
        if cidade and estado:
            pdf.field_label_value("CIDADE/UF", f"{cidade}/{estado}")
        
        pdf.ln(5)
        
        # === DADOS DO SERVIÇO ===
        pdf.section_title("DADOS DO SERVIÇO")
        
        numero_rel = get_value("numero_relatorio")
        pdf.field_label_value("Nº RELATÓRIO", numero_rel)
        
        data_criacao = get_value("data_criacao")
        if data_criacao:
            pdf.field_label_value("DATA", format_date(data_criacao))
        
        formulario = get_value("formulario_servico")
        pdf.field_label_value("FORMULÁRIO DE SERVIÇO", formulario)
        
        tipo_servico = get_value("tipo_servico")
        pdf.field_label_value("TIPO DE SERVIÇO", tipo_servico)
        
        descricao_servico = get_value("descricao_servico")
        pdf.multi_line_field("DESCRIÇÃO DO SERVIÇO", descricao_servico)
        
        pdf.ln(5)
        
        # === TÉCNICOS E EVENTOS ===
        pdf.section_title("REGISTRO DE EVENTOS E TÉCNICOS")

        def format_datetime(dt_val):
            try:
                # Aceita formatos ISO ou já formatados
                if isinstance(dt_val, str):
                    try:
                        # Tentar parse ISO completo
                        dt = datetime.fromisoformat(dt_val.replace('Z', ''))
                    except ValueError:
                        # Tentar formatos comuns
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
                            try:
                                dt = datetime.strptime(dt_val, fmt)
                                break
                            except ValueError:
                                dt = None
                        if dt is None:
                            return str(dt_val)
                else:
                    dt = dt_val
                return dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                return str(dt_val)

        # Renderizar tabela somente se houver eventos
        if eventos:
            # Larguras das colunas somando 190mm (área útil entre as margens)
            col_widths = [50, 40, 20, 80]  # Técnico, Data/Hora, Tipo, Evento
            start_x = 10
            max_y = 270

            # Cabeçalho da tabela
            pdf.set_x(start_x)
            pdf.set_fill_color(*pdf.dark_blue)
            pdf.set_text_color(255, 255, 255)
            pdf.set_pdf_font('B', 9)
            headers = ["TÉCNICO", "DATA/HORA", "TIPO", "EVENTO"]
            for w, htext in zip(col_widths, headers):
                pdf.cell(w, 7, pdf.clean_pdf_text(htext), 1, 0, 'C', True)
            pdf.ln(7)

            pdf.set_text_color(0, 0, 0)
            pdf.set_pdf_font('', 9)
            line_height = 5

            for tecnico, data_hora, desc_evento, tipo_evento in eventos:
                # Quebra de página se necessário (antes de desenhar a linha)
                pdf.set_x(start_x)
                # Calcular altura necessária com base no campo EVENTO
                evento_text = pdf.clean_pdf_text(str(desc_evento or ''))
                # Usar split_only=True do fpdf2 para obter linhas sem renderizar
                try:
                    lines = pdf.multi_cell(col_widths[3], line_height, evento_text, border=0, align='L', ln=0, split_only=True)
                    num_lines = max(1, len(lines))
                except TypeError:
                    # Fallback se split_only não estiver disponível
                    approx_chars_per_line = int(col_widths[3] / (pdf.get_string_width('M') or 1) * 1.8)
                    if approx_chars_per_line <= 0:
                        approx_chars_per_line = 40
                    num_lines = max(1, (len(evento_text) // approx_chars_per_line) + 1)
                row_height = max(line_height, num_lines * line_height)

                if pdf.get_y() + row_height > max_y:
                    pdf.add_page()
                    # Reimprimir cabeçalho da tabela na nova página
                    pdf.set_x(start_x)
                    pdf.set_fill_color(*pdf.dark_blue)
                    pdf.set_text_color(255, 255, 255)
                    pdf.set_pdf_font('B', 9)
                    for w, htext in zip(col_widths, headers):
                        pdf.cell(w, 7, pdf.clean_pdf_text(htext), 1, 0, 'C', True)
                    pdf.ln(7)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_pdf_font('', 9)

                # Posição inicial da linha
                x0 = start_x
                y0 = pdf.get_y()

                # Coluna Técnico
                pdf.set_xy(x0, y0)
                pdf.cell(col_widths[0], row_height, pdf.clean_pdf_text(str(tecnico or '')), 1, 0, 'L')
                x0 += col_widths[0]

                # Coluna Data/Hora
                pdf.set_xy(x0, y0)
                pdf.cell(col_widths[1], row_height, pdf.clean_pdf_text(format_datetime(data_hora)), 1, 0, 'C')
                x0 += col_widths[1]

                # Coluna Tipo
                pdf.set_xy(x0, y0)
                pdf.cell(col_widths[2], row_height, pdf.clean_pdf_text(str(tipo_evento or '')), 1, 0, 'C')
                x0 += col_widths[2]

                # Coluna Evento (quebra automática)
                pdf.set_xy(x0, y0)
                pdf.multi_cell(col_widths[3], line_height, evento_text, border=1, align='L')

                # Garantir que o cursor vá para o início da próxima linha
                pdf.set_y(y0 + row_height)
            pdf.ln(2)
        else:
            pdf.set_pdf_font('', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, "Nenhum evento de campo registrado até o momento.", 0, 1)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # Adicionar informações de tempo se disponíveis
        tempo_trabalho = get_value("tempo_trabalho_total")
        if tempo_trabalho:
            pdf.field_label_value("TEMPO DE TRABALHO TOTAL", tempo_trabalho)
            
        tempo_deslocamento = get_value("tempo_deslocamento_total")
        if tempo_deslocamento:
            pdf.field_label_value("TEMPO DE DESLOCAMENTO TOTAL", tempo_deslocamento)
        
        # === PÁGINA 2: MÓDULO A - CONDIÇÃO INICIAL ===
        pdf.add_page()
        pdf.section_title("MÓDULO A - CONDIÇÃO INICIAL DO EQUIPAMENTO")
        
        condicao_encontrada = get_value("condicao_encontrada")
        pdf.smart_field("CONDIÇÃO ENCONTRADA", condicao_encontrada)
            
        placa_id = get_value("placa_identificacao")
        pdf.smart_field("PLACA DE IDENTIFICAÇÃO/Nº SÉRIE", placa_id)
        
        acoplamento = get_value("acoplamento")
        pdf.smart_field("ACOPLAMENTO", acoplamento)
        
        aspectos_rotores = get_value("aspectos_rotores")
        pdf.smart_field("ASPECTOS DOS ROTORES", aspectos_rotores)
        
        valvulas = get_value("valvulas_acopladas")
        pdf.smart_field("VÁLVULAS ACOPLADAS", valvulas)
            
        data_receb_equip = get_value("data_recebimento_equip")
        pdf.field_label_value("DATA DE RECEBIMENTO DO EQUIPAMENTO", data_receb_equip)
        
        # Anexos da Aba 1 com imagens
        if 1 in anexos_abas and anexos_abas[1]:
            pdf.add_attachments_section(anexos_abas[1], "ANEXOS - CONDIÇÃO INICIAL")
        
        # === PÁGINA 3: MÓDULO B - PERITAGEM DO SUBCONJUNTO ===
        pdf.add_page()
        pdf.section_title("MÓDULO B - PERITAGEM DO SUBCONJUNTO")
        pdf.ln(2)
        pdf.set_pdf_font('', 9)
        pdf.cell(0, 5, "Desacoplando elemento compressor da caixa de acionamento", 0, 1)
        pdf.ln(2)
        
        parafusos_pinos = get_value("parafusos_pinos")
        pdf.smart_field("PARAFUSOS/PINOS", parafusos_pinos)
            
        superficie_vedacao = get_value("superficie_vedacao")
        pdf.smart_field("SUPERFÍCIE DE VEDAÇÃO", superficie_vedacao)
            
        engrenagens = get_value("engrenagens")
        pdf.smart_field("ENGRENAGENS", engrenagens)
            
        bico_injetor = get_value("bico_injetor")
        pdf.smart_field("BICO INJETOR", bico_injetor)
            
        rolamentos = get_value("rolamentos")
        pdf.smart_field("ROLAMENTOS", rolamentos)
            
        aspecto_oleo = get_value("aspecto_oleo")
        pdf.smart_field("ASPECTO DO ÓLEO", aspecto_oleo)
            
        data_peritagem = get_value("data_peritagem")
        pdf.field_label_value("DATA DA PERITAGEM", data_peritagem)
        
        # Anexos da Aba 2 com imagens
        if 2 in anexos_abas and anexos_abas[2]:
            pdf.add_attachments_section(anexos_abas[2], "ANEXOS - PERITAGEM DO SUBCONJUNTO")
        
        # === PÁGINA 4: MÓDULO C - DESMEMBRANDO UNIDADE COMPRESSORA ===
        pdf.add_page()
        pdf.section_title("MÓDULO C - DESMEMBRANDO UNIDADE COMPRESSORA")
        pdf.ln(2)
        pdf.set_pdf_font('', 9)
        pdf.cell(0, 5, "Grau de interferência na desmontagem", 0, 1)
        pdf.ln(2)
        
        interf_desmontagem = get_value("interf_desmontagem")
        pdf.smart_field("INTERFERÊNCIA PARA DESMONTAGEM", interf_desmontagem)
            
        aspecto_rotores_aba3 = get_value("aspecto_rotores_aba3")
        pdf.smart_field("ASPECTO DOS ROTORES", aspecto_rotores_aba3)
            
        aspecto_carcaca = get_value("aspecto_carcaca")
        pdf.smart_field("ASPECTO DA CARCAÇA", aspecto_carcaca)
            
        interf_mancais = get_value("interf_mancais")
        pdf.smart_field("INTERFERÊNCIA DOS MANCAIS", interf_mancais)
            
        galeria_hidraulica = get_value("galeria_hidraulica")
        pdf.smart_field("GALERIA HIDRÁULICA", galeria_hidraulica)
            
        data_desmembracao = get_value("data_desmembracao")
        pdf.field_label_value("DATA DE DESMEMBRAÇÃO", data_desmembracao)
        
        # Anexos da Aba 3 com imagens
        if 3 in anexos_abas and anexos_abas[3]:
            pdf.add_attachments_section(anexos_abas[3], "ANEXOS - DESMEMBRAÇÃO DA UNIDADE")
        
        # === PÁGINA 5: MÓDULO D - RELAÇÃO DE PEÇAS E SERVIÇOS ===
        pdf.add_page()
        pdf.section_title("MÓDULO D - RELAÇÃO DE PEÇAS E SERVIÇOS")
        
        servicos_propostos = get_value("servicos_propostos")
        pdf.multi_line_field("SERVIÇOS PROPOSTOS PARA REFORMA DO SUBCONJUNTO", servicos_propostos)
            
        pecas_recomendadas = get_value("pecas_recomendadas")
        pdf.multi_line_field("PEÇAS RECOMENDADAS PARA REFORMA", pecas_recomendadas)
            
        data_pecas = get_value("data_pecas")
        pdf.field_label_value("DATA", data_pecas)
        
        pdf.ln(5)
        
        # === INFORMAÇÕES COMPLEMENTARES ===
        pdf.section_title("INFORMAÇÕES COMPLEMENTARES")
        
        # Informações de tempo já foram adicionadas na primeira página
        # Aqui podem ser adicionadas outras informações complementares se necessário
        
        # Anexos da Aba 4 com imagens
        if 4 in anexos_abas and anexos_abas[4]:
            pdf.add_attachments_section(anexos_abas[4], "ANEXOS - PEÇAS E SERVIÇOS")
        
        # Salvar arquivo
        output_dir = os.path.join("data", "relatorios")
        os.makedirs(output_dir, exist_ok=True)
        filename = f"relatorio_{relatorio_id}.pdf"
        filepath = os.path.join(output_dir, filename)
        pdf.output(filepath)
        
        return True, filepath
        
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()