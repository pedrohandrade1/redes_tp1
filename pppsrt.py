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
import random
import time

FLAG = 0x7E #Flag
ADDS= 0xFF #Address
DCTRL = 0x03 #Control de dados
CCTRL = 0x07 #Control de confirmação ACK


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
        # Stream vazia
        if len(stream) == 0:
            raise EOFError

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

        raise SyntaxError("package with not two flags")
    
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
            raise Exception("unescape especial byte error")

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

    def send(self, message):
        aux_protocol = int(self.protocol, 16)

        # Incrementa o protocolo              
        aux_protocol += 1

        # Protocolo 0 representa NACK
        if aux_protocol == 0:
            aux_protocol += 1

        # Cria o payload em bytearray                                                               
        payload = bytearray(message)         

        # Cria o pacote                                           
        package_escaped = Frame.make_package_escaped(ADDS, DCTRL, aux_protocol, payload)   

        # Envia o pacote
        print("Transmitting: ", aux_protocol)
        self.link.send(package_escaped)
        
        # Aguarda a confirmação
        try:
            while True: 
                # Obtem ACK
                ack_message = self.link.recv(1500)
                ack_escaped = Frame.get_package_escaped(ack_message)
                ack_unescaped = Frame.get_package_unescaped(ack_escaped)
                _, control, protocol_bytearray, _, _ = Frame.get_package_deconstructed(ack_unescaped)
                protocol_int = int.from_bytes(protocol_bytearray, 'big')

                # Se o protocolo e o controle estiverem corretos
                if control == CCTRL and protocol_int == aux_protocol: 
                    print("ACK arrive in time: ", protocol_int)
                    break
                else: 
                    print("Retransmitting: ", aux_protocol)
                    self.link.send(package_escaped)

            # Atualiza o protocolo
            self.protocol = format(aux_protocol, '04x') 

        # Confirmação não chegou a tempo
        except TimeoutError: 
            print("ACK did not arrive in time: ", aux_protocol)

            # Retransmite pacote
            self.send(message)
        

    def recv(self):
        try:
            frame = self.link.recv(1500)

            # Obtem pacote
            package_escaped = Frame.get_package_escaped(frame)
            package_unescaped = Frame.get_package_unescaped(package_escaped)

            # Desencapsula o quadro
            address, control, protocol_bytearray, payload, checksum_int = Frame.get_package_deconstructed(package_unescaped)    

            # Converte o protocolo para inteiro
            protocol_int = int.from_bytes(protocol_bytearray, 'big') 

            try:
                # Verifica se há erros no quadro
                Frame.check_errors(address, control, protocol_bytearray, payload, checksum_int) 

                # Cria o ACK
                ack_escaped = Frame.make_package_escaped(ADDS, CCTRL, protocol_int, bytearray())

                # Envia o ACK   
                self.link.send(ack_escaped)

                return payload

            #  Se houver erro, avisa pelo NACK com um protocol 0 e descarta o quadro         
            except Exception:         
                print("Checksum error!")

                # Cria o NACK
                nack_escaped = Frame.make_package_escaped(ADDS,CCTRL,0,bytearray())

                # Envia o NACK
                self.link.send(nack_escaped)
            
                # Escuta novamente
                return self.recv() 

        # Tratando temporizações
        except TimeoutError: 
            print("Timeout error!")

        # Erro no enquadramento
        except SyntaxError:  
            print("Framing error!")

            # Escuta novamente
            return self.recv() 
        
        # Canal Vazio
        except EOFError:
            print("EOF!")

            return
        
