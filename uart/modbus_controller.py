import struct
import time
import threading

from .crc_utils import compute_crc, check_crc
from .uart import Uart


class ModbusController:
    """Classe responsável por controlar a comunicação via protocolo Modbus com dispositivos UART.
    """
    def __init__(self, device_id, student_id) -> None:
        """Inicializa uma nova instância do controlador Modbus.

        :param device_id: ID do dispositivo Modbus
        :type device_id: int
        :param student_id: Matrícula do aluno
        :type student_id: list[int]
        """
        self.device_id = device_id
        self.student_id = bytes(student_id)
        self.lock = threading.Lock()
        self.uart = Uart()
        self.uart.connect()

    def _build_message(self, function_code, sub_code, data) -> bytes:
        """Constrói a mensagem Modbus com os parâmetros fornecidos.

        :param function_code: Código da função Modbus
        :type function_code: int
        :param sub_code: Subcódigo específico da função
        :type sub_code: int
        :param data: Dados a serem enviados
        :type data: bytes
        :return: Mensagem Modbus formatada
        :rtype: bytes
        """
        message = struct.pack('B', self.device_id) + struct.pack('B', function_code)
        message += struct.pack('B', sub_code) + data + self.student_id
        crc = compute_crc(message, len(message))
        message += struct.pack('<H', crc)

        return message

    def _parse_response(self, response, expected_length) -> tuple:
        """Analisa a resposta recebida e verifica sua integridade.

        :param response: Resposta recebida
        :type response: bytes
        :param expected_length: Comprimento esperado da resposta
        :type expected_length: int
        :return: Elementos extraídos da resposta Modbus
        :rtype: tuple
        :raises ValueError: Se a resposta estiver incompleta ou o CRC for inválido
        """
        if len(response) < expected_length:
            raise ValueError("Resposta incompleta!")

        if not check_crc(response):
            print(f'Dados com CRC Inválidos: {response}!')

        device_id = response[0]
        function_code = response[1]

        # Leitura de Registradores
        if function_code  in [0x06, 0x03]:
            data = response[2:-2]
            # data = response[3:3 + num_bytes]
            return (device_id, function_code, data)

        # Comandos de Escrita ou Leitura de Encoder
        if function_code in [0x16, 0x23]:
            sub_code = response[2]

            # Leitura de encoder)
            if len(response) > 4:
                data = response[3:-2]
                return (device_id, function_code, sub_code, data)

            # Caso de comandos sem dados adicionais (ex.: controle PWM)
            return (device_id, function_code, sub_code)

        raise ValueError("Código de função desconhecido ou não suportado!")

    def _send_and_receive(self, function_code, sub_code, data, expected_length, expected_quantity=None) -> tuple:
        """Envia uma mensagem Modbus e recebe a resposta.

        :param function_code: Código da função Modbus
        :type function_code: int
        :param sub_code: Subcódigo específico da função
        :type sub_code: int
        :param data: Dados a serem enviados
        :type data: bytes
        :param expected_length: Comprimento esperado da resposta
        :type expected_length: int
        :param expected_quantity: Quantidade esperada de dados na resposta, se aplicável
        :type expected_quantity: int, opcional
        :return: Elementos extraídos da resposta Modbus
        :rtype: tuple
        :raises ValueError: Se houver inconsistências na resposta
        """
        with self.lock:
            message = self._build_message(function_code, sub_code, data)
            self.uart.connect()
            self.uart.send_data(message)
            time.sleep(0.1)

            response = self.uart.receive_data(expected_length)
            parsed_response = self._parse_response(response, expected_length)

            if parsed_response[0] != 0x00:
                raise ValueError(f"Esperado device_id 0x00, mas recebeu 0x{function_code:X}!")
            if parsed_response[1] != function_code:
                raise ValueError(f"Esperado function_code 0x{function_code:X}, mas recebeu 0x{parsed_response[1]:X}")

            if expected_quantity is None:
                sub_code_response = parsed_response[2]
                if sub_code_response != sub_code:
                    raise ValueError(f"Esperado sub_code 0x{sub_code:X}, mas recebeu 0x{sub_code_response:X}!")

            self.uart.disconnect()

            return parsed_response

    def read_encoder(self, engine_id) -> int:
        """Lê o valor do encoder de um motor específico.

        :param engine_id: ID do motor
        :type engine_id: int
        :return: Valor lido do encoder
        :rtype: int
        """
        packed_data = struct.pack('B', engine_id)

        # 1 (device_id) + 1 (function_code) + 1 (sub_code) + 4 (int) + 2 (CRC) == 9
        parsed_response = self._send_and_receive(function_code=0x23, sub_code=0xC1,
                                                data=packed_data, expected_length=9)

        data = parsed_response[3]

        return struct.unpack('<I', data)[0]

    def send_control_signal(self, engine_id: int, value: int) -> None:
        """Envia um sinal de controle PWM para um motor específico.

        :param engine_id: ID do motor
        :type engine_id: int
        :param value: Valor do sinal de controle
        :type value: int
        """
        packed_data = struct.pack('B', engine_id) + struct.pack('<i', value)

        # 1 (device_id) + 1 (function_code) + 1 (sub_code) + 2 (CRC) == 5
        _ = self._send_and_receive(function_code=0x16, sub_code=0xC2,
                                                data=packed_data, expected_length=5)

    def send_temperature(self, elevator_id: int, temperature: float) -> None:
        """Envia a temperatura de um elevador específico.

        :param elevator_id: ID do elevador
        :type elevator_id: int
        :param temperature: Valor da temperatura
        :type temperature: float
        """
        packed_data = struct.pack('B', elevator_id) + struct.pack('<f', temperature)

        # 1 (device_id) + 1 (function_code) + 1 (sub_code) + 2 (CRC) == 5
        _ = self._send_and_receive(function_code=0x16, sub_code=0xD1,
                                                data=packed_data, expected_length=5)


    def read_registers(self, initial_address, quantity) -> bytes:
        """Lê registradores Modbus a partir de um endereço inicial.

        :param initial_address: Endereço inicial dos registradores
        :type initial_address: int
        :param quantity: Quantidade de registradores a serem lidos
        :type quantity: int
        :return: Valores lidos dos registradores
        :rtype: bytes
        """
        packed_data = struct.pack('B', quantity)

        ## 1 (device_id) + 1 (function_code)  + 2 (CRC) + x (número de bytes) == y
        parsed_response = self._send_and_receive(function_code=0x03, sub_code=initial_address, data=packed_data,
                                                 expected_length=4 + quantity, expected_quantity=quantity)

        return parsed_response[2]


    def write_registers(self, initial_address, quantity, values: bytes) -> None:
        """Escreve valores nos registradores Modbus a partir de um endereço inicial.

        :param initial_address: Endereço inicial dos registradores
        :type initial_address: int
        :param quantity: Quantidade de registradores a serem escritos
        :type quantity: int
        :param values: Valores a serem escritos nos registradores
        :type values: bytes
        """
        packed_data = struct.pack('B', quantity) + values

        # 1 (device_id) + 1 (function_code)  + 2 (CRC) + x (número de bytes) == y
        _ = self._send_and_receive(function_code=0x06, sub_code=initial_address, data=packed_data,
                                   expected_length=4 + quantity, expected_quantity=quantity)

    def disconnect(self) -> None:
        """Desconecta a comunicação UART.
        """
        self.uart.disconnect()
        print("Conexão UART encerrada.")
