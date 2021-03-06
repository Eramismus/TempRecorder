
# -*- coding: utf-8 -*-
 
import time, math
import RPi.GPIO as GPIO
import pandas as pd
import datetime as dt
from weather import Weather, Unit

# Set GPIO pins to Broadcom numbering system
GPIO.setmode(GPIO.BCM)
 
# Define our constants
RUNNING = True
led_list = [5,6,13,16,19,26,20,21] # GPIO pins for LEDs
temp_low = 18 # Lowest temperature for LEDs (F)
temp_high = 23 # Highest temperature for LEDs (F)
a_pin = 23
b_pin = 22

# rgb-led
red_pin = 4
green_pin = 17
blue_pin = 27

# button 
button_pin = 18

#GPIO.setwarnings(False) # Ignore warning for now
GPIO.setup(red_pin, GPIO.OUT)
GPIO.output(red_pin,0)
GPIO.setup(green_pin, GPIO.OUT)
GPIO.output(green_pin,0)
GPIO.setup(blue_pin, GPIO.OUT)
GPIO.output(blue_pin,0)

GPIO.setup(button_pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)

# Initialize a dictionary for data collection
tempdata = {}
t_list = [] # list for temperature readings to calculate averages

# Filename for the csv-file
fileid = 4 # ID-number for csv files
filename = "./" + str(fileid) + "_data_record.csv" # Path to file
 
# Set up our LED GPIO pins as outputs
for x in range(0,8):
    GPIO.setup(led_list[x], GPIO.OUT)
    GPIO.output(led_list[x], GPIO.LOW)
 
# Try to keep this value near 1 but adjust it until
# the temperature readings match a known thermometer
adjustment_value = 0.70

def red_on():
	GPIO.output(red_pin,1)
	GPIO.output(green_pin,0)
	GPIO.output(blue_pin,0)

def green_on():
	GPIO.output(red_pin,0)
	GPIO.output(green_pin,1)
	GPIO.output(blue_pin,0)

def blue_on():
	GPIO.output(red_pin,0)
	GPIO.output(green_pin,0)
	GPIO.output(blue_pin,1)

def custom_on(in1, in2, in3):
	GPIO.output(red_pin,in1)
	GPIO.output(green_pin,in2)
	GPIO.output(blue_pin,in3)

def all_off():
	GPIO.output(red_pin,0)
	GPIO.output(green_pin,0)
	GPIO.output(blue_pin,0)
 
# Create a function to take an analog reading of the
# time taken to charge a capacitor after first discharging it
# Perform the procedure 100 times and take an average
# in order to minimize errors and then convert this
# reading to a resistance

def resistance_reading():
    total = 0
    for i in range(1, 100):
        # Discharge the 330nf capacitor
        GPIO.setup(a_pin, GPIO.IN)
        GPIO.setup(b_pin, GPIO.OUT)
        GPIO.output(b_pin, False)
        time.sleep(0.01)
        # Charge the capacitor until our GPIO pin
        # reads HIGH or approximately 1.65 volts
        GPIO.setup(b_pin, GPIO.IN)
        GPIO.setup(a_pin, GPIO.OUT)
        GPIO.output(a_pin, True)
        t1 = time.time()
        while not GPIO.input(b_pin):
            pass
        t2 = time.time()
        # Record the time taken and add to our total for
        # an eventual average calculation
        total = total + (t2 - t1) * 1000000
    # Average our time readings
    reading = total / 100
    # Convert our average time reading to a resistance
    resistance = reading * 6.05 - 939
    return resistance
 
# Create a function to convert a resistance reading from our
# thermistor to a temperature in Celsius which we convert to
# Fahrenheit and return to our main loop
def temperature_reading(R):
    B = 3000.0 # Thermistor constant from thermistor datasheet
    R0 = 100000.0 # Resistance of the thermistor being used
    t0 = 273.15 # 0 deg C in K
    t25 = t0 + 25.0 # 25 deg C in K
    # Steinhart-Hart equation
    inv_T = 1/t25 + 1/B * math.log(R/R0)
    T = (1/inv_T - t0) * adjustment_value
    return T 

def change_occupancy(state):
	print('Occupancy changed from: '+ state)
	if state == 'occupied':
		new_state = 'unoccupied'
	if state == 'unoccupied':
		new_state = 'occupied'
	return new_state
 
