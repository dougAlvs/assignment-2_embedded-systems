import time
import threading

from uart.modbus_controller import ModbusController
from .elevator import Elevator

class ElevatorController():
    """Classe responsável por gerenciar as requisições dos elevadores e o envio/recebimento de mensagens pelo Modbus. 
    Também administra a fila de requisições, comandando cada elevador ao andar necessário. 
    """
    def __init__(self) -> None:
        self.modbus_controller = ModbusController(device_id=0x01, student_id=[9, 6, 2, 0])
        self.elevators = [Elevator(elevator_num=1, modbus_controller=self.modbus_controller, controller=self),
                          Elevator(elevator_num=2, modbus_controller=self.modbus_controller, controller=self)]
        self.requests_queues = [[], []]
        self.elevators_registers = [b'\x00' * 11, b'\x00' * 11]

        self.btn_addresses = [[0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A],
                              [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA]]

        # G = Ground, F = First, S = Second, T = Third, E = Emergency
        self.requests_idx = ["G", "F", "F", "S", "S", "T", "E", "G", "F", "S", "T"]

    def calibrate_elevators(self) -> None:
        """Envia o comando de calibração para os elevadores.
        """
        for elevator in self.elevators:
            elevator.calibrate()


    def insert_request(self, request, queue_idx) -> None:
        """Insere na fila de índice `queue_idx` a requisição para movimentar os elevadores para o andar de `request`.

        :param request: Andar no qual um elevador é requisitado
        :type request: char
        :param queue_idx: Índice da fila de requisição do elevador
        :type queue_idx: int
        """
        print(f"Inserindo requisição para {request} no Elevador {queue_idx + 1}")
        q = self.requests_queues[queue_idx]
        if request not in q:
            q.append(request)

    def remove_last_request(self, queue_idx) -> None:
        """Remove da fila de índice `queue_idx` todas as requisições para o último andar em que o elevador chegou.

        :param queue_idx: Índice da fila de requisição do elevador
        :type queue_idx: int
        """
        requests_queue = self.requests_queues[queue_idx]
        if len(requests_queue) != 0:
            current_floor = requests_queue[0]
            while current_floor in requests_queue:
                requests_queue.remove(current_floor)

    def set_registers(self, elevator_idx, registers) -> None:
        """Atualiza a lista de registradores de um determinado elevador.

        :param elevator_idx: Índice do elevador
        :type elevator_idx: int
        :param registers: Lista de registradores
        :type registers: bytes
        """
        self.elevators_registers[elevator_idx] = list(registers)

    def turn_btns_off(self, elevator_idx, request_code) -> None:
        """Desliga todos os botões referentes ao andar de `request_code` para o elevador de índice `elevator_idx`.

        :param elevator_idx: Índice do elevador
        :type elevator_idx: int
        :param request_code: Andar no qual o elevador foi requisitado
        :type request_code: char
        """
        # Pega o endereço dos botões a serem desligados
        btns_adresses = [addr for idx, addr in enumerate(self.btn_addresses[elevator_idx]) if self.requests_idx[idx] == request_code]

        # Chama o modbus para desligar cada um
        for btn_adress in btns_adresses:
            self.modbus_controller.write_registers(initial_address=btn_adress,
                                                               quantity=1, values=bytes([0]))

    def handle_registers(self) -> None:
        """Trata a lista de registradores de cada um dos elevadores. Verifica quais botões 
        foram pressionados e adiciona as respectivas requisições na fila.
        """
        for elv_index in range(2):

            # Pega os registradores dos dois elevadores
            elevator_registers = self.elevators_registers[elv_index]
            other_elv_index = elv_index == 0
            other_elevator_registers = self.elevators_registers[other_elv_index]

            for btn_index in range(11):
                btn = elevator_registers[btn_index]

                # Se o botão não estiver pressionado ou já estiver na fila, continua
                if not btn or self.requests_idx[btn_index] in self.requests_queues[elv_index]:
                    continue

                # Botão de emergência
                if btn_index == 6:
                    self.requests_queues[elv_index] = [self.requests_idx[btn_index]]
                    # Desliga todos os outros botões
                    for floor in ["G", "F", "S", "T"]:
                        self.turn_btns_off(elv_index, floor)
                    break  # Em caso de emergência, interrompe o processamento

                # Lógica exclusiva dos botões externos
                if btn_index < 6:
                    # Botão do outro elevador
                    other_btn = other_elevator_registers[btn_index]

                    # Se o outro botão não tiver pressionado, pressiona ele
                    if not other_btn:
                        self.modbus_controller.write_registers(initial_address=self.btn_addresses[other_elv_index][btn_index],
                                                               quantity=1, values=bytes([1]))

                    # Põe ambos elevadores para atender o pedido
                    for q_index in range(2):
                        self.insert_request(request=self.requests_idx[btn_index], queue_idx=q_index)

                # Lógica exclusiva dos botões internos
                else:
                    # Põe apenas o respectivo elevador para atender o pedido
                    self.insert_request(request=self.requests_idx[btn_index], queue_idx=elv_index)

        # Reseta os registradores de ambos os elevadores
        self.elevators_registers = [b'\x00' * 11, b'\x00' * 11]

    def get_elevator_info(self, elevator_number):
        """Requisita ao elevador `elevator_number` seu andar e estado atual.

        :param elevator_number: Número do elevador
        :type elevator_number: int
        :return: Andar e estado do elevador
        :rtype: tuple(str, str)
        """
        floors_display = {"ground_floor": "Terreo",
                    "first_floor": "1º Andar",
                    "second_floor": "2º Andar",
                    "third_floor": "3º Andar",
                    None: "N/A",}

        floor = floors_display[self.elevators[elevator_number].current_floor]
        state = self.elevators[elevator_number].state

        return floor, state

    def handle_requests(self, exit_event):
        """Lê os botões do Modbus e trata-os, mandando as requisições para os elevadores enquanto
        `exit_event` não é definido na thread principal.

        :param exit_event: Evento para finalização da thread
        :type exit_event: class:`threading.Event`
        """
        self.calibrate_elevators()

        for elevator in self.elevators:
            elevator.set_floor_detection_callbacks()

        while not exit_event.is_set():
            self.set_registers(elevator_idx= 0, registers=self.modbus_controller.read_registers(initial_address=0x00, quantity=11))
            self.set_registers(elevator_idx= 1, registers=self.modbus_controller.read_registers(initial_address=0xA0, quantity=11))
            self.handle_registers()

            for idx, queue in enumerate(self.requests_queues):
                elevator = self.elevators[idx]

                # Em emergência para o elevador e limpa a fila
                if len(queue) != 0 and queue[0] == 'E':
                    print("DEBUG: Emergencia")
                    elevator.emergency()
                    self.requests_queues[idx] = []

                elif len(queue) != 0 and elevator.state == "Parado":
                    target_floor = queue[0]
                    move_elevator_thread = threading.Thread(target=elevator.move_to_floor, args=(target_floor,))
                    move_elevator_thread.start()
                time.sleep(0.05)

    def shutdown_elevators(self):
        """Desliga o motor dos elevadores e desconecta o Modbus.
        """
        print("Desligando elevadores ...")
        for elevator in self.elevators:
            elevator.engine.shutdown()

        self.modbus_controller.disconnect()
