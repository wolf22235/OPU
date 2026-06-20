import socket
import struct
from commands import CMD_POWERSTEP01

class motor(CMD_POWERSTEP01):
    """Класс для работы с шаговым двигателем"""
    def __init__(self):
        super().__init__()

        self.IP = "192.168.1.2"
        self.PORT = 5000
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.mask = {
            'MASK_0': 1, # 1 - контроллер обрабатывает сигналы на соответствующем физическом входе
            'MASK_1': 1, # 0 - не обрабатывает
            'MASK_2': 1,
            'MASK_3': 1,
            'MASK_4': 1,
            'MASK_5': 1,
            'MASK_6': 1,
            'MASK_7': 1
        }

    def authorization(self):
        """ 
        Авторизация и подключение к контроллеру через TCP\\
        """
        self.client.connect((self.IP, self.PORT))
        # При создании TCP соединения от контроллера приходит сообщение
        self.client.recv(2048)

        # Отправляем пароль для подключения
        msg = self.CODE_CMD_REQUEST()
        byte_msg = struct.pack('14B', *msg)
        self.client.sendall(byte_msg)

        #Ждем порлучения ответа
        byte_response = self.client.recv(2048)
        print("\nauthorization:")
        print(f'to server: {msg}')
        #print(f'from server: {byte_response}')
        result = self.response_processing(byte_response)
        return result


    def set_movement_parameters(self, speed_min: int, speed_max: int, acc: int, dec: int):
        """Задание основных параметров движения: 
        минимальной и маскимальной скоростей движения, ускорения и замедления"""
        list_light = [] # 0 - зелен, 1 - красн

        # Задаем макс скорость (от 16 до 15600 шаг/сек)
        msg1 = self.SET_MAX_SPEED(speed_max)
        byte_msg = struct.pack('10B', *msg1)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        colour = self.response_processing(byte_response)
        list_light.append(colour)

        print("\nset_max_speed:")
        print(f'to server: {msg1}')
        #print(f'from server: {byte_response}')

        # Задаем мин скорость (от 0 до 950 шаг/сек)
        msg2 = self.SET_MIN_SPEED(speed_min)
        byte_msg = struct.pack('10B', *msg2)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        colour = self.response_processing(byte_response)
        list_light.append(colour)

        print("\nset_min_speed:")
        print(f'to server: {msg2}')
        #print(f'from server: {byte_response}')

        # Задаем ускорение (от 15 до 59000 шаг/сек^2)
        msg3 = self.SET_ACC(acc)
        byte_msg = struct.pack('10B', *msg3)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        colour = self.response_processing(byte_response)
        list_light.append(colour)

        print("\nset_acc:")
        print(f'to server: {msg3}')
        #print(f'from server: {byte_response}')

        # Задаем замедление (от 15 до 59000 шаг/сек^2)
        msg4 = self.SET_DEC(dec)
        byte_msg = struct.pack('10B', *msg4)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        colour = self.response_processing(byte_response)
        list_light.append(colour)

        print("\nset_acc:")
        print(f'to server: {msg4}')
        #print(f'from server: {byte_response}')

        return list_light

    def get_movement_parameters(self):
        """Считывание с контроллера характеристик движения: 
        минимальной и маскимальной скоростекй движения, ускорения и замедления"""
        # Минимальная скорость на контроллера
        msg1 = self.GET_MIN_SPEED()
        byte_msg = struct.pack('10B', *msg1)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        min_speed = self.response_processing(byte_response)

        print("\nget_min_speed:")
        print(f'to server: {msg1}')
        #print(f'from server: {byte_response}')

        msg1 = self.GET_MAX_SPEED()
        byte_msg = struct.pack('10B', *msg1)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        max_speed = self.response_processing(byte_response)

        print("\nget_max_speed:")
        print(f'to server: {msg1}')
        #print(f'from server: {byte_response}')

        return min_speed, max_speed
        

    def set_mode_parameters(self):
        '''Установка параметров системы'''
        # Предварительно нужно считать данные с интерфейса
        msg = self.SET_MODE()
        byte_msg = struct.pack('10B', *msg)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        colour = self.response_processing(byte_response)

        print("\nset_mode:")
        print(f'to server: {msg}')
        #print(f'from server: {byte_response}')

        return colour


    def get_mode_parameters(self):
        """Считывание с контроллера параметров работы системы"""
        msg = self.GET_MODE()
        byte_msg = struct.pack('10B', *msg)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        self.response_processing(byte_response)

        print("\nset_mode:")
        print(f'to server: {msg}')
        #print(f'from server: {byte_response}')


    def run_f_or_r(self, direction: str):
        """Начало движения двигателя в прямом (f) или обратном (r) направлении"""
        if direction == 'f':
            msg = self.RUN_F()
            print("\nrun_f:")
        else:
            msg = self.RUN_R()
            print("\nrun_r:")
        byte_msg = struct.pack('10B', *msg)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        result = self.response_processing(byte_response)

        print(f'to server: {msg}')
        #print(f'from server: {byte_response}')
        return result


    def hard_stop(self):
        '''Резкая остановка двигателя без обесточивания обмоток'''
        msg = self.HARD_STOP()
        byte_msg = struct.pack('10B', *msg)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        result = self.response_processing(byte_response)

        print("\nhard_stop:")
        print(f'to server: {msg}')
        #print(f'from server: {byte_response}')
        return result


    def soft_stop(self):
        '''Плавная остановка двигателя без обесточивания обмоток'''
        msg = self.SOFT_STOP()
        byte_msg = struct.pack('10B', *msg)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        result = self.response_processing(byte_response)

        print("\nhard_stop:")
        print(f'to server: {msg}')
        #print(f'from server: {byte_response}')
        return result


    def move_to_f_or_r(self, distance: int, direction: str):
        '''Перемещение двигателя в прямом или обратном направлении на указанную величину в микрошагах'''
        if direction == 'f':
            msg = self.MOVE_F(distance)
            print("\nmove_f:")
        else:
            msg = self.MOVE_R(distance)
            print("\nmove_r:")
        byte_msg = struct.pack('10B', *msg)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        result = self.response_processing(byte_response)

        print(f'to server: {msg}')
        #print(f'from server: {byte_response}')

        return result

    def set_zero(self):
        '''Обнуление счетчика нулевого положения. Текущее положение двигателя принимается за нулевое'''
        msg = self.RESET_POS()
        byte_msg = struct.pack('10B', *msg)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        result = self.response_processing(byte_response)

        print("\nreset_pos:")
        print(f'to server: {msg}')
        #print(f'from server: {byte_response}')
        return result


    def go_zero(self):
        '''Перемещение в нулевое положение'''

    
    def end_work(self):
        '''Завершение работы и плавная остановка двигателя с обесточиванием обмоток'''
        msg = self.HARD_HI_Z()
        byte_msg = struct.pack('10B', *msg)
        self.client.sendall(byte_msg)

        byte_response = self.client.recv(2048)
        result = self.response_processing(byte_response)

        print("\nhard_hi_z:")
        print(f'to server: {msg}')
        #print(f'from server: {byte_response}')

        # Разрываем соединение
        self.client.close()
        return result

    
    ############### Функции дополнительных рассчетов ###########
    def response_processing(self, byte_response: bytes):
        ''' Обработка сообщений, пришедших с сервера'''
        type_response = byte_response[8] # поле ERROR_OR_COMMAND в пришедшем сообщении
        
        if type_response <= 1:
            """Успешная авторизация или успешное задание параметра или режима работы"""
            msg = self.ERROR_OR_COMMAND[str(type_response)]['msg']
            print(msg)
            # Можно добавить задание цветового индикатора (ошибка или нет)
            return 0

        elif type_response > 1 and type_response < 12:
            """Errors"""
            msg = self.ERROR_OR_COMMAND[str(type_response)]['msg']
            print(msg)
            return 1

        elif type_response == 15:
            '''Получение MODE parameters'''
            data = byte_response[9:] # младшим байтом вперед
            bits_string = self.bytes_to_bits(data)

            # Записвываем полученные значения в параметры 
            p1 = self.CURENT_OR_VOLTAGE = int('0b' + bits_string[-1], 2) # ток
            p2 = self.MOTOR_TYPE = int('0b' + bits_string[-7:-1], 2) # последовательное соединение обмоток
            p3 = self.MICROSTEPPING = int('0b' + bits_string[-10:-7], 2) # 1/16 - дробление шага
            p4 = self.WORK_CURRENT = int('0b' + bits_string[-17:-10], 2) # - 1 А
            p5 = self.STOP_CURRENT = int('0b' + bits_string[-19:-17], 2)
            #self.PROGRAM_N = int('0b' + bits_string[-21:-19], 2)
            print(f'parameters: {p1}, {p2}, {p3}, {p4}, {p5}')
            return None

        elif type_response >= 18 and type_response <= 20:
            """speed"""
            data = byte_response[9:]
            # Преобразование в int с указанием формата - младшим байтом вперед
            speed = int.from_bytes(data, byteorder = 'little')
            return speed

    def bytes_to_bits(self, byte_string: bytes):
        """Переводит байтовую строку, записанную младшим байтом вперед, в битовую строку"""
        # Записываем старшим байтом вперед
        reversed_bytes = byte_string[::-1]
        # Формируем список битовых строк, дополненных нулями слева до 8 символов в каждой строке
        list_bits = ['{:08b}'.format(byte) for byte in reversed_bytes]
        # Объединяем в единую строку
        return ''.join(list_bits)

    def to_pack(self):
        data = [0x72, 0x03, 0x02, 0x02, 0x04, 0x00, 0x60, 0x02, 0x01, 0x01]
        #print(struct.pack('10I', *data))
        print()
        print(struct.pack('10B', *data).hex())
        return data


if __name__ == '__main__':
    #print(hex(100))
    data = [0x20, 0x03]
    #print(hex(XOR_SUM([0x72, 0x03, 0x02, 0x02, 0x04, 0x00, 0x60 , 0x20, 0x03, 0x00])))

    motor1  = motor()
    #motor1.SET_MODE()
    data = [0x72, 0x03, 0x02, 0x02, 0x04, 0x00, 0x60 , 0x20, 0x0F, 0x03, 0x49, 0x04, 0x00]
    data_bytes = struct.pack('13B', *data)
    motor1.response_processing(data_bytes)

    #motor1.set_movement_parameters_test(speed_min = 500, speed_max = 500, acc = 500, dec = 500)
    #byte_string = b'\x04\x03\x02\x01'
    #bits = motor1.bytes_to_bits(byte_string)
    #print(bits)
    #motor1.MOVE_F(5000)
    #motor1.SET_DEC(100)
