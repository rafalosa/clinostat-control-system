#include "LiquidCrystal.h"
#include "lcd_commands.h"

#define ENABLE_DELAY_US 1
#define COMMAND_DELAY_US 37
#define CLEAR_DELAY_US 1520

#define PORT(x) tempPORT(x)
#define tempPORT(x) (PORT##x)

#define DDR(x) tempDDR(x)
#define tempDDR(x) (DDR##x) // Setting up macros

#define LCD_DATA_PORT B // 4 highest bits of given port will be used for data pins.
#define LCD_RS_PORT D
#define LCD_EN_PORT D
#define LCD_RW_PORT C


#define RS_PIN 4//PORT(LCD_RS_PORT)
#define EN_PIN 7//PORT(LCD_EN_PORT)
#define RW_PIN 6//PORT(LCD_RW_PORT)


#define CLEAR_DATA_PORT(COMM) PORT(LCD_DATA_PORT) &= ~(COMM)
#define TOGGLE_PIN(REG,VAR) PORT(REG) ^= 1 << VAR


LCD::LCD(const uint8_t& ROWS,const uint8_t& COLS){ //Create an LCD object,assign RS, Enable and Data pins

	width = COLS;
	height = ROWS;
	DDR(LCD_DATA_PORT) |= 0xf0;
	DDR(LCD_RS_PORT) |= _BV(RS_PIN);
	DDR(LCD_RW_PORT) |= _BV(RW_PIN);
	DDR(LCD_EN_PORT) |= _BV(EN_PIN);

}

LCD::~LCD(){




}

void LCD::init(){

	this->shift_command_4bit(DISPLAY_WRITE_IR,BIT_MODE_4);
	this->shift_command_4bit(DISPLAY_WRITE_IR,DISPLAY_LINES_2_5x8_DOTS);
	this->shift_command_4bit(DISPLAY_WRITE_IR,DISPLAY_POWER_ON);
	this->shift_command_4bit(DISPLAY_WRITE_IR,DISPLAY_ENTRY_MODE);
	this->shift_command_4bit(DISPLAY_WRITE_IR,DISPLAY_HOME);
	this->shift_command_4bit(DISPLAY_WRITE_IR,DISPLAY_CURSOR_VISIBLE);
	_delay_us(1);

}

void LCD::shift_command_4bit(const uint8_t& config_bits,const uint8_t& command_bits){

	//config_bits: 0b RS RW
	uint8_t least_bits = (command_bits & 0x0F) << 4; // First 4 least significant bits.
	uint8_t most_bits = command_bits & 0xF0; // 4 most significant bits.

	PORT(LCD_RW_PORT) ^= ((config_bits & 0x01) << RW_PIN); // Setting RS and RW pins.
	PORT(LCD_RS_PORT) ^= ((((config_bits & 0x02)) >> 1 )<< RS_PIN);
	PORT(LCD_DATA_PORT) |= most_bits; //Setting data pins.

	TOGGLE_PIN(LCD_EN_PORT,EN_PIN);
	_delay_us(ENABLE_DELAY_US); // Sending command by blinking EN pin.
	TOGGLE_PIN(LCD_EN_PORT,EN_PIN);

	CLEAR_DATA_PORT(most_bits);

	if(this->initial_command){

		PORT(LCD_RW_PORT) ^= ((config_bits & 0x01) << RW_PIN); // Setting RS and RW pins.
		PORT(LCD_RS_PORT) ^= ((((config_bits & 0x02)) >> 1 )<< RS_PIN);
		this->initial_command = false;

	}
	else{

	PORT(LCD_DATA_PORT) |= least_bits;

	TOGGLE_PIN(LCD_EN_PORT,EN_PIN);
	_delay_us(ENABLE_DELAY_US);
	TOGGLE_PIN(LCD_EN_PORT,EN_PIN);

	CLEAR_DATA_PORT(least_bits);

	PORT(LCD_RW_PORT) ^= ((config_bits & 0x01) << RW_PIN); // Resetting RS and RW pins.
	PORT(LCD_RS_PORT) ^= ((((config_bits & 0x02)) >> 1 )<< RS_PIN);
	}
	_delay_us(COMMAND_DELAY_US);
}

void LCD::print_char(const int& character){

	this->shift_command_4bit(DISPLAY_WRITE_DR,character);

}

void LCD::print(const char arr[]){

	while(*arr){

		this->print_char(*arr++);
	}
}

template<typename T>
void LCD::print(const T& num){

	long long int num_cop = num;

	if(num < 0){

		num_cop *= -1;
		this->print_char('-');
	}

	char buffer[16];
	uint8_t i = 0;

	while(num_cop != 0){

		buffer[i++] = num_cop%10 + 48;
		num_cop /= 10;

	}
	for(uint8_t j = i;j>0;j--){

		this->print_char(buffer[j-1]);

	}
}

void LCD::print(const float& num, const uint8_t& precision = 1){




}

void LCD::clear(){

	this->shift_command_4bit(DISPLAY_WRITE_IR,DISPLAY_CLEAR);
	_delay_us(CLEAR_DELAY_US);
}




