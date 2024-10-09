import serial

class Uart:
    """Classe responsável pela comunicação UART entre a Raspberry Pi e a ESP32.
    """
    def __init__(self) -> None:
        """Inicializa a conexão UART."""
        try:
            self.serial_connection = serial.Serial(
                port='/dev/serial0',
                baudrate=115200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
            )
        except Exception as e:
            print(f"Erro de conexão UART: {e}")

    def connect(self) -> None:
        """Conecta à UART.
        """
        if self.serial_connection is not None and not self.serial_connection.is_open:
            try:
                self.serial_connection.open()
                # print("Conexão UART iniciada.")
            except Exception as e:
                print(f"Erro ao abrir conexão UART: {e}")
    def send_data(self, data) -> None:
        """Envia dados para a UART.

        :param data: Dados a serem enviados
        :type data: bytes
        """
        if self.serial_connection is None:
            print("Erro: Conexão UART não inicializada.")
            return
        if not self.serial_connection.is_open:
            self.connect()
        if self.serial_connection.is_open:
            try:
                self.serial_connection.write(data)
            except Exception as e:
                print(f"Erro ao enviar dados: {e}")


    def receive_data(self, size) -> bytes:
        """Recebe dados da UART.

        :param size: Tamanho dos dados a serem recebidos.
        :type size: int
        :return: Dados recebidos
        :rtype: bytes
        """
        if self.serial_connection is None:
            print("Erro: Conexão UART não inicializada.")
            return b''

        if not self.serial_connection.is_open:
            self.connect()

        if self.serial_connection.is_open:
            try:
                return self.serial_connection.read(size)
            except Exception as e:
                print(f"Erro ao receber dados: {e}")
                return b''
        else:
            return b''


    def disconnect(self) -> None:
        """Desconecta da UART
        """
        if self.serial_connection is not None and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
            except Exception as e:
                print(f"Erro ao fechar conexão UART: {e}")
