from flask import Flask, request, jsonify
from flask_caching import Cache

import socket
import threading

from SERVER_TCP import thread_listen_conections
from SERVER_UDP import thread_receiva_udp

from config import conf
from broker import Broker

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})  # Configuração básica de cache
broker = Broker(1)


#### COLOCAR A REQUISIÇÃO NA FILA DA THREAD PROCESSADORA, Aí ELA DA POP LÀ E VAI EXECUTANDO. DEIXA OS CANAIS DE RECEBIMENTO LIVRES
@app.route('/pub/<string:topic>', methods=['POST'])
def post_mensagem(topic: str):
    '''Publica a mensagem no topico'''
    # Se não for um tópico permitido, já encerra e retorna o status
    if not topic.startswith('comandos_'):
        return jsonify({"erro": "Você não tem permissão para este topico"}), 403
    # Obtem o body da requisição
    conteudo = request.json
    # print(conteudo['topico'])
    ## === Bloco para validar o body === ##
    # Verifica se a solicitação contém um JSON
    if conteudo is None:
        return jsonify({"erro": "A solicitação deve conter um JSON"}), 400
    confirm = broker.publish_message(topic, conteudo, '')
    status = 200
    if confirm:
        status = 201
    return jsonify({"mensagem": "Mensagem publicada com sucesso"}), status




@app.route('/sub', methods=['GET'])
@cache.cached(timeout=2)  # Cache válido por 60 segundos
def get_mensagens():
    '''Pega mensagens de todos os tópicos'''
    # Aqui você pode implementar a lógica para ler as mensagens do tópico MQTT
    # Neste exemplo, retornaremos uma lista vazia
    return jsonify(broker.pega_mensagens_todos_topicos_dados()), 200


# Rota para ler as mensagens de um dispositivo especifico
@app.route('/sub/<string:topic>', methods=['GET'])
def get_mensagem(topic:str):
    '''Pega uma mensagem de um topico'''
    # Se não for um tópico permitido, já encerra e retorna o status
    if not topic.startswith('dados_'):
        return jsonify({"erro": "Você não tem permissão para este topico"}), 403
    msg = broker.pop_message(topic)
    # Aqui você pode implementar a lógica para ler as mensagens do tópico MQTT
    # Neste exemplo, retornaremos uma lista vazia
    return jsonify({'value': msg}), 200


@app.route('/device_names', methods=['GET'])
@cache.cached(timeout=2)  # Cache válido por 60 segundos
def get_devices():
    '''Obtem os nomes dos dispositivos cadastrados'''
    return jsonify(broker.get_registered_devices()), 200








if __name__ == '__main__':

    # Pro caso de dar erro???
    # Dou start nas threads udp e tcp
    # Dou start na thread de processamento
    # Dou start na thread do broker????
    # Dou start no api restful
    app.run(debug=True)

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    origem = (conf['tcp_addres_con'], conf['udp_port'])
    udp.bind(origem)

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    origem = (conf['tcp_addres_con'], conf['tcp_port'])
    tcp.bind(origem)
    tcp.listen(9) ## DEIXEI UM NÚMERO FIXO DE DISPOSITIVOS PARA SE CONECTAREM AQUI

    
    #
    thread_udp = threading.Thread(target=thread_receiva_udp, args=[udp, broker])
    thread_tcp = threading.Thread(target=thread_listen_conections, args=[tcp, broker])
    ## Dá start nas threads
    thread_tcp.start()
    thread_udp.start()
    #
    thread_tcp.join()
    thread_udp.join()
    
