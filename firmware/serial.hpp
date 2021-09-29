#include "headers.hpp"

class Serial{

private:

public:

uint16_t baud;

Serial();
~Serial();
void begin();
void write(const uint8_t& byte);
uint8_t read();
bool available();
void flush();
};