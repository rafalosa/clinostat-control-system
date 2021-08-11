#ifndef DRIVER_CONF_H
#define DRIVER_CONF_H

#define CHAMBER_STEP 0 // PD0 for chamber step pin.
#define FRAME_STEP 4 // PD4 for frame step pin.

#define STOP_INTERVAL_CHAMBER 2000 // Determiens the starting speed of the steppers.
#define STOP_INTERVAL_FRAME 2000

#define ENABLE_TIMER1_INTERRUPTS    TIMSK1 |= (1 << OCIE1A) // Macro for enabling the timer1 interrupts.
#define DISABLE_TIMER1_INTERRUPTS   TIMSK1 &= ~(1 << OCIE1A) // Macro for disabling the timer1 interrupts.

#define ENABLE_TIMER3_INTERRUPTS    TIMSK3 |= (1 << OCIE3A) // Macro for enabling the timer3 interrupts.
#define DISABLE_TIMER3_INTERRUPTS   TIMSK3 &= ~(1 << OCIE3A) // Macro for disabling the timer3 interrupts.

#define CHAMBER_STEP_HIGH   PORTD |= (1 << CHAMBER_STEP) // Macro for setting a pin connected to chamber step high.
#define CHAMBER_STEP_LOW    PORTD &= ~(1 << CHAMBER_STEP) // Macro for setting a pin connected to chamber step low.

#define FRAME_STEP_HIGH   PORTD |= (1 << FRAME_STEP) // Macro for setting a pin connected to frame step high.
#define FRAME_STEP_LOW    PORTD &= ~(1 << FRAME_STEP) // Macro for setting a pin connected to frame step low.

void SETUP_TIMER1_INTERRUPTS();
void SETUP_TIMER3_INTERRUPTS();

#endif