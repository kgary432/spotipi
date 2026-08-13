# Spotipi
### Overview
This project is to display information on 32x32 led matrix from the Spotify web api.
### Getting Started
* Create a new application within the [Spotify developer dashboard](https://developer.spotify.com/dashboard/applications) <br />
* Edit the settings of the application within the dashboard.
    * Set the redirect uri to any local url such as http://127.0.0.1/callback
* First step is to ssh to your raspberry pi to clone the repository
```
git clone  https://github.com/ryanwa18/spotipi.git
```
* Next go ahead and change into the directory using 
```
cd spotipi
```
* Run the generate token script and enter the prompted spotify credentials using
```
bash generate-token.sh
```
* This will generate a file named `.cache` which will be used for authentication
    * A url will show up in the terminal window and you must copy this into your own web broswer
    * The url will redirect you to another url and you need to copy/paste this in the terminal when prompted.
   
* Install the software: <br />
```
cd spotipi
sudo bash setup.sh
```
* Edit settings on the web app: <br />
```
navigate to http://<raspberrypi_hostname or ip_address> within a web browser
```

### Final Product
![](https://i.redd.it/8s1cxqo5jfk51.jpg)


NOTES FROM KATE:
may need to run in venv, use 

python3 -m venv ~/spotipi-venv
source ~/spotipi-venv/bin/activate
pip install --upgrade pip
pip install spotipy==2.23.0 pillow==9.3.0 flask==3.0.0

when running setup.sh it will ask for a token path. currently that path is:

setup.sh is currently configured in convenience mode. to switch to optimized, the matrix bonnet will need to be altered.
solder pins 4 an 18 together. For a 64x64 matrix (current is 32x32)  solder the E pad to the 8 pad.

parts used are linked here:
https://www.adafruit.com/product/607
https://www.adafruit.com/product/3400
https://www.adafruit.com/product/3211
https://www.adafruit.com/product/276


/home/kgary/spotipy/spotipi/.cache

all of these need to be run on the raspberry pi zero currently attached to the LED matrix bonnet. 
its hostname is rpizero

if you need the username and password to access please message me at kgary7373@gmail.com or on github at kgary432

the other computer in the CS lounge has a folder pinned to the desktop containing a .txt file with the spotify account information. 
feel free to reach out to me if you have any questions.
