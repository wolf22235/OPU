
class CMD_POWERSTEP01():
    def __init__(self):
        """ 
        Класс, составляющий сообщения, отправляемые в контроллер
        """
        self.CURENT_OR_VOLTAGE = 1 # ток
        self.MOTOR_TYPE = 30 # последовательное соединение обмоток
        self.MICROSTEPPING = 4 # 1/16 - дробление шага
        self.WORK_CURRENT = 15 # - 1,5 А
        self.STOP_CURRENT = 0 # - 25% от рабочего тока (0,25 А)

        self.ERROR_OR_COMMAND = {
            '0': {
                'response': 'OK',
                'msg': 'Без ошибок'
            },
            '1': {
                'response': 'OK_ACCESS',
                'msg': 'Получени доступ к управлению контроллером'
            },
            '2': {
                'response': 'ERROR_ACCESS',
                'msg': 'Ошибка получения доступа к управлению контроллером. Cоединение закрывается контроллером'
            },
            '3': {
                'response': 'ERROR_ACCESS_TIMEOUT',
                'msg': 'Не истек таймаут для повтороной авторизации (1 сек)'
            },
            '4': {
                'response': 'ERROR_XOR',
                'msg': 'Ошибка контрольной суммы команды'
            },
            '5': {
                'response': 'ERROR_NO_COMMAND',
                'msg': 'Такой команды не существет'
            },
            '6': {
                'response': 'ERROR_LEN',
                'msg': 'Ошибочная длина пакета'
            },
            '7': {
                'response': 'ERROR_RANGE',
                'msg': 'Выход за допустимый диапазон значений'
            },
            '8': {
                'response': 'ERROR_WRITE',
                'msg': 'Ошибка записи'
            },
            '9': {
                'response': 'ERROR_READ',
                'msg': 'Ошибка чтения'
            },
            '10': {
                'response': 'ERROR_PROGRAMS',
                'msg': 'Для внутреннего пользования'
            },
            '11': {
                'response': 'ERROR_WRITE_SETUP',
                'msg': 'Для внутреннего пользования'
            },
            '12': {
                'response': 'NO_NEXT',
                'msg': 'Для внутреннего пользования'
            },
            '13': {
                'response': 'END_PROGRAMS', # Не записываем программы в контроллер
                'msg': 'Конец программы'
            },
            '14': {
                'response': 'COMMAND_GET_STATUS_IN_EVENT',
                'msg': 'В поле данных RETURN_DATA содержится битовая карта входных сигналов'
            },
            '15': {
                'response': 'COMMAND_GET_MODE',
                'msg': 'В поле данных RETURN_DATA содержится битовая карта текущих настроек контроллера'
            },
            '16': {
                'response': 'COMMAND_GET_ABS_POS',
                'msg': 'В поле данных RETURN_DATA содержится текущее положение шагового двигателя в шагах'
            },
            '17': {
                'response': 'COMMAND_GET_EL_POS',
                'msg': 'В поле данных RETURN_DATA содержится текущее электрическое положение двигателя'
            },
            '18': {
                'response': 'COMMAND_GET_SPEED',
                'msg': 'В поле данных RETURN_DATA содержится текущая скорость двигателя'
            },
            '19': {
                'response': 'COMMAND_GET_MIN_SPEED',
                'msg': 'В поле данных RETURN_DATA содержится текущая установленная минимальная скорость двигателя'
            },
            '20': {
                'response': 'COMMAND_GET_MAX_SPEED',
                'msg': 'В поле данных RETURN_DATA содержится текущая установленная максимальная скорость двигателя'
            },
            '21': {
                'response': 'COMMAND_GET_STACK',
                'msg': 'В поле данных RETURN_DATA содержится информация о номере текущей выполняемой программы и номер выполнемой команды'
            },
            '22': {
                'response': 'STATUS_RELE_SET',
                'msg': 'Реле включено'
            },
            '23': {
                'response': 'STATUS_RELE_CLR',
                'msg': 'Реле выключено'
            },
        }

    def CODE_CMD_REQUEST(self):
        """ 
        Отправление пароля в контроллер при авторизации.
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x00 - авторизация\\
            CMD_IDENTIFICATION = 0x00 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x08\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xEF, 0xCD, 0xAB, 0x89, 0x67, 0x45, 0x23, 0x01] - пароль
        """
        msg = [0x00, 0x03, 0x00, 0x00, 0x08, 0x00, 0xEF, 0xCD, 0xAB, 0x89, 0x67, 0x45, 0x23, 0x01]
        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SET_MAX_SPEED(self, speed: int = 200):
        """ 
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x01 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x60 , speed]\\
            например, speed = 0x20, 0x03, 0x00
        """
        msg = [0x00, 0x03, 0x02, 0x01, 0x04, 0x00, 0x60]

        bytes_speed = calc_move_parameter(speed, '00')
        for byte in bytes_speed:
            msg.append(byte)
        print(msg)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    
    def SET_MIN_SPEED(self, speed: int = 100):
        """ 
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x02 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x50 , speed]\\
            например, speed = 0x20, 0x03, 0x00
        """
        #msg1 = [0x14, 0x03, 0x02, 0x02, 0x04, 0x00, 0x50 , 0x90, 0x01, 0x00] # speed min = 100
        msg = [0x00, 0x03, 0x02, 0x02, 0x04, 0x00, 0x50]
        
        bytes_speed = calc_move_parameter(speed, '00')
        for byte in bytes_speed:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg
    
    def SET_ACC(self, acc: int = 100):
        """ 
        Устанавливаем ускорение
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x03 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x70 , acc]\\
            например, acc = 0x20, 0x03, 0x00
        """
        #msg1 = [0xF3, 0x03, 0x02, 0x03, 0x04, 0x00, 0x70 , 0x90, 0x01, 0x00] # ускорение = 100
        #print(f'msg1: {msg1}')
        msg = [0x00, 0x03, 0x02, 0x03, 0x04, 0x00, 0x70]
        
        bytes_acc = calc_move_parameter(acc, '00')
        for byte in bytes_acc:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SET_DEC(self, dec: int = 200):
        """ 
        Устанавливаем замедление
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x04 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x80 , dec]\\
            например, dec = 0x20, 0x03, 0x00
        """
        msg1 = [0xE2, 0x03, 0x02, 0x04, 0x04, 0x00, 0x80 , 0x90, 0x01, 0x00] # замедление = 100
        msg = [0x00, 0x03, 0x02, 0x04, 0x04, 0x00, 0x80]
        
        bytes_dec = calc_move_parameter(dec, '00')
        for byte in bytes_dec:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def GET_SPEED(self):
        """ 
        Чтение текущего значения скорости\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x05 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x10 , 0x00, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x05, 0x04, 0x00, 0x10, 0x00, 0x00, 0x00]
        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SET_MODE(self):
        """ 
        Установка параметров управления двигателем\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x06 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x30 , DATA]\\
        """
        msg = [0x00, 0x03, 0x02, 0x06, 0x04, 0x00, 0x30]

        parameters_and_bits = [
            (0, 2), # значение парамметра и количесвто бит
            (self.CURENT_OR_VOLTAGE, 1),
            (self.MOTOR_TYPE, 6),
            (self.MICROSTEPPING, 3),
            (self.WORK_CURRENT, 7),
            (self.STOP_CURRENT, 2),
            (0, 3)
        ]
        binary_string = create_bit_string(parameters_and_bits)
        #print(binary_string)

        list_byts = byte_devision(binary_string, 3)
        #print(list_byts)

        for byte in list_byts:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR

        return msg
    
    def GET_MODE(self):
        """ 
        Чтение настроек управления двигателем\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x07 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x40 , 0x00, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x07, 0x04, 0x00, 0x40, 0x00, 0x00, 0x00]
        XOR = XOR_SUM(msg)
        msg[0] = XOR

        return msg

    def SET_MASK_IVENT(self, mask: list):
        """ 
        Маскирование входных сигналов\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x08 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xA0 , DATA]\\
        """
        msg = [0x00, 0x03, 0x02, 0x08, 0x04, 0x00, 0xA0]
        binary_string = '00'
        for i in range(8):
            bit = mask[f'MASK_{i}']
            binary_string = f'{bit}' + binary_string

        #print(binary_string)
        binary_string = '000000' + binary_string
        
        list_byts = byte_devision(binary_string, 3)
        #print(list_byts)

        for byte in list_byts:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg
    
    def GET_ABS_POS(self):
        """ 
        Чтение положения двигателя\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x09 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xB0 , 0x00, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x09, 0x04, 0x00, 0xB0 , 0x00, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg
    
    def GET_EL_POS():
        """ 
        Чтение электрического положения ротора двигателя\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x0A - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xC0 , 0x00, 0x00, 0x00]\\
            На этот запрос получаем текущий шаг и микрошаг
        """
        msg = [0x00, 0x03, 0x02, 0x0A, 0x04, 0x00, 0xC0 , 0x00, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def RUN_F(self, speed: int):
        """ 
        Старт непрерывного вращения двигателя в прямом направлении
        на указанной скорости\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x0B - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xE0 , speed]\\
        """
        msg = [0x00, 0x03, 0x02, 0x0B, 0x04, 0x00, 0xE0]
        bytes_speed = calc_move_parameter(speed, '00')
        for byte in bytes_speed:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg
    
    def RUN_R(self, speed: int):
        """ 
        Старт непрерывного вращения двигателя в прямом направлении
        на указанной скорости\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x0C - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xF0 , speed]\\
        """
        msg = [0x00, 0x03, 0x02, 0x0C, 0x04, 0x00, 0xF0]
        bytes_speed = calc_move_parameter(speed, '00')
        for byte in bytes_speed:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg
    
    def MOVE_F(self, distance: int):
        """ 
        Перемещение двигателя в прямом направлении НА
        указанную величину\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x0E - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x00 , distance]\\
            distance - скорее всего в микрошагах измеряется
        """
        msg = [0x00, 0x03, 0x02, 0x0E, 0x04, 0x00, 0x00]
        bytes_distance = calc_move_parameter(distance, '01')
        for byte in bytes_distance:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def MOVE_R(self, distance: int):
        """ 
        Перемещение двигателя в обратном направлении НА
        указанную величину\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x0F - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x10 , distance]\\
            distance - скорее всего в микрошагах измеряется
        """
        msg = [0x00, 0x03, 0x02, 0x0F, 0x04, 0x00, 0x10]
        bytes_distance = calc_move_parameter(distance, '01')
        for byte in bytes_distance:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def GO_TO_F(self, position):
        """ 
        Перемещение двигателя в заданную позицию в 
        прямом направлении\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x10 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x20 , position]\\
            position - скорее всего в микрошагах измеряется
        """
        msg = [0x00, 0x03, 0x02, 0x10, 0x04, 0x00, 0x20]
        bytes_position = calc_move_parameter(position, '01')
        for byte in bytes_position:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def GO_TO_R(self, position):
        """ 
        Перемещение двигателя в заданную позицию в 
        обратном направлении\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x11 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x30 , position]\\
            position - скорее всего в микрошагах измеряется
        """
        msg = [0x00, 0x03, 0x02, 0x11, 0x04, 0x00, 0x30]
        bytes_position = calc_move_parameter(position, '01')
        for byte in bytes_position:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def GO_UNIT_F(self, num: int):
        """ 
        Старт вращения двигателя в прямом направлении на максимальной скорости до 
        получения сигнала на вход, указанный в Data\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x12 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x40 , num_chanel]\\
            num_chanel - номер входа (от 0 до 7)
        """
        msg = [0x00, 0x03, 0x02, 0x12, 0x04, 0x00, 0x40]
        bytes_position = calc_move_parameter(num, '01')
        for byte in bytes_position:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def GO_UNIT_R(self, num: int):
        """ 
        Старт вращения двигателя в обратном направлении на максимальной скорости до 
        получения сигнала на вход, указанный в Data\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x13 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x50 , num_chanel]\\
            num_chanel - номер входа (от 0 до 7)
        """
        msg = [0x00, 0x03, 0x02, 0x13, 0x04, 0x00, 0x50]
        bytes_position = calc_move_parameter(num, '01')
        for byte in bytes_position:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SCAN_ZERO_F(self, speed: int):
        """ 
        Поиск нулевого положения в прямом направлении с заданной скоростью. Останавливается
        при получении сигнала на воходе SET_ZERO. При этом текущее положение принимается
        за новое нулевое\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x14 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x60 , speed]\\
            speed - скорость поиска нулевого значения 
        """
        msg = [0x00, 0x03, 0x02, 0x14, 0x04, 0x00, 0x60]
        bytes_speed = calc_move_parameter(speed, '01')
        for byte in bytes_speed:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SCAN_ZERO_R(self, speed: int):
        """ 
        Поиск нулевого положения в обратном направлении с заданной скоростью. Останавливается
        при получении сигнала на воходе SET_ZERO. При этом текущее положение принимается
        за новое нулевое\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x15 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x70 , speed]\\
            speed - скорость поиска нулевого значения 
        """
        msg = [0x00, 0x03, 0x02, 0x15, 0x04, 0x00, 0x70]
        bytes_speed = calc_move_parameter(speed, '01')
        for byte in bytes_speed:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SCAN_LABLE_F(self, speed: int):
        """ 
        Поиск метки положения в прямом направлении с заданной скоростью. Движение продолжается
        до поступления сигнала на воход IN1. При этом текущее положение принимается за новую метку\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x16 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x80 , speed]\\
            speed - скорость поиска метки
        """
        msg = [0x00, 0x03, 0x02, 0x16, 0x04, 0x00, 0x80]
        bytes_speed = calc_move_parameter(speed, '01')
        for byte in bytes_speed:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SCAN_LABLE_R(self, speed: int):
        """ 
        Поиск метки положения в обратном направлении с заданной скоростью. Движение продолжается
        до поступления сигнала на воход IN1. При этом текущее положение принимается за новую метку\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x17 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x90 , speed]\\
            speed - скорость поиска метки
        """
        msg = [0x00, 0x03, 0x02, 0x17, 0x04, 0x00, 0x90]
        bytes_speed = calc_move_parameter(speed, '01')
        for byte in bytes_speed:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def GO_ZERO(self):
        """ 
        Перемещение в нулевое положение\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x18 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xA0 , 0x01, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x18, 0x04, 0x00, 0xA0, 0x01, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def GO_LABEL(self):
        """ 
        Перемещение в положение, которое было отмечено как метка\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x19 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xB0 , 0x01, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x19, 0x04, 0x00, 0xB0, 0x01, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg
    
    def GO_TO(self, position: int):
        """ 
        Перемещение в заданное положение по кратчайшему пути\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x1A - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xC0 , position]\\
            position - скорость поиска метки
        """
        msg = [0x00, 0x03, 0x02, 0x1A, 0x04, 0x00, 0xC0]
        bytes_position = calc_move_parameter(position, '01')
        for byte in bytes_position:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def RESET_POS(self):
        """ 
        Обнуление счетчика текущего положения. После выполнения команды текущее положение
        принимается как нулевое\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x1B - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xD0 , 0x01, 0x00, 0x00]\\
            position - скорость поиска метки
        """
        msg = [0x00, 0x03, 0x02, 0x1B, 0x04, 0x00, 0xD0, 0x01, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def RESET_POWERSTEP01(self):
        """ 
        Полный аппаратный и програмный сброс модуля управления шагового двигателя
        (не контроллера в целом)\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x1C - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xE0 , 0x01, 0x00, 0x00]\\
            position - скорость поиска метки
        """
        msg = [0x00, 0x03, 0x02, 0x1C, 0x04, 0x00, 0xE0, 0x01, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        
        return msg

    def SOFT_STOP(self):
        """ 
        Полная остановка двигателя с заданным ускорением\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x1D - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xF0 , 0x01, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x1D, 0x04, 0x00, 0xF0 , 0x01, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        
        return msg

    def HARD_STOP(self):
        """ 
        Резкая остановка шагового двигателя. После остановки двигатель удерживает положение
        с заданным током удержания\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x1E - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x00 , 0x02, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x1E, 0x04, 0x00, 0x00 , 0x02, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        
        return msg

    def SOFT_HI_Z(self):
        """ 
        Плавная остановка шагового двигателя с заданным ускорением. После 
        остановки питание с обмоток двигателя снимается\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x1F - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x10 , 0x02, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x1F, 0x04, 0x00, 0x10 , 0x02, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        
        return msg

    def HARD_HI_Z(self):
        """ 
        Резкая отсановка и обесточивание обмоток двигателя\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x20 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x20 , 0x02, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x20, 0x04, 0x00, 0x20 , 0x02, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        
        return msg

    def SET_WAIT(self, pause: int):
        """ 
        Задание паузы\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x21 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x30 , pause]\\
            pause - время ожидания в мс
        """
        msg = [0x00, 0x03, 0x02, 0x21, 0x04, 0x00, 0x30]
        bytes_pause = calc_move_parameter(pause, '10')
        for byte in bytes_pause:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        
        return msg
    
    def SET_RELE(self):
        """ 
        Включение реле контроллера\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x22 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x40 , 0x02, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x22, 0x04, 0x00, 0x40 , 0x02, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        
        return msg

    def CLR_RELE(self):
        """ 
        Выключение реле контроллера\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x23 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x50 , 0x02, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x23, 0x04, 0x00, 0x50 , 0x02, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        
        return msg

    def GET_RELE(self):
        """ 
        Запрос о состоянии реле контроллера\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x24 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x60 , 0x02, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x24, 0x04, 0x00, 0x60 , 0x02, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def WAIT_IN0(self):
        """ 
        Ожидание посткпление сигнала на вход IN0\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x25 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x70 , 0x02, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x25, 0x04, 0x00, 0x70 , 0x02, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def WAIT_IN1(self):
        """ 
        Ожидание посткпление сигнала на вход IN1\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x26 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x80 , 0x02, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x26, 0x04, 0x00, 0x80 , 0x02, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def GET_MIN_SPEED(self):
        """ 
        Чтение установленного значения минимальной скорости\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x27 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x60 , 0x03, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x27, 0x04, 0x00, 0x60 , 0x03, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg
    
    def GET_MAX_SPEED(self):
        """ 
        Чтение установленного значения максимальной скорости\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x28 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0x70 , 0x03, 0x00, 0x00]\\
        """
        msg = [0x00, 0x03, 0x02, 0x28, 0x04, 0x00, 0x70 , 0x03, 0x00, 0x00]

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SET_WAIT_2(self, pause: int):
        """ 
        Задание паузы. Выполнение данной команды может быть прервано поступлением сигнала\\
        на IN0, IN1 или SET_ZERO\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x29 - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xC0 , pause]\\
            pause - время ожидания в мс
        """
        
        msg = [0x00, 0x03, 0x02, 0x29, 0x04, 0x00, 0xC0]
        bytes_pause = calc_move_parameter(pause, '11')
        for byte in bytes_pause:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SCAN_MARK2_F(self, speed: int):
        """ 
        Поиск метки положения в прямом направлении с заданной скоростью. Движение продолжается до\\
        поступления сигнала на вход IN1\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x2A - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xD0 , speed]\\
            speed - скорость в полных шагах в секунду
        """
        
        msg = [0x00, 0x03, 0x02, 0x2A, 0x04, 0x00, 0xD0]
        bytes_speed = calc_move_parameter(speed, '11')
        for byte in bytes_speed:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg

    def SCAN_MARK2_R(self, speed: int):
        """ 
        Поиск метки положения в обратном направлении с заданной скоростью. Движение продолжается до\\
        поступления сигнала на вход IN1\\
        msg:
            XOR = 0x00 - предварительно\\
            VER = 0x03\\
            CMD_TYPE = 0x02 - управление приводом в режме реального времени\\
            CMD_IDENTIFICATION = 0x2B - уникальный номер для каждой из команд\\
            lENGHT_DATA (младший байт) = 0x04\\
            lENGHT_DATA (старший байт) = 0x00\\
            data = [0xE0 , speed]\\
            speed - скорость в полных шагах в секунду
        """
        
        msg = [0x00, 0x03, 0x02, 0x2B, 0x04, 0x00, 0xE0]
        bytes_speed = calc_move_parameter(speed, '11')
        for byte in bytes_speed:
            msg.append(byte)

        XOR = XOR_SUM(msg)
        msg[0] = XOR
        return msg



def XOR_SUM(msg: list) -> int:
    """Вычисление контррольной суммы - младшего байта от суммы XOR всех байтов\\
    XOR - исключающее 'ИЛИ' (побитовое сравнение).\\
    Пример:
    msg = [0x72, 0x03, 0x02, 0x02, 0x04, 0x00, 0x60 , 0x20, 0x03, 0x00]
    -> result = 0x0\\
    sum = 0xFF\\
    for i in range(len(msg)):\\
        sum += msg[i]\\
    xor_sum = sum ^ 0xFF
    result = xor_sum & 0xFF
    """
    result = -sum(msg) & 0xFF
    return result


def calc_move_parameter(num: int, start_string: str):
    """Представляем параметр двищения (скорость, ускорение или перемещение) в виде трех байтов для записи в data"""
    # Бинарное представление, удалем '0b'
    bin_num = bin(num)[2:]
    # Добавляем справа два нуля
    bin_num += "00"
    # Дополняем слева нули, чтобы длина была кратна 8
    if len(bin_num) % 8 > 0:
        bin_num = bin_num.zfill((len(bin_num) // 8 + 1) * 8)

    data = byte_devision(bin_num, 3)
    return data


def byte_devision(binary_string: str, num: int):
    """
    Разделяем на байты и добавляем в массив младшим байтом вперед\\
    num - количество байт, которое должен соджержать список 
    """
    data = []
    # разделяем на байты
    for i in range(0, len(binary_string), 8):
        byte = '0b' + binary_string[i:i+8]
        # Переводим в десятичное число, в памяти 10-и и 16-иричные числа хранятся в одном формате
        data.append(int(byte, 2))
    #print(data)
    data.reverse()
    if len(data) < num:
        for i in range(num - len(data)):
            data.append(0x00)
    #print(data)
    return data


def create_bit_string(numbers_and_bits):
    '''Переводим числа в битовые строки заднной длины и составляем общую
        битовую строку'''
    bits_string = ''
    for num, bits in numbers_and_bits:
        binary_representation = '{num:0>{width}b}'.format(num = num, width = bits)
        #print(binary_representation)
        bits_string = binary_representation + bits_string
    return bits_string
    
