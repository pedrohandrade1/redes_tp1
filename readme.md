01111110 (0x7E) Flag

11111111 (0xFF) Address

00000011 (0x03) Control de dados

00000111 (0x07) Control de confirmação ACK

16 bits Protocol para numerar quadro de dados e confirmações

Payload tamanho variável até 1500 bytes

16 bits CheckSum

8 bits Flag

01111101 (0x7d) Escape para byte stuffing quando presentes no payload quadro, bytes com valor 0x7d e 0x7e 
são substituídos por 0x5d e 0x5e, respectivamente.
Isto é, um byte 0x7d no meio de um quadro será substituído pelo par 0x7d 0x5d;
um byte 0x7e será substituído por 0x7d 0x5ee