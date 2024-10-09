from time import sleep

from smbus2 import SMBus
from bmp280 import BMP280

class TempSensorController:
    """Classe que gerencia os sensores de temperatura BMP280.
    """
    def __init__(self) -> None:
        """Inicializa uma nova instância do controlador de sensores de temperatura.
        """
        self.bus = SMBus(1)
        
        # self.sensors = [ BMP280(i2c_dev=self.bus, i2c_addr=0x76),
        #                 BMP280(i2c_dev=self.bus, i2c_addr=0x77)]

        self.sensor = BMP280(i2c_dev=self.bus, i2c_addr=0x76)

    def get_temperature(self, elevator_number) -> float:
        """Obtém a temperatura de um dos sensores BMP280.

        :param elevator_number: Número do elevador (0 ou 1)
        :type elevator_number: int
        :return: Temperatura medida pelo sensor em graus Celsius
        :rtype: float
        :raises ValueError: Se o número do elevador não for 0 ou 1
        """
        if elevator_number not in [0, 1]:
            raise ValueError

        # return self.sensors[elevator_number].get_temperature()
        return self.sensor.get_temperature()
