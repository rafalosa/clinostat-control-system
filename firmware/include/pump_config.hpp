#ifndef PUMP_CONF_H
#define PUMP_CONF_H

#define ML_PER_MIN 200
#define PRIMING_CONSTANT 1
#define PUMPING_CONSTANT (ML_PER_MIN*PRIMING_CONSTANT) // Pump parameter [ml/min]

#define TURN_ON_PUMP PORTD |= (1 << PUMP_PIN)
#define TURN_OFF_PUMP PORTD &= ~(1 << PUMP_PIN)
#define TOGGLE_PUMP PORTD ^= (1 << PUMP_PIN)

#endif