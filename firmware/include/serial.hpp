#pragma once

#include "headers.hpp"

class Serial{

    private:
    
    uint16_t baud;

    public:

    Serial();
    ~Serial();
    void begin();
    void write(const uint8_t& byte);
    uint8_t read();
    bool available();
    void flush();
};