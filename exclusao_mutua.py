import socket
import sys
import threading
import time
import json

PORTAS_PROCESSOS = [10000, 10001, 10002]
NUMPROCESS = 3


#############################################################################
# Consumo de recursos
#############################################################################

# Consome os recursos em uso (a cada 5 segundos decrementa o contador de tempo do recurso)
def consumir(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSoliciatados, listaRecursosACK):
	
	while(True):
		time.sleep(5)
		for i in range(len(listaRecursosACK)):
			listaRecursosACK[i]["tempo"] = listaRecursosACK[i]["tempo"] - 1
			if listaRecursosACK[i]["tempo"] == 0:
				del listaRecursosEmUso[i]
			# Enviar ACK para os outros processos dizendo que o recurso foi liberado



#############################################################################
# Processamento da mensagem
#############################################################################

# Atualiza o clock lógico do processo
def updateClock(mensagem, clockInicial):
    if(int(mensagem["marcaTempo"][:-3]) > clockInicial[0]):
        clockInicial[0] = int(mensagem["marcaTempo"][:-3]) + 1
    else:
    	clockInicial[0] = clockInicial[0] + 1


# Identificar o que a mensagem fará
def gerenciarRecurso(mensagemJson, clockInicial, listaRecursosEmUso, listaRecursosSoliciatados, listaRecursosACK, portaPross):
	mensagem = json.loads(mensagemJson.decode('utf-8'))
	print(mensagem)

	# Atualiza o relógio lógico
	updateClock(mensagem, clockInicial)

	if mensagem["tipoMensagem"] == "requisicao":
		print(mensagem)
		# colocarRecuso em uso
		#enviarMensagem de ACK

#############################################################################
# Configuração de envio/recebimento mensagens com socket
#############################################################################

# Recebe mensagens via socket UDP
def receiver(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSoliciatados, listaRecursosACK):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	server_address = ('', PORTAS_PROCESSOS[portaPross])
	sock.bind(server_address)

	while(True):
		data, address = sock.recvfrom(4096)
		gerenciarRecurso(data, clockInicial, listaRecursosEmUso, listaRecursosEmUso, listaRecursosSoliciatados, portaPross)

# Envia mensagens em Unicast
def sender(mensagem, portaPross):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	server_address = ('', portaPross)
	sent = sock.sendto(mensagem.encode('utf-8'), server_address)

# Enviar mensagem em Unicast
def enviarUnicast(mensagem, portaPross):
	sender(mensagem, PORTAS_PROCESSOS[portaPross])

# Envia mensagem em Broadcast
def enviarBroadcast(mensagem, portaPross):
	for i in range(NUMPROCESS):
		if i == portaPross:
			continue;
		enviarUnicast(mensagem, i)

#############################################################################
# Programa principal
#############################################################################

# Inicio programa
listaRecursosEmUso=[]
listaRecursosSoliciatados = []
listaRecursosACK = []

portaPross = int(input("Digite a porta do processo (0-2): "))
idPross = int(input("Digite o id do processo: "))
clockInicial = input("Digite o clock inicial: ")
clockInicial = [int(clockInicial)]

# Cria thead responśvel por receber as mensagens
t1 = threading.Thread(target=receiver, args=(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSoliciatados, listaRecursosACK))
t1.start()

# Cria thread que é responsável por consumir os recursos
t2 = threading.Thread(target=consumir, args=(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSoliciatados, listaRecursosACK))
t2.start()

# Thread principal é responsável por solicitar recursos aos outros processos
while(True):
	time.sleep(0.5);
	input()
	recurso =  input("Nome do recurso a ser utilizado: ")
	tempo = int(input("Tempo que o recurso será utilizado: "))
	print("")

	# Verifica se o recurso está em uso ou já foi solicitado, caso contrário ele é solicitado.
	podeSocilitar = True

	for i in range(len(listaRecursosEmUso)):
		if listaRecursosEmUso[i]["nomeRecurso"] == recurso:
			podeSocilitar = False

	for i in range(len(listaRecursosSoliciatados)):
		if listaRecursosSoliciatados[i]["nomeRecurso"] == recurso:
			podeSocilitar = False
	
	if podeSocilitar == False:
		print("Recurso já está em uso ou já foi solicitado!")
	else:
		listaRecursosSoliciatados.append( {"nomeRecurso": recurso, "marcaTempo": str(clockInicial[0]+1).zfill(3) + str(idPross).zfill(3), "tempo": tempo} )
		listaRecursosSoliciatados.sort(key=lambda x:x["marcaTempo"])
		mensagemJson = {"tipoMensagem": "requisicao" , "marcaTempo": str(clockInicial[0]+1).zfill(3) + str(idPross).zfill(3), "recurso": recurso, "tempo": tempo}
		mensagem = json.dumps(mensagemJson)
		enviarBroadcast(mensagem, portaPross)