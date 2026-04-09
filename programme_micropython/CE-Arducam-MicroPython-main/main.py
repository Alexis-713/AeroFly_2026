from machine import Pin, SPI, reset
from camera import *

'''
#################### PINOUT ####################

Camera pin - ESP32 S3
VCC        - 5V - rouge
GND        - GND - noir
SCK        - GP40 - blanc
MISO       - RX - GP41 - marron
MOSI       - TX - GP42 - jaune
CS         - GP39 - orange

SPI - 2
'''


################################################################## PROGRAMME ##################################################################
#ESP 32 S3
spi = SPI(2,sck=Pin(40), miso=Pin(41), mosi=Pin(42), baudrate=1000000)
cs = Pin(39, Pin.OUT)

# Allumage de la led lors d'une capture
#onboard_LED = Pin(48, Pin.OUT) 

fm = FileManager()

#Mettre debug_text_enabled sur false si la console n'est pas utilisé
cam = Camera(spi, cs, debug_text_enabled=True)
#cam.resolution = '320X240' 
#cam.resolution = '640x480'
cam.resolution = '1920x1080'
# cam.set_filter(cam.SPECIAL_REVERSE)
cam.set_brightness_level(cam.BRIGHTNESS_PLUS_4)
cam.set_contrast(cam.CONTRAST_MINUS_3)

cam.capture_jpg()
sleep_ms(50)
#cam.saveJPG('modifier_ici_le_nom.jpg') #nom fixe
cam.saveJPG(fm.new_jpg_fn('change_name')) #nom pouvant s'incrémenter


#################################################################################################################################################
'''
Benchmarks
- La vitesse du SPI par défaut (1000000), cam.resolution = '640X480', no burst read (camera pointée au plafond) ==== TIME: ~7.8 secondes
- Vitesse augmentée (8000000), cam.resolution = '640X480', no burst read (camera pointée au plafond) ==== TIME: ~7.3 secondes

'''
