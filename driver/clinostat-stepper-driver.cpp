#define __AVR_ATmega32U4__ 
#define F_CPU 16000000UL
#define BAUD 9600
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
#include <stdbool.h>
#include <util/setbaud.h>
//#include "lcd/LiquidCrystal.cpp"
#include "driver_config.cpp"
#include "commands.hpp"
#include "clinostat_mechanics.hpp"
#include "serial.hpp"

uint16_t top_speed_interval_chamber = 1;
uint16_t top_speed_interval_frame = 1;

volatile uint32_t steps_chamber_stepper = 0;
volatile uint32_t steps_frame_stepper = 4;

volatile uint8_t chamber_stepper_status = 0; //0 - rampup, 1 - speed reached and rotating, 2 - stopping.
volatile uint8_t frame_stepper_status = 0;

volatile unsigned long chamber_interval = STOP_INTERVAL_CHAMBER;
volatile unsigned long frame_interval = STOP_INTERVAL_FRAME;


/* Flags declarations. */

bool top_speed_flag = false;
bool receive_serial = true;
bool clinostat_stopping = false;
bool clinostat_connected = false;


uint8_t current_program_status = 0; /* 0 -idle, 1 - running, 2 - paused,   */
uint8_t previous_program_status = 1;

int main(){

    DDRD |= (1 << CHAMBER_STEP); // Setting appropriate pins as output.
    DDRD |= (1 << FRAME_STEP);

    SETUP_TIMER1_INTERRUPTS();
    //SETUP_TIMER3_INTERRUPTS();

    //ENABLE_TIMER1_INTERRUPTS;
    //ENABLE_TIMER3_INTERRUPTS

    while(true){
        
        /* Main should:

        - Check for commands in serial, and respond accordingly.
        - Check for motor status to disable timer interrupts if they've stopped.
        - Notify the controller about stepper's status, reaching top speed etc.
        - Monitor in what mode the clinostat is in.


        Program structure in pseudocode:

        if(serial not empty && serial flag){

            new status = handleSerial();
            check if program status needs to be updated();

        }

        checkFlags();
        checkForMotorStop();
        handleProgramStatus();


        */


    }

    return 0;
}

ISR(TIMER1_COMPA_vect){

    switch(chamber_stepper_status){

        case 0: // Ramp up to top speed.

            CHAMBER_STEP_HIGH;
            CHAMBER_STEP_LOW;

            chamber_interval = STOP_INTERVAL_CHAMBER/steps_chamber_stepper*ACCElERATION_MODIFIER;

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

            chamber_interval = STOP_INTERVAL_CHAMBER/steps_chamber_stepper*ACCElERATION_MODIFIER;
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

void checkForMotorStop(){ // This function controls the absolute stop of the stepper motors
// turning off the timers.

    if(chamber_stepper_status == 4 && frame_stepper_status == 4){

        // Motor stopped and is waiting for the ISR to be disabled.
        DISABLE_TIMER1_INTERRUPTS;
        chamber_stepper_status = 0;
        //DISABLE_TIMER3_INTERRUPTS;
        //frame_stepper_status = 0;
        // Send message to serial.
        current_program_status = 0;

    }
}

uint8_t rpmToTimerInterval(const float& speed){

    // First consider the mechanics of the system.

    /* Notes for calculating the conversion.

    Timer ticks per second: F_CPU/TIMER_PRESCALER/TIMER_INTERVAL
    Time delay per timer tick: TIMER_PRESCALER/F_CPU*TIMER_INTERVAL
    Steps per rotation with step division: 400*MICROSTEP_DIVISION

    Stepper speed [steps/s]: F_CPU/TIMER_PRESCALER/TIMER_INTERVAL
    Stepper speed [RPS]: F_CPU/TIMER_PRESCALER/TIMER_INTERVAL/STEPS_PER_ROTATION
    Stepper speed [RPM]: F_CPU/TIMER_PRESCALER/TIMER_INTERVAL/STEPS_PER_ROTATION*60

    Stepper speed [RPM]: F_CPU/TIMER_PRESCALER/TIMER_INTERVAL/(400*MICROSTEP_DIVISION)*60

    INTERVAL = F_CPU/TIMER_PRESCALER/RPM/400/MICROSTEP_DIVISION*60

    */

   return uint8_t(F_CPU/TIMER_PRESCALER/STEPS_PER_REVOLUTION*60/speed);


}

void runSteppers(const float& RPM1, const float& RPM2){

    top_speed_interval_chamber = rpmToTimerInterval(RPM1);
    top_speed_interval_frame = rpmToTimerInterval(RPM2);

    if(chamber_stepper_status == 0 && frame_stepper_status == 0){

        ENABLE_TIMER1_INTERRUPTS;
        //ENABLE_TIMER3_INTERRUPTS;
        // Write to serial.

    }
    
    // else report error (?)

}

void stopSteppers(){

    chamber_stepper_status = 2;
    frame_stepper_status = 2;
    // Just setting the status to ramping down,
    // the interrupt service routine will do the rest.

}

void updateProgramStatus(const uint8_t& new_mode){

    /* Some previous and new program status combinations should be impossible to occur due to how
    the clinostat control system app is built. They were also eliminated here to add some
    redundancy to the whole driver. */

    switch(new_mode){

        case 0: // Idle mode. Switched to only when abort or pause
                //commands were issued, after the motors have stopped.

            if(current_program_status == 3){



            } 

            // else do nothing.

        break;

        case 1: // Running mode. Swtiched to when resume or start commands have been issued.
                // The only possible previous modes are idle or paused.

            if(current_program_status == 2 || current_program_status == 0){



            } 
            // else do nothig.

        break;

        case 2: // Paused mode. Switched to only from running mode.

            if(current_program_status == 1){



            } 
            // else do nothig.


        break;

        case 3: // Stopping the clinostat mode. 
                //Switched to only from running mode when pause or abort commands were issued.

            if(current_program_status == 1){

                //stopSteppers();

            } 

        break;

        default:
        break;


    }





}
