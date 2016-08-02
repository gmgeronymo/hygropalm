# Programa para ler condicoes ambientais do termohigrometro
# Rotronic Hygropalm 2 via interface RS-232
# Autor: Gean M. Geronymo
# Data: 20/04/2016

# carrega as bibliotecas necessarias
import serial       # interface RS-232
import time
import psycopg2     # interface com PostgreSQL
import datetime     # funcoes de data e hora
import configparser # ler arquivo de configuracao
import csv          # salvar dados antes de enviar ao DB

# o arquivo settings.ini reune as configuracoes que podem ser alteradas

config = configparser.ConfigParser()    # iniciar o objeto config
config.read('settings.ini')             # ler o arquivo de configuracao

# configuracao da conexao serial
# seguindo informacoes do manual do fabricante
ser = serial.Serial(
    port=config['SerialConfig']['port'],
    baudrate=19200,
    parity=serial.PARITY_EVEN,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.SEVENBITS,
    timeout = int(config['SerialConfig']['timeout'])
    )

querystring = config['SerialConfig']['querystring']
# envia para o termohigrometro a query string com o terminador de linha \r
#ser.write(b'{u00RDD}\r')
ser.write((querystring+'\r').encode())

# le a resposta do termohigrometro
rcv_str = ser.read(50)
# fecha a conexao serial
ser.close()

# transformar o byte object recebido em uma string
dec_str = rcv_str.decode('utf-8')
# processa a string para extrair os valores de temperatura e umidade
# o termohigrometro retorna uma string do tipo:
# '{u00RDD 0071.68;0022.78;----.--;----.--;#6\r'
# o comando abaixo remove o trecho
# '{u00RDD '
# Assim, e possivel separar temperatura e umidade utilizando ';'
data_array = (dec_str.replace(querystring.replace('}',' '),'')).split(';')
# arredonda a temperatura e umidade para uma casa decimal
temperature = round(float(data_array[1]),1)
humidity = round(float(data_array[0]),1)

# data e hora
date = datetime.datetime.now();
timestamp = datetime.datetime.strftime(date, '%Y-%m-%d %H:%M:%S')
data = datetime.datetime.strftime(date, '%d/%m/%Y')
hora = datetime.datetime.strftime(date, '%H:%M')
ano = datetime.datetime.strftime(date, '%Y')

# escrever em arquivo texto (compatibilidade com versao antiga)
with open("Log_"+ano+".txt","a") as text_file:
    print("{}\t{}\t{}%\t{}ºC".format(data,hora,int(humidity),temperature), file=text_file)
text_file.close();

# escrever a ultima leitura no arquivo TermHigr.dat
# compatibilidade com o programa de medicao
with open("TermHigr.dat","w") as text_file:
    print("{}\n{}\n{}\n{}".format(data,hora,int(humidity),temperature), file=text_file)
text_file.close();

# escrever a ultima leitura no arquivo TermHigr.txt
with open("TermHigr.txt","w") as text_file:
    print("{}\t{}\t{}%\t{}ºC".format(data,hora,int(humidity),temperature), file=text_file)
text_file.close();

# buffer de escrita para o banco de dados
# salva as informacoes em um arquivo txt, quando conseguir conexao com o DB,
# envia todas as informacoes

with open("write_buffer.txt","a") as csvfile:
    write_buffer = csv.writer(csvfile, delimiter=',',lineterminator='\n')
    write_buffer.writerow([str(temperature),str(humidity),timestamp])
csvfile.close();
# conectar ao banco de dados
try:
    conn = psycopg2.connect("dbname={} user={} password={} host={}".format(config['DatabaseConfig']['dbname'],config['DatabaseConfig']['user'],config['DatabaseConfig']['password'],config['DatabaseConfig']['host']))
except:
    print("error")
    
with open("write_buffer.txt") as csvfile:
    reader = csv.DictReader(csvfile,delimiter=',',fieldnames=['temperature','humidity','date'])
    d = list(reader)
csvfile.close();
# cursor
cur = conn.cursor()
# envia dados para o banco de dados
try:
    cur.executemany("""INSERT INTO condicoes_ambientais (temperature, humidity, date) VALUES (%(temperature)s, %(humidity)s, %(date)s);""",d)
except:
    print("error")

open('write_buffer.txt','w').close()
# salva as alteracoes
conn.commit()
cur.close()
# fecha a conexao
conn.close()

