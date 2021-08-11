#ifndef CLINOSTAT_MECH_H
#define CLINOSTAT_MECH_H

#define STEPPER_BELT_WHEEL_TEETH 1 // Number of teeth on the wheels mounted on stepper motors.
#define MAIN_DRIVE_WHEEL_TEETH 1 // Number of teeth on the main wheels driving the clinostat.
#define FRAME_BELT_WHEEL_TEETH 1 // Number of teeth on the wheel responsible for driving the outer frame of the clinostat.
#define STEPPER_STEPS_PER_REVOLUTION 1 // Number of steps per revolution for the stepper motor.
#define MICROSTEP_DIVISION 16 // Chosen mode of microstepping.

#define STEPS_PER_REVOLUTION STEPPER_STEPS_PER_REVOLUTION*MICROSTEP_DIVISION // Number of steps per revolution considering the microstepping.

#endif