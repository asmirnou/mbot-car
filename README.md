# mBot Car

Remote controlled car with a camera, built based on mBot - Entry-level educational robot kit.

## Hardware

Learn about mBot from Makeblock official website: https://www.makeblock.com/mbot

Raspberry Pi Zero WH: https://thepihut.com/products/raspberry-pi-zero-wh-with-pre-soldered-header

Raspberry Pi Camera Module V2: https://thepihut.com/products/raspberry-pi-camera-module

UPS HAT For Raspberry Pi: www.waveshare.com/wiki/UPS_HAT

## Software

Python: https://www.python.org/

Virtual joystick: https://github.com/jehervy/node-virtual-gamepads

MJPG Streamer: https://github.com/jacksonliam/mjpg-streamer

## Installation

Setup Raspberry Pi in [headless mode](https://www.raspberrypi.org/documentation/configuration/wireless/headless.md). 
Enable [camera](https://www.raspberrypi.org/documentation/configuration/camera.md) and I2C interface.

1. Install system dependencies.

    ```bash
    sudo apt-get update && sudo apt-get install -y --no-install-recommends \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        cmake \
        joystick \
        nginx \
        libsdl2-dev \
        libjpeg8-dev
    ```

2. Create Python virtual environment and activate it.

    ```bash
    git clone https://github.com/asmirnou/mbot-car
    cd /home/pi/mbot-car
    
    python3 -m venv venv --system-site-packages
    
    source venv/bin/activate
    ```

3. Install Python tools.

    ```bash
    python -m pip install --upgrade \
        pip \
        setuptools \
        wheel
    ```

4. Install application dependencies.

    ```bash
    python -m pip install -r requirements.txt
    ```

5. Connect Raspberry Pi and Makeblock mCore Control Board for mBor via Bluetooth.

    ```bash
    hcitool scan  # to get the MAC address of your device
    sudo bluetoothctl
    pair <MAC_ADDRRESS>
    exit
    ```
    
    Run `sudo crontab -e` and add the following line:  
    
    ```bash
    @reboot rfcomm bind 0 00:1B:10:10:19:D4
    ```

6. Install Node JS v9.11.2

    ```bash
    cd /home/pi/
    wget https://nodejs.org/dist/v9.11.2/node-v9.11.2-linux-armv6l.tar.xz
    ```

    Install Node.js via [binary archive on Linux](https://github.com/nodejs/help/wiki/Installation#how-to-install-nodejs-via-binary-archive-on-linux).

    Allow to run node with sudo:
        
    ```bash
    sudo ln -s /usr/local/lib/nodejs/node-v9.11.2-linux-armv6l/bin/node /sbin/node
    ```

7. Install virtual joystick

    ```bash
    cd /home/pi/
    git clone https://github.com/miroof/node-virtual-gamepads
    cd node-virtual-gamepads
    npm install
    ```

    Edit `config.json` as follows:

    ```json
    {
      "port": 8080,
      "useGamepadByDefault": true,
      "analog": false,
      "logLevel": "info",
      "ledBitFieldSequence": [1]
    }
    ```

    To check the joystick (in different terminals) run:
    
    ```bash
    sudo node main.js
    ```
    
    and after connecting from a phone to http://<raspberrypi-ip>:8080/
    
    ```bash
    jstest --event /dev/input/js0
    ```

8. Install MJPG Streamer

    ```bash
    cd /home/pi/
    git clone https://github.com/jacksonliam/mjpg-streamer
    cd mjpg-streamer/mjpg-streamer-experimental
    make
    sudo make install
    ```

9. In `raspi-config` change the hostname of your Paspberry Pi to `mbot`.

### Running manually

```bash
cd /home/pi/mbot-car

source venv/bin/activate

sudo rfcomm bind 0 00:1B:10:10:19:D4

export SDL_VIDEODRIVER=dummy && python car.py -sp /dev/rfcomm0
```

### Running as a service

1. Create new users:

    ```bash
    sudo addgroup -gid 1001 mbot
    sudo adduser -uid 1001 -gid 1001 -gecos mbot --no-create-home --disabled-password mbot
    sudo usermod -a --groups dialout,audio,video,plugdev,games,input,i2c mbot
    
    sudo addgroup -gid 1002 streamer
    sudo adduser -uid 1002 -gid 1002 -gecos streamer --no-create-home --disabled-password streamer
    sudo usermod -a --groups video streamer
    ```

2. Copy _systemd_ service definition files:

    ```bash
    sudo cp conf/systemd/* /etc/systemd/system/
    ```
    
    Activate `systemd` service:
    
    ```bash
    sudo systemctl daemon-reload
    
    sudo systemctl enable node-virtual-gamepads.service --now
    sudo systemctl enable streamer@streamer.service --now
    sudo systemctl enable mbot@mbot.service --now
    ```

3. Copy Nginx configuration files and restart Nginx:

    ```bash
    sudo cp conf/nginx/sites-available.default /etc/nginx/sites-available/default
    sudo cp conf/nginx/index.html /var/www/html
    
    sudo systemctl restart nginx
    ```

4. Allow `mbot` user to shutdown the system when the onboard button is pressed:

    ```bash
    sudo visudo
    ```
    
    Add the following line:
    
    ```text
    # Allow mbot user to shutdown the system with no password
    mbot ALL=(ALL) NOPASSWD: /sbin/shutdown
    ```

## Usage

On your computer or tablet open a browser and navigate to http://mbot to watch the first-person-view.
On a phone open another browser and navigate to http://mbot/gamepads to drive the car.
