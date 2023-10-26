from machine import SPI, Pin, UART, ADC
import sdcard, uos, utime,time
from micropyGPS import MicropyGPS
from pico_epaper import epd_2in13_B_V4
from EPD_2in13_B_V4_Landscape import EPD_2in13_B_V4_Landscape


#initialise all required components

##led
led = Pin('LED', Pin.OUT)
led.on()
time.sleep_ms(500)
led.off()
##eink display
epd = EPD_2in13_B_V4_Landscape()
epd.Clear(0xff, 0xff)
epd.imageblack.fill(0xff)
epd.imagered.fill(0xff)
##button
button = Pin(14, Pin.IN, Pin.PULL_UP)
##temperature sensor
adcpin = 26
tmp36 = ADC(adcpin)
##irradiance sensors
irrad = ADC(27) #external sensor
irrad_p = ADC(28) #small solar panel
##SD Card
spi = SPI(0,sck=Pin(2), mosi=Pin(3), miso=Pin(0))
cs = Pin(1)
sd = sdcard.SDCard(spi, cs)
uos.mount(sd, '/sd')
##GPS module
gps_module = UART(0, baudrate=9600, tx=Pin(16), rx=Pin(17))
time_zone = 11 #time will be in AEDT unless this changes - for Darwin/Adelaide should be 9.5 (UTC offset)
gps = MicropyGPS(time_zone)

def convert_coordinates(sections):
    if sections[0] == 0:  # sections[0] contains the degrees
        return None
 
    # sections[1] contains the minutes
    data = sections[0] + (sections[1] / 60.0)
 
    # sections[2] contains 'E', 'W', 'N', 'S'
    if sections[2] == 'S':
        data = -data
    if sections[2] == 'W':
        data = -data
 
    data = '{0:.6f}'.format(data)  # 6 decimal places
    return str(data)

# Get a list of existing files in the "sd" folder
existing_files = uos.listdir("/sd")

# Extract the file numbers from the existing filenames
file_numbers = [int(filename.split('_')[1].split('.')[0]) for filename in existing_files if filename.startswith("data_")]

# Determine the next file number to use
if file_numbers:
    file_number = max(file_numbers) + 1
else:
    file_number = 1

#defining line count and file formats
i=0
line_count = 0
max_lines = 4320

#the loop below occurs every 10 seconds
while True:
    #GPS data - MUST COME BEFORE ANY GPS DATA CALLED
    length = gps_module.any()
    if length > 0:
        data = gps_module.read(length)
        #print(data)
        for byte in data:
            message = gps.update(chr(byte))
        #temperature
    raw_T = tmp36.read_u16() # Replace this line with a sensor reading of your choosing
    volt = (3.3/65535)*raw_T
    temp = (100*volt)-50
    #irradiance Si-V-1.5-TC (fancy sensor that is separate to the big circuit - use these values for your irradiance readings
    raw_irrad = irrad.read_u16()
    irrad_v = (3.3/65535)*raw_irrad # to convert to irradiance value times this by 1000 to get irradiance in W/m2
    #irradiance panel - for my own testing and comparison
    raw_irrad_p = irrad_p.read_u16()
    irrad_I_p = (3.3/65535)*raw_irrad_p
    #datetime
    timestamp = gps.timestamp
    date = gps.date_string('s_dmy')
    timestring=str(date+'  '+str(timestamp[0])+':'+str(timestamp[1])+':'+str(timestamp[2]))
    latitude = convert_coordinates(gps.latitude)
    longitude = convert_coordinates(gps.longitude)
    sat_details = str(gps.satellites_used)
    hdop = str(gps.hdop)
    pdop = str(gps.pdop)
    vdop = str(gps.vdop)
    fix = str(gps.fix_stat)
    filename = "/sd/data_{}.txt".format(file_number)

    with open(filename, "a") as f:
        #text file recording results
        if line_count == 0:
            header = "Timestamp, Raw Irradiance (SiV1.5TC), Irradiance Voltage (SiV1.5TC), Raw Irradiance (Panel), Irradiance Voltage (Panel), Temperature, Latitude, Longitude, HDOP, PDOP, VDOP, Satellites Used\n"
            f.write(header)
        f.write(timestring)
        f.write(',') 
        f.write(str(raw_irrad)) 
        f.write(',')
        f.write(str(irrad_v))
        f.write(',')
        f.write(str(raw_irrad_p)) 
        f.write(',')
        f.write(str(irrad_I_p))
        f.write(',')
        f.write(str(temp))
        f.write(',')
        f.write(str(latitude))
        f.write(',') 
        f.write(str(longitude))
        f.write(',') 
        f.write(str(hdop))
        f.write(',') 
        f.write(str(vdop))
        f.write(',') 
        f.write(str(pdop))
        f.write(',') 
        f.write(str(sat_details))
        f.write('\n') # A new line
        f.flush()
        line_count += 1

    if line_count >= max_lines:
        line_count = 0
        file_number += 1
    led.on()
    time.sleep_ms(500)
    led.off()

    if i % 10 == 0:
    #updating what is printed to the E-Ink display every 10 samples
        #preamble - REQUIRED
        epd.imageblack.fill(0xff)
        epd.imagered.fill(0xff)
        #writing to the E-Ink display - change the 3 item in brackets (10,20,30) to write to a new line 
        epd.imageblack.text("Time: " + str(timestring), 0, 10, 0x00)
        epd.imageblack.text("Temperature: " + str(temp), 0, 20, 0x00)
        epd.imageblack.text("Latitude: " +str(gps.latitude_string()), 0, 30, 0x00)
        epd.imageblack.text("Longitude: " +str(gps.longitude_string()), 0, 40, 0x00)
        epd.imageblack.text("Irradiance:" +str(irrad_v*1000)+ " W/m2",0 ,50, 0x00)
        epd.display()
        i += 1
    
    elif i % 10000 == 0:
        #full eink refresh 
        epd.Clear(0xff, 0xff)
        epd.imageblack.fill(0xff)
        epd.imagered.fill(0xff)
        epd.imageblack.fill_rect(0, 10, 250, 8, 0xff)
        epd.imageblack.fill_rect(0, 20, 250, 8, 0xff)
        epd.imageblack.fill_rect(0, 30, 250, 8, 0xff)
        epd.imageblack.fill_rect(0, 40, 250, 8, 0xff)
        epd.imageblack.fill_rect(0, 50, 250, 8, 0xff)
        #writing to the E-Ink display - change the 3 item in brackets (10,20,30) to write to a new line 
        epd.imageblack.text("Time: " + str(timestring), 0, 10, 0x00)
        epd.imageblack.text("Temperature: " + str(temp), 0, 20, 0x00)
        epd.imageblack.text("Latitude: " +str(gps.latitude_string()), 0, 30, 0x00)
        epd.imageblack.text("Longitude: " +str(gps.longitude_string()), 0, 40, 0x00)
        epd.imageblack.text("Irradiance:" +str(irrad_v*1000)+ " W/m2",0 ,50, 0x00)
        epd.display()
        i += 1
    else:
        i += 1
        
    if button.value() == 0:
        #click button to reset E-Ink screen
        led.on()
        time.sleep_ms(100)
        led.off()
        epd.Clear(0xff, 0xff)
        epd.imageblack.fill(0xff)
        epd.imagered.fill(0xff)
        epd.display()
        epd.delay_ms(2000)
        epd.Clear(0xff, 0xff)
        epd.delay_ms(2000)
        print("sleep")
        epd.sleep()
    print("loop")
    time.sleep(10) #sampling timing in seconds

