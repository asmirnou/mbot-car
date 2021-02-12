# mBot Car

## Description

Learn more from Makeblock official website http://www.makeblock.com

Virtual joystick: https://github.com/jehervy/node-virtual-gamepads

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
sudo rfcomm bind 0 00:1B:10:10:19:D4 1
```

```bash
python car.py -p /dev/rfcomm0
```
