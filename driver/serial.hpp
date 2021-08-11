
class Serial{

private:

public:

uint16_t baud;

Serial(uint16_t baud);
~Serial();
void begin();
void write(uint8_t message);
uint8_t read();

};