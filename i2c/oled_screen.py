import time

import Adafruit_SSD1306
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from .temp_sensors_controller import TempSensorController

class Screen():
    """Classe responsável pela exibição das informações dos elevadores na tela OLED.
    """
    def __init__(self, elevator_controller) -> None:
        """Inicializa uma nova tela.

        :param elevator_controller: Instnacia do controle dos elevadores
        :type elevator_controller: class:`gpio.ElevatorController`
        """
        print("Inicializando display ...")
        self.display = Adafruit_SSD1306.SSD1306_128_64(rst=None)

        self.display.begin()

        self.display.clear()
        self.display.display()

        self.width = self.display.width
        self.height = self.display.height
        self.image = Image.new('1', (self.width , self.height))

        self.font = ImageFont.load_default()

        self.elevators_info = [
            {"temperature": -1.0, "floor": "N/A", "state": "Parado"},
            {"temperature": -1.0, "floor": "N/A", "state": "Parado"}
        ]

        self.elevator_controller = elevator_controller
        self.temp_sensors_controller = TempSensorController()

    def update_elevators_info(self) -> None:
        """Atualiza as informações de andar e estado do elevador com os dados recebidos de :class:`gpio.ElevatorController`
        e a temperatura com os dados de :class:`i2c.TempSensorController`.
        """
        for elevator_idx in range(2):
            floor, state = self.elevator_controller.get_elevator_info(elevator_number=elevator_idx)
            temperature = self.temp_sensors_controller.get_temperature(elevator_number=elevator_idx)

            self.elevators_info[elevator_idx]["temperature"] = temperature
            self.elevator_controller.modbus_controller.send_temperature(elevator_id=elevator_idx, temperature=temperature)

            if floor != "N/A":
                self.elevators_info[elevator_idx]["floor"] = floor
            self.elevators_info[elevator_idx]["state"] = state

    def shutdown(self) -> None:
        """Limpa a tela para finalização da aplicação.
        """
        print("Limpando display ...")
        draw = ImageDraw.Draw(self.image)
        draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        self.display.image(self.image)
        self.display.display()

    def update(self, exit_event) -> None:
        """Loop que atualiza a tela OLED com as informações dos elevadores, finalizando
        quando `exit_event` é definido na thread principal.

        :param exit_event: Evento para finalização da thread
        :type exit_event: class:`threading.Event`
        """
        while not exit_event.is_set():
            draw = ImageDraw.Draw(self.image)

            draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

            elevator_width = self.width // len(self.elevators_info)

            # Desenha o retangulo do outline de cada elevador
            for i in range(2):
                x0 = i * (self.width - 1) // 2
                x1 = (i + 1) * elevator_width - 1
                draw.rectangle((x0, 0, x1, 63), outline=255, fill=0)

            # Linha do cabeçalho
            header_height = 15
            draw.line((0, header_height, self.width, header_height), fill=255)

            for i, elevator in enumerate(self.elevators_info):
                x = i * elevator_width + 4
                draw.text((x - 4, 2), f"Elevador {i+1}", font=self.font, fill=255)
                draw.text((x, 16), f"{elevator['temperature']:.2f} C", font=self.font, fill=255)
                draw.text((x, 30), f"{elevator['floor']}", font=self.font, fill=255)
                draw.text((x, 44), elevator['state'], font=self.font, fill=255)

            self.display.image(self.image)
            self.display.display()
            time.sleep(0.1)
            self.update_elevators_info()

        self.shutdown()
