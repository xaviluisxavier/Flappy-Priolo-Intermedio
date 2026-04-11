import threading
import os
from comunicacao.sockets_util import receive_object

class BroadcastReceiver(threading.Thread):
    def __init__(self, connection):
        """Inicializa a thread de broadcast receiver, armazenando a conexão e definindo a thread como daemon."""
        super().__init__(daemon=True)
        self.connection = connection
        self.ativo = True

    def run(self):
        """Recebe os estados do jogo do servidor e os imprime no terminal."""
        while self.ativo:
            try:
                estado = receive_object(self.connection)
                if not estado:
                    break
                
                if "acao" in estado and estado["acao"] == "ERRO":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"\nLIGAÇÃO RECUSADA: {estado['motivo']}")
                    print("Pressiona [ENTER] para sair.")
                    self.ativo = False
                    break
                
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print("JOGO EM EXECUÇÃO")
                for pid, info in estado['jogadores'].items(): 
                    altura_visual = max(0, int(info['y'] // 10)) 
                    espaco = " " * altura_visual
                    print(f"[{info['nome']}] Score: {info['score']} | Altura: {info['y']}")
                    print(f"{espaco} 🐦")
                    print("-" * 40)
                    
                print("\nEscreve 'f' e [ENTER] para saltar. Ou 'sair' para fechar.")
            except:
                self.ativo = False
                break
