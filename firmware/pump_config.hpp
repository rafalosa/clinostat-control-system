#ifndef PUMP_CONF_H
#define PUMP_CONF_H

#define PUMPING_CONSTANT 200 // Pump parameter [ml/min]

#define TURN_ON_PUMP PORTD |= (1 << PUMP_PIN)
#define TURN_OFF_PUMP PORTD &= ~(1 << PUMP_PIN)
#define TOGGLE_PUMP PORTD ^= (1 << PUMP_PIN)

#endif