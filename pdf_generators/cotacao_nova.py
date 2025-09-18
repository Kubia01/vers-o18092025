import sqlite3
import os
import datetime
import sys
import re
import time
import tempfile
from fpdf import FPDF
from database import DB_NAME
from utils.formatters import format_cep, format_phone, format_currency, format_date, format_cnpj

# Adicionar o diretório assets ao path para importar os templates
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from assets.filiais.filiais_config import obter_filial, obter_usuario_cotacao, obter_template_capa_jpeg

def clean_text(text):
    """Normaliza espaços e símbolos problemáticos preservando acentuação (Latin-1)."""
    if text is None:
        return ""
    text = str(text)
    # Substitui tabs por 4 espaços
    text = text.replace('\t', '    ')
    # Substitui alguns símbolos especiais por equivalentes simples
    replacements = {
        '•': '- ', '●': '- ', '◦': '- ', '◆': '- ', '▪': '- ', '▫': '- ',
        '★': '* ', '☆': '* ', '–': '-', '—': '-', '…': '...', '®': '(R)', '™': '(TM)', '©': '(C)'
    }
    for old_char, new_char in replacements.items():
        text = text.replace(old_char, new_char)
    # Garantir compatibilidade Latin-1 sem remover acentos comuns
    try:
        text.encode('latin-1')
    except Exception:
        text = text.encode('latin-1', 'replace').decode('latin-1')
    return text

def replace_company_names(text, filial_name):
    """Substitui qualquer ocorrência de 'World Comp' (case-insensitive, com espaços) pelo nome da filial."""
    try:
        return re.sub(r"(?i)world\s*comp", filial_name or "WORLD COMP", text or "")
    except Exception:
        return text

def save_pdf_with_fallback(pdf, output_dir, file_name, cot_id, conn):
    """
    Salvar PDF com tratamento robusto de erros de permissão
    Retorna (sucesso, caminho_arquivo)
    """
    try:
        # Garantir que o diretório existe
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, file_name)
        
        # Se o arquivo já existe, tentar removê-lo primeiro
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except PermissionError:
                # Se não conseguir remover, tentar com nome diferente
                timestamp = int(time.time())
                base_name = file_name.replace('.pdf', '')
                file_name = f"{base_name}_{timestamp}.pdf"
                pdf_path = os.path.join(output_dir, file_name)
        
        # Tentar salvar o PDF
        pdf.output(pdf_path)
        
        # Atualizar caminho do PDF no banco de dados
        c = conn.cursor()
        c.execute("UPDATE cotacoes SET caminho_arquivo_pdf=? WHERE id=?", (pdf_path, cot_id))
        conn.commit()
        
        return True, pdf_path
        
    except PermissionError:
        # Se não conseguir salvar no diretório original, tentar em diretório temporário
        try:
            temp_dir = tempfile.gettempdir()
            temp_pdf_path = os.path.join(temp_dir, file_name)
            pdf.output(temp_pdf_path)
            
            # Atualizar caminho do PDF no banco de dados
            c = conn.cursor()
            c.execute("UPDATE cotacoes SET caminho_arquivo_pdf=? WHERE id=?", (temp_pdf_path, cot_id))
            conn.commit()
            
            return True, temp_pdf_path
            
        except Exception as e:
            return False, f"Erro ao salvar PDF: {str(e)}"
    
    except Exception as e:
        return False, f"Erro ao salvar PDF: {str(e)}"

