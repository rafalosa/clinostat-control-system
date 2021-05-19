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

AccelStepper outer_frame_stepper(1, OUTER_FRAME_STEP, OUTER_FRAME_DIR);
AccelStepper chamber_stepper(1, CHAMBER_STEP, CHAMBER_DIR);
MultiStepper clinostat;

unsigned int currentTimeEncoder1 = 0;
unsigned int lastTimeEncoder1 = 0;
int encoder_ticks1 = 0;

unsigned int currentTimeEncode2 = 0;
unsigned int lastTimeEncoder2 = 0;
int encoder_ticks2 = 0;

void setup() {
  pinMode (encoder_A_pin, INPUT);
  pinMode (encoder_B_pin, INPUT);
  attachInterrupt(digitalPinToInterrupt(encoder_A_pin),updateEncoder,RISING);
  outer_frame_stepper.setMaxSpeed(gearedRPMtoSteps(4));
  outer_frame_stepper.setAcceleration(1200);
  chamber_stepper.setMaxSpeed(gearedRPMtoSteps(4));
  chamber_stepper.setAcceleration(1200);
  clinostat.addStepper(outer_frame_stepper);
  clinostat.addStepper(chamber_stepper);

}

void loop() {  

  chamber_stepper.moveTo(10000);
  outer_frame_stepper.moveTo(5000);
  
  chamber_stepper.setSpeed(6000);
  outer_frame_stepper.setSpeed(6000);
  
  while(chamber_stepper.currentPosition() != chamber_stepper.targetPosition() ){

    if(outer_frame_stepper.currentPosition() != outer_frame_stepper.targetPosition()){

      outer_frame_stepper.runSpeedToPosition();
      
    }
    chamber_stepper.runSpeedToPosition();

  }
    while(outer_frame_stepper.currentPosition() != outer_frame_stepper.targetPosition()){

      outer_frame_stepper.runSpeedToPosition();
    }
    
    returnHome();
    }


void returnHome(){

  //outer_frame_stepper.runToNewPosition(0);
  //chamber_stepper.runToNewPosition(0);
  
  //additionally check encoder counters.
  //if they dont agree run the motors at low RPM till the reading is correct.

  //set motors speed very low

  //run motors till encoder_reading % STEPS_PER_ROTATION == 0
  
  chamber_stepper.stop();
  outer_frame_stepper.stop();

  long home_pos[2] = {0,0};
  clinostat.moveTo(home_pos);

  while(clinostat.run());

  if(encoder_ticks1 != 0){

    outer_frame_stepper.setSpeed(SAFE_SPEED);
    chamber_stepper.setSpeed(SAFE_SPEED);
  }

  while(encoder_ticks1 != 0){ // in final form has to check both encoders, and run them independently
  
    outer_frame_stepper.runSpeed();
    chamber_stepper.runSpeed();
    
  }
  outer_frame_stepper.stop();
  chamber_stepper.stop();
  
  outer_frame_stepper.setCurrentPosition(0);
  chamber_stepper.setCurrentPosition(0);
  

}

void updateEncoder(){

   currentTimeEncoder1 = millis();
   bool bState = digitalRead(encoder_B_pin);
   
  if(currentTimeEncoder1 - lastTimeEncoder1 > 10){
  if(bState == HIGH){

    encoder_ticks1 = --encoder_ticks1 % ENCODER_PPR;
    
  }
  else{

  encoder_ticks1 = ++encoder_ticks1 % ENCODER_PPR;

    
  }

  }
  lastTimeEncoder1 = currentTimeEncoder1;
}

int gearedRPMtoSteps(float RPM){ //RPM to steps per second conversion, with gearbox consideration.
  
  return RPM / 60 * STEPS_PER_REVOLUTION * DRIVE_WHEEL_TEETH/STEPPER_WHEEL_TEETH * MICROSTEP_DIVISION;

}
