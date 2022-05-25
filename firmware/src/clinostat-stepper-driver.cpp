#include "headers.hpp"
#include "driver_config.hpp"
#include "commands.hpp"
#include "clinostat_mechanics.hpp"
#include "serial.hpp"
#include "pump_config.hpp"
#include "driver_states.hpp"

void handleSerial();
void checkMotorStatus();
uint16_t rpmToTimerInterval(const float&);
uint32_t volumeToPumpTime(const float&);
void updateProgramStatus(States::Driver&&);

extern volatile uint64_t program_time_milis;
uint64_t pump_start_timestamp = 0;

uint16_t top_speed_interval_chamber = 10;
uint16_t top_speed_interval_frame = 10;

volatile uint32_t steps_chamber_stepper = 1;
volatile uint32_t steps_frame_stepper = 1;

volatile States::Steppers chamber_stepper_status = States::Steppers::RAMP_UP; //0 - rampup, 1 - speed reached, 2 - stopping, 3 - running at full speed, 4 - immediate stop.
volatile States::Steppers frame_stepper_status = States::Steppers::RAMP_UP;

volatile unsigned long chamber_interval = STOP_INTERVAL_CHAMBER;
volatile unsigned long frame_interval = STOP_INTERVAL_FRAME;

union {

    float float_value;
    uint8_t byte_value[4];

} speed_buffer[2], watering_volume;

uint32_t watering_time;

// Flags
bool device_connected = false;
bool pumping = false;

States::Driver current_program_status = States::Driver::IDLE; 
States::Driver previous_program_status = States::Driver::RUNNING;

Serial serial;

int main(){

    DDRD |= (1 << CHAMBER_STEP); // Setting appropriate pins as output.
    DDRD |= (1 << FRAME_STEP);
    DDRB |= (1 <<  ENABLE_PIN);
    DDRD |= (1 << PUMP_PIN);

    SETUP_TIMER1_INTERRUPTS();
    SETUP_TIMER3_INTERRUPTS();
    SETUP_TIMER0_INTERRUPTS();
    ENABLE_TIMER0_INTERRUPTS; // Begin time tracking rightaway.

    DISABLE_STEPPERS;

    serial.begin();

    uint64_t now = program_time_milis;

    while(true){

        if(serial.available()){

            handleSerial();
        }

        if(pumping){

            if(program_time_milis - pump_start_timestamp >= watering_time){

                TURN_OFF_PUMP;
                pumping = false;
            }
        }
        checkMotorStatus();
    }
    return 0;
}

void checkMotorStatus(){ // This function checks if the stepper motors status needs to be updated once every program loop.

    if(chamber_stepper_status == States::Steppers::WAITING && frame_stepper_status == States::Steppers::WAITING){

        // Motor stopped and is waiting for the ISR to be disabled.
        DISABLE_TIMER1_INTERRUPTS;
        DISABLE_TIMER3_INTERRUPTS;
        frame_stepper_status = States::Steppers::RAMP_UP;
        chamber_stepper_status = States::Steppers::RAMP_UP;
        updateProgramStatus(States::Driver::IDLE);

    }

    else if(chamber_stepper_status == States::Steppers::CONTINUE_RUN && frame_stepper_status == States::Steppers::CONTINUE_RUN){

        chamber_stepper_status = States::Steppers::SPEED_REACHED;
        frame_stepper_status = States::Steppers::SPEED_REACHED;
        //serial.write(TOP_SPEED_REACHED);

    }
}

uint16_t rpmToTimerInterval(const float& speed){ // speed [RPM]

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

   return uint16_t(F_CPU/TIMER_PRESCALER/STEPS_PER_REVOLUTION*60/
   (speed*GEARBOX_REDUCTION*(MAIN_DRIVE_WHEEL_TEETH/STEPPER_BELT_WHEEL_TEETH)));


}

uint32_t volumeToPumpTime(const float& volume){

    return volume/PUMPING_CONSTANT*60*1000;

}

void runSteppers(const float& RPM1, const float& RPM2){

    top_speed_interval_chamber = rpmToTimerInterval(RPM1);
    top_speed_interval_frame = rpmToTimerInterval(RPM2);

    if(chamber_stepper_status == States::Steppers::RAMP_UP && frame_stepper_status == States::Steppers::RAMP_UP){

        ENABLE_STEPPERS;
        ENABLE_TIMER1_INTERRUPTS; // Enabling the timer interrupts starts the motors.
        ENABLE_TIMER3_INTERRUPTS;

    }
    
    // else report error (?)

}

void stopSteppers(){

    chamber_stepper_status = States::Steppers::RAMP_DOWN;
    frame_stepper_status = States::Steppers::RAMP_DOWN;
    // Just setting the status to ramping down,
    // the interrupt service routines will do the rest.

}

