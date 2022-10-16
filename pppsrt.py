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

FLAG = 0x7E #Flag
ADDS= 0xFF #Address
DCTRL = 0x03 #Control de dados
CCTRL = 0x07 #Control de confirmação ACK


def encodeHex(message): # caracteres da mensagem para hexadecimal
    return binascii.hexlify(message)

def decodeHex(message): #  hexadecimal da mensagem para caracteres
    return binascii.unhexlify(message)

class Frame:

    FLAG = 0x7e

    # Cria pacote escapado
    def make_package_escaped(address, control, protocol_int: int, payload: bytearray):
        package = bytearray()
        package.append(Frame.FLAG)
        package.append(address)
        package.append(control)

        protocol_bytearray = protocol_int.to_bytes(2, 'big')
        protocol_bytearray_escaped = ByteStuffing.escape(protocol_bytearray)
        package.extend(protocol_bytearray_escaped)

        payload_escaped = ByteStuffing.escape(payload)
        package.extend(payload_escaped)

        checksum_entry = bytearray()
        checksum_entry.append(Frame.FLAG)
        checksum_entry.append(address)
        checksum_entry.append(control)
        checksum_entry.extend(protocol_bytearray)
        checksum_entry.extend(payload)
        checksum_entry.append(Frame.FLAG)

        checksum_int = CheckSum.make(checksum_entry)
        checksum_bytearray = CheckSum.to_bytes(checksum_int)
        checksum_escaped = ByteStuffing.escape(checksum_bytearray)
        package.extend(checksum_escaped)

        package.append(Frame.FLAG)
        return package
        
    # Obtem pacote escapado
    def get_package_escaped(stream: bytearray):
        escaped_package = bytearray()
        started = False

        for byte in stream:
            if byte == Frame.FLAG:
                if started:
                    escaped_package.append(Frame.FLAG)
                    return escaped_package
                else:
                    started = True

            if started:
                escaped_package.append(byte)
        
        return escaped_package
    
    # Obtem pacote sem escape
    def get_package_unescaped(escaped_package: bytearray):
        return ByteStuffing.unescape(escaped_package)

    # Obtem frame desconstruido
    def get_package_deconstructed(package_unescaped: bytearray):
        address = package_unescaped[1]
        control = package_unescaped[2]

        protocol_bytearray  = bytearray()
        protocol_bytearray.append(package_unescaped[3])
        protocol_bytearray.append(package_unescaped[4])

        payload = bytearray()

        frame_size = len(package_unescaped)
        i = 5
        while i < frame_size - 3:
            byte = package_unescaped[i]
            payload.append(byte)
            i += 1
        
        checksum_bytearray = bytearray()
        checksum_bytearray.append(package_unescaped[frame_size - 3])
        checksum_bytearray.append(package_unescaped[frame_size - 2])

        checksum_int = CheckSum.from_bytes(checksum_bytearray)

        return address, control, protocol_bytearray, payload, checksum_int
    
    # Performa checksum para verificar errors
    def check_errors(address, control, protocol_bytearray, payload, checksum_int):
        checksum_entry = bytearray()
        checksum_entry.append(Frame.FLAG)
        checksum_entry.append(address)
        checksum_entry.append(control)
        checksum_entry.extend(protocol_bytearray)
        checksum_entry.extend(payload)
        checksum_entry.append(Frame.FLAG)

        if not CheckSum.check(checksum_entry, checksum_int):
            raise Exception("CheckSum error")
        

class CheckSum:
    
    # Soma os bytes de um pacote para int 16 bits
    def sum_package(package: bytearray):
        even = True

        sum = 0
        for byte in package:

            if even:
                sum += byte
            else:
                sum += byte * 256
            
            if sum > 65535:
                sum = (sum % 65536) + 1

            even = not even
            
        return sum 

    # Calcula o checksum
    def make(package: bytearray):
        sum = CheckSum.sum_package(package)
        return 65536 - sum
    
    # Confere o checksum
    def check(package: bytearray, checksum: int):
        sum = CheckSum.sum_package(package) + checksum
        return 65536 - sum == 0

    def to_bytes(checksum: int):
        return checksum.to_bytes(2, 'big')
    
    def from_bytes(checksum: bytearray):
        return int.from_bytes(checksum, 'big')

