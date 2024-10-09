import json

import RPi.GPIO as GPIO

class Engine():
    """Classe para controlar o movimento do motor.
    """
    def __init__(self, elevator_num) -> None:
        """Inicializa um novo motor.

        :param elevator_num: Número do elevador ao qual o motor pertence
        :type elevator_num: int
        """
        self.elevator_num = elevator_num

        # Configurações da GPIO
        with open("./setup/config.json", "r") as f:
            configs_file = json.load(f)

        outputs = configs_file[f"elevador_{elevator_num}"]["outputs"]

        for out in outputs:
            if out["tag"] == "DIR1":
                self.dir_1 = out["gpio"]
            elif out["tag"] == "DIR2":
                self.dir_2 = out["gpio"]
            elif out["tag"] == "POTM":
                self.potm = out["gpio"]

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(self.dir_1, GPIO.OUT)
        GPIO.setup(self.dir_2, GPIO.OUT)
        GPIO.setup(self.potm, GPIO.OUT)

        # Início do PWM
        self.pwm = GPIO.PWM(self.potm, 1000)
        self.pwm.start(0)
        self.status = 'Parado'

    def _up(self) -> None:
        """Define os pinos da GPIO para o motor subir.
        """
        GPIO.output(self.dir_1, GPIO.HIGH)
        GPIO.output(self.dir_2, GPIO.LOW)

    def _down(self) -> None:
        """Define os pinos da GPIO para o motor descer.
        """
        GPIO.output(self.dir_1, GPIO.LOW)
        GPIO.output(self.dir_2, GPIO.HIGH)

    def _idle(self) -> None:
        """Define os pinos da GPIO para o motor ficar livre.
        """
        GPIO.output(self.dir_1, GPIO.LOW)
        GPIO.output(self.dir_2, GPIO.LOW)

    def brake(self) -> None:
        """Define os pinos da GPIO para o motor frear.
        """
        GPIO.output(self.dir_1, GPIO.HIGH)
        GPIO.output(self.dir_2, GPIO.HIGH)

    def set_duty_cycle(self, power) -> None:
        """Define a potência do PWM do motor.
        """
        self.pwm.ChangeDutyCycle(power)

    def trigger_movement(self, power) -> None:
        """Define a potência e direção de movimento do motor.
        Valores negativos indicam descida, positivos, subida e
        o zero deixa o motor livre.

        :param power: Potência do motor
        :type power: float
        """
        self.set_duty_cycle(abs(power))
        if power < 0:
            self._down()
            self.status = 'Descendo'
        elif power > 0:
            self._up()
            self.status = 'Subindo'
        else:
            self._idle()
            self.status = 'Parado'

    def shutdown(self) -> None:
        """Desliga totalmente o motor.
        """
        self.trigger_movement(0)
        GPIO.output(self.potm, GPIO.LOW)
        GPIO.output(self.dir_1, GPIO.LOW)
        GPIO.output(self.dir_2, GPIO.LOW)
        self.pwm.stop()
