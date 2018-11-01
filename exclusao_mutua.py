import socket
import sys
import threading
import time
import json

PORTAS_PROCESSOS = [10000, 10001, 10002]
NUMPROCESS = 3


#############################################################################
# Imprimir resultados
#############################################################################

# Imprime a fila de resursos em uso
def imprimirRecursosEmUso(listaRecursosEmUso):
	print("#################################################################")
	
	if not listaRecursosEmUso:
		print("# Não há recursos sendo utilizados")
	
	for registro in listaRecursosEmUso:
		print("# Recurso: {} | Tempo: {}".format(registro["nomeRecurso"], registro["tempo"]))
	
	print("#################################################################")


# Imprime a fila de resursos solicitados
def imprimirRecursosSolicitados(listaRecursosSolicitados):
	print("#################################################################")
	
	if not listaRecursosSolicitados:
		print("# Não há recursos solicitados")
	
	for registro in listaRecursosSolicitados:
		print("# Recurso: {} | Marca de Tempo: {} | Num ACKS: {} | Tempo: {}".format(registro["nomeRecurso"], 
			registro["marcaTempo"], registro["numACKS"], registro["tempo"]))
	
	print("#################################################################")

#############################################################################
# Consumo de recursos
#############################################################################

# Consome os recursos em uso (a cada 10 segundos decrementa o contador de tempo do recurso)
def consumir(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSolicitados, listaRecursosACK, listaProcessosProximos):
	
	while(True):
		print("\nRecursos em uso")
		imprimirRecursosEmUso(listaRecursosEmUso)
		print("\nRecursos solicitados")
		imprimirRecursosSolicitados(listaRecursosSolicitados)

		time.sleep(10)
		for i in range(len(listaRecursosACK)):
			listaRecursosACK[i]["tempo"] = listaRecursosACK[i]["tempo"] - 1
			if listaRecursosACK[i]["tempo"] == 0:
				del listaRecursosEmUso[i]
				# Enviar ACK para os outros processos dizendo que o recurso foi liberado

# Envia o recurso para ser consumido
def enviarConsumir(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSolicitados, listaRecursosACK, listaProcessosProximos):

	while(True):
		time.sleep(1)
		
		# Verifica se alguma solicitação recebeu todos os ACKS
		for i in range(len(listaRecursosSolicitados)):
			if listaRecursosSolicitados[i]["numACKS"] == NUMPROCESS-1:
				
				# Verifica se recurso não está em uso
				existe = False
				for j in range(len(listaRecursosEmUso)):
					if listaRecursosEmUso[j]["recurso"] == listaRecursosSolicitados[i]["nomeRecurso"]:
						existe = True
				

				listaRecursosEmUso.append({"tempo": listaRecursosSolicitados[i]["tempo"], "nomeRecurso": listaRecursosSolicitados[i]["nomeRecurso"]})
			del listaRecursosSolicitados[i]
			break

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
def gerenciarRecurso(mensagemJson, clockInicial, listaRecursosEmUso, listaRecursosSolicitados, listaRecursosACK, listaProcessosProximos, portaPross):
	mensagem = json.loads(mensagemJson.decode('utf-8'))
	print(mensagem)

	# Atualiza o relógio lógico
	updateClock(mensagem, clockInicial)

	# Ao receber um ACK é acrescetada a quantidade de elementos da file de ACKS daquele recurso
	if mensagem["tipoMensagem"] == "ACK":
		for registro in listaRecursosSolicitados:
			if registro["nomeRecurso"] == mensagem["nomeRecurso"]:
				registro["numACKS"] = registro["numACKS"] + 1
				break 

	# Ao receber um NACK somente é notificado que foi recebido um NACK
	elif mensagem["tipoMensagem"] == "NACK":
		print("Recebido NACK, recurso não está disponível ainda!")

	# Ao receber um requisição é verificado se o recuso está em uso ou na fila de solicitações
	# Caso esteja em uso é envidao um NACK e é acrescentado um registro na lista de solicitações
	# Caso esteja na fila de solicitações é 
	elif mensagem["tipoMensagem"] == "requisicao":
		
		# Atualiza o clock lógico para a mensagem que será enviada
		clockInicial[0] = clockInicial[0] + 1
		
		# Verificar se está na lista de recursos em uso. 
		# Caso estiver, envia NACK e acrescenta o id do processo que solicitou o recurso na lista de próximos
		for i in range(len(listaRecursosEmUso)):
			if listaRecursosEmUso[i]["nomeRecurso"] == mensagem["nomeRecurso"]:
				listaProcessosProximos[mensagem["nomeRecurso"]].append(mensagem["marcaTempo"][3:])
				listaProcessosProximos.sort(key=lambda x:x["marcaTempo"])
				
				mensagemJson = {"tipoMensagem": "NACK", "marcaTempo": str(clockInicial[0]).zfill(3) + str(idPross).zfill(3), 
					"marcaTempoSolicitacao": mensagem["marcaTempo"], "nomeRecurso": mensagem["nomeRecurso"]}
				enviarUnicast(json.dumps(mensagemJson), mensagem["portaPross"])

		# Verificar se está na lista de recursos solicitados


		# enviarMensagem de ACK
		mensagemJson = {"tipoMensagem": "ACK", "marcaTempo": str(clockInicial[0]).zfill(3) + str(idPross).zfill(3), "marcaTempoSolicitacao": mensagem["marcaTempo"], "nomeRecurso": mensagem["recurso"]}
		enviarUnicast(json.dumps(mensagemJson), mensagem["portaPross"])

