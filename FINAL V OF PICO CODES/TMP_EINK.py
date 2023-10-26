## try to print temperature outputted to the E-Ink tablet

from machine import ADC, Pin, SPI
from time import sleep
from EPD_2in13_B_V4 import epd_2in13_B_V4
import framebuf
import utime
from centerwriter import CenterWriter
import freesans20
#TMP 36 PINS
adcpin = 26
tmp36 = ADC(adcpin)

 
if __name__ == '__main__':
    epd = epd_2in13_B_V4()
    #cw = CenterWriter(epd, freesans20)
    epd.Clear(0xff,0xff)
    epd.imageblack.text("Waveshare", 0, 10, 0x00)
    
    #cw.set_vertical_spacing(10)
    #cw.set_vertical_shift(-30)
    #cw.write_lines(["Hello"])
    epd.display()
    epd.delay_ms(2000)
    epd.Clear(0xff, 0xff)
    epd.delay_ms(2000)
    epd.sleep()
    
        

#while True:
  #  adc_value = tmp36.read_u16()
   # volt = (3.3/65535)*adc_value
    #degC = (100*volt)-50
    #print(round(degC,1))
    #epd.imageblack.text(str(degC), 0, 40, 0x00)
    #epd.display()
    #sleep(5)
    
    