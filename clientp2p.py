import argparse
# Стандартный модуль argparse.
# Подробнее: https://docs.python.org/3/library/argparse.html
import socket
# Стандартный модуль socket.
# Подробнее: https://docs.python.org/3/library/socket.html
import sys
# Стандартный модуль sys.
# Подробнее: https://docs.python.org/3/library/sys.html
import time
# Стандартный модуль time.
# Подробнее: https://docs.python.org/3/library/time.html
import json
# Стандартный модуль json.
# Подробнее: https://docs.python.org/3/library/json.html

import threading
import rncryptor

# Стандартный модуль threading.
# Подробнее: https://docs.python.org/3/library/threading.html

# Глобальная переменная, отвечающая за остановку клиента.
shutdown = False


class Message:
   def __init__(self, **data):
       # Устанавливаем дополнительные атрибуты сообщения.
       self.status = 'online'
       # Распаковываем кортеж именованных аргументов в параметры класса.
       # Паттерн Builder
       for param, value in data.items():
           setattr(self, param, value)

       # время получения сообщения.
       self.curr_time = time.strftime("%Y-%m-%d-%H.%M.%S",
                                      time.localtime())

   def to_json(self):
       return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True,
                         indent=4)

class P2PClient:
   def __init__(self, host, port, password, name=None):
       # Атрибут для хранения текущего соединения:
       self.current_connection = None
       # Атрибут для хранения адреса текущего клиента
       self.client_address = (host, port)
       self.password = password

       # Если имя не задано, то в качестве имени сохраняем адрес клиента:
       if name is None:
           self.name = f"{host[0]}:{port[1]}"
       else:
           self.name = name
       # Создаем сокет, как это делали в предыдущей работе:
       self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
       # Запускаем "прослушивание" указанного адреса:
       self.socket.bind(self.client_address)

   def receive(self):
       global shutdown
       # Пока клиент не остановлен
       while not shutdown:
           try:
               # Получаем данные и адрес отправителя
               data, addr = self.socket.recvfrom(1024)
               data = dict(json.loads(data.decode('utf-8')))
               # Создаем объект сообщения из полученных данных:
               message = Message(**data)
               # Выводим сообщение в консоль:
               sender_name = getattr(message, 'sender_name', str(addr))
               text = self.decryptString(getattr(message, 'message', ''))
               sys.stdout.write(f'@{sender_name}: {text}\n')
               # Делаем небольшую задержку для уменьшения нагрузки:
               time.sleep(0.2)
           except socket.error as ex:
               # Если возникли проблемы с соединением, завершаем программу.
               print(f"P2PClient.receive: Что-то пошло не так: {ex}")
               shutdown = True
       self.socket.close()

   def send(self):
       global shutdown
       # Пока клиент не остановлен
       while not shutdown:
           # Ожидаем ввод данных
           input_data = input()
           if input_data:
               # Создаем объект сообщения из введенных данных:
               message = Message(message=self.encryptString(input_data),
                                 sender_name=self.name)
               # Отправляем данные:
               data = message.to_json()
               try:
                   self.socket.sendto(data.encode('utf-8'),
                                      self.current_connection)
               except socket.error as ex:
                   self.current_connection = None
                   self.send()
           time.sleep(0.2)

   def connect(self):
       # Пока клиент не остановлен и соединение не задано
       while not shutdown and not self.current_connection:
           # Вводим, куда подключаться:
           connect_data = input("Connect to (ip:port, like 127.0.0.1:8001):")
           try:
               # Приводим введенные данные к нужному виду (str, int).
               ip, port = connect_data.split(":")
               port = int(port)
               # Отправка сообщения о подключении:
               connect_message = Message(
                   message=self.encryptString(f'User @{self.name} wants to chat with you.\n'),
                   sender_name=self.name
               )
               data = connect_message.to_json()
               self.current_connection = (ip, port)
               self.socket.sendto(data.encode('utf-8'),
                                  self.current_connection)
           except (ValueError, TypeError, AttributeError, socket.error) as ex:
               print(f"Не удается соединиться с {connect_data}, "
                     f"по причине: {ex}.\nПопробуйте снова.")
               self.current_connection = None

   def run(self):
       self.connect()
       # В отдельном потоке вызываем обработку получения сообщений:
       recv_thread = threading.Thread(target=self.receive)
       recv_thread.start()
       # В главном потоке вызываем обработку отправки сообщений:
       self.send()
       # Прикрепляем поток с обработкой получения сообщений к главному потоку:
       recv_thread.join()

   def decryptString(self, string):
       cryptor = rncryptor.RNCryptor()
       decrypted_data = cryptor.decrypt(bytes.fromhex(string), self.password)
       return decrypted_data

   def encryptString(self, string):
       cryptor = rncryptor.RNCryptor()
       encrypted_data = cryptor.encrypt(string, password).hex()
       return encrypted_data

if __name__ == '__main__':
   # Задаем настройки распознавания параметров запуска используя argparse:
   parser = argparse.ArgumentParser()
   parser.add_argument("-ho", "--host",
                       help="p2p client host ip address, like 127.0.0.1")
   parser.add_argument("-p", "--port",
                       help="p2p client host port, like 8001")
   parser.add_argument("-pw", "--password",
                       help="symmetric encryption password")
   args = parser.parse_args()

   try:
       # Устанавливаем параметры P2P клиента
       host = args.host
       port = int(args.port)
       password = args.password
       name = input("Name: ").strip()
       # Создаем объект P2P клиента
       p2p_client = P2PClient(host, port, password, name=name)
       # Запускаем P2P клиента
       p2p_client.run()
   except (TypeError, ValueError):
       print("Incorrect arguments values, use --help/-h for more info.")
