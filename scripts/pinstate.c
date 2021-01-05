#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <unistd.h>
#include <stdbool.h>
#include <pigpio.h>

#define PULSE 6
#define LED 5
#define OPTO 22

#define WAIT_1 20
#define WAIT_2 65
#define WAIT_3 50
#define WAIT_4 100


int state;
int dur;
bool pin;
bool module_on;

void blink() {
	if (pin) {
		gpioWrite(LED,0);
		pin = false;
	}
	else {
		gpioWrite(LED,1);
		pin = true;
	}
	return;
}

	

void event(int gpio, int level, uint32_t tick)
{
	printf("presionado %d 0.00 %d\n", level, tick);
	
	if (level==0) {
		printf("In with state %d\n",state);
		dur = 0;
	}
	else{
		printf("debounce out with state %d",state);
		if (state==0 || state==2) {
			gpioWrite(LED,1);
			pin = true;
		}
		else {
			gpioWrite(LED,0);
			pin = false;
		}
	}
	
}

int main(int argc, char *argv[])
{
	int usecs = 100000;
	int debounce = 20000;

	gpioCfgClock(5, 0, 0); /* Dont use PCM!*/
   	if (gpioInitialise() < 0)
   	{
      	fprintf(stderr, "pigpio initialisation failed\n");
      	return 1;
   	}	

   	/* Set GPIO modes */
   	gpioSetMode(PULSE, PI_INPUT);
   	gpioSetPullUpDown(PULSE, PI_PUD_UP);
   	gpioSetMode(LED, PI_OUTPUT);
   	gpioSetMode(OPTO, PI_OUTPUT);
	gpioSetAlertFunc(PULSE, event);
	gpioGlitchFilter(PULSE, debounce);	

	/* START */
	state = 0;
	gpioWrite(LED,1);
	pin = true;
	module_on = false;
	gpioWrite(OPTO,0);
	
	/* LOOP */
	while(1) 
	{
	   	usleep(usecs);
		if (gpioRead(PULSE)==0) {
			if (state==0 && dur>WAIT_1) {
				blink();
				if (!module_on) {
					gpioWrite(OPTO,1);
					module_on = true;
				}
				if (dur>WAIT_2) {
					state = 1;
					gpioWrite(LED,0);
					pin = false;
					gpioWrite(OPTO,0);
					/* check if module started */
					/*or start service module*/
					printf("*************** COMENZAMOS A GRABAR!!! ************");
					dur = 0;
				}
			}
			else if (state==1 && dur>WAIT_3){
				blink();
				if (dur>WAIT_4) {
					state = 2;
					gpioWrite(LED,1);
					pin = true;
					printf("*************** SHUTDOWN !!!!!!!!!!!! ************");
				}
			}
			dur++;
			printf("dur %d state %d %d\n",dur,state,pin);
		}
	}
   	gpioTerminate();
}
