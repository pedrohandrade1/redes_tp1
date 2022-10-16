#################################################################
# pppsrt.py - protocolo ponto-a-ponto simples com retransmissão
#           - entrega interface semelhante a um socket
#################################################################
# fornece a classe PPPSRT, que tem os métodos:
#
# contrutor: pode receber um ou dois parâmetros, para criar um
#            canal que implementa o protocolo PPPSRT;
#            - o servidor cria o objeto apenas com o porto;
#            - o cliente cria o objeto com host e porto.
# close: encerra o enlace
# send(m): envia o array de bytes m pelo canal, calculando o 
#           checksum, fazendo o enquadramento e controlando a
#           retransmissão, se necessário.
# recv(): recebe um quadro e retorna-o como um array de bytes,
#         conferindo o enquadramento, conferindo o checksum e
#         enviando uma mensagem de confirmação, se for o caso.
# OBS: o tamanho da mensagem enviada/recebida pode variar, 
#      mas não deve ser maior que 1500 bytes.
################################################################
# PPPSRT utiliza o módulo dcc023_tp1 como API para envio e recepção
#        pelo enlace; o qual não deve ser alterado.
# PPPSRT não pode utilizar a interface de sockets diretamente.
################################################################

import dcc023_tp1
import binascii
import time

FLAG = '7E' #Flag
ADDS= 'FF' #Address
DCTRL = '03' #Control de dados
CCTRL = '07' #Control de confirmação ACK


def encodeHex(message): # caracteres da mensagem para hexadecimal
    return binascii.hexlify(message)

def decodeHex(message): #  hexadecimal da mensagem para caracteres
    return binascii.unhexlify(message)

class PPPSRT:
  
    def __init__(self, port, host='' ):
        self.link = dcc023_tp1.Link(port,host)
        self.protocol = b'0000'

    def close(self):
        self.link.close()
        
####################################################################
# A princípio, só é preciso alterar as duas funções a seguir.


    def send(self,message):
        
        aux_protocol = int(self.protocol, 16)                   
        aux_protocol += 1                                       # Incrementa o protocolo
        self.protocol = '{:04x}'.format(aux_protocol)           # Formata como string hexadecimal
        
        payload = encodeHex(message)
        message = (FLAG + ADDS + DCTRL + self.protocol).encode() + payload + FLAG.encode() #Monta o quadro

        # Aqui, PPSRT deve fazer:
        #   - fazer o encapsulamento de cada mensagem em um quadro PPP,
        #   - calcular o Checksum do quadro e incluído,
        #   - fazer o byte stuffing durante o envio da mensagem,
        #   - aguardar pela mensagem de confirmação,
        #   - retransmitir a mensagem se a confirmação não chegar.
        self.link.send(message)

    def recv(self):
        # Aqui, PPSRT deve fazer:
        #   - identificar começo de um quadro,
        #   - receber a mensagem byte-a-byte, para retirar o stuffing,
        #   - detectar o fim do quadro,
        #   - calcular o checksum do quadro recebido,
        #   - descartar silenciosamente quadros com erro,
        #   - enviar uma confirmação para quadros recebidos corretamente,
        #   - conferir a ordem dos quadros e descartar quadros repetidos.
        try:
            frame = self.link.recv(1500)
        except TimeoutError: # use para tratar temporizações
            print("Timeout")
        return frame
