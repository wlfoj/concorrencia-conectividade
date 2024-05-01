import socket
from cryptography.fernet import Fernet
from Broker import Broker
import json
from config import conf

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from Utils import Utils

def thread_listen_conections_tcp(socket_tcp: socket.socket, broker: Broker, decrypt: Fernet):
    '''Esta função atua apenas ouvindo conexões e registrando no broker'''
    logging.info(f'TCP LISTEN CONN - Thread para receber conexões na porta tcp iniciada')
    while True:
        # Aceitando uma nova conexão
        conexao, cliente = socket_tcp.accept()
        if conexao and cliente:
            logging.info(f'TCP LISTEN CONN - Conexão recebida de {cliente[0]}')
            ### ================ Valido a conexão ================ ###
            ## Devo receber, logo após aceitar uma conexão, um dado no tipo {'key': "valor_da_secret"} 
            dados_recebidos = conexao.recv(1024)
            logging.info(f'TCP LISTEN CONN - mensagem para validar a conexão recebida de {cliente[0]}')
            # O try existe para o caso de dar algum erro no decriptar
            try:
                # Decodifica a mensagem
                mensagem_descriptografado = decrypt.decrypt(dados_recebidos)
                # # Converte a mensagem de bytes para string
                mensagem_string = mensagem_descriptografado.decode('utf-8')
                mensagem_json_dict = json.loads(mensagem_string)
                # ============ Valido a conexão ============= #
                if mensagem_json_dict['key'] == conf['key_conn']:
                    # Registra o cliente no broker
                    confirm = broker.register_device(conexao, cliente[0])
                    if confirm:
                        logging.info(f'TCP LISTEN CONN - Conexão aceita de {cliente[0]} e registrada no BROKER')
                        # Envio a confirmação
                                            # Monta o obj
                        obj_to_send = {'is_acc': True}
                        # Criptografa
                        obj_encrypted = Utils.encrypt(decrypt, obj_to_send)
                        # Envia
                        conexao.send(obj_encrypted)
                        #print(broker._dispositivos)
                    else:
                        logging.warning(f'TCP LISTEN CONN - Conexão de {cliente[0]} rejeitada pelo BROKER')
                        conexao.close()
                else:
                    obj_to_send = {'is_acc': False}
                    # Criptografa
                    obj_encrypted = Utils.encrypt(decrypt, obj_to_send)
                    # Envia
                    conexao.send(obj_encrypted)
                    logging.warning(f'TCP LISTEN CONN - Conexão de {cliente[0]} rejeitada, pois a chave está incorreta')
                    conexao.close()
            except:
                obj_to_send = {'is_acc': False}
                # Criptografa
                obj_encrypted = Utils.encrypt(decrypt, obj_to_send)
                # Envia
                conexao.send(obj_encrypted)
                logging.warning(f'TCP LISTEN CONN - Conexão de {cliente[0]} rejeitada, pois a chave está incorreta')
                conexao.close()
 


def thread_send_message(broker: Broker, encrypt: Fernet):
    '''Função responsável por repassar o comando no tópico para o respectivo dispositivo
    '''
    logging.info(f'TCP - Thread para enviar mensagens pela porta tcp iniciada')
    while True:
        # Percoro os tópicos de comandos vendo quais tem mensagens para serem mandadas
        to_send = broker.get_msg_and_device_to_send_command()
        # Percorrendo a lista de operações que preciso fazer
        for info in to_send:
            # Faço o envio
            if (info['msg'] is not None) :#and (info['conn'] is not None):
                try:
                    msg = info['msg']
                    ip = info['ip']
                    logging.info(f'TCP - Enviando {msg} para {ip} via tcp')
                    # Monta o obj
                    obj_to_send = {'command': msg}
                    # Criptografa
                    obj_encrypted = Utils.encrypt(encrypt, obj_to_send)
                    # Envia
                    info['conn'].send(obj_encrypted) # Envio a mensagem para a conexão correspondente
                except ConnectionResetError:
                    info['conn'].close()
                    broker.delete_device(ip)
                    logging.warning(f'TCP - O dispositivo {ip} foi desconectado e por isso removido do broker')




def thread_check_conn_health(broker: Broker):
    '''Thread para verificar se uma conexão está ativa e destruir ela se não estiver'''
    logging.info(f'TCP HEALTH CONN - Thread para verificar a saúde das conexões iniciada')
    #{"device_name":"", "ip": '', "tcp_connection": None}
    while True:
        for device in broker.get_devices():
            try:
                # Tenta obter o nome do par remoto (endereço IP e porta)
                peername = device['tcp_connection'].getpeername()
            except OSError:
                # Se ocorrer um erro, a conexão não está mais ativa
                broker.delete_device(device['ip'])
                logging.warning(f"TCP HEALTH CONN - O dispositivo {device['ip']} foi desconectado e por isso removido do broker") 