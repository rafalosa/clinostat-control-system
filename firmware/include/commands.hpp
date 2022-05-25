#pragma once
namespace Commands{
    namespace Receive{
        constexpr uint8_t RUN_COMMAND  = 0x01;
        constexpr uint8_t HOME_COMMAND  = 0x02;
        constexpr uint8_t ABORT_COMMAND = 0x03;
        constexpr uint8_t PAUSE_COMMAND = 0x04;
        constexpr uint8_t RESUME_COMMAND = 0x05;
        constexpr uint8_t ECHO_COMMAND = 0x06;
        constexpr uint8_t CONNECT_COMMAND = 0x07;
        constexpr uint8_t DISCONNECT_COMMAND = 0x08;
        constexpr uint8_t BEGIN_WATERING_COMMAND = 0x09;
    }
    namespace Transmit{

        constexpr uint8_t CLINOSTAT_CONNECTED = 0x01;
        constexpr uint8_t TOP_SPEED_REACHED = 0x02;
        constexpr uint8_t STEPPERS_STARTING = 0x03;
        constexpr uint8_t STOPPING_STEPPERS = 0x04;
        constexpr uint8_t STEPPERS_STOPPED = 0x05;
        constexpr uint8_t WATERING_STARTED = 0x09;
        constexpr uint8_t STILL_WATERING = 0x0A;
        
        constexpr uint8_t RUNNING_MODE_REPORT = 0x06;
        constexpr uint8_t STOPPING_MODE_REPORT = 0x07;
        constexpr uint8_t IDLE_MODE_REPORT = 0x08;
    }
}
