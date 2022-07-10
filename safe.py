import RPi.GPIO as GPIO
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
from time import sleep, time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from picamera import PiCamera
import Keypad       #import module Keypad
ROWS = 4        # number of rows of the Keypad
COLS = 4        #number of columns of the Keypad
keys =  [   '1','2','3','A',    #key code
			'4','5','6','B',
			'7','8','9','C',
			'*','0','#','D'     ]
rowsPins = [12,16,18,22]        #connect to the row pinouts of the keypad
colsPins = [19,15,13,11]        #connect to the column pinouts of the keypad

buzzerPin = 7 # store pin number of buzzer in variable
buttonPin = 29 # store pin number of button in variable

state = "waiting"  # Use a state to determine what to do according to user input.

passcode = "1234" # Store passcode in variable
text_entered = "" # Create empty string for user to add text to

OFFSET_DUTY = 0.5        # define pulse offset of servo
SERVO_MIN_DUTY = 2.5 + OFFSET_DUTY     # define pulse duty cycle for minimum angle of servo
SERVO_MAX_DUTY = 12.5 + OFFSET_DUTY    # define pulse duty cycle for maximum angle of servo
servoPin = 40

attemptsLeft = 3 # To keep track of how many times user has input wrong passcode

camera = PiCamera() # Instantiate camera object


# Ultrasonic sensor pins
trigPin = 35
echoPin = 37

MAX_DISTANCE = 220  # define the maximum measurable distance
timeOut = MAX_DISTANCE*60 # claculate time out according to the maximum measured distance


#Email Variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
GMAIL_USERNAME = "pisafe123@gmail.com"
GMAIL_PASSWORD = "rpi12345"
APP_PASSWORD = "ewmtklqzvsdkqmgj"

# Create a class for the emailer so we can send multiple emails throughout the code.
class Emailer:
	def sendmail(self, recipient, subject, content, image):
		#Create Headers
		emailData = MIMEMultipart()
		emailData['Subject'] = subject
		emailData['To'] = recipient
		emailData['From'] = GMAIL_USERNAME

		# Attach text data
		emailData.attach(MIMEText(content))

		#Create our Image Data from the defined image
		imageData = MIMEImage(open(image, 'rb').read(), 'jpg')
		imageData.add_header('Content-Disposition', 'attachment; filename="image.jpg"')
		emailData.attach(imageData)

		#Connect to Gmail Server
		session = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
		session.ehlo()
		session.starttls()
		session.ehlo()

		#Login to Gmail
		session.login(GMAIL_USERNAME, APP_PASSWORD)

		#Send Email & Exit
		session.sendmail(GMAIL_USERNAME, recipient, emailData.as_string())
		session.quit
# Create an instance of the emailer class
alertor = Emailer()

# Everything here will be executed on start up
def setup():
	global servo1
	GPIO.setmode(GPIO.BOARD)

	GPIO.setup(buzzerPin, GPIO.OUT)
	GPIO.output(buzzerPin, GPIO.LOW)

	GPIO.setup(servoPin, GPIO.OUT)   # Set servoPin to OUTPUT mode
	GPIO.output(servoPin, GPIO.LOW)  # Make servoPin output LOW level

	servo1 = GPIO.PWM(servoPin, 50)     # set Frequence to 50Hz
	servo1.start(0)                     # Set initial Duty Cycle to 0

	GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	GPIO.setup(trigPin, GPIO.OUT)
	GPIO.output(trigPin, GPIO.LOW)

	GPIO.setup(echoPin, GPIO.IN)

def pulseIn(pin, level, timeOut): # obtain pulse time of a pin
	t0 = time()
	while GPIO.input(pin) != level:
		if time() - t0 > timeOut*0.000001:
			return 0
	t0 = time()
	while GPIO.input(pin) == level:
		if time() - t0 > timeOut*0.000001:
			return 0
	pulseTime = (time() - t0)*1000000
	return pulseTime

