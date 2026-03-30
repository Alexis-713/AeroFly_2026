import serial
import time

ser = serial.Serial("COM11", 9600, timeout=1)

time.sleep(2)

ser.write(b'AT+VER\r\n')
time.sleep(1)

print(ser.read_all())

ser.write(b'AT+MODE=LWOTAA\r\n')
time.sleep(1)

print(ser.read_all())

ser.write(b'AT+ID=DevEui\r\n')
time.sleep(1)

print(ser.read_all())

ser.write(b'AT+ID=AppEui\r\n')
time.sleep(1)

print(ser.read_all())

ser.close()