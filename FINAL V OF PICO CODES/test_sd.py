import machine 
import sdcard, uos
import time

cs = machine.Pin(1, machine.Pin.OUT)

# Intialize SPI peripheral (start with 1 MHz)
spi = machine.SPI(0,
                  baudrate=1000000,
                  polarity=0,
                  phase=0,
                  bits=8,
                  firstbit=machine.SPI.MSB,
                  sck=machine.Pin(2),
                  mosi=machine.Pin(3),
                  miso=machine.Pin(4))
sd = sdcard.SDCard(spi, cs)
time.sleep_ms(500)
vfs = uos.VfsFat(sd)
uos.mount(vfs, "/sd")
#uos.mount(sd, '/sd')
time.sleep_ms(500)
print(uos.listdir('/sd'))

print("Starting ADC samples")

adc = ADC(0)
with open('/sd/adcData.txt', "w") as f:
    while True:
        x = adc.read_u16() # Replace this line with a sensor reading of your choosing
        t = time.ticks_ms()/1000
        f.write(str(t)) # Write time sample was taken in seconds
        f.write(' ') # A space
        f.write(str(x)) # Write sample data
        f.write('\n') # A new line
        f.flush() # Force writing of buffered data to the SD card
        print(t, x)
        time.sleep_ms(500)