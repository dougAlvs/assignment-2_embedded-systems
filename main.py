import signal
import time
from threading import Thread, Event

import RPi.GPIO as GPIO

from reset_all import reset_all
from gpio.elevator_controller import ElevatorController
from i2c.oled_screen import Screen

def main():
    def exit_handler(sig, frame):
        print("Finalizando execução do programa ...")
        exit_execution.set()
        time.sleep(0.5)

    exit_execution = Event()

    elevator_controller = ElevatorController()
    screen = Screen(elevator_controller=elevator_controller)

    try:
        # Iniciando as threads
        screen_thread = Thread(target=screen.update, args=(exit_execution,))
        elevators_requests_thread = Thread(target=elevator_controller.handle_requests, args=(exit_execution,))

        # Configurando as threads como daemon
        screen_thread.daemon = True
        elevators_requests_thread.daemon = True

        # Configurando o tratamento de sinais para finalizar o programa
        signal.signal(signal.SIGINT, exit_handler)
        signal.signal(signal.SIGTERM, exit_handler)

        # Iniciando as threads
        screen_thread.start()
        elevators_requests_thread.start()

        # Aguarda evento de termino das threads
        exit_execution.wait()


    except KeyboardInterrupt:
        print("Programa interrompido pelo usuario")

    finally:
        # Limpar configurações ao finalizar
        elevator_controller.shutdown_elevators()

        screen.shutdown()
        GPIO.cleanup()
        reset_all()
        print("Recursos limpos e programa encerrado com sucesso.")

if __name__ == "__main__":
    main()
    