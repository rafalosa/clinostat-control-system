#include "headers.hpp"
#include "driver_config.hpp"

void SETUP_TIMER1_INTERRUPTS(){

    cli();
    TCCR1A = 0;
    TCCR1B = 0;
    TCCR1B |= (1 << WGM12); // Timer CTC mode, with OCR1A as TOP.
    TCCR1B |= (1 << CS10); // Setting lock prescaler.
    TCCR1B |= (1 << CS11);
    //TCCR1B |= (1 << CS12); // Setting clock prescaler.
    TCNT1 = 0;
    OCR1A = STOP_INTERVAL_CHAMBER;
    sei();

}

void SETUP_TIMER3_INTERRUPTS(){
    cli();
    TCCR3A = 0;
    TCCR3B = 0;
    TCCR3B |= (1 << WGM32);// Timer CTC mode, with OCR3A as TOP.
    TCCR3B |= (1 << CS30); // Setting lock prescaler.
    TCCR3B |= (1 << CS31);
    //TCCR3B |= (1 << CS32); // Setting lock prescaler.
    TCNT3 = 0;
    OCR3A = STOP_INTERVAL_FRAME;
    sei();
}