class ByteStuffing:

    ESCAPE = 0x7d
    FLAG = 0x7e

    ESCAPE_SUBS = 0x5d
    FLAG_SUBS = 0x5e

    # Escapa algum byte se necessario
    def escape_byte(escaped_package: bytearray, byte):
        # Escapa o byte de escape
        if byte == ByteStuffing.ESCAPE:
            escaped_package.append(ByteStuffing.ESCAPE)
            escaped_package.append(ByteStuffing.ESCAPE_SUBS)

        # Escapa o byte de flag
        elif byte == ByteStuffing.FLAG:
            escaped_package.append(ByteStuffing.ESCAPE)
            escaped_package.append(ByteStuffing.FLAG_SUBS)

        # Não é necessário fazer escape
        else:
            escaped_package.append(byte)

    # Remove o escape de algum byte especial
    def unescape_especial_byte(package: bytearray, byte):
        # Remove escape de byte de escape
        if byte == ByteStuffing.ESCAPE_SUBS:
            package.append(ByteStuffing.ESCAPE)

        # Remove escape de byte de flag
        elif byte == ByteStuffing.FLAG_SUBS:
            package.append(ByteStuffing.FLAG)

        else:
            False
            # error

    # Adiciona o escapamento ao frame
    def escape(package: bytearray):
        # Sequencia de bytes escapada vazia
        escaped_package = bytearray()

        # Verifica para cada byte do Payload se é necessário escapar o byte
        for byte in package:
            ByteStuffing.escape_byte(escaped_package, byte)
        
        return escaped_package

    # Remove o escapamento de um frame
    def unescape(escaped_package: bytearray):
        # Sequencia de bytes vazia
        package = bytearray()

        i = 0
        size = len(escaped_package)

        while(i < size):

            byte = escaped_package[i]

            # Byte especial
            if byte == ByteStuffing.ESCAPE:

                if i < size - 1:
                    next_byte = escaped_package[i + 1]
                    ByteStuffing.unescape_especial_byte(package, next_byte)
                    i += 2

                else:
                    False
                    # error

            # Byte qualquer
            else:
                package.append(byte)
                i += 1
        
        return package


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
        aux_protocol += 1                                                               # Incrementa o protocolo
        payload = bytearray(message)                                                    # Codifica a mensagem em hexadecimal
        escaped_message = Frame.make_package_escaped(ADDS,DCTRL,aux_protocol,payload)   # Cria o pacote
        escaped_package = Frame.get_package_escaped(escaped_message)
        print("escaped_package:", escaped_package)


        # message = bytearray(FLAG + ADDS + DCTRL + self.protocol, encoding = 'utf-8') + payload + bytearray(checksum + FLAG, encoding= 'utf-8') #Monta o quadro

        # Aqui, PPSRT deve fazer:
        #   - fazer o encapsulamento de cada mensagem em um quadro PPP,
        #   - calcular o Checksum do quadro e incluído,
        #   - fazer o byte stuffing durante o envio da mensagem,
        #   - aguardar pela mensagem de confirmação,
        #   - retransmitir a mensagem se a confirmação não chegar.
        self.link.send(escaped_message)
        
        while True: # Aguarda a confirmação
            ACK = self.link.recv(1500)
            if len(ACK) == 0:
                print("Retransmitting")
                self.link.send(escaped_message)
            else:
                unescaped_ACK = Frame.get_package_unescaped(ACK)
                address, control, protocol_bytearray, payload, checksum_int = Frame.get_package_deconstructed(unescaped_ACK)
                protocol_int = int.from_bytes(protocol_bytearray, 'big')
                if control == CCTRL and protocol_int == aux_protocol:
                    print("ACK:",ACK)
                    break
                else:
                    print("Retransmitting")
                    self.link.send(escaped_message)
        
        self.protocol = format(aux_protocol, '04x') # Atualiza o protocolo




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

        unescaped_message = Frame.get_package_unescaped(frame)
        if len(unescaped_message) > 0:
            # print("unescaped_message:", unescaped_message)
            address, control, protocol_bytearray, payload, checksum_int = Frame.get_package_deconstructed(unescaped_message)    # Desencapsula o quadro
            # print("payload:", payload)
            protocol_int = int.from_bytes(protocol_bytearray, 'big') # Converte o protocolo para inteiro
            if protocol_int == 1: # Erro proposital
                checksum_int+=1
            try:
                Frame.check_errors(address, control, protocol_bytearray, payload, checksum_int) # Verifica se há erros no quadro
                ACK = Frame.make_package_escaped(ADDS,CCTRL,protocol_int,bytearray())   # Cria o ACK
                ACK = Frame.get_package_escaped(ACK)
                self.link.send(ACK)
                return payload
            except Exception:                    
                print("Erro no quadro")
                self.link.send(bytearray())
                # return None
            # return payload