# Main loop
def main_loop(RUNNING):
    	k=0 # defined for determining whether we are in the first loop
    	systime = dt.datetime.now() # Initialize these just in case
	systime_prev = systime
	systimemin_prev = int(systime.minute)
    	t_list = []
	occ_list = []
	tempdata = {}
	tempdata[systime] = {}
	occ_state = 'occupied'
	# Weather
	woeid = 27504 #loughborough weather station
	weather = Weather(unit=Unit.CELSIUS)
	location = weather.lookup(woeid)

	condition = location.condition
	forecasts = location.forecast
	wind = location.wind

	descr = condition.text
	out_temp = float(condition.temp)
	wind_speed = float(wind.speed)*0.44704 #conversion from mph
	wind_direction = float(wind.direction)
	wind_chill = wind.chill

	try:
        	while RUNNING:
			# Update system time
			systime=dt.datetime.now()
			button_state = GPIO.wait_for_edge(button_pin, GPIO.FALLING, timeout=15000)
			if button_state is None:
				#print('No change in occupancy, currently ' + occ_state)
				pass
			else:
				occ_state = change_occupancy(occ_state)

			# Get occupancy
			if occ_state == 'occupied':
				green_on()
			if occ_state == 'unoccupied':
				red_on()

			if (systime - systime_prev).total_seconds() >= 15:
				systime_prev = systime
				# Get the thermistor temperature
				t = temperature_reading(resistance_reading())
				t_list.append(t)
						
				# Print temperature values in real time
				print(systime)
				print("Temp   " +str(t))
				# Turn off LEDs
				for x in range(0,8):
					GPIO.output(led_list[x], GPIO.LOW)
		 
				# Calculate how many LEDs to illuminate
				# within our temp_low to temp_high range
				if t <= temp_low:
					t_led = temp_low
				if t >= temp_high:
					t_led = temp_high
				else:
					t_led = t
						
				num_leds = int(round(((t_led-temp_low) / (temp_high-temp_low))*8))
     
				# Turn LEDs on
				for x in range(0,num_leds):
					GPIO.output(led_list[x], GPIO.HIGH)
			
				# Get occupancy
				if occ_state == 'occupied':
					green_on()
					occ_list.append(1)
				if occ_state == 'unoccupied':
					red_on()
					occ_list.append(0)

            			# Part to write into csv
            			if int(systime.minute) == (systimemin_prev + 1): # Do this at defined intervals
                			# Update the systime_prev to prepare for the next loop
                			tempdata = {}
					tempdata[systime] = {} # clear the old reading
					# Weather
					if systime.minute == 59:
						weather = Weather(unit=Unit.CELSIUS)
						location = weather.lookup(woeid)
						condition = location.condition
						forecasts = location.forecast
						wind = location.wind
				
						descr = condition.text
						out_temp = float(condition.temp)
						wind_speed = float(wind.speed)*0.44704 #conversion from mph
						wind_direction = float(wind.direction)
						wind_chill = wind.chill
						
					tempdata[systime]['Temp'] = sum(t_list)/len(t_list) # average of the recorded temperature within last minute
					tempdata[systime]['Occupancy'] = sum(occ_list)/len(occ_list)
					tempdata[systime]['Weather'] = descr
					tempdata[systime]['Outside_temp'] = out_temp
					tempdata[systime]['Wind_speed'] = wind_speed
					tempdata[systime]['Wind_direction'] = wind_direction
					tempdata[systime]['Wind_chill'] = wind_chill
						
					df = pd.DataFrame.from_dict(tempdata,orient='index') 
					df.index.name = "Time" # Define the index as time
					if k == 0:
						df.to_csv(filename) # create a new file
						t_list = [] #Empty the list
						occ_list = []
						print(tempdata)
						k = 1 # set to 1 after the file has been created
					else:
						print("---Recorded---")
						print(tempdata)
						df.to_csv(filename, mode='a', header=False) # Append the current file
						t_list = [] #Empty the list
						occ_list = []

				if int(systime.minute) == 59: # If 59th minute set to start again from zero
					systimemin_prev = int(-1)
				else:
					systimemin_prev = int(systime.minute) # Normal update

		# Time interval for taking readings in seconds and printing
		time.sleep(0.1)
		# If CTRL+C is pressed the main loop is broken
    	except KeyboardInterrupt:
        	RUNNING = False
        	print("\Quitting")
	finally:
		GPIO.cleanup()

main_loop(RUNNING)
GPIO.cleanup()