def calculate_text_lines(pdf, text, width, line_height):
    """
    Calcular quantas linhas um texto precisará em uma largura específica
    Retorna o número de linhas necessárias
    """
    if not text or not text.strip():
        return 1
    
    try:
        # Usar split_only=True para calcular altura sem renderizar
        lines = pdf.multi_cell(width, line_height, text, border=0, align='L', ln=0, split_only=True)
        return max(1, len(lines))
    except TypeError:
        # Fallback se split_only não estiver disponível
        char_width = pdf.get_string_width('M')
        if char_width <= 0:
            char_width = 1
        
        # Calcular caracteres por linha com margem de segurança
        chars_per_line = int(width / char_width * 0.8)  # 80% da largura para segurança
        if chars_per_line <= 0:
            chars_per_line = 20
        
        return max(1, (len(text) // chars_per_line) + 1)


class PDFCotacao(FPDF):
    def __init__(self, dados_filial, dados_usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.baby_blue = (137, 207, 240)  # Azul bebê #89CFF0
        self.dados_filial = dados_filial
        self.dados_usuario = dados_usuario
        
        # Configurar encoding para suportar mais caracteres
        self.set_doc_option('core_fonts_encoding', 'latin-1')

        # Controle de seções com margens diferenciadas
        self._section_mode = None
        self._section_top_first = None
        self._section_bottom_first = None
        self._section_top_cont = None
        self._section_bottom_cont = None
        self._default_top = 10
        self._default_bottom = 25
        self._section_title = None

    def begin_section(self, name, top_first, bottom_first, top_cont, bottom_cont, title=None):
        self._section_mode = name
        self._section_top_first = top_first
        self._section_bottom_first = bottom_first
        self._section_top_cont = top_cont
        self._section_bottom_cont = bottom_cont
        self._section_title = title
        # Aplicar margens da primeira página da seção
        self.set_top_margin(top_first)
        self.set_auto_page_break(auto=True, margin=bottom_first)

    def end_section(self):
        # Restaurar margens padrão e limpar estado
        self.set_top_margin(self._default_top)
        self.set_auto_page_break(auto=True, margin=self._default_bottom)
        self._section_mode = None
        self._section_top_first = None
        self._section_bottom_first = None
        self._section_top_cont = None
        self._section_bottom_cont = None
        self._section_title = None

    def accept_page_break(self):
        # Em páginas complementares de uma seção, usar margens de continuação
        if self._section_mode:
            if self._section_top_cont is not None:
                self.set_top_margin(self._section_top_cont)
            if self._section_bottom_cont is not None:
                self.set_auto_page_break(auto=True, margin=self._section_bottom_cont)
            # Marcar que próxima página é complementar da seção
            self._section_cont_break = True
        return True

    def header(self):
        # Não exibir header apenas na capa
        if self.page_no() == 1:
            return

        # Borda da página
        self.set_line_width(0.5)
        self.rect(5, 5, 200, 287)

        # Cabeçalho com imagem fixa ocupando toda a faixa do cabeçalho, encostando na borda
        # (incluindo página 2, mas sem logo)
        try:
            header_img = os.path.join(os.path.dirname(__file__), '..', 'cabeçalho.jpeg')
            if not os.path.exists(header_img):
                header_img = os.path.join(os.path.dirname(__file__), '..', 'cabecalho.jpeg')
            if os.path.exists(header_img):
                # Posicionar a imagem dentro da borda (sem cobrir a linha)
                self.image(header_img, x=5.5, y=5.5, w=199, h=29)
        except Exception:
            pass

        # Garantir que nenhum texto fique sobre o cabeçalho
        try:
            # Definir margem superior e cursor abaixo do header
            self.set_top_margin(40)
        except Exception:
            pass
        if self.get_y() < 40:
            self.set_y(40)

        # Se estiver em seção e esta for uma página complementar, reposicionar e imprimir o título do módulo
        if self._section_mode and getattr(self, '_section_cont_break', False):
            if self._section_top_cont is not None:
                # Nunca permitir conteúdo dentro da faixa do cabeçalho
                safe_top = max(self._section_top_cont, 45)
                self.set_y(safe_top)
            if self._section_title:
                self.set_font("Arial", 'B', 14)
                self.cell(0, 8, clean_text(self._section_title), 0, 1, 'L')
                self.ln(5)
            # limpar flag de página complementar
            self._section_cont_break = False

    def footer(self):
        # NÃO exibir footer na página da capa JPEG (primeira página)
        if self.page_no() == 1:
            return
            
        # Posiciona o rodapé a 1.5 cm do fundo
        self.set_y(-25)  # Aumentou um pouco para acomodar mais uma linha
        
        # Linha divisória acima do rodapé
        self.line(10, self.get_y() - 5, 200, self.get_y() - 5)
        
        # Usar fonte padrão e cor azul bebê - RODAPÉ MINIMALISTA
        self.set_font("Arial", '', 10)  # Fonte menor
        self.set_text_color(*self.baby_blue)  # Cor azul bebê
        
        # Informações do rodapé centralizadas - adaptadas por filial (nome, CNPJ/IE, endereço)
        cnpj_val = self.dados_filial.get('cnpj', '') or 'N/A'
        email_val = self.dados_filial.get('email', '')
        fone_val = self.dados_filial.get('telefones', '')

        # Defaults por CNPJ informado
        nome_emp = self.dados_filial.get('nome', '')
        ie_val = self.dados_filial.get('ie', '') or self.dados_filial.get('inscricao_estadual', '')
        endereco_val = self.dados_filial.get('endereco', '')

        if cnpj_val == "10.644.944/0001-55":
            # World Comp Compressores Eireli (Filial 1 segundo o usuário)
            nome_emp = nome_emp or "World Comp Compressores Eireli"
            ie_val = ie_val or "635970206110"
            endereco_val = endereco_val or "Rua Fernando Pessoa 11-Mezanino, Batistini (  Jardim Represa)- São Bernardo do Campo"
        elif cnpj_val == "22.790.603/0001-77":
            # World Comp Do Brasil Compressores Eireli (Filial 2)
            nome_emp = nome_emp or "World Comp Do Brasil Compressores Eireli"
            ie_val = ie_val or "635835470115"
            endereco_val = endereco_val or "Rua Fernando Pessoa 17-Mezanino, Batistini (  Jardim Represa)- São Bernardo do Campo"

        linha_nome = nome_emp if nome_emp else ""
        linha_cnpj_ie = f"CNPJ: {cnpj_val}  |  IE: {ie_val}" if cnpj_val != 'N/A' else ""
        linha_endereco = endereco_val
        contato_completo = f"E-mail: {email_val} | Fone: {fone_val}"

        if linha_nome:
            self.cell(0, 5, clean_text(linha_nome), 0, 1, 'C')
        if linha_cnpj_ie:
            self.cell(0, 5, clean_text(linha_cnpj_ie), 0, 1, 'C')
        if linha_endereco:
            self.cell(0, 5, clean_text(linha_endereco), 0, 1, 'C')
        if email_val or fone_val:
            self.cell(0, 5, clean_text(contato_completo), 0, 1, 'C')
        
        # Resetar cor para preto para o conteúdo principal
        self.set_text_color(0, 0, 0)
    
    @staticmethod
    def obter_composicao_kit(kit_id):
        """Obtém a composição de um kit a partir do banco de dados"""
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        composicao = []
        
        try:
            c.execute("""
                SELECT p.nome, kc.quantidade 
                FROM kit_items kc
                JOIN produtos p ON kc.produto_id = p.id
                WHERE kc.kit_id = ?
            """, (kit_id,))
            
            for row in c.fetchall():
                nome, quantidade = row
                composicao.append(f"{quantidade} x {nome}")
                
        except sqlite3.Error:
            composicao = ["Erro ao carregar composição"]
        finally:
            conn.close()
        
        return composicao

def gerar_pdf_cotacao_nova(cotacao_id, db_name, current_user=None, contato_nome=None, locacao_pagina4_text=None, locacao_pagina4_image=None):
    """
    Versão melhorada do gerador de PDF de cotações
    - Corrige problemas de logo
    - Adiciona capa personalizada por usuário
    - Corrige problemas de descrição e valores
    - Inclui CNPJ da filial no rodapé
    """
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()   

        # Obter dados da cotação (incluindo filial_id)
        c.execute("""
            SELECT 
                cot.id, cot.numero_proposta, cot.modelo_compressor, cot.numero_serie_compressor, 
                cot.descricao_atividade, cot.observacoes, cot.data_criacao,
                cot.valor_total, cot.tipo_frete, cot.condicao_pagamento, cot.prazo_entrega,
                cli.id AS cliente_id, cli.nome AS cliente_nome, cli.nome_fantasia, cli.endereco, cli.email, 
                cli.telefone, cli.site, cli.cnpj, cli.cidade, cli.estado, cli.cep,
                usr.id AS responsavel_id, usr.nome_completo, usr.email AS usr_email, usr.telefone AS usr_telefone, usr.username,
                cot.moeda, cot.relacao_pecas, cot.filial_id, cot.esboco_servico, cot.relacao_pecas_substituir, cot.tipo_cotacao,
                cot.locacao_nome_equipamento, cot.locacao_imagem_path
            FROM cotacoes AS cot
            JOIN clientes AS cli ON cot.cliente_id = cli.id
            JOIN usuarios AS usr ON cot.responsavel_id = usr.id
            WHERE cot.id = ?
        """, (cotacao_id,))
        cotacao_data = c.fetchone()

        if not cotacao_data:
            return False, "Cotação não encontrada para gerar PDF."

        (
            cot_id, numero_proposta, modelo_compressor, numero_serie_compressor,
            descricao_atividade, observacoes, data_criacao,
            valor_total, tipo_frete, condicao_pagamento, prazo_entrega,
            cliente_id, cliente_nome, cliente_nome_fantasia, cliente_endereco, cliente_email, 
            cliente_telefone, cliente_site, cliente_cnpj, cliente_cidade, 
            cliente_estado, cliente_cep,
            responsavel_id, responsavel_nome, responsavel_email, responsavel_telefone, responsavel_username,
            moeda, relacao_pecas, filial_id, esboco_servico, relacao_pecas_substituir, tipo_cotacao,
            locacao_nome_equipamento_db, locacao_imagem_path_db
        ) = cotacao_data

        # Obter dados da filial
        dados_filial = obter_filial(filial_id or 2)  # Default para filial 2
        if not dados_filial:
            return False, "Dados da filial não encontrados."

        # Obter configurações do usuário
        dados_usuario = obter_usuario_cotacao(responsavel_username)
        if not dados_usuario:
            dados_usuario = {
                'nome_completo': responsavel_nome,
                'assinatura': f"{responsavel_nome}\nVendas"
            }
        
        # Usar email do usuário que já vem da query principal
        if responsavel_email:
            dados_usuario['email'] = responsavel_email

        # Obter contato do parâmetro ou buscar principal
        if not contato_nome:
            c.execute("""
                SELECT nome FROM contatos 
                WHERE cliente_id = ? 
                LIMIT 1
            """, (cliente_id,))
            contato_principal = c.fetchone()
            contato_nome = contato_principal[0] if contato_principal else "Não informado"

        # Obter itens da cotação - QUERY SIMPLIFICADA (como modelo antigo)
        c.execute("""
            SELECT 
                id, tipo, item_nome, quantidade, descricao, 
                valor_unitario, valor_total_item, 
                mao_obra, deslocamento, estadia, produto_id, tipo_operacao, icms, iss
            FROM itens_cotacao 
            WHERE cotacao_id=?
        """, (cotacao_id,))
        itens_cotacao = c.fetchall()

        # Criar o PDF
        pdf = PDFCotacao(dados_filial, dados_usuario, orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=30)
        
        # Configurar dados para cabeçalho/footer (como modelo antigo)
        pdf.numero_proposta = numero_proposta
        pdf.data_proposta = format_date(data_criacao)
        pdf.cliente_nome = cliente_nome_fantasia if cliente_nome_fantasia else cliente_nome
        pdf.cliente_cnpj = cliente_cnpj
        pdf.cliente_telefone = cliente_telefone
        pdf.contato_nome = contato_nome
        pdf.responsavel_nome = responsavel_nome

        # PÁGINA 1: CAPA
        # ===============
        pdf.add_page()

        # Fundo fixo para capa: usar sempre caploc.jpg (padrão unificado)
        capa_path = os.path.join(os.path.dirname(__file__), '..', 'caploc.jpg')
        if os.path.exists(capa_path):
            pdf.image(capa_path, x=0, y=0, w=210, h=297)

        # Textos dinâmicos na capa, canto inferior esquerdo (branco, negrito, mesmo tamanho)
        try:
            pdf.set_text_color(255, 255, 255)
            # Prevenir quebra automática ao escrever próximo ao rodapé
            try:
                pdf.set_auto_page_break(auto=False)
            except Exception:
                pass
            # Posição segura na parte inferior esquerda (abaixado um pouco)
            pdf.set_xy(14, 254)  # ajuste fino conforme feedback
            try:
                pdf.set_font('Arial', 'B', 12)
            except Exception:
                pdf.set_pdf_font('B', 12)

            cliente_line = (pdf.cliente_nome or '').strip()
            if cliente_line:
                line = getattr(pdf, 'clean_pdf_text', lambda x: x)(cliente_line)
                pdf.set_x(14)
                pdf.cell(0, 6, line, 0, 1, 'L')

            contato_line = (contato_nome or '').strip()
            if contato_line:
                line = getattr(pdf, 'clean_pdf_text', lambda x: x)(f"A/C : {contato_line}")
                pdf.set_x(14)
                pdf.cell(0, 6, line, 0, 1, 'L')

            data_line = getattr(pdf, 'data_proposta', None) or format_date(data_criacao)
            if data_line:
                line = getattr(pdf, 'clean_pdf_text', lambda x: x)(f"Data: {data_line}")
                pdf.set_x(14)
                pdf.cell(0, 6, line, 0, 1, 'L')
        except Exception:
            pass
        finally:
            # Restaurar quebra automática para o restante do documento
            try:
                pdf.set_auto_page_break(auto=True, margin=30)
            except Exception:
                pass
        # Não exibir nenhum texto na capa
        pdf.set_text_color(0, 0, 0)

        # PÁGINA 2: APRESENTAÇÃO COM DADOS (SEM LOGO)
        # ============================================
        pdf.add_page()
        # (Sem fundo padrão nas páginas subsequentes)
        
        # Logo removido conforme solicitado
        
        # Posição para dados do cliente e empresa (ajustado sem logo)
        pdf.set_y(40)  # Ajustado para posição sem logo
        
        # Dados do cliente (lado esquerdo) e empresa (lado direito)
        pdf.set_font("Arial", 'B', 10)  # Fonte menor para acomodar mais texto
        pdf.cell(95, 7, clean_text("APRESENTADO PARA:"), 0, 0, 'L')
        pdf.set_x(105)  # Reduzido ainda mais para dar espaço
        pdf.cell(95, 7, clean_text("APRESENTADO POR:"), 0, 1, 'L')
        
        # Nome do cliente/empresa
        pdf.set_font("Arial", 'B', 10)
        cliente_nome_display = getattr(pdf, 'cliente_nome', 'N/A')
        pdf.cell(95, 5, clean_text(cliente_nome_display), 0, 0, 'L')
        
        pdf.set_x(105)
        nome_filial = dados_filial.get('nome', 'N/A')
        pdf.cell(95, 5, clean_text(nome_filial), 0, 1, 'L')
        
        # CNPJ (com I.E. quando Filial 1)
        pdf.set_font("Arial", '', 10)
        cliente_cnpj = getattr(pdf, 'cliente_cnpj', '')
        if cliente_cnpj:
            cnpj_texto = f"CNPJ: {format_cnpj(cliente_cnpj)}"
        else:
            cnpj_texto = "CNPJ: N/A"
        pdf.cell(95, 5, clean_text(cnpj_texto), 0, 0, 'L')
        
        pdf.set_x(105)
        cnpj_filial = dados_filial.get('cnpj', 'N/A')
        try:
            # Verificar se é filial 1 pelo CNPJ (mais confiável)
            filial_is_1 = cnpj_filial == "10.644.944/0001-55"
        except Exception:
            filial_is_1 = False
        cnpj_ie_text = f"CNPJ: {cnpj_filial}"
        if filial_is_1:
            cnpj_ie_text += "  |  I.E: 635970206110"
        pdf.cell(95, 5, clean_text(cnpj_ie_text), 0, 1, 'L')
        
        # Telefone
        cliente_telefone = getattr(pdf, 'cliente_telefone', '')
        if cliente_telefone:
            telefone_texto = f"FONE: {format_phone(cliente_telefone)}"
        else:
            telefone_texto = "FONE: N/A"
        pdf.cell(95, 5, clean_text(telefone_texto), 0, 0, 'L')
        
        pdf.set_x(105)
        telefones_filial = dados_filial.get('telefones', 'N/A')
        pdf.cell(95, 5, clean_text(f"FONE: {telefones_filial}"), 0, 1, 'L')
        
        # Contato/Email
        contato_nome = getattr(pdf, 'contato_nome', '')
        if contato_nome:
            contato_texto = f"Sr(a). {contato_nome}"
        else:
            contato_texto = "Contato: N/A"
        pdf.cell(95, 5, clean_text(contato_texto), 0, 0, 'L')
        
        pdf.set_x(105)
        # Buscar e-mail do responsável da cotação (forçar e-mail do usuário criador)
        email_responsavel = (responsavel_email or dados_usuario.get('email') or 'N/A')
        pdf.cell(95, 5, clean_text(f"E-mail: {email_responsavel}"), 0, 1, 'L')
        
        # Linha adicional - Responsável
        pdf.cell(95, 5, "", 0, 0, 'L')  # Espaço vazio no lado esquerdo
        pdf.set_x(105)
        responsavel_nome = getattr(pdf, 'responsavel_nome', 'N/A')
        pdf.cell(95, 5, clean_text(f"Responsável: {responsavel_nome}"), 0, 1, 'L')
        
        pdf.ln(10)  # Espaço antes do conteúdo
        
        # Preparar nome do equipamento (Locação) para uso dinâmico no texto
        equipamento_nome_preview = None
        if (tipo_cotacao or '').lower() in ('locação','locacao'):
            try:
                c.execute("SELECT item_nome FROM itens_cotacao WHERE cotacao_id = ? AND (tipo_operacao = 'Locação' OR tipo_operacao IS NULL) ORDER BY id LIMIT 1", (cot_id,))
                row_nome = c.fetchone()
                if row_nome and row_nome[0]:
                    equipamento_nome_preview = row_nome[0]
                elif locacao_nome_equipamento_db:
                    equipamento_nome_preview = locacao_nome_equipamento_db
            except Exception:
                equipamento_nome_preview = locacao_nome_equipamento_db

        # Texto de apresentação
        pdf.set_font("Arial", size=11)
        texto_apresentacao = None
        if (tipo_cotacao or '').lower() == 'locação' or (tipo_cotacao or '').lower() == 'locacao':
            # Texto completo com linha alvo mantendo posição e tamanho originais
            equip_nome_for_line = (equipamento_nome_preview or "").strip()
            texto_str = (
                "Prezados Senhores:\n\n"
                "Agradecemos por nos conceder a oportunidade de apresentarmos nossa proposta para\n"
                f"fornecimento de Locação de Compressor de Ar {equip_nome_for_line if equip_nome_for_line else ''}.\n\n"
                "A World Comp Compressores e especializada em manutencao de compressores de parafuso\n"
                "das principais marcas do mercado, como Atlas Copco, Ingersoll Rand, Chicago. Atuamos tambem com\n"
                "revisao de equipamentos e unidades compressoras, venda de pecas, bem como venda e locacao de\n"
                "compressores de parafuso isentos de oleo e lubrificados.\n\n"
                "Com profissionais altamente qualificados e atendimento especializado, colocamo-nos a\n"
                "disposicao para analisar, corrigir e prestar os devidos esclarecimentos, sempre buscando atender as\n"
                "especificacoes e necessidades dos nossos clientes."
            )
            texto_str = replace_company_names(clean_text(texto_str), dados_filial.get('nome'))
            alvo = "LOCACAO DE COMPRESSOR DE AR"
            paragrafos = texto_str.split("\n\n")
            for idx, par in enumerate(paragrafos):
                # No parágrafo com a linha de fornecimento, deixar o NOME do equipamento em negrito
                if idx == 1 and equip_nome_for_line:
                    alvo_nome = equip_nome_for_line
                    if alvo_nome in par:
                        antes, _, resto = par.partition(alvo_nome)
                        pdf.set_font("Arial", '', 11)
                        pdf.write(5, clean_text(antes))
                        pdf.set_font("Arial", 'B', 11)
                        pdf.write(5, clean_text(alvo_nome))
                        pdf.set_font("Arial", '', 11)
                        pdf.write(5, clean_text(resto))
                    else:
                        pdf.multi_cell(0, 5, clean_text(par))
                else:
                    pdf.multi_cell(0, 5, clean_text(par))
                # Quebra entre parágrafos
                pdf.ln(5)
                # Após o 2º parágrafo (idx == 1), inserir 4 linhas extras
                if idx == 1:
                    pdf.ln(20)
            texto_apresentacao = None
        else:
            modelo_text = f" {modelo_compressor}" if modelo_compressor else ""
            texto_apresentacao = clean_text(f"""
Prezados,

Agradecemos a sua solicitação e, conforme requerido, apresentamos nossas condições comerciais para fornecimento de serviços e mão de obra para seu compressor{modelo_text}.

A Word Comp Compressores é especializada em manutenção de compressores de parafuso das principais marcas do mercado, como Atlas Copco, Ingersoll Rand, Chicago. Atuamos também com revisão de equipamentos e unidades compressoras, venda de peças, bem como venda e locação de compressores de parafuso isento de óleo e lubrificados

Com profissionais altamente qualificados e atendimento especializado, colocamo-nos à disposição para analisar, corrigir e prestar os devidos esclarecimentos, sempre buscando atender às especificações e necessidades dos nossos clientes.

Atenciosamente,
            """)
        if texto_apresentacao:
            # Serviços/Produtos: inserir 4 linhas extras após o segundo parágrafo
            partes = texto_apresentacao.split("\n\n")
            for idx, par in enumerate(partes):
                if idx == 1 and (modelo_compressor or '').strip():
                    # Negritar apenas o modelo dentro do 2º parágrafo
                    modelo_text = f" {modelo_compressor}"
                    alvo_modelo = f"compressor{modelo_text}"
                    if alvo_modelo in par:
                        antes, _, resto = par.partition(alvo_modelo)
                        pdf.set_font("Arial", '', 11)
                        pdf.write(5, clean_text(antes + "compressor"))
                        pdf.set_font("Arial", 'B', 11)
                        pdf.write(5, clean_text(modelo_text))
                        pdf.set_font("Arial", '', 11)
                        pdf.write(5, clean_text(resto))
                    else:
                        pdf.multi_cell(0, 5, clean_text(par))
                else:
                    pdf.multi_cell(0, 5, clean_text(par))
                pdf.ln(5)
                if idx == 1:
                    pdf.ln(20)
        
        # Assinatura na parte inferior da página 2
        pdf.set_y(240)  # Posiciona mais baixo para garantir que fique na página 2
        if (tipo_cotacao or '').lower() == 'locação' or (tipo_cotacao or '').lower() == 'locacao':
            # Layout reorganizado para Locação: "Atenciosamente" separado do nome da empresa
            # Subir mais 6 linhas antes de escrever "Atenciosamente" (total de 12 linhas)
            pdf.ln(-60)  # Subir 60mm (aproximadamente 12 linhas)
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 5, clean_text("Atenciosamente,"), 0, 1, 'L')
            
            # Voltar para a posição original e escrever as informações do responsável
            pdf.set_y(240)  # Voltar para a posição original
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 6, clean_text(responsavel_nome.upper()), 0, 1, 'L')
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 5, clean_text("Vendas"), 0, 1, 'L')
            pdf.cell(0, 5, clean_text(f"Fone: {dados_filial.get('telefones', '')}"), 0, 1, 'L')
            # Nome da empresa após o telefone
            pdf.cell(0, 5, clean_text("WORLD COMP DO BRASIL COMPRESSORES LTDA"), 0, 1, 'L')
        else:
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 6, clean_text(responsavel_nome.upper()), 0, 1, 'L')
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 5, clean_text("Vendas"), 0, 1, 'L')
            pdf.cell(0, 5, clean_text(f"Fone: {dados_filial.get('telefones', '')}"), 0, 1, 'L')
            pdf.cell(0, 5, clean_text(dados_filial.get('nome', '')), 0, 1, 'L')

        # PÁGINA 3: SOBRE A EMPRESA
        # ==========================
        pdf.add_page()
        pdf.set_y(45)
        if (tipo_cotacao or '').lower() == 'locação' or (tipo_cotacao or '').lower() == 'locacao':
            # Locação: usar textos específicos fornecidos
            secoes_loc = [
                ("SOBRE A WORLD COMP", clean_text(
"A World Comp Compressores e uma empresa com mais de uma decada de atuacao no\n"
"mercado nacional, especializada na manutencao de compressores de ar do tipo parafuso. Seu\n"
"atendimento abrange todo o territorio brasileiro, oferecendo solucoes tecnicas e comerciais voltadas a\n"
"maximizacao do desempenho e da confiabilidade dos sistemas de ar comprimido utilizados por seus\n"
"clientes.\n"
                )),
                ("NOSSOS SERVICOS", clean_text(
"A empresa oferece um portfolio completo de servicos, que contempla a manutencao\n"
"preventiva e corretiva de compressores e unidades compressoras, a venda de pecas de reposicao\n"
"para diversas marcas, a locacao de compressores de parafuso — incluindo modelos lubrificados e\n"
"isentos de oleo —, alem da recuperacao de unidades compressoras e trocadores de calor.\n"
"A World Comp tambem disponibiliza contratos de manutencao personalizados, adaptados as\n"
"necessidades operacionais especificas de cada cliente. Dentre os principais fabricantes atendidos,\n"
"destacam-se marcas reconhecidas como Atlas Copco, Ingersoll Rand e Chicago Pneumatic.\n"
                )),
                ("QUALIDADE DOS SERVICOS & MELHORIA CONTINUA", clean_text(
"A empresa investe continuamente na capacitacao de sua equipe, na modernizacao de\n"
"processos e no aprimoramento da estrutura de atendimento, assegurando alto padrao de qualidade,\n"
"agilidade e eficacia nos servicos. Mantem ainda uma politica ativa de melhoria continua, com\n"
"avaliacoes periodicas que visam atualizar tecnologias, aperfeicoar metodos e garantir excelencia\n"
"tecnica.\n"
                )),
                ("CONTE CONOSCO PARA UMA PARCERIA!", clean_text(
"Nossa missao e ser sua melhor parceria com sinonimo de qualidade, garantia e o melhor\n"
"custo beneficio.\n"
                ))
            ]
            for titulo, texto in secoes_loc:
                pdf.set_text_color(*pdf.baby_blue)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 8, titulo, 0, 1, 'L')
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 5, replace_company_names(texto, dados_filial.get('nome')))
                pdf.ln(3)
            pdf.ln(7)
        else:
            # Cotação (padrão): manter conteúdo original
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, clean_text("SOBRE A WORLD COMP"), 0, 1, 'L')
            pdf.set_font("Arial", '', 11)
            sobre_empresa = clean_text("Há mais de uma década no mercado de manutenção de compressores de ar de parafuso, de diversas marcas, atendemos clientes em todo território brasileiro.")
            pdf.multi_cell(0, 5, sobre_empresa)
            pdf.ln(5)
            secoes = [
                ("FORNECIMENTO, SERVIÇO E LOCAÇÃO", """
A World Comp oferece os serviços de Manutenção Preventiva e Corretiva em Compressores e Unidades Compressoras, Venda de peças, Locação de compressores, Recuperação de Unidades Compressoras, Recuperação de Trocadores de Calor e Contrato de Manutenção em compressores de marcas como: Atlas Copco, Ingersoll Rand, Chicago Pneumatic entre outros.
                """),
                ("CONTE CONOSCO PARA UMA PARCERIA", """
Adaptamos nossa oferta para suas necessidades, objetivos e planejamento. Trabalhamos para que seu processo seja eficiente.
                """),
                ("MELHORIA CONTÍNUA", """
Continuamente investindo em comprometimento, competência e eficiência de nossos serviços, produtos e estrutura para garantirmos a máxima eficiência de sua produtividade.
                """),
                ("QUALIDADE DE SERVIÇOS", """
Com uma equipe de técnicos altamente qualificados e constantemente treinados para atendimentos em todos os modelos de compressores de ar, a World Comp oferece garantia de excelente atendimento e produtividade superior com rapidez e eficácia.
                """)
            ]
            for titulo, texto in secoes:
                pdf.set_text_color(*pdf.baby_blue)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 8, clean_text(titulo), 0, 1, 'L')
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 5, clean_text(texto))
                pdf.ln(3)
            texto_final = clean_text("Nossa missão é ser sua melhor parceria com sinônimo de qualidade, garantia e o melhor custo benefício.")
            pdf.multi_cell(0, 5, texto_final)
            pdf.ln(10)
        
        # =====================================================
        # PÁGINA 4: ESBOÇO DO SERVIÇO A SER EXECUTADO (COMPRA)
        # OU PÁGINA 4 DE LOCAÇÃO COM TEXTO  IMAGEM
        # =====================================================
        if (tipo_cotacao or '').lower() == 'locação' or (tipo_cotacao or '').lower() == 'locacao':
            # Página 4 específica de Locação
            pdf.add_page()
            pdf.set_y(50)

            # Determinar título dinâmico a partir do "Modelo do Compressor" informado na Locação
            modelo_titulo = None
            try:
                for it in itens_cotacao or []:
                    desc = it[4] if len(it) > 4 else None
                    tipo_oper = (it[11] if len(it) > 11 else '') or ''
                    if 'loca' in tipo_oper.lower() and desc:
                        m = re.search(r"(?i)modelo\s*:\s*(.)$", str(desc))
                        if m:
                            modelo_titulo = m.group(1).strip()
                            break
            except Exception:
                pass
            # Remover título do modelo acima da cobertura: não imprimiremos título de equipamento aqui
            # Imagem dinâmica (se fornecida) ou fallback do banco de dados
            imagem_pagina4 = None
            if locacao_pagina4_image and os.path.exists(locacao_pagina4_image):
                imagem_pagina4 = locacao_pagina4_image
            elif 'locacao_imagem_path_db' in locals() and locacao_imagem_path_db and os.path.exists(locacao_imagem_path_db):
                imagem_pagina4 = locacao_imagem_path_db

            # Imagem será renderizada apenas uma vez mais abaixo com tamanho padronizado
            # Bloco de cobertura total conforme especificação
            pdf.set_text_color(*pdf.baby_blue)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, clean_text("COBERTURA TOTAL"), 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 11)
            texto_cobertura = (
                "O Contrato de Locação cobre todos os serviços e manutenções, isso significa que não existe custos \n"
                "inesperados com o seu sistema de ar comprimido. O cronograma de manutenções preventivas é \n"
                "seguido à risca e gerenciado por um time de engenheiros especializados para garantir o mais alto nível \n"
                "de eficiência. Além de você contar com a cobertura completa para reparos, intervenções emergenciais \n"
                "e atendimento proativo completa para reparos, intervenções emergenciais e atendimento proativo. "
            )
            pdf.multi_cell(0, 5, clean_text(texto_cobertura))
            pdf.ln(4)
            pdf.set_text_color(*pdf.baby_blue)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, clean_text("EQUIPAMENTO A SER OFERTADO:"), 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", 'B', 12)
            # Não imprimir o nome do modelo aqui conforme solicitado
            pdf.ln(2)

            # Tentar obter do primeiro item de locação
            equipamento_nome = None
            try:
                c.execute("SELECT item_nome, locacao_imagem_path FROM itens_cotacao WHERE cotacao_id = ? AND tipo_operacao = 'Locação' ORDER BY id LIMIT 1", (cot_id,))
                row_first = c.fetchone()
                if row_first:
                    equipamento_nome = row_first[0]
                    locacao_imagem_path_db = locacao_imagem_path_db or row_first[1]
            except Exception:
                equipamento_nome = None
            if not equipamento_nome:
                equipamento_nome = locacao_nome_equipamento_db or modelo_titulo or "COMPRESSOR DE PARAFUSO LUBRIFICADO REFRIGERADO À AR"
            pdf.set_font("Arial", 'B', 12)
            pdf.multi_cell(0, 6, clean_text(equipamento_nome))
            pdf.ln(3)
            # Debug: verificar parâmetros recebidos
            print(f"DEBUG PDF - Tipo cotação: {tipo_cotacao}")
            print(f"DEBUG PDF - Texto: {locacao_pagina4_text}")
            print(f"DEBUG PDF - Imagem: {locacao_pagina4_image}")
            print(f"DEBUG PDF - Imagem existe: {locacao_pagina4_image and os.path.exists(locacao_pagina4_image) if locacao_pagina4_image else False}")
            # Imagem dinâmica (se fornecida) ou fallback do banco de dados
            imagem_pagina4 = None
            if locacao_pagina4_image and os.path.exists(locacao_pagina4_image):
                imagem_pagina4 = locacao_pagina4_image
            elif 'locacao_imagem_path_db' in locals() and locacao_imagem_path_db and os.path.exists(locacao_imagem_path_db):
                imagem_pagina4 = locacao_imagem_path_db

            if imagem_pagina4:
                # Padronizar tamanho para todas as imagens
                # Largura desejada mantida (70*1.3); altura ajustada para 3.5
                w, h = 70 * 1.3, 24 * 1.3 * 3.5
                x = (210 - w) / 2
                y = pdf.get_y() + 10
                if y + h > 270:
                    pdf.add_page()
                    y = 35
                pdf.image(imagem_pagina4, x=x, y=y, w=w, h=h)
                pdf.set_y(y + h + 6)

            # (Cobertura já adicionada acima)

            # =====================================================
            # PÁGINA 5: TABELA DE ITENS VENDIDOS (EQUIPAMENTOS DA LOCAÇÃO)
            # =====================================================
            pdf.add_page()
            pdf.set_y(50)
            pdf.set_text_color(*pdf.baby_blue)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, clean_text("EQUIPAMENTOS"), 0, 1, 'L')
            pdf.ln(2)

            # Buscar itens de locação com meses (sem ICMS)
            c.execute(
                """
                SELECT item_nome, quantidade, valor_unitario, COALESCE(locacao_qtd_meses, 0) AS meses, 0 AS icms
                FROM itens_cotacao
                WHERE cotacao_id = ? AND (tipo_operacao = 'Locação' OR (tipo_operacao IS NULL AND ? IN ('locação','locacao')))
                ORDER BY id
                """,
                (cot_id, (tipo_cotacao or '').lower(),)
            )
            itens_loc = c.fetchall() or []
            # Calcular total mensal (soma de valores mensais * qtd)
            total_mensal_locacao = 0.0
            try:
                for (nome_eq, qtd, valor_mensal, meses, _ic) in itens_loc:
                    qtd_num = float(qtd or 0)
                    vm_num = float(valor_mensal or 0)
                    total_mensal_locacao += (vm_num * qtd_num)
            except Exception:
                total_mensal_locacao = 0.0

            # Cabeçalho da tabela: usar largura total de borda a borda (x=5 até x=205 => 200mm)
            pdf.set_x(5)
            pdf.set_fill_color(50, 100, 150)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 11)
            # Larguras somando 200mm para encostar nas bordas (x=5 a 205)
            # Nome 90, Qtd 20, Valor Mensal 50, Período (meses) 40 => 200
            col_w = [90, 20, 50, 40]
            pdf.cell(col_w[0], 8, clean_text("Nome do Equipamento"), 1, 0, 'C', 1)
            pdf.cell(col_w[1], 8, clean_text("Qtd"), 1, 0, 'C', 1)
            pdf.cell(col_w[2], 8, clean_text("Valor Mensal"), 1, 0, 'C', 1)
            pdf.cell(col_w[3], 8, clean_text("Período (meses)"), 1, 1, 'C', 1)

            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 11)
            total_geral = 0.0
            for (nome_eq, qtd, valor_mensal, meses, icms_val) in itens_loc:
                qtd_num = float(qtd or 0)
                vm_num = float(valor_mensal or 0)
                meses_num = int(meses or 0)
                total_geral += (vm_num * meses_num * qtd_num)

                # Posição inicial da linha - garantir que comece na mesma posição do cabeçalho
                pdf.set_x(5)
                x0 = pdf.get_x()
                y0 = pdf.get_y()
                
                # Preparar textos para cada coluna
                nome_text = clean_text(str(nome_eq or ''))
                qtd_text = clean_text(f"{int(qtd_num)}")
                valor_text = clean_text(format_currency(vm_num))
                meses_text = clean_text(str(meses_num))
                
                # Calcular altura necessária para cada coluna
                line_height = 6
                max_lines = 1
                
                # Calcular linhas para cada coluna que pode ter texto longo
                nome_lines = calculate_text_lines(pdf, nome_text, col_w[0], line_height)
                valor_lines = calculate_text_lines(pdf, valor_text, col_w[2], line_height)
                
                max_lines = max(max_lines, nome_lines, valor_lines)
                
                # Altura final da linha
                h = max(line_height, max_lines * line_height)
                
                # Desenhar todas as células da linha na mesma altura
                pdf.set_xy(x0, y0)
                
                # Nome do equipamento (pode quebrar linha)
                pdf.multi_cell(col_w[0], line_height, nome_text, 1, 'L', 0)
                pdf.set_xy(x0 + col_w[0], y0)
                
                # Quantidade (centralizado)
                pdf.cell(col_w[1], h, qtd_text, 1, 0, 'C')
                
                # Valor mensal (alinhado à direita, pode quebrar linha)
                pdf.multi_cell(col_w[2], line_height, valor_text, 1, 'R', 0)
                pdf.set_xy(x0 + col_w[0] + col_w[1] + col_w[2], y0)
                
                # Período (centralizado)
                pdf.cell(col_w[3], h, meses_text, 1, 1, 'C')

            pdf.ln(6)
            pdf.set_x(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(200, 200, 200)
            pdf.set_text_color(0, 0, 0)
            # Usar a função format_currency para consistência
            pdf.cell(sum(col_w[:-1]), 10, clean_text("TOTAL GERAL:"), 1, 0, 'R', 1)
            pdf.cell(col_w[-1], 10, clean_text(format_currency(total_geral)), 1, 1, 'R', 1)

            # Condições comerciais imediatamente abaixo da tabela (Página 5)
            pdf.ln(6)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 6, clean_text("CONDIÇÕES COMERCIAIS:"), 0, 1, 'L')
            pdf.set_font("Arial", '', 11)
            try:
                # Verificar se é filial 1 pelo CNPJ (mais confiável)
                filial_is_1 = dados_filial.get('cnpj', '') == "10.644.944/0001-55"
            except Exception:
                filial_is_1 = False
            if filial_is_1:
                pdf.cell(0, 5, clean_text(f"Tipo de Frete: {tipo_frete if tipo_frete else 'FOB'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Condição de Pagamento: {condicao_pagamento if condicao_pagamento else 'A combinar'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Prazo de Entrega: {prazo_entrega if prazo_entrega else 'A combinar'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Moeda: {moeda if moeda else 'BRL (Real Brasileiro)'}"), 0, 1, 'L')
                if (tipo_cotacao or '').lower() in ('locação','locacao'):
                    pdf.cell(0, 5, clean_text('O faturamento será realizado através de "recibo de locação"'), 0, 1, 'L')
                # ICMS: Imposto Incluso apenas quando orçamento de Produtos (Filial 1) e NÃO for Locação
                tipos_itens_cc = [(it[1] or '') for it in itens_cotacao]
                is_produtos_cc = any(str(t).strip().lower() == 'produto' for t in tipos_itens_cc)
                is_locacao = (str(tipo_cotacao or '').lower() in ('locação','locacao'))
                if is_produtos_cc and not is_locacao:
                    pdf.cell(0, 5, clean_text("ICMS: Imposto Incluso"), 0, 1, 'L')
            else:
                pdf.cell(0, 5, clean_text(f"Tipo de Frete: {tipo_frete if tipo_frete else 'FOB'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Condição de Pagamento: {condicao_pagamento if condicao_pagamento else 'A combinar'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Prazo de Entrega: {prazo_entrega if prazo_entrega else 'A combinar'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Moeda: {moeda if moeda else 'BRL (Real Brasileiro)'}"), 0, 1, 'L')
                if (tipo_cotacao or '').lower() in ('locação','locacao'):
                    pdf.cell(0, 5, clean_text('O faturamento será realizado através de "recibo de locação"'), 0, 1, 'L')
            
            # Observações se houver
            if observacoes and observacoes.strip():
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 6, clean_text("OBSERVAÇÕES:"), 0, 1, 'L')
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 5, clean_text(observacoes))

            # =====================================================
            # PÁGINA 6: CONDIÇÕES DE PAGAMENTO e CONDIÇÕES COMERCIAIS
            # =====================================================
            pdf.add_page()
            pdf.set_y(35)

            # Título principal
            pdf.set_text_color(*pdf.baby_blue)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, clean_text("CONDIÇÕES DE PAGAMENTO:"), 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 11)

            # DDL dinâmico a partir de condicao_pagamento
            ddl_valor = None
            try:
                m = re.search(r"(\d)\s*DDL", (condicao_pagamento or ''), flags=re.IGNORECASE)
                if m:
                    ddl_valor = m.group(1)
            except Exception:
                pass
            raw_cp = (condicao_pagamento or '').strip()
            ddl_texto = raw_cp if raw_cp else (f"{ddl_valor} DDL" if ddl_valor else "30 dias")

            # Formatar valor mensal dinâmico (somatório mensal de equipamentos)
            def brl(v):
                try:
                    return ("R$ "  f"{v:,.2f}").replace(",", "@").replace(".", ",").replace("@", ".")
                except Exception:
                    return f"R$ {v:.2f}"
            valor_mensal_texto = brl(total_mensal_locacao)

            texto_pagamento = (
                "O preço inclui: Uso do equipamento listado no Resumo da Proposta Preço, partida técnica, serviços \n"
                "preventivos e corretivos, peças, deslocamento e acomodação dos técnicos, quando necessário. \n"
                "Pelos serviços objeto desta proposta, após a entrega do(s) equipamento(s) previsto neste contrato, o \n"
                f"CONTRATANTE deverá iniciar os respectivos pagamentos mensais referentes a locação no valor de {valor_mensal_texto} taxa fixa mensal, com vencimento à {ddl_texto}, Data esta que \n"
                "contará a partir da entrega do equipamento nas dependencias da contratante, ( COM \n"
                "FATURAMENTO ATRAVÉS DE RECIBO DE LOCAÇÃO)."
            )
            pdf.multi_cell(0, 6, clean_text(texto_pagamento))
            pdf.ln(6)

            # Título secundário
            pdf.set_text_color(*pdf.baby_blue)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, clean_text("CONDIÇÕES COMERCIAIS"), 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 11)

            condicoes_texto = (
                "- Os equipamentos objetos desta proposta serão fornecidos em caráter de Locação, cujas regras \n"
                "dessa modalidade estão descritas nos Termos e Condições Gerais de Locação de Equipamento, \n"
                "parte integrante deste documento.\n"
                "- Assim que V. Sa. receber os equipamentos e materiais, entrar em contato conosco para agendar \n"
                "o serviço de partida(s) técnica(s). \n"
                "- Validade do Contrato 5 anos \n"
                "- Informar sobre a necessidade de envio de documentos necessários para integração de técnicos. \n"
                "- Antes da compra do serviço, o cliente deve informar a World Comp, ou seu representante, se \n"
                "existem quaisquer riscos ou circunstâncias na sua operação que possam provocar acidentes \n"
                "envolvendo as pessoas que realizarão o serviço, assim como as medidas de proteção ou outras \n"
                "ações necessárias que a World Comp deva tomar a fim de reduzir tais riscos. \n"
                "- É de responsabilidade do cliente fornecer todas as condições necessárias para a execução das \n"
                "manutenções, tais como equipamentos para elevação/transporte interno, iluminação, água e local \n"
                "adequados para limpeza de resfriadores e demais componentes, mão de obra para eventuais \n"
                "necessidades, etc. \n"
                "- Os resíduos gerados pelas atividades da World Comp são de responsabilidade do cliente. \n"
                "- Todos os preços são para horário de trabalho definido como horário comercial, de segunda a \n"
                "sexta-feira, das 8h às 17h. \n"
                "- A World Comp não se responsabiliza perante o cliente, seus funcionários ou terceiros por perdas \n"
                "ou danos pessoais, diretos e indiretos, de imagem, lucros cessantes e perda econômica \n"
                "decorrentes dos serviços ora contratados ou de acidentes de qualquer tipo causados pelos \n"
                "equipamentos que sofrerão manutenção."
            )
            # Espaçamento leve entre tópicos: quebrar com linha em branco entre bullets
            for paragraph in condicoes_texto.split("- "):
                if paragraph.strip():
                    txt = ("- " + paragraph).strip()
                    pdf.multi_cell(0, 6, clean_text(txt))
                    pdf.ln(1)

            # =====================================================
            # PÁGINAS 7 A 13: TERMOS E CONDIÇÕES GERAIS (LOCAÇÃO)
            # =====================================================
            # Ajustar margens para corpo do contrato (mais afastado do cabeçalho/rodapé)
            pdf.set_top_margin(77)
            pdf.set_auto_page_break(auto=True, margin=35)
            pdf.add_page()
            pdf.set_y(77)
            imagem_p7 = None
            try:
                # Reaproveitar a imagem do primeiro item de locação, se houver
                c.execute("SELECT locacao_imagem_path FROM itens_cotacao WHERE cotacao_id=? AND (tipo_operacao='Locação' OR tipo_operacao IS NULL) AND locacao_imagem_path IS NOT NULL AND TRIM(locacao_imagem_path)<>'' ORDER BY id LIMIT 1", (cot_id,))
                row_img = c.fetchone()
                if row_img and row_img[0] and os.path.exists(row_img[0]):
                    imagem_p7 = row_img[0]
                elif locacao_imagem_path_db and os.path.exists(locacao_imagem_path_db):
                    imagem_p7 = locacao_imagem_path_db
            except Exception:
                pass
            if imagem_p7:
                # Padronizar tamanho para todas as imagens (altura ajustada para 3.5)
                w, h = 70 * 1.3, 24 * 1.3 * 3.5
                x = (210 - w) / 2
                y = 77
                pdf.image(imagem_p7, x=x, y=y, w=w, h=h)
                pdf.set_y(y + h + 8)
            else:
                pdf.set_y(82)
            pdf.set_text_color(*pdf.baby_blue)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, clean_text("TERMOS E CONDIÇÕES GERAIS DE LOCAÇÃO DE EQUIPAMENTO"), 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 11)

            # Montar texto do contrato com substituições dinâmicas
            locadora_nome = dados_filial.get('nome', 'WORLD COMP')
            locadora_endereco = dados_filial.get('endereco', '')
            locadora_cnpj = dados_filial.get('cnpj', 'N/A')
            locataria_nome = cliente_nome
            proposta_num = numero_proposta
            proposta_data = format_date(data_criacao)

            intro_dyn = (
                f"Pelo presente instrumento particular,\n"
                f"LOCADORA: {locadora_nome}, com sede em {locadora_endereco}, inscrita no CNPJ/MF sob nº {locadora_cnpj}.\n"
                f"LOCATÁRIA: {locataria_nome}\n"
                f"{locadora_nome} e CONTRATANTE serão referidas individualmente como Parte e, em conjunto, Partes.\n"
                f"As partes qualificadas, por seus representantes legais ao final assinados, têm entre si justo e acertado os presentes Termos e Condições Gerais de Locação de Equipamento, denominado simplesmente Contrato, que se regerá pelas cláusulas e condições seguintes, com efeitos a partir da data {proposta_data} da Proposta Comercial nº {proposta_num}.\n\n"
            )

            contrato_base = (
                "1 -CLÁUSULA PRIMEIRA – DO OBJETO\n"
                "O presente Contrato consiste na locação do(s) Equipamento(s) mencionado(s) NA Proposta Comercial Preço anexa, denominados simplesmente Equipamento(s), de propriedade da World Comp, como parte da Locação de Compressores oferecida ao CONTRATANTE, para uso em suas atividades industriais, sendo proibido o uso para outros fins.\n"
                "Caberá ao CONTRATANTE a obrigação de manter o(s) Equipamento(s) em suas dependências, em endereço descrito como sua sede no preâmbulo do presente instrumento, obrigando-se a solicitar previamente e por escrito à World Comp eventual alteração de sua localização, sob pena de expressa e inequívoca violação do presente instrumento, o que autorizará a incidência de multa de 10% (dez por cento), em caráter não compensatório, sobre o valor do Contrato, bem como facultará à World Comp a rescisão do presente instrumento, com a imediata retomada liminar do(s) Equipamento(s).\n"
                "Referida Proposta Comercial dispõe as descrições e especificações técnicas do(s) equipamento(s) locado(s), bem como as condições comerciais para a presente locação.\n"
                "Caso ocorra qualquer alteração relevante nas condições de operação dos Equipamento(s) (tais como condições de operação, escopo do trabalho, ou ainda nas condições ambientais, qualidade do ar, ventilação, temperatura, fornecimento de água e energia elétrica) ou do local ou regime de trabalho do equipamento, a World Comp deverá ser notificada previamente, por escrito.\n"
                "Nessa hipótese, o presente Contrato deverá ser revisto pelas Partes, a fim de adaptá-lo à nova realidade, assumindo a CONTRATANTE integral responsabilidade antes da avaliação pela World Comp das novas condições e/ou da celebração de termo aditivo que reflita as novas condições.\n"
                "Estão incluídos no objeto deste instrumento:\n"
                "Equipamento(s): Equipamentos listados de acordo com relação descrita na Proposta Comercial Preço.\n"
                "Partida técnica dos Equipamento(s), sendo obrigatório sua realização somente, e exclusivamente, por funcionários especializados da World Comp, em horário comercial, sendo de responsabilidade do CONTRATANTE a instalação do(s) equipamento(s) contratados de acordo com o manual de instalação.\n"
                "Peças, componentes e insumos específicos para cada visita de manutenção preventiva ou corretiva\n"
                "A World Comp, reserva o direito realizar as intervenções técnicas que entender necessárias para o bom funcionamento e manutenção do(s) Equipamento(s), incluindo substituição de peças e produtos utilizados nas manutenções preventivas e/ou corretivas, em especial alterando o lubrificante utilizado conforme recomendação para melhor desempenho, consumo energético e extensão da vida útil do(s) Equipamento(s) e seus componentes.\n"
                "Estão excluídos do objeto deste instrumento:\n"
                "Atendimento para manutenções preventivas e/ou corretivas fora do horário comercial entendido como das 8:00h às 17:00h, de segunda a sexta-feira, salvo especificação em contrário na Proposta.\n"
                "Custos com componentes ou peças que tenham sido danificados por negligência, mau uso, falha operacional ou elétrica da contratante.\n"
                "O presente Contrato, alcança não apenas o(s) Equipamento(s) já relacionados na Proposta Comercial, mas também todos os demais que poderão vir a ser enviados, através de solicitação do CONTRATANTE, conforme as respectivas propostas comerciais futuras, e por meio de Notas Fiscais de Remessa emitidas pela World Comp e termos aditivos a serem celebrados entre as Partes.\n"
                "– CLÁUSULA SEGUNDA – DA VIGÊNCIA EXECUÇÃO\n"
                "O presente Contrato terá o seu início, com efeitos a partir da data de assinatura desta Proposta Comercial nº {num} de disponibilização do(s) Equipamento(s) pela World Comp, vigerá pelo prazo definido na Proposta Comercial, sendo renovado automaticamente ao final do contrato até que haja manifestação das partes.\n"
                "Quando do encerramento do presente Contrato o CONTRATANTE se compromete a devolver o(s) Equipamento(s) nas mesmas condições de uso e manutenção em que entregue(s), salvo desgaste natural do tempo, conforme condições normais e aprovada de uso.\n"
                " No término deste Contrato será realizada uma nova inspeção em conjunto pelas Partes, da qual será elaborado um relatório, que deverá ser assinado por representantes de ambas as Partes, detalhando as condições do(s) Equipamento(s), para devolução.\n"
                "Se na inspeção conjunta, forem constatados que o(s) Equipamento(s), por razões técnicas ou mecânicas, não se encontra(m) dentro das condições mínimas exigidas para o seu funcionamento e/ou operação, em decorrência de mau uso ou quaisquer atos, fatos ou danos imputáveis ou causados pelo CONTRATANTE, este arcará com os custos de reparo do(s) Equipamento(s).\n"
                "Não obstante, será de responsabilidade do CONTRATANTE qualquer manutenção corretiva, cuja necessidade seja identificada durante a vigência contratual, em decorrência de negligência ou má operação do(s) Equipamento(s), a qual será cobrada à parte, mediante apresentação de orçamento pela World Comp, em cada caso.\n"
                "Durante o período em que permanecer na posse do(s) Equipamento(s), o representante legal do CONTRATANTE, qualificado abaixo e que assina este documento, ficará como depositário fiel do(s) Equipamento(s).\n"
                "3- CLÁUSULA TERCEIRA – DAS CONDIÇÕES DE PAGAMENTO\n"
                "3.1 O CONTRATANTE pagará à World Comp o valor descrito e em conformidade com as condições constantes da Proposta Comercial.\n"
                "3.1.2 A CONTRATANTE efetuará os pagamentos através de boleto bancário ou depósito em conta, servindo os respectivos comprovantes de pagamento claramente identificados como prova de quitação, salvo se previsto de forma contrária na Proposta.\n"
                "3.2 A ausência de pagamento na data estipulada, inclusive na hipótese de não recebimento do boleto bancário, observado o disposto na Cláusula acima, implicará na incidência de multa moratória de 2% (doia por cento) sobre o valor do débito, além de juros de 1% (um por cento) ao mês, calculados 'pro rata dia', a partir do dia seguinte ao do vencimento.\n"
                "3.2.1 Caso o atraso dos pagamentos devidos pelo CONTRATANTE prolongue-se por prazo superior a 03 (três) meses consecutivos, a World Comp poderá encerrar o Contrato imediatamente.\n"
                "3.3 O preço mencionado na proposta comercial será reajustado automaticamente a cada 12 (doze) meses de vigência contratual ou em períodos inferiores, caso a legislação da época assim permita.\n"
                "3.4 O preço ora estabelecido está sujeito à renegociação, na hipótese de qualquer mudança nas condições operacionais dos equipamentos sob contrato.\n"
                "4- CLÁUSULA QUARTA – DAS RESPONSABILIDADES DA WORLD COMP\n"
                "4.1 A partida técnica, ou seja, acionar o funcionamento do(s) Equipamento(s) no início da locação, bem como o seu desligamento no término deste Contrato\n"
                "4.1.1 Contatar o CONTRATANTE previamente à data de cada visita.\n"
                "4.1.2 Fornecer ao CONTRATANTE, após cada visita, ordem de serviço que deverá ser assinada por esta., relatando o estado do(s) Equipamento(s) após as visitas realizadas e incluindo a lista de peças aplicadas, bem como relação das intervenções realizadas.\n"
                "4.1.3 Enviar técnicos para as manutenções munidos de equipamentos de proteção pessoal, trajando uniformes devidamente identificados.\n"
                "4.1.4 Informar a necessidade de eventuais manutenções corretivas necessárias à boa operação do compressor, iniciando a execução de tais atendimentos, se aplicável.\n"
                "4.2 Não obstante os esforços da World Comp, fica desde já estabelecido que o atendimento aqui disposto não configura a imediata solução de eventual problema, já que somente durante o atendimento corretivo a World Comp avaliará necessidade de utilização/substituição de peça(s) a(s) qual(is) poderá(ão) não estar disponível(is) no momento do atendimento.\n"
                "4.3 Em caso de morosidade superior a 1 (uma) hora entre a chegada ao CONTRATANTE e a liberação do técnico da World Comp para executar as intervenções programadas ou, ainda, não disponibilidade do(s) Equipamento(s) à World Comp, os custos da espera ou reprogramação da visita serão repassados ao CONTRATANTE, conforme tabela vigente de preços praticados.\n"
                "5 - CLÁUSULA QUINTA - DAS RESPONSABILIDADES DO CONTRATANTE\n"
                "5.1 Solicitar a partida técnica após a instalação do(s) Equipamento(s).\n"
                "5.1.1 Utilizar o(s) Equipamento(s) para os seus estritos fins, obedecendo às recomendações fornecidas pela World Comp, sob pena de, em assim não procedendo, incorrer nos ônus previstos no artigo 570 do novo Código Civil e demais cominações contratuais e legais.\n"
                "5.1.2Manter e guardar o(s) Equipamento(s) como se seu fosse(m), desde a sua [retirada | entrega] até sua efetiva devolução a World Comp, ficando responsável pela sua conservação e obrigando-se a devolvê-lo em perfeito estado, respeito desgastes naturais de uso, limpo e nas condições de uso que o encontrou quando da retirada, sem qualquer dano ou avaria, mesmo se provocados por incêndios, roubo, uso indevido ou qualquer outra coisa, quer por sua culpa, quer por culpa de terceiros, obrigando-se ao ressarcimento dos danos causados e ficando responsável ainda pela sua conservação e contratação de seguro, nos termos da Cláusula Sexta, abaixo.\n"
                "5.1.3Devolver o(s) Equipamento(s) tão logo rescindido de direito o presente Contrato, incorrendo, se assim não o fizer, no arbitramento de aluguéis e demais consectários a que alude o artigo 575 do Código Civil.\n"
                "5.1.4 Manter, na qualidade de única responsável pelo(s) Equipamento(s), a World Comp isenta de todas e quaisquer reclamações, reivindicações, responsabilidades, perdas, danos, custos e despesas que possam a ela serem imputados por terceiros, decorrentes da locação ora ajustada, incluindo empregados e terceiros sob a responsabilidade do CONTRATANTE. Cabe ao CONTRATANTE, informar imediatamente e por escrito à World Comp quaisquer reclamações dessa natureza, contra ele próprio ou contra a World Comp.\n"
                "5.1.5 Indenizar a World Comp , por qualquer perda ou dano causado ao(s) Equipamento(s), pelo valor total de cada componente eventualmente perdido ou avariado.\n"
                "5.1.6 Realizar a inspeção/manutenção diária e semanal (8 e 40 horas) da(s) máquina(s), conforme indicado Manual de Instruções.\n"
                "5.1.7 Utilizar somente lubrificantes, filtros de ar e de óleo, separador de óleo – quando aplicável, e peças originais, genuínas ou aprovadas pela World Comp.\n"
                "5.1.8 Disponibilizar ventilação adequada ao redor do(s) Equipamento(s) (de acordo com recomendações da World Comp e limpar regulamente o(s) Equipamento(s)\n"
                "5.1.9 Notificar a World Comp imediatamente e por escrito sobre quaisquer mudanças na operação ou nas condições do local e de quaisquer problemas no funcionamento ou falhas que possam influenciar o funcionamento apropriado do(s) Equipamento(s).\n"
                "5.1.10Permitir que a World Comp tenha acesso livre e integral aos equipamentos durante o horário comercial normal a fim de realizar visitas de serviço programadas, assegurando ainda, o direito de vistoria a qualquer momento dentro do horário comercial normal, independente de prévio aviso.\n"
                "5.1.11 Tomar as medidas necessárias recomendadas pela World Comp a título de reparo.\n"
                "5.1.12 Prestar assistência médica gratuita ao pessoal da World Comp nas mesmas condições que a oferecida aos funcionários do CONTRATANTE, em caso de acidente ou emergência dentro de suas dependências. Se o acidente ou emergência exigir maiores cuidados ou tratamentos médicos, a(s) pessoa(s) acidentada(as) deverá(ão) ser conduzida(s) ao centro médico mais próximo.\n"
                "5.1.13 Fornecer todas as condições necessárias para a execução das manutenções, tais como equipamentos para elevação/transporte interno, iluminação, água e local adequados para limpeza de resfriadores e demais componentes, mão de obra para eventuais necessidades, etc.\n"
                "5.1.14 Fornecer toda a instalação elétrica de acordo com manual de instruções do equipamento, e seguir as recomendações para a sala de compressores e o meio ambiente.\n"
                "5.1.15 Fornecer edificações ou modificações para a sala de compressores, dutos para cabos elétricos e outros fins, bem como instalações de água se necessário, e todas as instalações diferentes do sistema de ar comprimido.\n"
                "5.1.16Preparar todas as instalações de tubulação necessária para a passagem de ar comprimido a partir da sala do compressor para o local de consumo.\n"
                "5.1.17 Não realizar qualquer intervenção no equipamento sem prévio consentimento da World Comp, por escrito.\n"
                "5.1.18 Manter registro atualizado das ocorrências com o(s) Equipamento(s)\n"
                "5.1.19 Solicitar formalmente as manutenções corretivas à World Comp e confirmar, antecipadamente, que o equipamento está disponível para a realização da manutenção preventiva na data combinada, sob pena de se caracterizar mau uso do(s) Equipamento(s), sendo permitido apenas um aditamento de manutenção já agendada, observado período máximo de adiamento de 45 (quarenta e cinco) dias. A hipótese de adiamento de qualquer manutenção por indisponibilidade do(s) Equipamento(s) por prazo superior a 45 (quarenta e cinco) dias facultará à World Comp a rescisão do presente instrumento, com a imediata retomada liminar do(s) Equipamento(s).\n"
                "5.1.20 Efetivar o pagamento devido na Proposta Comercial, nos termos da Cláusula 3ª do presente Contrato.\n"
                "5.1.21 Em caso de acidente de qualquer natureza envolvendo o(s) Equipamento(s), o CONTRATANTE é responsável por fornecer notificação imediata e escrita à World Comp, em prazo não superior a 24 (vinte e quatro) horas após o evento.\n"
                "6 - CLÁUSULA SEXTA – SEGURO\n"
                "6.1 O CONTRATANTE deverá providenciar o seguro do(s) Equipamento(s), de modo a cobrir o seu valor de propriedade, conforme estipulado nas respectivas Notas Fiscais de Remessa do(s) Equipamento(s), no qual a World Comp é a única beneficiária, abrangendo todos os riscos, inclusive contra terceiros, cobrindo, mas não se limitando a roubo, furto, incêndio, riscos de explosão, raios e inundações.\n"
                "6.1.1 Caso o CONTRATANTE possua uma apólice coletiva de seguros que cubra todo o seu parque de máquinas em operação em seu estabelecimento, deverá incluir o(s) referido(s) Equipamento(s) objeto deste Contrato, na cobertura deste seguro.\n"
                "6.1.2 Caso o CONTRATANTE não efetue o seguro na forma aqui estabelecida, assumirá total responsabilidade pelos riscos inerentes à operação do(s) Equipamento(s), e deverá indenizar integralmente a World Comp pelos danos causados ao mesmo.\n"
                "6.1.3 A vigência do seguro deverá iniciar-se no primeiro dia posterior à liberação do(s) Equipamento(s) no local de operação, devendo o CONTRATANTE entregar uma cópia da apólice correspondente, tão logo a tenha disponível.\n"
                "7 – CLÁUSULA SÉTIMA – RESCISÃO\n"
                "7.1 As partes, desde já, manifestam sua ciência e concordância de que em caso de solicitação de resilição unilateral do presente, do contratado pelo CONTRATANTE, durante os três (03) primeiros meses de vigência, este arcará com multa não-compensatória a ser calculada da seguinte maneira: Valor da multa a a ser pago pela CONTRATANTE = Valor equivalente ao custo de 01 mês de locação.\n"
                "7.1.1 Transcorrido os três (03) primeiros meses iniciais de vigência, o CONTRATANTE poderá resilir o presente Contrato desde que informe a World Comp com antecedência mínima de 30 (trinta) dias, através de notificação por escrito, não cabendo qualquer indenização ou multa.\n"
                "7.1.2 A resilição unilateral por denúncia da World Comp independerá de decurso de qualquer prazo, devendo apenas observar a antecedência mínima de 30 (trinta) dias, através de notificação por escrito, não cabendo qualquer indenização ou multa.\n"
                "7.2 As Partes poderão ainda considerar rescindido de pleno direito o presente Contrato, com imediata reintegração na posse do equipamento, mediante comunicação expressa, nos seguintes casos\n"
                "7.2.1 Se o CONTRATANTE sublocar, penhorar ou repassar qualquer direito relativo ao(s) Equipamento(s) para terceiros, sem aprovação prévia e por escrito da World Comp..\n"
                "7.2.2 Se o CONTRATANTE não efetuar o seguro do(s) Equipamento(s) na forma estabelecida na Cláusula Sexta.\n"
                "7.2.3 Se o CONTRATANTE não utilizar corretamente o(s) Equipamento(s) e/ou não permitir a realização de intervenções de manutenção, de forma a mantê-lo(s) em boas condições de operação e funcionamento, conforme avaliação feita de comum acordo entre as Partes.\n"
                "7.2.4 Se algum embargo, execução ou outro processo legal for aplicado contra o(s) Equipamento(s) ou parte dele ou ainda, contra quaisquer instalações onde estiver sendo usado.\n"
                "7.2.5 Se o CONTRATANTE ceder ou transferir os direitos e obrigações oriundas do presente contrato para terceiros, sem a prévia e expressa autorização por parte da World Comp.\n"
                "7.2.6 Se qualquer uma das Partes entrar em liquidação ou falência, convocar credores ou apontar um curador com respeito a qualquer dos seus empreendimentos ou bens.\n"
                "7.3 Acordam as Partes, ainda, na possibilidade de busca e apreensão do(s) Equipamento(s) de forma imediata, mediante envio de notificação extrajudicial da World Comp ou protesto deste título.\n"
                "7.4 Caso o(s) Equipamento(s) não seja(m) localizado(s) pela World Comp, esta poderá, independentemente de qualquer aviso ou notificação, cobrá-lo por via judicial, pleiteando o valor constante da(s) Nota(s) Fiscal(is) de Remessa, custas e outras despesas, além de honorários advocatícios desde já arbitrados em 20% (vinte por cento) sobre o valor pleiteado.\n"
                "8- CLÁUSULA OITAVA – CASO FORTUITO OU FORÇA MAIOR\n"
                "8.1 As Partes não responderão pelo eventual descumprimento de suas obrigações contratuais, se este resultar de caso fortuito ou força maior, nos termos do art. 393 do Código Civil Brasileiro.\n"
                "a) Comunicar o fato à outra Parte, por escrito, no prazo de 10 (dez) dias da sua ocorrência ou de seu início, fornecendo-lhe detalhes sobre o evento.\n"
                "b) Comprovar, perante a outra Parte, que o fato alegado realmente contribuiu para o descumprimento da obrigação.\n"
                "8.3 Não poderá invocar a exceção de força maior ou caso fortuito a Parte que houver agido com culpa, concomitante ou anteriormente ao evento.\n"
                "9– CLÁUSULA NONA – DA RESPONSABILIDADE TRABALHISTA\n"
                "10.1Cada Parte será única e exclusivamente responsável pelas obrigações decorrentes dos acordos de trabalho de seus empregados, inclusive por eventuais inadimplementos trabalhistas em que possa incorrer, não podendo ser arguida solidariamente entre as Partes nem responsabilidade subsidiária, não existindo, por conseguinte, vinculação empregatícia entre os empregados das Partes, sendo cada uma responsável pelos salários, encargos, refeições e transporte de seus funcionários/prepostos.\n"
                "10- CLÁUSULA DÉCIMA – DAS DISPOSIÇÕES GERAIS\n"
                "11.1 Os termos e condições deste Contrato e dos demais documentos aqui presentes constituirão o completo acordo e entendimento entre as Partes e substituirão quaisquer comunicações prévias entre as partes, sejam elas verbais ou por escrito, incluindo qualquer acordo ou entendimento, variando ou estendendo o mesmo assunto.\n"
                "11.2 Qualquer alteração no presente Contrato deverá ser feita mediante termo aditivo assinado pelas Partes.\n"
                "11.3 Caso quaisquer das disposições deste Contrato sejam ou venham a se tornar legalmente ineficazes ou inválidas, a validade e o efeito das disposições restantes não serão afetados.\n"
                "11.4 Não haverá responsabilidade da World Comp por perda de produção, perda de lucro, perda de uso, perda de contrato ou qualquer outra perda consequente ou indireta que seja.\n"
                "11.5 O presente Contrato não estabelece entre as Partes qualquer forma de sociedade, associação, relação de emprego, responsabilidade solidária e conjunta, nem poderá ser entendido como mandato ou agenciamento.\n"
                "11.6 A tolerância por qualquer das Partes, no que tange ao cumprimento das obrigações da outra Parte, não será considerada novação ou perdão, permanecendo as cláusulas deste Contrato em pleno vigor e efeito, na forma aqui prevista.\n"
                "11.7 As Partes contratantes declaram, sob as penas da Lei, que os signatários do presente instrumento são seus representantes/procuradores legais, devidamente constituídos na forma dos respectivos atos constitutivos, com poderes para assumir as obrigações ora contraídas.\n"
                "11.8 Todas as correspondências, notificações e comunicações permitidas ou exigidas entre as Partes deverão ser feitas por escrito, por meio de carta protocolada ou qualquer outro meio idôneo que confirme o recebimento (correio eletrônico,e-mail etc.), devendo ser encaminhadas aos endereços constantes do preâmbulo desse instrumento, sendo que, caso, no curso do presente instrumento ocorra modificação nos endereços de quaisquer das partes, a parte que tiver a mudança de endereço deverá comunicar a outra parte imediatamente.\n"
                "11.9 O presente Contrato e suas obrigações vinculam as Partes, seus herdeiros e sucessores a qualquer título.\n"
                "11.10 O presente Contrato e os direitos e obrigações dele decorrentes não poderão ser cedidos, transferidos ou sub-rogados por quaisquer das partes sem o prévio consentimento por escrito da outra.\n"
                "11– CLÁUSULA DÉCIMA PRIMEIRA – FORO\n"
                "Para dirimir definitivamente quaisquer dúvidas decorrentes do presente ajuste, as partes elegem, de comum acordo, o foro de São Bernardo do Campo, São Paulo, com renúncia expressa de qualquer outro, por mais especial que seja.\n"
            ).format(num=numero_proposta)

            # Substituir 'World Comp' pelo nome da filial (case-insensitive)
            contrato_texto = re.sub(r"(?i)world\s*comp", locadora_nome, contrato_base)

            # Concatenar introdução dinâmica + contrato
            full_text = intro_dyn + contrato_texto

            # Renderizar texto com quebras automáticas até o fim (páginas seguintes)
            pdf.multi_cell(0, 5, clean_text(full_text))
            # Encerramento e assinaturas: aproveitar espaço restante da página atual antes de abrir nova
            left_margin = 15
            right_margin = 15
            usable_width = 210 - left_margin - right_margin
            # Se não houver espaço suficiente, criar nova página; caso contrário, continuar na mesma
            y_current = pdf.get_y()
            if y_current + 80 > 280:  # precisa de ~80mm para o bloco de encerramento
                pdf.add_page()
                pdf.set_y(35)
            else:
                pdf.set_y(max(y_current + 8, 35))
            pdf.set_x(left_margin)
            pdf.set_text_color(*pdf.baby_blue)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(usable_width, 8, clean_text("ENCERRAMENTO E ASSINATURAS"), 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 11)
            texto_final = (
                "Para dirimir definitivamente quaisquer dúvidas decorrentes do presente ajuste, as partes elegem, de comum acordo, o foro de São Bernardo do Campo, São Paulo, com renúncia expressa de qualquer outro, por mais especial que seja. \n\n"
                "E, por estarem assim justas e contratadas, as partes assinam o presente instrumento em 02 (duas) vias de igual teor e para os mesmos fins e efeitos de direito, juntamente com as 02 (duas) testemunhas abaixo."
            )
            pdf.set_x(left_margin)
            pdf.multi_cell(usable_width, 6, clean_text(texto_final))
            pdf.ln(8)
            data_long = format_date_long_pt(data_criacao)
            pdf.set_x(left_margin)
            pdf.cell(usable_width, 6, clean_text(f"São Bernardo do Campo, {data_long}."), 0, 1, 'L')
            pdf.ln(16)
            # Linhas e labels de assinatura com margens
            col_w = (usable_width - 10) / 2
            pdf.set_x(left_margin)
            pdf.cell(col_w, 6, clean_text("______________________________________"), 0, 0, 'L')
            pdf.cell(10, 6, "", 0, 0)
            pdf.cell(col_w, 6, clean_text("______________________________________"), 0, 1, 'L')
            # Contratante / Contratada com quebras
            x_left = left_margin
            y_row = pdf.get_y()
            pdf.set_xy(x_left, y_row)
            pdf.multi_cell(col_w, 6, clean_text(f"Contratante: {cliente_nome}"), 0, 'L')
            height_left = pdf.get_y() - y_row
            x_right = left_margin + col_w + 10
            pdf.set_xy(x_right, y_row)
            pdf.multi_cell(col_w, 6, clean_text(f"Contratada: {dados_filial.get('nome', '')}"), 0, 'L')
            height_right = pdf.get_y() - y_row
            row_h = max(height_left, height_right)
            pdf.set_y(y_row + row_h)
            cnpj_cli = format_cnpj(cliente_cnpj) if cliente_cnpj else ""
            y_row = pdf.get_y()
            pdf.set_xy(x_left, y_row)
            pdf.multi_cell(col_w, 6, clean_text(f"CNPJ: {cnpj_cli}"), 0, 'L')
            height_left = pdf.get_y() - y_row
            pdf.set_xy(x_right, y_row)
            pdf.multi_cell(col_w, 6, clean_text(f"CNPJ: {dados_filial.get('cnpj', '')}"), 0, 'L')
            height_right = pdf.get_y() - y_row
            row_h = max(height_left, height_right)
            pdf.set_y(y_row + row_h)
            pdf.ln(16)
            # Testemunhas
            for i in range(2):
                pdf.set_x(left_margin)
                pdf.cell(col_w, 6, clean_text("______________________________________"), 0, 0, 'L')
                pdf.cell(10, 6, "", 0, 0)
                pdf.cell(col_w, 6, clean_text("_______________________________________"), 0, 1, 'L')
                pdf.set_x(left_margin)
                pdf.cell(col_w, 6, clean_text("Nome:"), 0, 0, 'L')
                pdf.cell(10, 6, "", 0, 0)
                pdf.cell(col_w, 6, clean_text("Nome:"), 0, 1, 'L')
                pdf.set_x(left_margin)
                pdf.cell(col_w, 6, clean_text("CPF:"), 0, 0, 'L')
                pdf.cell(10, 6, "", 0, 0)
                pdf.cell(col_w, 6, clean_text("CPF:"), 0, 1, 'L')
        else:
            # Compra: manter comportamento existente
            if esboco_servico:
                pdf.add_page()
                # Primeira página da seção: mais alto; complementares: afastar ainda mais do cabeçalho
                pdf.begin_section('esboco', top_first=35, bottom_first=40, top_cont=130, bottom_cont=40, title="ESBOÇO DO SERVIÇO A SER EXECUTADO")
                pdf.set_y(35)
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 8, clean_text("ESBOÇO DO SERVIÇO A SER EXECUTADO"), 0, 1, 'L')
                pdf.ln(5)
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 6, clean_text(esboco_servico))
                # Restaurar margens padrão
                pdf.end_section()
        
        # =====================================================
        # PÁGINA 5: RELAÇÃO DE PEÇAS A SEREM SUBSTITUÍDAS
        # =====================================================
        if relacao_pecas_substituir and not ((tipo_cotacao or '').lower() in ('locação','locacao')):
            pdf.add_page()
            pdf.begin_section('relacao', top_first=35, bottom_first=40, top_cont=130, bottom_cont=40, title="RELAÇÃO DE PEÇAS A SEREM SUBSTITUÍDAS")
            pdf.set_y(35)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 8, clean_text("RELAÇÃO DE PEÇAS A SEREM SUBSTITUÍDAS"), 0, 1, 'L')
            pdf.ln(5)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 6, clean_text(relacao_pecas_substituir))
            pdf.end_section()

        # =====================================================
        # PÁGINAS SEGUINTES: DETALHES DA PROPOSTA (somente não-locação)
        # =====================================================
        if not ((tipo_cotacao or '').lower() in ('locação','locacao')):
            pdf.add_page()
            # Dados da proposta
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, clean_text(f"PROPOSTA Nº {numero_proposta}"), 0, 1, 'L')
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 6, clean_text(f"Data: {format_date(data_criacao)}"), 0, 1, 'L')
            pdf.cell(0, 6, clean_text(f"Responsável: {responsavel_nome}"), 0, 1, 'L')
            pdf.cell(0, 6, clean_text(f"Telefone Responsável: {format_phone(responsavel_telefone)}"), 0, 1, 'L')
            pdf.ln(10)

            # Dados do cliente
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 6, clean_text("DADOS DO CLIENTE:"), 0, 1, 'L')
            pdf.set_font("Arial", '', 11)
            
            cliente_nome_display = cliente_nome_fantasia if cliente_nome_fantasia else cliente_nome
            pdf.cell(0, 5, clean_text(f"Empresa: {cliente_nome_display}"), 0, 1, 'L')
            if cliente_cnpj:
                pdf.cell(0, 5, clean_text(f"CNPJ: {format_cnpj(cliente_cnpj)}"), 0, 1, 'L')
            if contato_nome and contato_nome != "Não informado":
                pdf.cell(0, 5, clean_text(f"Contato: {contato_nome}"), 0, 1, 'L')
            pdf.ln(5)

            # Dados do compressor
            if modelo_compressor or numero_serie_compressor:
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 6, clean_text("DADOS DO COMPRESSOR:"), 0, 1, 'L')
                pdf.set_font("Arial", '', 11)
                if modelo_compressor:
                    pdf.cell(0, 5, clean_text(f"Modelo: {modelo_compressor}"), 0, 1, 'L')
                if numero_serie_compressor:
                    pdf.cell(0, 5, clean_text(f"Nº de Série: {numero_serie_compressor}"), 0, 1, 'L')
                pdf.ln(5)

            # Descrição - GARANTIR que não seja vazia
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 6, clean_text("DESCRIÇÃO DO SERVIÇO:"), 0, 1, 'L')
            pdf.set_font("Arial", '', 11)
            # Definir texto padrão conforme tipo (Produtos x Serviços)
            try:
                tipos_itens_desc = [(it[1] or '') for it in (itens_cotacao or [])]
                is_produtos_desc = any(str(t).strip().lower() == 'produto' for t in tipos_itens_desc)
            except Exception:
                is_produtos_desc = False
            default_desc = "Fornecimento de peças para compressores" if is_produtos_desc else "Fornecimento de serviços para compressor"
            descricao_final = descricao_atividade if descricao_atividade and descricao_atividade.strip() else default_desc
            pdf.multi_cell(0, 5, clean_text(descricao_final))
            pdf.ln(10)

            # Relação de Peças - GARANTIR que seja exibida corretamente
            if relacao_pecas and relacao_pecas.strip():
                relacao_sem_prefixo = relacao_pecas.replace("Serviço: ", "").replace("Produto: ", "").replace("Kit: ", "")
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 6, clean_text("RELAÇÃO DE PEÇAS A SEREM SUBSTITUÍDAS:"), 0, 1, 'L')
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 5, clean_text(relacao_sem_prefixo))
                pdf.ln(5)

            # ITENS DA PROPOSTA - CORRIGIDO (regras ICMS por tipo/filial)
            # =============================
            if itens_cotacao:
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 8, clean_text("ITENS DA PROPOSTA"), 0, 1, 'C')
                pdf.ln(5)

                # Determinar se é orçamento de produtos (há item tipo Produto)
                tipos_itens = [(it[1] or '') for it in itens_cotacao]
                is_produtos = any(str(t).strip().lower() == 'produto' for t in tipos_itens)
                is_servicos = any(str(t).strip().lower() == 'serviços' for t in tipos_itens)
                
                # Filial 1 não mostra ICMS na tabela; Filial 2 mostra ICMS para Produtos e ICMS+ISS para Serviços
                try:
                    filial_is_1 = (int(filial_id or 0) == 1)
                except Exception:
                    filial_is_1 = False
                if not filial_is_1:
                    filial_is_1 = (str(dados_filial.get('cnpj', '')) == "10.644.944/0001-55")
                
                show_icms_column = is_produtos and not filial_is_1
                show_icms_iss_columns = is_servicos and not filial_is_1
                
                # Larguras com total exato de 200mm (de borda a borda; início em x=5)
                if show_icms_iss_columns:
                    # Para Serviços na Filial 2: Item 15, Descrição 70, Qtd 15, Valor Unit 25, ICMS 20, ISS 20, Total 35 => 200
                    col_widths = [15, 70, 15, 25, 20, 20, 35]
                elif show_icms_column:
                    # Para Produtos na Filial 2: Item 15, Descrição 88, Qtd 15, Valor Unit 30, ICMS 22, Total 30 => 200
                    col_widths = [15, 88, 15, 30, 22, 30]
                else:
                    # Sem ICMS/ISS: Item 15, Descrição 115, Qtd 15, Valor Unit 25, Total 30 => 200
                    col_widths = [15, 115, 15, 25, 30]
                
                # Cabeçalho da tabela - posicionando nas bordas
                pdf.set_x(5)  # Margem esquerda na borda interna
                pdf.set_fill_color(50, 100, 150)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(col_widths[0], 8, clean_text("Item"), 1, 0, 'C', 1)
                pdf.cell(col_widths[1], 8, clean_text("Descrição"), 1, 0, 'L', 1)
                pdf.cell(col_widths[2], 8, clean_text("Qtd."), 1, 0, 'C', 1)
                pdf.cell(col_widths[3], 8, clean_text("Valor Unit."), 1, 0, 'R', 1)
                if show_icms_iss_columns:
                    pdf.cell(col_widths[4], 8, clean_text("ICMS"), 1, 0, 'R', 1)
                    pdf.cell(col_widths[5], 8, clean_text("ISS"), 1, 0, 'R', 1)
                    pdf.cell(col_widths[6], 8, clean_text("Total"), 1, 1, 'R', 1)
                elif show_icms_column:
                    pdf.cell(col_widths[4], 8, clean_text("ICMS"), 1, 0, 'R', 1)
                    pdf.cell(col_widths[5], 8, clean_text("Total"), 1, 1, 'R', 1)
                else:
                    pdf.cell(col_widths[4], 8, clean_text("Total"), 1, 1, 'R', 1)

                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 11)
                item_counter = 1
                valor_total_pdf_soma = 0
                
                for item in itens_cotacao:
                    (item_id, item_tipo, item_nome, quantidade, descricao, 
                     valor_unitario, valor_total_item, 
                     mao_obra, deslocamento, estadia, produto_id, tipo_operacao, icms, iss) = item
                    
                    # DEBUG: Verificar valores vindos do banco
                    print(f"DEBUG Item {item_counter}:")
                    print(f"  - ID: {item_id}")
                    print(f"  - Tipo: {item_tipo}")
                    print(f"  - Nome: {item_nome}")
                    print(f"  - Quantidade: {quantidade}")
                    print(f"  - Descrição: '{descricao}'")
                    print(f"  - Valor Unitário: {valor_unitario}")
                    print(f"  - Valor Total: {valor_total_item}")
                    print(f"  - Produto ID: {produto_id}")
                    
                    # Obter ICMS e ISS diretamente do item
                    icms_value = float(icms or 0)
                    iss_value = float(iss or 0)

                    # GARANTIR que descrição não seja vazia ou None
                    if not descricao or str(descricao).strip() == '' or str(descricao).lower() in ['none', 'null']:
                        descricao = item_nome if item_nome else "Descrição não informada"
                        print(f"  - Descrição corrigida para: '{descricao}'")

                    # TRATAMENTO ESPECIAL PARA KITS E SERVIÇOS (como modelo antigo)
                    descricao_final = descricao
                    
                    # Adicionar prefixo baseado no tipo de operação
                    if tipo_operacao == "Locação":
                        prefixo = "Locação - "
                    else:
                        prefixo = ""
                    
                    if item_tipo == "Kit" and produto_id:
                        # Obter composição do kit
                        composicao = PDFCotacao.obter_composicao_kit(produto_id)
                        descricao_final = f"{prefixo}Kit: {item_nome}\nComposição:\n"  "\n".join(composicao)
                    
                    elif item_tipo == "Serviço":
                        descricao_final = f"{prefixo}Serviço: {item_nome}"
                        if mao_obra or deslocamento or estadia:
                            # Layout conforme exemplo solicitado - CONCATENAR em vez de sobrescrever
                            if estadia:
                                descricao_final += f"\nEstadia: R$ {estadia:.2f}"
                            if deslocamento:
                                descricao_final += f"\nDeslocamento: R$ {deslocamento:.2f}"
                            if mao_obra:
                                descricao_final += f"\nMão de Obra: R$ {mao_obra:.2f}"
                        # ICMS removido da descrição - agora aparece apenas na coluna ICMS
                    
                    elif item_tipo == "Serviços":
                        descricao_final = f"{prefixo}Serviços: {item_nome}"
                        if mao_obra or deslocamento or estadia:
                            if estadia:
                                descricao_final += f"\nEstadia: R$ {estadia:.2f}"
                            if deslocamento:
                                descricao_final += f"\nDeslocamento: R$ {deslocamento:.2f}"
                            if mao_obra:
                                descricao_final += f"\nMão de Obra: R$ {mao_obra:.2f}"
                        # ICMS removido da descrição - agora aparece apenas na coluna ICMS
                    
                    elif item_tipo == "Kit" and not produto_id:
                        # Kits sem produto_id válido: tratar como Serviços
                        descricao_final = f"{prefixo}Serviços: {item_nome}"
                        if mao_obra or deslocamento or estadia:
                            if estadia:
                                descricao_final += f"\nEstadia: R$ {estadia:.2f}"
                            if deslocamento:
                                descricao_final += f"\nDeslocamento: R$ {deslocamento:.2f}"
                            if mao_obra:
                                descricao_final += f"\nMão de Obra: R$ {mao_obra:.2f}"
                        # ICMS removido da descrição - agora aparece apenas na coluna ICMS
                    
                    else:  # Produto
                        if (tipo_operacao or "").lower().startswith('loca'):
                            # Locação: Exibir nome do equipamento
                            descricao_final = f"Nome do Equipamento\n{item_nome}"
                            # ICMS removido da descrição - agora aparece apenas na coluna ICMS
                        else:
                            descricao_final = f"{prefixo}{item_nome}"
                    
                    # Calcular altura baseada no número de linhas
                    num_linhas = descricao_final.count('\n') + 1
                    altura_total = max(num_linhas * 6, 6)

                    # Posição inicial da linha
                    x_start = 5
                    pdf.set_x(x_start)
                    y_pos = pdf.get_y()
                    # Avançar para a coluna de descrição antes de renderizar texto
                    x_pos = x_start + col_widths[0]
                    pdf.set_x(x_pos)

                    # Renderizar descrição com primeira linha em negrito, mantendo UMA borda ao redor
                    linhas_desc = str(descricao_final or '').split('\n')
                    primeira_linha = linhas_desc[0] if linhas_desc else ''
                    outras_linhas = '\n'.join(linhas_desc[1:]) if len(linhas_desc) > 1 else ''

                    # Desenhar texto sem borda e, ao final, desenhar a borda única do bloco
                    pdf.set_font("Arial", 'B', 11)
                    pdf.set_xy(x_pos, y_pos)
                    pdf.multi_cell(col_widths[1], 6, clean_text(primeira_linha), 0, 'L')
                    if outras_linhas:
                        pdf.set_font("Arial", '', 11)
                        pdf.set_x(x_pos)
                        pdf.multi_cell(col_widths[1], 6, clean_text(outras_linhas), 0, 'L')
                    # Altura efetiva utilizada
                    new_y = pdf.get_y()
                    altura_real = max(new_y - y_pos, 6)
                    # Desenhar a borda única envolvendo todo o bloco de descrição
                    pdf.rect(x_pos, y_pos, col_widths[1], altura_real)

                    # Coluna "Item" (número) com a MESMA altura calculada
                    pdf.set_xy(x_start, y_pos)
                    pdf.cell(col_widths[0], altura_real, str(item_counter), 1, 0, 'C')

                    # Calcular nova posição Y após o texto (já calculada): altura_real

                    # Voltar para posição original das outras colunas
                    pdf.set_xy(x_pos + col_widths[1], y_pos)

                    # Quantidade (usar fonte menor para caber melhor)
                    pdf.set_font("Arial", '', 10)
                    pdf.cell(col_widths[2], altura_real, clean_text(str(int(quantidade))), 1, 0, 'C')

                    # Valor Unitário (usar fonte menor e alinhamento à direita)
                    pdf.cell(col_widths[3], altura_real, clean_text(format_currency(valor_unitario)), 1, 0, 'R')

                    # ICMS e ISS (conforme tipo e filial)
                    valor_total_display = float(valor_total_item or 0)
                    if show_icms_iss_columns:
                        # Serviços na Filial 2: mostrar ICMS e ISS
                        pdf.cell(col_widths[4], altura_real, clean_text(format_currency(icms_value)), 1, 0, 'R')
                        pdf.cell(col_widths[5], altura_real, clean_text(format_currency(iss_value)), 1, 0, 'R')
                        pdf.cell(col_widths[6], altura_real, clean_text(format_currency(valor_total_display)), 1, 1, 'R')
                    elif show_icms_column:
                        # Produtos na Filial 2: mostrar apenas ICMS
                        pdf.cell(col_widths[4], altura_real, clean_text(format_currency(icms_value)), 1, 0, 'R')
                        pdf.cell(col_widths[5], altura_real, clean_text(format_currency(valor_total_display)), 1, 1, 'R')
                    else:
                        # Filial 1 ou sem ICMS/ISS: mostrar apenas total
                        pdf.cell(col_widths[4], altura_real, clean_text(format_currency(valor_total_display)), 1, 1, 'R')

                    # Restaurar fonte padrão para descrição em linhas seguintes
                    pdf.set_font("Arial", '', 11)

                    # Acumular total para o rodapé (incluindo ICMS quando aplicável)
                    try:
                        valor_total_pdf_soma += float(valor_total_display)
                    except Exception:
                        pass
                    
                    item_counter += 1

                # Linha do valor total - alinhada com a tabela
                pdf.set_x(5)  # Mesma margem esquerda da tabela
                pdf.set_font("Arial", 'B', 12)
                pdf.set_fill_color(200, 200, 200)
                pdf.set_text_color(0, 0, 0)
                if show_icms_iss_columns:
                    pdf.cell(sum(col_widths[0:6]), 10, clean_text("VALOR TOTAL DA PROPOSTA:"), 1, 0, 'R', 1)
                    pdf.cell(col_widths[6], 10, clean_text(format_currency(valor_total_pdf_soma)), 1, 1, 'R', 1)
                elif show_icms_column:
                    pdf.cell(sum(col_widths[0:5]), 10, clean_text("VALOR TOTAL DA PROPOSTA:"), 1, 0, 'R', 1)
                    pdf.cell(col_widths[5], 10, clean_text(format_currency(valor_total_pdf_soma)), 1, 1, 'R', 1)
                else:
                    pdf.cell(sum(col_widths[0:4]), 10, clean_text("VALOR TOTAL DA PROPOSTA:"), 1, 0, 'R', 1)
                    pdf.cell(col_widths[4], 10, clean_text(format_currency(valor_total_pdf_soma)), 1, 1, 'R', 1)
                pdf.ln(10)

            # Condições comerciais
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 6, clean_text("CONDIÇÕES COMERCIAIS:"), 0, 1, 'L')
            pdf.set_font("Arial", '', 11)
            try:
                # Verificar se é filial 1 pelo CNPJ (mais confiável)
                filial_is_1 = dados_filial.get('cnpj', '') == "10.644.944/0001-55"
            except Exception:
                filial_is_1 = False
            if filial_is_1:
                pdf.cell(0, 5, clean_text(f"Tipo de Frete: {tipo_frete if tipo_frete else 'FOB'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Condição de Pagamento: {condicao_pagamento if condicao_pagamento else 'A combinar'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Prazo de Entrega: {prazo_entrega if prazo_entrega else 'A combinar'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Moeda: {moeda if moeda else 'BRL (Real Brasileiro)'}"), 0, 1, 'L')
                # Exibir texto "Imposto Incluso" para Filial 1 (Produtos e Serviços)
                tipos_itens = [(it[1] or '') for it in itens_cotacao]
                is_produtos = any(str(t).strip().lower() == 'produto' for t in tipos_itens)
                is_servicos = any(str(t).strip().lower() == 'serviços' for t in tipos_itens)
                if is_produtos or is_servicos:
                    pdf.cell(0, 5, clean_text("Imposto Incluso"), 0, 1, 'L')
            else:
                pdf.cell(0, 5, clean_text(f"Tipo de Frete: {tipo_frete if tipo_frete else 'FOB'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Condição de Pagamento: {condicao_pagamento if condicao_pagamento else 'A combinar'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Prazo de Entrega: {prazo_entrega if prazo_entrega else 'A combinar'}"), 0, 1, 'L')
                pdf.cell(0, 5, clean_text(f"Moeda: {moeda if moeda else 'BRL (Real Brasileiro)'}"), 0, 1, 'L')
            
            # Observações se houver
            if observacoes and observacoes.strip():
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 6, clean_text("OBSERVAÇÕES:"), 0, 1, 'L')
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 5, clean_text(observacoes))
            
            pdf.ln(5)

            # Salvar PDF usando função utilitária com tratamento de erro
            output_dir = os.path.join("data", "cotacoes", "arquivos")
            file_name = f"Proposta_{numero_proposta.replace('/', '_').replace(' ', '')}.pdf"
            
            sucesso, pdf_path = save_pdf_with_fallback(pdf, output_dir, file_name, cot_id, conn)
            if sucesso:
                return True, pdf_path
            else:
                return False, pdf_path

        # Garantir salvamento/retorno para Locação também
        if (tipo_cotacao or '').lower() in ('locação','locacao'):
            output_dir = os.path.join("data", "cotacoes", "arquivos")
            file_name = f"Proposta_{numero_proposta.replace('/', '_').replace(' ', '')}.pdf"
            
            sucesso, pdf_path = save_pdf_with_fallback(pdf, output_dir, file_name, cot_id, conn)
            if sucesso:
                return True, pdf_path
            else:
                return False, pdf_path

    except Exception as e:
        return False, f"Erro ao gerar PDF: {str(e)}"
    finally:
        if conn:
            conn.close()

# Manter compatibilidade com versão antiga
def gerar_pdf_cotacao(cotacao_id, db_name):
    """Função de compatibilidade que chama a nova versão"""
    return gerar_pdf_cotacao_nova(cotacao_id, db_name)

# Utilitário para data longa em PT-BR
def format_date_long_pt(date_obj):
    try:
        import locale
        locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
    except Exception:
        pass
    try:
        meses = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
        ]
        d = datetime.datetime.strptime(date_obj, '%Y-%m-%d').date() if isinstance(date_obj, str) else date_obj
        return f"{d.day} de {meses[d.month-1]} de {d.year}"
    except Exception:
        return format_date(date_obj)