// #include <avr/io.h>
// #include <util/delay.h>
// #include <stdbool.h>
// #include <stdlib.h>
// //#include <stdio.h>

//Define necessary commands here

#ifndef LCD_H
#define LCD_H


class LCD{

	public:

		 LCD(const uint8_t&,const uint8_t&);
		~LCD();
		 void init();
		 void home();
		 void setCursor(const uint8_t&,const uint8_t&);
		 void changeCursor(const uint8_t&);
		 void clear();
		 void print(const char arr[]);
		 void print(const float&, const uint8_t&);
		 template<typename T>
		 void print(const T&);
		 void scroll(const bool&);

	private:

		 uint8_t width;
		 uint8_t height;
		 uint8_t operation_mode;

		 bool initial_command = true;
		 void shift_command_4bit(const uint8_t&,const uint8_t&);
		 void print_char(const int&);
		 //void print_char(const uint8_t&);


};

#endif 