void updateProgramStatus(States::Driver&& new_mode){

    /* Some previous and new program status combinations should be impossible to occur due to how
    the clinostat control system app is built. They were also eliminated here to add some
    redundancy to the whole driver. */

    switch(new_mode){

        case States::Driver::IDLE: // Idle mode. Switched to only when abort or pause
                //commands were issued, after the motors have stopped.

            if(current_program_status == States::Driver::SOFT_STOPPING || current_program_status == States::Driver::ABORT){
                
                if(device_connected){
                    
                    serial.write(Commands::Transmit::STEPPERS_STOPPED);
                }
                current_program_status = States::Driver::IDLE;
            } 

            // else do nothing.

        break;

        case States::Driver::RUNNING: // Running mode. Swtiched to when resume or start commands have been issued.
                // The only possible previous modes are idle or paused.

            if(current_program_status == States::Driver::PAUSED || current_program_status == States::Driver::IDLE){

                previous_program_status = current_program_status;
                current_program_status = States::Driver::RUNNING;
                runSteppers(speed_buffer[0].float_value,speed_buffer[1].float_value);
                serial.write(Commands::Transmit::STEPPERS_STARTING);
            } 
            // else do nothig.

        break;

        case States::Driver::PAUSED: // Paused mode. Switched to only from running mode.

            if(current_program_status == States::Driver::RUNNING){

                previous_program_status = current_program_status;
                current_program_status = States::Driver::SOFT_STOPPING;
                stopSteppers();
                serial.write(Commands::Transmit::STOPPING_STEPPERS);
            } 
            // else do nothig.

        break;

        case States::Driver::SOFT_STOPPING: // Soft stopping the clinostat mode. 
                //Switched to only from running mode when pause command is issued.

            if(current_program_status == States::Driver::RUNNING){
                
                previous_program_status = current_program_status;
                current_program_status = States::Driver::SOFT_STOPPING;
                stopSteppers();
                serial.write(Commands::Transmit::STOPPING_STEPPERS);

            } 

        break;

        case States::Driver::ABORT: // Aborting the current run of the clinostat. Used to completely deenergize motors after
        // soft stop or to immediately stop the clinostat in the case of emergency.


            if(current_program_status == States::Driver::RUNNING){
                
                previous_program_status = current_program_status;
                current_program_status = States::Driver::ABORT;
                DISABLE_STEPPERS;
                chamber_interval = STOP_INTERVAL_CHAMBER;
                frame_interval = STOP_INTERVAL_FRAME;
                frame_stepper_status = States::Steppers::WAITING;
                chamber_stepper_status = States::Steppers::WAITING;
                steps_chamber_stepper = 1;
                steps_frame_stepper = 1;
            }
            else if(current_program_status == States::Driver::IDLE){
                previous_program_status = current_program_status;
                DISABLE_STEPPERS;
            }

        default:
        break;

    }

}

void handleSerial(){

    /* 

    First byte read from serial is the command ID.
    Depending on what command has been sent another 8 bytes
    can be read from serial that contain information about
    the set speeds.  
    
    */

    uint8_t command = serial.read(); // Read 1 byte.

    if(command == Commands::Receive::CONNECT_COMMAND){

        serial.write(Commands::Transmit::CLINOSTAT_CONNECTED);
        device_connected = true;
    }

    else if(command == Commands::Receive::DISCONNECT_COMMAND){

        updateProgramStatus(States::Driver::ABORT);
        device_connected = false;
        if(pumping){

            TURN_OFF_PUMP;
            pumping = false;
        }
    }

    else{

        if(device_connected){ // Before clinostat can do anything it has to first receive an connection attempt command.

            if(command == Commands::Receive::RUN_COMMAND){ // If the command is run then read another 8 bytes to ge the set speeds.

            for(uint8_t i=0;i<2;i++){
                
                for(uint8_t j=0;j<4;j++){

                    uint8_t temp = serial.read();
                    speed_buffer[i].byte_value[j] = temp;

                    }
                }

            }
            else if(command == Commands::Receive::BEGIN_WATERING_COMMAND){

                for(uint8_t j=0;j<4;j++){

                    uint8_t temp = serial.read();
                    watering_volume.byte_value[j] = temp;

                    }
                watering_time = volumeToPumpTime(watering_volume.float_value);

            }

    
            switch(command){

                case Commands::Receive::RUN_COMMAND:

                    updateProgramStatus(States::Driver::RUNNING);

                break;

                case Commands::Receive::ABORT_COMMAND:

                    // Immediate stop of the steppers.
                    // Disable steppers after stop.

                    updateProgramStatus(States::Driver::ABORT);

                break;

                case Commands::Receive::PAUSE_COMMAND:

                    // Slow deceleration of steppers.
                    // Leave steppers enabled.

                    updateProgramStatus(States::Driver::SOFT_STOPPING);

                break;

                case Commands::Receive::RESUME_COMMAND:

                    updateProgramStatus(States::Driver::RUNNING);

                break;

                case Commands::Receive::ECHO_COMMAND:

                    switch(current_program_status){

                        case States::Driver::IDLE:
                            serial.write(Commands::Transmit::IDLE_MODE_REPORT);
                        break;

                        case States::Driver::RUNNING:
                            serial.write(Commands::Transmit::RUNNING_MODE_REPORT);
                        break;

                        case States::Driver::SOFT_STOPPING:
                            serial.write(Commands::Transmit::STOPPING_MODE_REPORT);
                        break;

                        default:
                        break;
                    }

                break;

                case Commands::Receive::BEGIN_WATERING_COMMAND:

                    if(pumping){

                        serial.write(Commands::Transmit::STILL_WATERING);

                    }

                    else{
                        serial.write(Commands::Transmit::WATERING_STARTED);
                        TURN_ON_PUMP;
                        pump_start_timestamp = program_time_milis;
                        pumping = true;
                    }

                break;

                default:
                break;

            }
        }
    }

}

