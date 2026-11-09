#pragma once
struct AccelStepper{ enum{DRIVER=1,HALF4WIRE=8}; AccelStepper(int,int,int,int=0,int=0){}
 long distanceToGo(){return 0;} long currentPosition(){return 0;} void run(){} void moveTo(long){} void move(long){}
 void setMaxSpeed(float){} void setAcceleration(float){} void setCurrentPosition(long){} void enableOutputs(){} void disableOutputs(){}};