#############################################################################
# Configuração de envio/recebimento mensagens com socket
#############################################################################

# Recebe mensagens via socket UDP
def receiver(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSolicitados, listaRecursosACK, listaProcessosProximos):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	server_address = ('', PORTAS_PROCESSOS[portaPross])
	sock.bind(server_address)

	while(True):
		data, address = sock.recvfrom(4096)
		gerenciarRecurso(data, clockInicial, listaRecursosEmUso, listaRecursosSolicitados, listaRecursosACK, listaProcessosProximos, portaPross)

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
listaRecursosSolicitados = []
listaRecursosACK = []
listaProcessosProximos = []

portaPross = int(input("Digite a porta do processo (0-2): "))
idPross = int(input("Digite o id do processo: "))
clockInicial = input("Digite o clock inicial: ")
clockInicial = [int(clockInicial)]

# Cria thead responśvel por receber as mensagens
t1 = threading.Thread(target=receiver, args=(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSolicitados, listaRecursosACK, listaProcessosProximos))
t1.start()

# Cria thread que é responsável por consumir os recursos
t2 = threading.Thread(target=consumir, args=(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSolicitados, listaRecursosACK, listaProcessosProximos))
t2.start()

# Envia solicitações para consumo
t3= threading.Thread(target=enviarConsumir, args=(idPross, portaPross, clockInicial, listaRecursosEmUso, listaRecursosSolicitados, listaRecursosACK, listaProcessosProximos))
t3.start()

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
			break

	for i in range(len(listaRecursosSolicitados)):
		if listaRecursosSolicitados[i]["nomeRecurso"] == recurso:
			podeSocilitar = False
			break

	if podeSocilitar == False:
		print("Recurso já está em uso ou já foi solicitado!")
	else:
		clockInicial[0] = clockInicial[0]+1
		listaRecursosSolicitados.append( {"nomeRecurso": recurso, "marcaTempo": str(clockInicial[0]).zfill(3) + str(idPross).zfill(3), "tempo": tempo, "numACKS": 0} )
		listaRecursosSolicitados.sort(key=lambda x:x["marcaTempo"])
		mensagemJson = {"tipoMensagem": "requisicao" , "marcaTempo": str(clockInicial[0]).zfill(3) + str(idPross).zfill(3), "recurso": recurso, "tempo": tempo, "portaPross": portaPross}
		mensagem = json.dumps(mensagemJson)
		enviarBroadcast(mensagem, portaPross)


# Formato mensagem ACK: mensagemJson = {"tipoMensagem": "ACK", "marcaTempo": str(clockInicial[0]).zfill(3) + str(idPross).zfill(3), 
#					"marcaTempoSolicitacao": mensagem["marcaTempo"], "nomeRecurso": mensagem["nomeRecurso"]}
#
# Formato mensagem NACK: mensagemJson = {"tipoMensagem": "NACK", "marcaTempo": str(clockInicial[0]).zfill(3) + str(idPross).zfill(3), 
#					"marcaTempoSolicitacao": mensagem["marcaTempo"], "nomeRecurso": mensagem["nomeRecurso"]}
#
# Formato mensagem Requisicao: {"tipoMensagem": "requisicao" , "marcaTempo": str(clockInicial[0]).zfill(3) + str(idPross).zfill(3), 
# 					"recurso": recurso, "tempo": tempo, "portaPross": portaPross}