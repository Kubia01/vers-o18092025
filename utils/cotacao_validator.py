import sqlite3
from datetime import datetime, date
from database import DB_NAME

def verificar_e_atualizar_status_cotacoes():
    """
    Verifica e atualiza automaticamente o status das cotações que expiraram
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Buscar cotações com prazo de validade expirado e status "Em Aberto"
        hoje = date.today()
        c.execute("""
            SELECT id, numero_proposta, data_validade 
            FROM cotacoes 
            WHERE status = 'Em Aberto' 
            AND data_validade IS NOT NULL 
            AND data_validade < ?
        """, (hoje,))
        
        cotações_expiradas = c.fetchall()
        
        if cotações_expiradas:
            # Atualizar status para "Rejeitada"
            c.execute("""
                UPDATE cotacoes 
                SET status = 'Rejeitada' 
                WHERE status = 'Em Aberto' 
                AND data_validade IS NOT NULL 
                AND data_validade < ?
            """, (hoje,))
            
            conn.commit()
            print(f"✅ {len(cotações_expiradas)} cotações expiradas foram atualizadas para 'Rejeitada'")
            
            # Retornar detalhes das cotações atualizadas
            return cotações_expiradas
        else:
            print("✅ Nenhuma cotação expirada encontrada")
            return []
            
    except sqlite3.Error as e:
        print(f"❌ Erro ao verificar cotações expiradas: {e}")
        return []
    finally:
        conn.close()

def obter_cotacoes_por_status(status=None):
    """
    Obtém cotações filtradas por status
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        if status:
            c.execute("""
                SELECT c.id, c.numero_proposta, cl.nome, c.data_criacao, c.data_validade, 
                       c.valor_total, c.status, u.nome_completo
                FROM cotacoes c
                JOIN clientes cl ON c.cliente_id = cl.id
                JOIN usuarios u ON c.responsavel_id = u.id
                WHERE c.status = ?
                ORDER BY c.created_at DESC
            """, (status,))
        else:
            c.execute("""
                SELECT c.id, c.numero_proposta, cl.nome, c.data_criacao, c.data_validade, 
                       c.valor_total, c.status, u.nome_completo
                FROM cotacoes c
                JOIN clientes cl ON c.cliente_id = cl.id
                JOIN usuarios u ON c.responsavel_id = u.id
                ORDER BY c.created_at DESC
            """)
        
        return c.fetchall()
        
    except sqlite3.Error as e:
        print(f"❌ Erro ao buscar cotações: {e}")
        return []
    finally:
        conn.close()

def obter_estatisticas_cotacoes():
    """
    Obtém estatísticas das cotações por status
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute("""
            SELECT status, COUNT(*) as quantidade, SUM(valor_total) as valor_total
            FROM cotacoes
            GROUP BY status
        """)
        
        return c.fetchall()
        
    except sqlite3.Error as e:
        print(f"❌ Erro ao buscar estatísticas: {e}")
        return []
    finally:
        conn.close()

def obter_cotacoes_por_usuario(usuario_id):
    """
    Obtém cotações de um usuário específico
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute("""
            SELECT c.id, c.numero_proposta, cl.nome, c.data_criacao, c.data_validade, 
                   c.valor_total, c.status
            FROM cotacoes c
            JOIN clientes cl ON c.cliente_id = cl.id
            WHERE c.responsavel_id = ?
            ORDER BY c.created_at DESC
        """, (usuario_id,))
        
        return c.fetchall()
        
    except sqlite3.Error as e:
        print(f"❌ Erro ao buscar cotações do usuário: {e}")
        return []
    finally:
        conn.close()

def obter_cotacoes_vencendo_em_dias(dias=7):
    """
    Obtém cotações que vencem em X dias
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        from datetime import timedelta
        data_limite = date.today() + timedelta(days=dias)
        
        c.execute("""
            SELECT c.id, c.numero_proposta, cl.nome, c.data_criacao, c.data_validade, 
                   c.valor_total, c.status, u.nome_completo
            FROM cotacoes c
            JOIN clientes cl ON c.cliente_id = cl.id
            JOIN usuarios u ON c.responsavel_id = u.id
            WHERE c.status = 'Em Aberto' 
            AND c.data_validade IS NOT NULL 
            AND c.data_validade <= ?
            ORDER BY c.data_validade ASC
        """, (data_limite,))
        
        return c.fetchall()
        
    except sqlite3.Error as e:
        print(f"❌ Erro ao buscar cotações vencendo: {e}")
        return []
    finally:
        conn.close()