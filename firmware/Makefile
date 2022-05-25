CC= avr-g++
CFLAGS= -Os -DF_CPU=16000000UL -mmcu=atmega32u4
INCLUDE_DIR:= include
SOURCE_DIR:= src

SRC:= $(wildcard $(SOURCE_DIR)/*.cpp)
DEPD:= $(wildcard $(INCLUDE_DIR)/*.hpp)

all: clinostat-stepper-driver.out

%.out: $(SOURCE_DIR)/%.cpp
	$(CC) $(CFLAGS) $(SRC) -I $(INCLUDE_DIR) -o $@

%.hex: %.out
	avr-objcopy -O ihex -R .eeprom $< $@

install.%: %.hex
	avrdude -F -V -c usbasp -p m32u4 -b 115200 -U flash:w:$<

clean:
	rm -f *.out