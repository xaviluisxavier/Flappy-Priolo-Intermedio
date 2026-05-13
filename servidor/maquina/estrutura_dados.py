"""
Módulo de gestão de dados do servidor para o jogo 'Flappy Priolo - Azores Edition'.
Gere o estado do jogo, a física (gravidade e colisões), a pontuação e a sincronização
entre múltiplos clientes através de threads.
"""

import threading
import random
import servidor

class DadosJogo:
    """
    Classe responsável por gerir e armazenar o estado global do jogo de forma 
    segura (thread-safe).
    """

    def __init__(self):
        """
        Inicializa a estrutura de dados do jogo.
        Cria o dicionário de jogadores, o mecanismo de bloqueio (lock) para 
        evitar conflitos entre threads e o contador de IDs para os vulcões.
        """
        self.jogadores = {} 
        self.lock = threading.Lock() 
        self.v_id_counter = 0

    def gerar_id_vulcao(self):
        """
        Gera um identificador único e sequencial para um novo vulcão.

        Returns:
            int: O ID gerado para o vulcão.
        """
        self.v_id_counter += 1
        return self.v_id_counter

    def adicionar_jogador(self, player_id, nome):
        """
        Tenta adicionar um novo jogador à sessão de jogo.

        Verifica se o servidor já atingiu o limite de jogadores (5) e se o nome
        escolhido já está a ser utilizado por outro jogador ativo.

        Args:
            player_id (str/int): O identificador único da ligação do cliente.
            nome (str): O nome escolhido pelo jogador.

        Returns:
            tuple: (bool, str) Um booleano indicando sucesso ou falha, e uma
                   mensagem descritiva do resultado.
        """
        with self.lock:
            if len(self.jogadores) >= 5: return False, "SERVIDOR CHEIO"
            for pid, dados in self.jogadores.items():
                if dados['nome'] == nome: return False, "NOME JÁ EXISTE"
            
            self.jogadores[player_id] = {
                'nome': nome, 
                'x': servidor.POSICAO_X_PRIOLOS, 
                'y': 20.0, 
                'vel_y': 0.0, 
                'score': 0,
                'vulcoes': [{'id': self.gerar_id_vulcao(), 'x': 100.0, 'abertura_y': random.randint(15, 85), 'contado': False}] 
            }
            return True, "SUCESSO"

    def remover_jogador(self, player_id):
        """
        Remove um jogador da sessão de jogo de forma segura.

        Args:
            player_id (str/int): O identificador da ligação do cliente a remover.
        """
        with self.lock:
            if player_id in self.jogadores: del self.jogadores[player_id]

    def atualizar_posicao(self, player_id, acao):
        """
        Atualiza a velocidade do jogador em resposta a uma ação recebida.

        Args:
            player_id (str/int): O identificador da ligação do cliente.
            acao (str): O comando enviado pelo cliente (ex: "FLAP" para saltar).

        Returns:
            bool: False por defeito (o retorno não é estritamente necessário neste fluxo).
        """
        with self.lock:
            if player_id in self.jogadores:
                if acao == "FLAP":
                    jogador = self.jogadores[player_id]
                    jogador['vel_y'] = -servidor.SALTO_BASE 
        return False

    def aplicar_gravidade(self, player_id):
        """
        Aplica a força da gravidade a um jogador, atualiza a sua posição no eixo Y
        e verifica a ocorrência de colisões.

        Se o jogador colidir com o chão, o teto ou um vulcão, o seu estado 
        (posição, pontuação e vulcões) é reiniciado.

        Args:
            player_id (str/int): O identificador da ligação do cliente.

        Returns:
            bool: True se o jogador morreu e foi reiniciado, False caso contrário.
        """
        with self.lock:
            if player_id not in self.jogadores: return False
            jogador = self.jogadores[player_id]
            
            jogador['vel_y'] += servidor.GRAVIDADE_BASE 
            
            if jogador['vel_y'] > 4.5:
                jogador['vel_y'] = 4.5
                
            jogador['y'] += jogador['vel_y']
            
            morreu = False
            
            # Colisão com o teto (0) ou o chão (100)
            if jogador['y'] >= 100 or jogador['y'] < 0: 
                morreu = True
            
            # Colisão com os vulcões
            for v in jogador['vulcoes']:
                if abs(v['x'] - jogador['x']) < 10: 
                    if jogador['y'] < v['abertura_y'] - 15 or jogador['y'] > v['abertura_y'] + 15: 
                        morreu = True

            if morreu:
                jogador['y'] = 20.0
                jogador['vel_y'] = 0.0 
                jogador['score'] = 0 
                jogador['vulcoes'] = [{'id': self.gerar_id_vulcao(), 'x': 100.0, 'abertura_y': random.randint(15, 85), 'contado': False}]
                return True
                
            return False
        
    def verificar_pontos(self):
        """
        Verifica a posição dos vulcões em relação aos jogadores para contabilizar pontos.
        Se um jogador ultrapassou um vulcão que ainda não foi contado, a sua
        pontuação é incrementada.
        """
        with self.lock:
            for pid, jogador in self.jogadores.items():
                for v in jogador['vulcoes']:
                    if v['x'] < servidor.POSICAO_X_PRIOLOS and not v.get('contado', False):
                        jogador['score'] += 1
                        v['contado'] = True

    def atualizar_mundo(self):
        """
        Atualiza o ambiente do jogo para todos os jogadores.
        
        Move os vulcões para a esquerda (aumentando a velocidade gradualmente com
        base na pontuação), remove os vulcões que já saíram do ecrã e gera novos
        vulcões no horizonte.
        """
        with self.lock:
            for pid, jogador in self.jogadores.items():
                velocidade_atual = servidor.VELOCIDADE_BASE + ((jogador['score'] // 5) * 0.2)
                for v in jogador['vulcoes']: 
                    v['x'] -= velocidade_atual
                    
                if jogador['vulcoes'] and jogador['vulcoes'][0]['x'] < -10: 
                    jogador['vulcoes'].pop(0)
                    
                if jogador['vulcoes'][-1]['x'] < (100 - servidor.DISTANCIA_ENTRE_VULCOES):
                    jogador['vulcoes'].append({'id': self.gerar_id_vulcao(), 'x': 100.0, 'abertura_y': random.randint(15, 85), 'contado': False})

    def obter_estado(self):
        """
        Recolhe e formata o estado atual do jogo e os parâmetros do servidor.

        Este método prepara um dicionário limpo contendo as posições, pontuações
        e vulcões de todos os jogadores, pronto para ser enviado pela rede 
        (broadcast) para os clientes renderizarem.

        Returns:
            dict: Um dicionário com duas chaves principais: 'jogadores' e 'parametros'.
        """
        with self.lock: 
            estado_limpo = {}
            for pid, j in self.jogadores.items():
                estado_limpo[pid] = {
                    'nome': j['nome'],
                    'x': int(j['x']),
                    'y': int(j['y']),
                    'score': j['score'],
                    'vulcoes': [{'id': v.get('id', 0), 'x': int(v['x']), 'abertura_y': int(v['abertura_y']), 'contado': v['contado']} for v in j['vulcoes']]
                }

            parametros_atuais = {
                'gravidade': round(servidor.GRAVIDADE_BASE, 2),
                'salto': round(servidor.SALTO_BASE, 2),
                'velocidade': round(servidor.VELOCIDADE_BASE, 2),
                'distancia': servidor.DISTANCIA_ENTRE_VULCOES,
                'v_ids': self.v_id_counter
            }
            return {'jogadores': estado_limpo, 'parametros': parametros_atuais}