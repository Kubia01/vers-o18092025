"""
Configuração das filiais da empresa para geração de PDFs
"""

FILIAIS = {
    1: {
        "nome": "WORLD COMP COMPRESSORES LTDA",
        "endereco": "Rua Fernando Pessoa, nº 11 – Batistini – São Bernardo do Campo – SP",
        "cep": "09844-390",
        "cnae_fiscal": "23222222",
        "cnpj": "10.644.944/0001-55",
        "inscricao_estadual": "635.970.206.110",
        "telefones": "(11) 4543-6893 / 4543-6857",
        "email": "contato@worldcompressores.com.br",
        "logo_path": "assets/logos/world_comp_brasil.jpg"
    },
    2: {
        "nome": "WORLD COMP DO BRASIL COMPRESSORES LTDA",
        "endereco": "Rua Fernando Pessoa, nº 17 – Batistini – São Bernardo do Campo – SP",
        "cep": "09844-390",
        "cnpj": "22.790.603/0001-77",
        "inscricao_estadual": "635.835.470.115",
        "telefones": "(11) 4543-6896 / 4543-6857 / 4357-8062",
        "email": "rogerio@worldcompressores.com.br",
        "logo_path": "assets/logos/world_comp_brasil.jpg"
    }
}

# Configuração de usuários que podem gerar cotações com templates personalizados JPEG
USUARIOS_COTACAO = {
    "valdir": {
        "nome_completo": "Valdir",
        "template_capa_jpeg": "assets/templates/capas/capa_valdir.jpg",
        "assinatura": "Valdir\nVendas"
    },
    "vagner": {
        "nome_completo": "Vagner Cerqueira",
        "template_capa_jpeg": "assets/templates/capas/capa_vagner.jpg",
        "assinatura": "Vagner Cerqueira\nVendas"
    },
    "rogerio": {
        "nome_completo": "Rogério Cerqueira",
        "template_capa_jpeg": "assets/templates/capas/capa_rogerio.jpg",
        "assinatura": "Rogério Cerqueira\nVendas"
    },
    "raquel": {
        "nome_completo": "Raquel",
        "template_capa_jpeg": "assets/templates/capas/capa_raquel.jpg",
        "assinatura": "Raquel\nVendas"
    },
    "jaqueline": {
        "nome_completo": "Jaqueline",
        "template_capa_jpeg": "assets/templates/capas/capa_jaqueline.jpg",
        "assinatura": "Jaqueline\nVendas"
    },
    "adam": {
        "nome_completo": "Adam",
        "template_capa_jpeg": "assets/templates/capas/capa_adam.jpg",
        "assinatura": "Adam\nVendas"
    },
    "cicero": {
        "nome_completo": "Cicero",
        "template_capa_jpeg": "assets/templates/capas/capa_cicero.jpg",
        "assinatura": "Cicero\nVendas"
    }
}

def obter_filial(filial_id):
    """Retorna informações da filial pelo ID"""
    return FILIAIS.get(filial_id)

def obter_usuario_cotacao(username):
    """Retorna configurações do usuário para cotação"""
    return USUARIOS_COTACAO.get(username.lower())

def listar_filiais():
    """Retorna lista de filiais disponíveis"""
    return [(id, info["nome"]) for id, info in FILIAIS.items()]

def obter_template_capa_jpeg(username):
    """Retorna o caminho do template JPEG para o usuário"""
    usuario = obter_usuario_cotacao(username)
    if usuario and 'template_capa_jpeg' in usuario:
        return usuario['template_capa_jpeg']
    return None