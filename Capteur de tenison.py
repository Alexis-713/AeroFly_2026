from machine import Pin, I2C
import time

i2c = I2C(0, scl=Pin(4), sda=Pin(5), freq=100000)

INA3221_ADDR = 0x41

def read_register(reg):
    data = i2c.readfrom_mem(INA3221_ADDR, reg, 2)
    return (data[0] << 8) | data[1]

def read_bus_voltage(channel):
    # registres bus voltage :
    reg_map = {
        1: 0x02,
        2: 0x04,
        3: 0x06
    }
    
    raw = read_register(reg_map[channel])
    
    # conversion (LSB = 8mV)
    voltage = (raw >> 3) * 0.008
    return voltage

while True:
    v1 = read_bus_voltage(1)
    v2 = read_bus_voltage(2)
    v3 = read_bus_voltage(3)
    
    print("Ch1: {:.3f} V | Ch2: {:.3f} V | Ch3: {:.3f} V".format(v1, v2, v3))
    time.sleep(1)