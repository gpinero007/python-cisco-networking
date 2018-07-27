import operator, sys, netmiko, traceback
import os, platform, logging
import getpass
from netmiko import ConnectHandler
from datetime import datetime, date, time, timedelta
from select import select

## Logging
dia= datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

"""
##############     Ejemplos de como meter mensajes en el log ##################
#logging.debug('Comienza el programa')
#logging.info('Procesando con normalidad')
#logging.warning('Advertencia')
#logging.error('Error')
#logging.critical('Exception')"""

def get_date_now():
	""" Devuelve la fecha u la hora actual en formato Mysql"""
	dia= datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
	return (dia)

def question_yn(texto):
	""" question with timer 5s"""
	print texto
	resp, _, _ = select([sys.stdin], [], [], 5)
	if resp:
		if sys.stdin.readline()[:1] == "s":
			return True
	return False	

try:
	cisco_user = raw_input('Usuario: ')
	cisco_pass = getpass.getpass('Password: ')
	ipSw = raw_input("Dime la ip del switch: ")
	
	# Preparamos el log
	fichero_log = 'static_'+dia+'_'+ipSw+'.log'
	# Configuracion basica de los LOGS
	logging.basicConfig(
		level=logging.DEBUG,
		format='%(asctime)s : %(levelname)s : %(message)s',
		filename = fichero_log,
		filemode = 'w',)
	logging.info('#### SCRIPT INICIADO #### FECHA-HORA: '+dia+'########')
	logging.info("Empezamos switch: "+ipSw+ " el culpable es "+cisco_user)
	# Nos conectamos al equipo
	ssh_connection = ConnectHandler(device_type='cisco_ios', ip=ipSw, username=cisco_user, password=cisco_pass)
	ssh_connection.enable()
	ssh_connection.send_command("terminal length 0")
	
	
	tempfile = 'temp.txt'
	fasigna = 'asignacion.txt'
	# Comprobamos el numero de equipos en el stack
	runc = ssh_connection.send_command("show switch", delay_factor=5)
	# Fichero temporal
	outfile = open(tempfile, 'w')
	outfile.write(runc)
	outfile.close()
	
	# Contador de pila
	nstack = 0
	with open(tempfile) as f:
		for line in f:
			if 'Ready' in line:
				nstack += 1
	print ("Switches en stack: "+str(nstack))
	logging.info('Switches en stack: '+str(nstack))
	# Salimos si algo no cuadra
	#resp = raw_input("Es correcto (s/n)?")
	#if resp.lower() =="n":
	#	sys.exit()
	print ("####################################")
	### PARA TEST interfaz = "gigabitEthernet1/0/2"
	# nswitch: numero de switch en la pila
	# nport: numero de puerto de switch 1-48
	for nswitch in range(1,nstack+1):
		for nport in range(1,49): #Switches de 48 puertos en stack este script no detecta la cantidad de puertos
			interfaz = "gigabitEthernet%d/0/%d"%(nswitch,nport)
			runc = ssh_connection.send_command("show run int "+interfaz, delay_factor=5)
			# Vemos la configuracion del puerto y la grabamos para consulta
			outfile = open(tempfile, 'w')
			outfile.write(runc)
			outfile.close()
			confestatica= True
			# Recorremos la config del puerto a ver si tiene MAB
			with open(tempfile) as f:
				for line in f:
					# Si tiene el MAB configurado en la interfaz
					if 'authentication order mab' in line:
						# Ese puerto lo marcamos como no estatico
						confestatica = False
						# Vemos en que VLAN esta asignado
						print interfaz+" tiene MAB habilitado"
						logging.info(interfaz+"--> MAB habilitado\n")
						runc2 = ssh_connection.send_command("show authentication sessions interface "+interfaz+" details", delay_factor=5)
						outfile2 = open(fasigna, 'w')
						outfile2.write(runc2)
						outfile2.close()
						nvoice = 0
						ndata = 0
						with open(fasigna) as f2:
							for line2 in f2:
								#Contamos la cantidad de equipos en DATA y VOICE
								if 'DATA' in line2:
									ndata+=1
								if 'VOICE' in line2:
									nvoice+=1
								# Leemos la VLAN que hay asignada
								if 'Vlan Group:' in line2:
									vlan_asig = line2.split(":")[2]
									vlan_asig = vlan_asig[1:]
									print (interfaz+" tiene vlan dinamica:"+vlan_asig)
									logging.info(interfaz+" tiene vlan dinamica:"+vlan_asig)
									if question_yn("Quieres hacer el cambio (s/n)?"):
										### Realizamos el cambio de config
										intport = "interface "+str(interfaz)
										switportvlan = "switchport access vlan "+str(vlan_asig)
										comandos_nomab= [intport, 'no authentication event fail', 'no authentication host-mode', 'no authentication order', 'no authentication priority', 'no authentication port-control','no mab',switportvlan,'shutdown','no shutdown']
										ssh_connection.send_config_set(comandos_nomab)
										print ("OK! - Configuracion estatica aplicada vlan:"+str(vlan_asig))
										print ("\n")
										logging.info("OK! - Configuracion estatica aplicada vlan:"+str(vlan_asig))
							#Puede que solo tenga telefono en el MAB
							if ndata == 0:
								if nvoice >0:
									print ("Solo activo el VOICE DOMAIN!!. Mira:")
									runc22 = ssh_connection.send_command("show mac address-table interface "+interfaz, delay_factor=5)
									print (runc22)
									print ("\n")
									logging.warning(interfaz+"--> Solo tiene conectado un telefono")
									logging.info(runc22)
								# Y ademas si nvoice es 0 es que no hay nada en ese puerto
								else:
									print ("No hay MACs en el puerto!! Te muestro el trafico y tu decides\n")
									runc23 = ssh_connection.send_command("show interface "+interfaz+" stats", delay_factor=5)
									print (runc23)
									print ("\n")
									logging.warning(interfaz+"--> No hay mac en el puerto \n")
									logging.info(runc23)
									if question_yn("Quieres cambiarlo tu a mano (s/n)?"):
										### Realizamos el cambio de config
										respv = raw_input("En que VLAN configuro el puerto?: ")
										intport = "interface "+str(interfaz)
										switportvlan = "switchport access vlan"+respv
										comandos_nomab= [intport, 'no authentication event fail', 'no authentication host-mode', 'no authentication order', 'no authentication priority', 'no authentication port-control','no mab',switportvlan,'shutdown','no shutdown']
										ssh_connection.send_config_set(comandos_nomab)
										print ("OK! - Configuracion estatica aplicada vlan:"+respv)
										print ("\n")
										logging.info("OK! - No habia trafico y me han dicho que ponga vlan: "+respv)
					elif confestatica and 'end' in line:
						print interfaz+" no tiene MAB configurado\n"
	print ("Hemos terminado!... puedes consultar el log para mas info.")
	resp = raw_input("Grabo los cambios en el switch (s/n)?")
	if resp.lower() =="s":
		comandos_wr = ['wr']
		ssh_connection.send_config_set(comandos_wr)
	print ("Adios muchacho!!")
	ssh_connection.disconnect()
except Exception as e:
	print(e)
	traceback.print_exc()
	logging.critical(e)
