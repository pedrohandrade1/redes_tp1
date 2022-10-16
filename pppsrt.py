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

class CheckSum:
    
    # Soma os bytes de um frame para int 16 bits
    def sum_frame(frame: bytearray):
        even = True

        sum = 0
        for byte in frame:

            if even:
                sum += byte
            else:
                sum += byte * 256
            
            if sum > 65535:
                sum = (sum % 65536) + 1

            even = not even
            
        return sum 

    # Calcula o checksum
    def make(frame: bytearray):
        sum = CheckSum.sum_frame(frame)
        return 65536 - sum
    
    # Confere o checksum
    def check(frame: bytearray, checksum):
        sum = CheckSum.sum_frame(frame) + checksum
        return 65536 - sum == 0

class ByteStuffing:

    ESCAPE = 0x7d
    FLAG = 0x7e

    ESCAPE_SUBS = 0x5d
    FLAG_SUBS = 0x5e

    # Escapa algum byte se necessario
    def escape_byte(escaped_frame: bytearray, byte):
        # Escapa o byte de escape
        if byte == ByteStuffing.ESCAPE:
            escaped_frame.append(ByteStuffing.ESCAPE)
            escaped_frame.append(ByteStuffing.ESCAPE_SUBS)

        # Escapa o byte de flag
        elif byte == ByteStuffing.FLAG:
            escaped_frame.append(ByteStuffing.ESCAPE)
            escaped_frame.append(ByteStuffing.FLAG_SUBS)

        # Não é necessário fazer escape
        else:
            escaped_frame.append(byte)

    # Remove o escape de algum byte especial
    def unescape_especial_byte(frame: bytearray, byte):
        # Remove escape de byte de escape
        if byte == ByteStuffing.ESCAPE_SUBS:
            frame.append(ByteStuffing.ESCAPE)

        # Remove escape de byte de flag
        elif byte == ByteStuffing.FLAG_SUBS:
            frame.append(ByteStuffing.FLAG)

        else:
            False
            # error

    # Adiciona o escapamento ao frame
    def add(frame: bytearray):
        # Sequencia de bytes escapada vazia
        escaped_frame = bytearray()

        # Verifica para cada byte do Payload se é necessário escapar o byte
        for byte in frame:
            ByteStuffing.escape_byte(escaped_frame, byte)
        
        return escaped_frame

    # Remove o escapamento de um frame
    def remove(escaped_frame: bytearray):
        # Sequencia de bytes vazia
        frame = bytearray()

        i = 0
        size = len(escaped_frame)

        while(i < size):

            byte = escaped_frame[i]

            # Byte especial
            if byte == ByteStuffing.ESCAPE:

                if i < size - 1:
                    next_byte = escaped_frame[i + 1]
                    ByteStuffing.unescape_especial_byte(frame, next_byte)
                    i += 2

                else:
                    False
                    # error

            # Byte qualquer
            else:
                frame.append(byte)
                i += 1
        
        return frame


class PPPSRT:
  
    def __init__(self, port, host='' ):
        self.link = dcc023_tp1.Link(port,host)
        self.protocol = bytearray('0000', encoding= 'utf-8')

    def close(self):
        self.link.close()
        
####################################################################
# A princípio, só é preciso alterar as duas funções a seguir.


    def send(self,message):
        
        aux_protocol = int(self.protocol, 16)                   
        aux_protocol += 1                                       # Incrementa o protocolo
        self.protocol = '{:04x}'.format(aux_protocol)           # Formata como string hexadecimal
        payload = encodeHex(message)
        # checksum = ///
        message = bytearray(FLAG + ADDS + DCTRL + self.protocol, encoding = 'utf-8') + payload + bytearray(FLAG, encoding= 'utf-8')#Monta o quadro
        print(message)
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
