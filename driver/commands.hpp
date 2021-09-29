#ifndef COMMANDS_H
#define COMMANDS_H

/* COMMANDS FROM CONTROL SYSTEM */


#define RUN_COMMAND  0x01
#define HOME_COMMAND  0x02
#define ABORT_COMMAND 0x03
#define PAUSE_COMMAND 0x04
#define RESUME_COMMAND 0x05
#define ECHO_COMMAND 0x06
#define CONNECT_COMMAND 0x07
#define DISCONNECT_COMMAND 0x08
#define BEGIN_WATERING_COMMAND 0x09

/* COMMANDS FROM DRIVER TO CONTROL SYSTEM */

// Notifiers

#define CLINOSTAT_CONNECTED 0x01
#define TOP_SPEED_REACHED 0x02
#define STEPPERS_STARTING 0x03
#define STOPPING_STEPPERS 0x04
#define STEPPERS_STOPPED 0x05
#define WATERING_STARTED 0x06

// Status report commands.

#define RUNNING_MODE_REPORT 0x06
#define STOPPING_MODE_REPORT 0x07
#define IDLE_MODE_REPORT 0x08

#endif