#include <AccelStepper.h>
#include <MultiStepper.h>

#define encoder_A_pin 7
#define encoder_B_pin 4


#define OUTER_FRAME_STEP 2
#define CHAMBER_STEP 3

#define OUTER_FRAME_DIR 5
#define CHAMBER_DIR 6

#define STEPPER_WHEEL_TEETH 33
#define DRIVE_WHEEL_TEETH 83

#define STEPS_PER_REVOLUTION 400

#define MICROSTEP_DIVISION 16

#define ENCODER_PPR 20

#define SAFE_SPEED 500


// Clinostat modes
#define STANDBY 0
#define RUNNING 1
#define HOMING 2
#define PAUSE 3

AccelStepper outer_frame_stepper(1, OUTER_FRAME_STEP, OUTER_FRAME_DIR);
AccelStepper chamber_stepper(1, CHAMBER_STEP, CHAMBER_DIR);
MultiStepper clinostat;

unsigned int current_mode = 0;
unsigned int previous_mode = 1;

unsigned int currentTimeEncoder1 = 0;
unsigned int lastTimeEncoder1 = 0;
int encoder_ticks1 = 0;

unsigned int currentTimeEncode2 = 0;
unsigned int lastTimeEncoder2 = 0;
int encoder_ticks2 = 0;

bool messageInSerial = false;

union {

  float float_vel;
  byte bytes_vel[4];


} RPM[2];

void setup() {

  pinMode (encoder_A_pin, INPUT);
  pinMode (encoder_B_pin, INPUT);
  attachInterrupt(digitalPinToInterrupt(encoder_A_pin), updateEncoder, RISING);

  //attachInterrupt(digitalPinToInterrupt(0),serialReceived,CHANGE); //Interrupt for serial received

  outer_frame_stepper.setMaxSpeed(gearedRPMtoSteps(10));
  //outer_frame_stepper.setMaxSpeed(22000);
  outer_frame_stepper.setAcceleration(1200);

  chamber_stepper.setMaxSpeed(gearedRPMtoSteps(10));
  //chamber_stepper.setMaxSpeed(22000);
  chamber_stepper.setAcceleration(1200);
  clinostat.addStepper(outer_frame_stepper);
  clinostat.addStepper(chamber_stepper);

}

void loop() {

  handleSerial();
  
  switch (current_mode) {

    case RUNNING:
      outer_frame_stepper.runSpeed();
      chamber_stepper.runSpeed();
    case HOMING:
    case STANDBY:
    default:
      break;

  }

}

void handleSerial() {

  if (Serial.available() > 0) { // first byte is the mode, depending which mode is requested expect additional bytes.

    int potential_mode = Serial.read();
    if (potential_mode == 1) { // change to switch later

      for (int j = 0; j < 2; j++) { // echo -e -n '\x01\x06\x51\x81\x43\xcd\x4c\x81\x43' >> /dev/ttyACM0 should return 1,258.63 and 258.60


        byte val[4];

        for (int i = 0; i < 4; i++)
        {
          val[i] = Serial.read();
          RPM[j].bytes_vel[i] = val[i];
        }

      }

    } //If everything went fine (received 8 bytes after the mode byte) set current mode to potential mode

    else if (potential_mode != 1) {

      // flush anything in serial buffer that may be interpreted as a next command, so it isnt decoded in the next loop

    }

    previous_mode = current_mode;
    current_mode = potential_mode;

    chamber_stepper.setSpeed(gearedRPMtoSteps(RPM[0].float_vel));
    outer_frame_stepper.setSpeed(gearedRPMtoSteps(RPM[1].float_vel));

    if (current_mode == HOMING && previous_mode != STANDBY) {

      returnHome(); // Homing here,because only 1 excution of this function is needed,avoiding calling it continously in the loop

    }
    
  }
  
}

void serialReceived() {

  PCMSK0 |= 0; //turn of r
  messageInSerial = true;

}

void returnHome() {

  //outer_frame_stepper.runToNewPosition(0);
  //chamber_stepper.runToNewPosition(0);

  //additionally check encoder counters.
  //if they dont agree run the motors at low RPM till the reading is correct.

  //set motors speed very low

  //run motors till encoder_reading % STEPS_PER_ROTATION == 0

  chamber_stepper.stop();
  outer_frame_stepper.stop();

  long home_pos[2] = {0, 0};
  clinostat.moveTo(home_pos);

  while (clinostat.run());

  while (chamber_stepper.currentPosition() != chamber_stepper.targetPosition() ) {

    if (outer_frame_stepper.currentPosition() != outer_frame_stepper.targetPosition()) {

      outer_frame_stepper.runSpeedToPosition();

    }
    chamber_stepper.runSpeedToPosition();

  }

  while (outer_frame_stepper.currentPosition() != outer_frame_stepper.targetPosition()) {

    outer_frame_stepper.runSpeedToPosition();
  }



  if (encoder_ticks1 != 0) {

    outer_frame_stepper.setSpeed(SAFE_SPEED);
    chamber_stepper.setSpeed(SAFE_SPEED);
  }

  while (encoder_ticks1 != 0) {

    //if(encoder_ticks2 != 0){

    outer_frame_stepper.runSpeed();

    //}
    chamber_stepper.runSpeed();

  }

  //    while(encoder_ticks2 != 0){
  //
  //      outer_frame_stepper.runSpeed();
  //    }

  outer_frame_stepper.setCurrentPosition(0);
  chamber_stepper.setCurrentPosition(0);
  current_mode = STANDBY;


}

void updateEncoder() {

  currentTimeEncoder1 = millis();
  bool bState = digitalRead(encoder_B_pin);

  if (currentTimeEncoder1 - lastTimeEncoder1 > 10) {
    if (bState == HIGH) {

      encoder_ticks1 = --encoder_ticks1 % ENCODER_PPR;

    }
    else {

      encoder_ticks1 = ++encoder_ticks1 % ENCODER_PPR;


    }

  }
  lastTimeEncoder1 = currentTimeEncoder1;
}

int gearedRPMtoSteps(float RPM) { //RPM to steps per second conversion, with gearbox consideration.

  return RPM / 60 * STEPS_PER_REVOLUTION * DRIVE_WHEEL_TEETH / STEPPER_WHEEL_TEETH * MICROSTEP_DIVISION;

}
