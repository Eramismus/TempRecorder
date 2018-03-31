
# -*- coding: utf-8 -*-
 
import time, math
import RPi.GPIO as GPIO
import pandas as pd
import datetime as dt
 
# Set GPIO pins to Broadcom numbering system
GPIO.setmode(GPIO.BCM)
 
# Define our constants
RUNNING = True
led_list = [5,6,13,16,19,26,20,21] # GPIO pins for LEDs
temp_low = 15 # Lowest temperature for LEDs (F)
temp_high = 23 # Highest temperature for LEDs (F)
a_pin = 23
b_pin = 22

# Initialize a dictionary for data collection
tempdata = {}
t_list = [] # list for temperature readings to calculate averages

# Filename for the csv-file
fileid = 1 # ID-number for csv files
filename = "./" + str(fileid) + "_temps.csv" # Path to file
 
# Set up our LED GPIO pins as outputs
for x in range(0,8):
    GPIO.setup(led_list[x], GPIO.OUT)
    GPIO.output(led_list[x], GPIO.LOW)
 
# Try to keep this value near 1 but adjust it until
# the temperature readings match a known thermometer
adjustment_value = 0.70
 
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
 
# Main loop
def main_loop(RUNNING):
    k=0 # defined for determining whether we are in the first loop
    systime = dt.datetime.now() # Initialize these just in case
    systimemin_prev = int(systime.minute)
    try:
        while RUNNING:
            # Update system time
            systime=dt.datetime.now()
            # Get the thermistor temperature
			t = temperature_reading(resistance_reading())
            t_list = t_list.append(t)
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
          
            # Part to write into csv
            if int(systime.minute) == (systimemin_prev + 1): # Do this at defined intervals
                # Update the systime_prev to prepare for the next loop
                tempdata = {} # clear the old reading
				if int(systime.minute) == 59: # If 59th minute set to start again from zero
					systimemin_prev = int(-1)
				else:
					systimemin_prev = int(systime.minute) # Normal update
				
				tempdata[systime] = sum(t_list)/len(t_list) # average of the recorded temperature within last minute
				df = pd.DataFrame.from_dict(tempdata,orient='index') 
				df.index.name = "Time" # Define the index as time
				if k == 0:
					df.to_csv(filename) # create a new file
					t_list = [] #Empty the list
					k = 1 # set to 1 after the file has been created
				else:
					print("---Recorded---")
					df.to_csv(filename, mode='a', header=False) # Append the current file
					t_list = [] #Empty the list
            
            # Time interval for taking readings in seconds and printing
            time.sleep(15)
            
    # If CTRL+C is pressed the main loop is broken
    except KeyboardInterrupt:
        RUNNING = False
        print("\Quitting")


try:
    while RUNNING:
        #This loop is for making sure the main loop is started at even seconds
        systime=dt.datetime.now()
        if (int(systime.second) % 10) == 0: # Start the main loop at even minute i.e. seconds are zero
            main_loop(RUNNING)
        else:
            time.sleep(1) # Wait for one sec, print and try again
            print("Not started yet")
except KeyboardInterrupt:
    RUNNING = False
    print("\Quitting")
        
        
        

 
# Actions under 'finally' will always be called
# regardless of what stopped the program
finally:
    # Stop and cleanup to finish cleanly so the pins
    # are available to be used again
    GPIO.cleanup()
