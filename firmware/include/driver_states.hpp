#pragma once

namespace States{

    enum class Driver : uint8_t{

        IDLE = 0,
        RUNNING = 1,
        PAUSED = 2,
        SOFT_STOPPING = 3,
        ABORT = 4
    };

    enum class Steppers : uint8_t{

        RAMP_UP = 0,
        CONTINUE_RUN = 1,
        RAMP_DOWN = 2,
        SPEED_REACHED = 3,
        WAITING = 4
    };
}