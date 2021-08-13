#include "headers.hpp"
#include "serial.hpp"

Serial::Serial(){



}

Serial::~Serial(){




}



void Serial::begin(){

    UBRR1H = UBRRH_VALUE;
    UBRR1L = UBRRL_VALUE;

    #if USE_2X

        UCSR1A |= (1 << U2X1);

    #else

        UCSR1A &= ~(1 << U2X1);

    #endif

    UCSR1C = (1 << UCSZ11) | (1 << UCSZ10); // 8 bit data frames.
    //UCSR1C = (1 << USBS1); // 2 Stop bits.
    UCSR1B = (1 << RXEN1) | (1 << TXEN1);   // Enable RX and TX.

}
void Serial::write(uint8_t byte){

    loop_until_bit_is_set(UCSR1A,UDRE1);
    UDR1 = byte;

}

uint8_t Serial::read(){

    loop_until_bit_is_set(UCSR1A, RXC1);
    return UDR1;

}


