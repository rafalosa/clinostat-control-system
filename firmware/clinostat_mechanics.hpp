#ifndef CLINOSTAT_MECH_H
#define CLINOSTAT_MECH_H

#define GEARBOX_REDUCTION 4 // Reduction of the gearbox mounted underneath the clinostat.
#define STEPPER_BELT_WHEEL_TEETH 28 // Number of teeth on the wheels mounted on stepper motors.
#define MAIN_DRIVE_WHEEL_TEETH 86 // Number of teeth on the main wheels driving the clinostat.
#define STEPPER_STEPS_PER_REVOLUTION 400 // Number of steps per revolution for the stepper motor.
#define MICROSTEP_DIVISION 16 // Chosen mode of microstepping.

#define STEPS_PER_REVOLUTION (STEPPER_STEPS_PER_REVOLUTION*MICROSTEP_DIVISION) // Number of steps per revolution considering the microstepping.

#endif