class PID:
    """Classe que define um controle PID para o movimento dos motores dos elevadores.
    """
    def __init__(self, kp=0.009, ki=0.04, kd=0.011, T=0.2):
        """Inicializa uma nova instância do controlador PID.

        :param kp: Ganho Proporcional, default é 0.009
        :type kp: float
        :param ki: Ganho Integral, default é 0.04
        :type ki: float
        :param kd: Ganho Derivativo, default é 0.011
        :type kd: float
        :param T: Período de Amostragem em segundos, default é 0.2
        :type T: float
        """
        self.referencia = 0
        self.kp = kp   # Ganho Proporcional
        self.ki = ki  # Ganho Integral
        self.kd = kd   # Ganho Derivativo
        self.T = T    # Período de Amostragem (ms)

        self.erro_total, self.erro_anterior = 0.0, 0.0

        self.sinal_de_controle_MAX = 100.0
        self.sinal_de_controle_MIN = -100.0

    def update_reference(self, referencia) -> None:
        """Atualiza a referência do controle.

        :param referencia: Valor da nova referência
        :type referencia: int
        """
        self.referencia = referencia

    def control(self, saida_medida) -> float:
        """Calcula o sinal de controle do PWM do motor com base na `saida_medida` e na
        referência e constantes da classe.

        :param saida_medida: Posição atual do encoder
        :type saida_medida: int
        :return: Valor do PWM do motor
        :rtype: float
        """
        erro = self.referencia - saida_medida

        self.erro_total += erro  # Acumula o erro (Termo Integral)

        if self.erro_total >= self.sinal_de_controle_MAX:
            self.erro_total = self.sinal_de_controle_MAX
        elif self.erro_total <= self.sinal_de_controle_MIN:
            self.erro_total = self.sinal_de_controle_MIN

        # Diferença entre os erros (Termo Derivativo)
        delta_error = erro - self.erro_anterior


        # PID calcula sinal de controle
        sinal_de_controle = self.kp * erro + (self.ki * self.T) * self.erro_total + (
            self.kd / self.T) * delta_error

        if sinal_de_controle >= self.sinal_de_controle_MAX:
            sinal_de_controle = self.sinal_de_controle_MAX
        elif sinal_de_controle <= self.sinal_de_controle_MIN:
            sinal_de_controle = self.sinal_de_controle_MIN

        self.erro_anterior = erro

        return sinal_de_controle
