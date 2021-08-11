CC=avr-gcc
CFLAGS= -Os -DF_CPU=16000000UL -mmcu=atmega32u4



all: clinostat-stepper-driver.out

%.out: %.cpp
	$(CC) $(CFLAGS) $< -o $@

%.hex: %.out
	avr-objcopy -O ihex -R .eeprom $< $@

#USBPORT:=$(shell ls /dev/ttyACM*)
#avrdude -F -V -c arduino -P $(USBPORT) -p m32u4 -b 115200 -U flash:w:$<

install.%: %.hex
	avrdude -F -V -c usbasp -p m32u4 -b 115200 -U flash:w:$<

clean:
	rm -f *.hex *.out