ISR(TIMER1_COMPA_vect){ // Interrupt service routine for Timer 1.

    switch(chamber_stepper_status){

        case States::Steppers::RAMP_UP: // Ramp up to top speed.

            CHAMBER_STEP_HIGH;
            CHAMBER_STEP_LOW;

            //chamber_interval = STOP_INTERVAL_CHAMBER/steps_chamber_stepper*ACCElERATION_MODIFIER;
            
            chamber_interval = STOP_INTERVAL_CHAMBER*(sqrt(steps_chamber_stepper+1) - sqrt(steps_chamber_stepper));

            if(chamber_interval <= top_speed_interval_chamber){

                chamber_interval = top_speed_interval_chamber;
                chamber_stepper_status = States::Steppers::CONTINUE_RUN;

            }

            else steps_chamber_stepper += 1;

            OCR1A = int(chamber_interval);
            break;

        case States::Steppers::CONTINUE_RUN: case States::Steppers::SPEED_REACHED: // Keep stepping at max speed.

            CHAMBER_STEP_HIGH;
            CHAMBER_STEP_LOW;
            break;

        case States::Steppers::RAMP_DOWN: // Ramp down to complete stop.

            CHAMBER_STEP_HIGH;
            CHAMBER_STEP_LOW;

            //chamber_interval = STOP_INTERVAL_CHAMBER/steps_chamber_stepper*ACCElERATION_MODIFIER;
            chamber_interval = STOP_INTERVAL_CHAMBER*(sqrt(steps_chamber_stepper+1) - sqrt(steps_chamber_stepper));
            
            if(chamber_interval >= STOP_INTERVAL_CHAMBER){

                chamber_interval = STOP_INTERVAL_CHAMBER;
                steps_chamber_stepper = 1;
                chamber_stepper_status = States::Steppers::WAITING;
                
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

ISR(TIMER3_COMPA_vect){ // Interrupt service routine for Timer 3.

    switch(frame_stepper_status){

        case States::Steppers::RAMP_UP: // Ramp up to top speed.

            FRAME_STEP_HIGH;
            FRAME_STEP_LOW;

            
            frame_interval = STOP_INTERVAL_FRAME*(sqrt(steps_frame_stepper+1) - sqrt(steps_frame_stepper));

            if(frame_interval <= top_speed_interval_frame){

                frame_interval = top_speed_interval_frame;
                frame_stepper_status = States::Steppers::CONTINUE_RUN;

            }

            else steps_frame_stepper += 1;

            OCR3A = int(frame_interval);
            break;

        case States::Steppers::CONTINUE_RUN: case States::Steppers::SPEED_REACHED: // Keep stepping at max speed.

            FRAME_STEP_HIGH;
            FRAME_STEP_LOW;
            break;

        case States::Steppers::RAMP_DOWN: // Ramp down to complete stop.

            FRAME_STEP_HIGH;
            FRAME_STEP_LOW;

            frame_interval = STOP_INTERVAL_FRAME*(sqrt(steps_frame_stepper+1) - sqrt(steps_frame_stepper));
            
            if(frame_interval >= STOP_INTERVAL_FRAME){

                frame_interval = STOP_INTERVAL_FRAME;
                steps_frame_stepper = 1;
                frame_stepper_status = States::Steppers::WAITING;
                
            }
            else steps_frame_stepper--;
            OCR3A = int(frame_interval);
            break;


        default:
            break;

            // Do nothing and wait for the interrupt to be disabled in the main loop.

    }

    TCNT3 = 0;

}
