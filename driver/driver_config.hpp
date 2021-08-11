#ifndef DRIVER_CONF_H
#define DRIVER_CONF_H

#define CHAMBER_STEP 0 // PD0 for chamber step pin.
#define FRAME_STEP 4 // PD4 for frame step pin.
#define CLK_PRESCALER 1024
#define STEP_DIV 16

#define STOP_INTERVAL_CHAMBER 5000 // Determiens the starting speed of the stepper.
#define STOP_INTERVAL_FRAME 5000

#define ENABLE_TIMER1_INTERRUPTS    TIMSK1 |= (1 << OCIE1A)
#define DISABLE_TIMER1_INTERRUPTS   TIMSK1 &= ~(1 << OCIE1A)

#define ENABLE_TIMER3_INTERRUPTS    TIMSK3 |= (1 << OCIE3A)
#define DISABLE_TIMER3_INTERRUPTS   TIMSK3 &= ~(1 << OCIE3A)

#define CHAMBER_STEP_HIGH   PORTD |= (1 << CHAMBER_STEP)
#define CHAMBER_STEP_LOW    PORTD &= ~(1 << CHAMBER_STEP)

void SETUP_TIMER1_INTERRUPTS(){

    cli();
    TCCR1A = 0;
    TCCR1B = 0;
    TCCR1B |= (1 << WGM12);
    TCCR1B |= (1 << CS10);
    //TCCR1B |= (1 << CS11);
    TCCR1B |= (1 << CS12);
    TCNT1 = 0;
    OCR1A = STOP_INTERVAL_CHAMBER;
    sei();

}

void SETUP_TIMER3_INTERRUPTS(){

    cli();
    TCCR3A = 0;
    TCCR3B = 0;
    TCCR3B |= (1 << WGM32);
    TCCR3B |= (1 << CS30);
    //TCCR3B |= (1 << CS31);
    TCCR3B |= (1 << CS32);
    TCNT3 = 0;
    OCR3A = STOP_INTERVAL_FRAME;
    sei();
}

#endif