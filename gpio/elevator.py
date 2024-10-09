import json
import time
import math

import RPi.GPIO as GPIO

from .engine import Engine
from .pid import PID


class Elevator():
    """Classe responsável por controlar o elevador, gerenciando a calibração, movimento e detecção de andares.
    """
    def __init__(self, elevator_num, modbus_controller, controller) -> None:
        """Inicializa um novo elevador.

        :param elevator_num: Número do elevador
        :type elevator_num: int
        :param modbus_controller: Instância do controlador Modbus
        :type modbus_controller: class:`uart.ModbusController`
        :param controller: Instância do controlador de elevadores
        :type controller: class:`gpio.ElevatorController`
        """
        self.elevator_num = elevator_num
        self.engine = Engine(elevator_num)
        self.pid = PID()

        self.modbus_controller = modbus_controller
        self.controller = controller

        self.current_floor = "ground_floor"
        self.state = "Parado"

        self.floors_positions = {"ground_floor": -1,
                                 "first_floor": -1,
                                 "second_floor": -1,
                                 "third_floor": -1}

        self.requests_floor_table = {"G": "ground_floor",
                                     "F": "first_floor",
                                     "S": "second_floor",
                                     "T": "third_floor"}

        # Configurações da GPIO
        with open("./setup/config.json", "r") as f:
            configs_file = json.load(f)

        inputs = configs_file[f"elevador_{elevator_num}"]["inputs"]

        for inp in inputs:
            if inp["tag"] == "SENSOR_TERREO":
                self.ground_sensor = inp["gpio"]
            elif inp["tag"] == "SENSOR_1_ANDAR":
                self.first_sensor = inp["gpio"]
            elif inp["tag"] == "SENSOR_2_ANDAR":
                self.second_sensor = inp["gpio"]
            elif inp["tag"] == "SENSOR_3_ANDAR":
                self.third_sensor = inp["gpio"]

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(self.ground_sensor, GPIO.IN)
        GPIO.setup(self.first_sensor, GPIO.IN)
        GPIO.setup(self.second_sensor, GPIO.IN)
        GPIO.setup(self.third_sensor, GPIO.IN)     

    def set_floor_detection_callbacks(self):
        """Seta os callbacks dos sensores dos andares depois que a calibração finaliza.
        """
        GPIO.add_event_detect(self.ground_sensor, GPIO.BOTH, callback=self.detect_floor, bouncetime=200)
        GPIO.add_event_detect(self.first_sensor, GPIO.BOTH, callback=self.detect_floor, bouncetime=200)
        GPIO.add_event_detect(self.second_sensor, GPIO.BOTH, callback=self.detect_floor, bouncetime=200)
        GPIO.add_event_detect(self.third_sensor, GPIO.BOTH, callback=self.detect_floor, bouncetime=200)

    def detect_floor(self, channel) -> None:
        """Detecta qual andar o elevador está com base no canal do sensor ativado.

        :param channel: Canal do sensor ativado
        :type channel: int
        """

        if channel == self.ground_sensor:
            self.current_floor = "ground_floor"
        elif channel == self.first_sensor:
            self.current_floor = "first_floor"
        elif channel == self.second_sensor:
            self.current_floor = "second_floor"
        elif channel == self.third_sensor:
            self.current_floor = "third_floor"
            

    def calibrate(self) -> None:
        """Calibra o elevador, identificando as posições dos andares com base nos sensores.
        """
        print(f"Iniciando Calibração do Elevador {self.elevator_num}  ...")
        starting_pos = self.modbus_controller.read_encoder(engine_id=self.elevator_num - 1)
        print(f"Posição inicial: {starting_pos}  ...")

        # Descer até o térreo
        if not GPIO.input(self.ground_sensor) == GPIO.HIGH and starting_pos > 0:
            print("Descendo até o final ...")
            self.state = "Descendo"
            self.engine.trigger_movement(-10)  # Define uma potência negativa para descer

        # Para o elevador
        self.engine.trigger_movement(0)

        # Subir lentamente e registrar posições dos sensores
        self.engine.trigger_movement(15)  # Define uma potência baixa para subir lentamente
        self.state = "Subindo"
        
        for floor in self.floors_positions:
            # Define qual sensor usar
            if floor == "ground_floor":
                channel = self.ground_sensor
            elif floor == "first_floor":
                channel = self.first_sensor
            elif floor == "second_floor":
                channel = self.second_sensor
            elif floor == "third_floor":
                channel = self.third_sensor

            # Espera pela borda de subida e da timeout caso não encontre
            rising_edge = GPIO.wait_for_edge(channel, GPIO.RISING, timeout=60000)

            asc_position = self.modbus_controller.read_encoder(engine_id=self.elevator_num - 1)

            if rising_edge is None:
                print(f"Timeout na calibração do andar {floor}!")
                continue

            GPIO.remove_event_detect(channel)

            # Espera pela borda de descida do sensor, mas usa só a de subida caso não encontre
            falling_edge = GPIO.wait_for_edge(channel, GPIO.FALLING, timeout=2000)

            # if falling_edge is None:
                # print(f"Borda de descida do andar {floor} não encontrada!")

            desc_position = self.modbus_controller.read_encoder(engine_id=self.elevator_num - 1)
            self.current_floor = floor

            # Calcula a média para determinar a posição exata do andar
            self.floors_positions[floor] = math.ceil((desc_position + asc_position) / 2)
            print(f"Andar {floor} calibrado: {self.floors_positions[floor]}")

            GPIO.remove_event_detect(channel)


        # Finaliza o movimento
        self.engine.trigger_movement(0)  # Para o elevador
        self.state = "Parado"
        print(f"Calibração do Elevador {self.elevator_num} finalizada!")
        self.move_to_floor("G")


    def move_to_floor(self, target_floor_request) -> None:
        """Move o elevador para o andar desejado.

        :param target_floor_request: Código do andar de destino
        :type target_floor_request: char
        """
        # Define o target do pid

        target_floor = self.requests_floor_table[target_floor_request]

        target_position = self.floors_positions[target_floor]
        self.pid = PID()
        self.pid.update_reference(target_position)

        # Pega a posição atual do elevador
        current_position = self.modbus_controller.read_encoder(engine_id=self.elevator_num - 1)

        self.state = "Subindo" if target_position - current_position > 0 else "Descendo"

        print(f"Elevador {self.elevator_num}: Iniciando deslocamento de {self.current_floor} ({current_position}) para {target_floor} ({target_position}) ...")

        error = target_position - current_position

        # Atualiza a potencia do motor enquanto não chegar no target
        while abs(error) > 5 and not self.current_floor == target_floor:
            current_position = self.modbus_controller.read_encoder(engine_id=self.elevator_num - 1)

            pwm_output = self.pid.control(current_position)
            self.engine.trigger_movement(pwm_output)
            self.modbus_controller.send_control_signal(engine_id=self.elevator_num - 1, value=int(abs(pwm_output)))

            time.sleep(0.2)
            error = target_position - current_position

        # Chegando no andar desejado, desliga o motor e o(s) respectivo(s) botão(s)
        self.engine.trigger_movement(0)
        self.state = "Parado"
        self.controller.turn_btns_off(elevator_idx=self.elevator_num - 1, request_code=target_floor_request)
        self.controller.remove_last_request(queue_idx=self.elevator_num - 1)

        # Abre as portas e espera passageiros entrarem/sairem
        print("Portas abertas para embarque/desembarque de passageiros ...")
        self.current_floor = target_floor
        
        time.sleep(5)

    def emergency(self):
        """Aciona o modo de emergência, parando o elevador imediatamente.
        """
        print(f"Parada de emergência {self.elevator_num}!")
        self.state = "Emergencia"
        self.engine.brake()
