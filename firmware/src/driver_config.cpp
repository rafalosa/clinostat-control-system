#include "headers.hpp"
#include "driver_config.hpp"

volatile uint64_t program_time_milis = 0;

void SETUP_TIMER1_INTERRUPTS(){

    cli();
    TCCR1A = 0;
    TCCR1B = 0;
    TCCR1B |= (1 << WGM12); // Timer CTC mode, with OCR1A as TOP.
    TCCR1B |= (1 << CS10); // Setting clock prescaler.
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
    TCCR3B |= (1 << CS30); // Setting clock prescaler.
    TCCR3B |= (1 << CS31);
    //TCCR3B |= (1 << CS32); // Setting clock prescaler.
    TCNT3 = 0;
    OCR3A = STOP_INTERVAL_FRAME;
    sei();
}

void SETUP_TIMER0_INTERRUPTS(){ // Configuration of 8-bit timer for time tracking.

    cli();
    TCCR0A = 0; // OC0A and OC0B pins disconnected.
    TCCR0B = 0;
    TCCR0A |= (1 << WGM01);// Timer CTC mode, with OCR0A as TOP.
    TCCR0B |= (1 << CS00); // Setting clock prescaler to 64.
    TCCR0B |= (1 << CS01);
    TCNT0 = 0;
    OCR0A = F_CPU/64/1000 - 1; // Timer counts to 249 around one thousand times a second with 64 prescaler, which calls the OCR0A ISR every milisecond.
    sei();
}

ISR(TIMER0_COMPA_vect){ // Interrupt service routine for Timer 0. Used only for tracking the program time.

    program_time_milis += 1;
    TCNT0 = 0;

}
