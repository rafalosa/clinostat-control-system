#define __AVR_ATmega32U4__ 
#define F_CPU 16000000UL
#define BAUD 9600
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
#include <stdbool.h>
#include <util/setbaud.h>
//#include "lcd/LiquidCrystal.cpp"
#include "driver_config.hpp"
#include "commands.hpp"

#define MAX_INTERVAL_CHAMBER 10 // Determines the max. speed of the stepper.
#define MAX_INTERVAL_FRAME 10

uint16_t top_speed_interval_chamber = 1;
uint16_t top_speed_interval_frame = 1;

volatile uint32_t steps_chamber_stepper = 0;
volatile uint32_t steps_frame_stepper = 4;

volatile uint8_t chamber_stepper_status = 0; //0 - rampup, 1 - speed reached and rotating, 2 - stopping.
volatile uint8_t frame_stepper_status = 0;

volatile unsigned long chamber_interval = STOP_INTERVAL_CHAMBER;
volatile unsigned long frame_interval = STOP_INTERVAL_FRAME;


int main(){

    DDRD |= (1 << CHAMBER_STEP); // Setting appropriate pins as output.
    DDRD |= (1 << FRAME_STEP);

    SETUP_TIMER1_INTERRUPTS();
    //SETUP_TIMER3_INTERRUPTS();

    ENABLE_TIMER1_INTERRUPTS;
    //ENABLE_TIMER3_INTERRUPTS

    while(true){
        
        /* Main should check for:
        - Check for commands in serial, and respond accordingly.
        - Check for motor status to disable timer interrupts if they stopped.
        - Notify the controller about stepper's status, reaching top speed etc.
        */

    }

    return 0;
}

ISR(TIMER1_COMPA_vect){

    switch(chamber_stepper_status){

        case 0: // Ramp up to top speed.

            CHAMBER_STEP_HIGH;
            CHAMBER_STEP_LOW;

            chamber_interval = STOP_INTERVAL_CHAMBER/steps_chamber_stepper*4;

            if(chamber_interval <= top_speed_interval_chamber){

                chamber_interval = top_speed_interval_chamber;
                chamber_stepper_status = 1;

            }

            else steps_chamber_stepper += 1;

            OCR1A = int(chamber_interval);
            break;

        case 1: // Keep stepping at max speed.

            CHAMBER_STEP_HIGH;
            CHAMBER_STEP_LOW;
            break;

        case 2: // Ramp down to complete stop.

            CHAMBER_STEP_HIGH;
            CHAMBER_STEP_LOW;

            chamber_interval = STOP_INTERVAL_CHAMBER/steps_chamber_stepper*4;
            //result = STOP_INTERVAL * (sqrt(steps+1) - sqrt(steps));
            
            if(chamber_interval >= STOP_INTERVAL_CHAMBER){

                steps_chamber_stepper = 1;
                chamber_stepper_status = 4;
                
            }
            else steps_chamber_stepper -= 1;
            OCR1A = int(chamber_interval);
            break;


        default:
            break;

            // Do nothing and wait for the interrupt to be disabled in the main loop.

    }

    TCNT1 = 0;

}

void checkMotorStatus(){

    if(chamber_stepper_status == 4){

        // Motor stopped and is waiting for the ISR to be disabled.
        DISABLE_TIMER1_INTERRUPTS;
        chamber_stepper_status = 1;
        // Send message to serial.

    }
    if(frame_stepper_status == 4){

        //DISABLE_TIMER3_INTERRUPTS;
        //frame_stepper_status = 1;

    }


}