def getSonar(): # get measurement results from ultrasonic unit
	GPIO.output(trigPin, GPIO.HIGH) # make trigger pin send out a signal
	sleep(0.00001)
	GPIO.output(trigPin, GPIO.LOW)
	pingTime = pulseIn(echoPin, GPIO.HIGH, timeOut)
	distance = pingTime*340.0/2.0/10000.0
	return distance

def servoWrite(angle):      # make the servo rotate to specific angle, 0-180
	global servo1
	if(angle < 0):
		angle = 0
	elif(angle > 180):
		angle = 180
	dc = SERVO_MIN_DUTY + (SERVO_MAX_DUTY - SERVO_MIN_DUTY) * angle / 180.0 # map the angle to duty cycle
	servo1.ChangeDutyCycle(dc)

# Everything here will be looped continuously
def loop():
	global passcode, text_entered, state, attemptsLeft, servo1
	mcp.output(3,1)
	lcd.begin(16,2)
	keypad = Keypad.Keypad(keys,rowsPins,colsPins,ROWS,COLS)    #creat Keypad object
	keypad.setDebounceTime(50)      #set the debounce time

	while True:
		key = keypad.getKey()
		if state == "waiting":
			lcd.setCursor(0,0)
			lcd.message("Enter passcode\nto open")
			if key != keypad.NULL:
				lcd.clear()
				GPIO.output(buzzerPin, GPIO.HIGH)
				sleep(0.1)
				GPIO.output(buzzerPin, GPIO.LOW)
				state = "checking"
		elif state == "checking":
			if key != keypad.NULL:
				GPIO.output(buzzerPin, GPIO.HIGH)
				if key == "*":
					if text_entered == passcode:
						sleep(0.01)
						GPIO.output(buzzerPin, GPIO.LOW)
						lcd.clear()
						lcd.message("Correct password")
						for angle in range(75, -1, -1):   # make servo rotate from 180 to 0 deg
							servoWrite(angle)
							sleep(0.001)
						servo1.ChangeDutyCycle(0)
						camera.start_preview(alpha=200)
						camera.capture('/home/pi/Desktop/image.jpg')
						camera.annotate_text = "I'm watching you!!!"
						state = "unlocked"
					else:
						if attemptsLeft > 1:
							lcd.clear()
							lcd.message("Incorrect\npassword!")
							attemptsLeft -= 1
							text_entered = ""
						else:
							lcd.clear()
							lcd.message("Entering 2\nminute lockdown!")
							GPIO.output(buzzerPin, GPIO.LOW)
							sleep(120)
							text_entered = ""
							attemptsLeft = 3
				elif key == "B":
					lcd.clear()
					text_entered = text_entered[:-1]
					for char in text_entered:
						lcd.message("*")
					lcd.message("|")
				else:
					lcd.clear()
					text_entered = text_entered + key
					for char in text_entered:
						lcd.message("*")
					lcd.message("|")
			else:
					GPIO.output(buzzerPin, GPIO.LOW)
		elif state == "unlocked":
			distance = getSonar()
			if distance > 8:
				state = "opened"
		elif state == "opened":
			distance = getSonar()
			if distance < 1:
				for angle in range(0, 76, 1): # make servo rotate from 180 to 0 deg
					servoWrite(angle)
					sleep(0.001)
				servo1.ChangeDutyCycle(0)
				camera.capture('/home/pi/Desktop/image2.jpg')
				camera.stop_preview()
				alertor.sendmail("samarthk2402@gmail.com", "Safe unlocked", "Your safe has been unlocked.", '/home/pi/Desktop/image.jpg')
				lcd.clear()
				lcd.message("Closed")
				text_entered = ""
				state="waiting"


def destroy():
	GPIO.cleanup()
	lcd.clear()
	servo1.stop()

PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.
# Create PCF8574 GPIO adapter.
try:
	mcp = PCF8574_GPIO(PCF8574_address)
except:
	try:
		mcp = PCF8574_GPIO(PCF8574A_address)
	except:
		print ('I2C Address Error !')
		exit(1)
# Create LCD, passing in MCP GPIO adapter.
lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=mcp)

if __name__ == '__main__':     #Program start from here
	print ("Program is starting ... ")
	setup()
	try:
		loop()
	except KeyboardInterrupt:
		destroy()
