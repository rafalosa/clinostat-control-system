#ifndef DRIVER_CONF_H
#define DRIVER_CONF_H

#define CHAMBER_STEP 0 // PD0 for chamber step pin.
#define FRAME_STEP 1 // PD1 for frame step pin.
#define ENABLE_PIN 4 // PB4 for enable pin for both motors.

#define STOP_INTERVAL_CHAMBER 10000 // Determiens the starting speed of the steppers.
#define STOP_INTERVAL_FRAME 10000

#define TIMER_PRESCALER 64
#define ACCElERATION_MODIFIER 3 // Streches out the acceleration period.

#define ENABLE_TIMER1_INTERRUPTS    TIMSK1 |= (1 << OCIE1A) // Macro for enabling the timer1 interrupts.
#define DISABLE_TIMER1_INTERRUPTS   TIMSK1 &= ~(1 << OCIE1A) // Macro for disabling the timer1 interrupts.

#define ENABLE_TIMER3_INTERRUPTS    TIMSK3 |= (1 << OCIE3A) // Macro for enabling the timer3 interrupts.
#define DISABLE_TIMER3_INTERRUPTS   TIMSK3 &= ~(1 << OCIE3A) // Macro for disabling the timer3 interrupts.

#define CHAMBER_STEP_HIGH   PORTD |= (1 << CHAMBER_STEP) // Macro for setting a pin connected to chamber step high.
#define CHAMBER_STEP_LOW    PORTD &= ~(1 << CHAMBER_STEP) // Macro for setting a pin connected to chamber step low.

#define FRAME_STEP_HIGH   PORTD |= (1 << FRAME_STEP) // Macro for setting a pin connected to frame step high.
#define FRAME_STEP_LOW    PORTD &= ~(1 << FRAME_STEP) // Macro for setting a pin connected to frame step low.

#define DISABLE_STEPPERS PORTB |= (1 << ENABLE_PIN)
#define ENABLE_STEPPERS PORTB &= ~(1 << ENABLE_PIN)

void SETUP_TIMER1_INTERRUPTS();
void SETUP_TIMER3_INTERRUPTS();

#endif