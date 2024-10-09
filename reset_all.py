import RPi.GPIO as GPIO

# Define o padrao de numeracao das portas como BCM
# A outra opcap e GPIO.BOARD para usar o numero dos pinos fisicos da placa
def reset_all():
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)

	output_pins = [
		20, 19,
		21, 26,
		12, 13,
		18, 17,
		23, 27,
		24, 22,
		25, 6,
	]

	for pin in output_pins:
		GPIO.setup(pin, GPIO.OUT)
		GPIO.output(pin, GPIO.LOW)

if __name__ == "__main__":
    reset_all()