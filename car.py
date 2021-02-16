import argparse
import threading
import pygame
import time
import signal
import mBot
import INA219
from functools import partial

# Constants
velocity_max = 150
velocity_min = 75
distance_max = 20
distance_min = 5
curve_max = 2.5
curve_min = 1.0
light_threshold = 200
headlight_time_sec = 30

# Sensors
_distance: float = None
_light: float = None
_line_follow: float = None
_button: float = None

_battery: float = None
_bus_voltage: float = None
_shunt_voltage: float = None
_current: float = None
_power: float = None

# Variables
_stop_main_event = threading.Event()


def _on_distance(value):
    global _distance
    _distance = value


def _on_light(value):
    global _light
    _light = value


def _on_button(value):
    global _button
    _button = value


def _on_line_follow(value):
    global _line_follow
    _line_follow = value


def _obstacle_avoidance(direction, distance, distance_min, distance_max, velocity_min, velocity_max):
    return velocity_max if direction < 0 \
                           or distance is None \
                           or distance > distance_max \
        else 0 if distance < distance_min \
        else velocity_min if distance_max <= distance_min \
        else velocity_min + (min(distance, distance_max) - distance_min) * \
             (velocity_max - velocity_min) / (distance_max - distance_min)


def _loop(bot, clock):
    old_left_speed = 0
    old_right_speed = 0
    old_headlights = False
    horn_time = 0
    headlights_time = 0
    curve = curve_max
    while not _stop_main_event.is_set():
        if not bot.is_alive() and not bot.start(True):
            time.sleep(1)
            continue

        # bot.requestLineFollower(10, 2, _on_line_follow)
        bot.requestUltrasonicSensor(20, 3, _on_distance)
        bot.requestLightOnBoard(30, _on_light)
        bot.requestButtonOnBoard(40, _on_button)

        clock.tick(20)

        horn = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _stop_main_event.set()
            elif event.type == pygame.JOYBUTTONDOWN:
                horn = True

        joystick_count = pygame.joystick.get_count()
        if joystick_count > 0:
            joystick = pygame.joystick.Joystick(joystick_count - 1)
            joystick.init()
            try:
                axis1 = joystick.get_axis(0)
                axis2 = joystick.get_axis(1)
            finally:
                joystick.quit()
        else:
            axis1 = 0
            axis2 = 0

        steering = -axis1
        direction = -axis2

        speed = _obstacle_avoidance(direction, _distance, distance_min, distance_max, velocity_min, velocity_max)

        left_speed = round(direction * speed * (1 - steering / curve))
        right_speed = round(direction * speed * (1 + steering / curve))

        headlights = True if _light is not None and _light < light_threshold \
                             or (old_headlights and time.time() - headlights_time < headlight_time_sec) else False

        if old_left_speed != left_speed or old_right_speed != right_speed:
            bot.doMove(left_speed, right_speed)

        if old_headlights != headlights:
            if headlights:
                bot.doRGBLedOnBoard(0, 253, 172, 10)
            else:
                bot.doRGBLedOnBoard(0, 0, 0, 0)
            headlights_time = time.time()

        if horn and time.time() - horn_time >= 0.500:
            bot.doBuzzer(123, 250)
            horn_time = time.time()

        if _button == 0:
            _stop_main_event.set()

        old_left_speed = left_speed
        old_right_speed = right_speed
        old_headlights = headlights

    bot.doMove(0, 0)
    bot.doRGBLedOnBoard(0, 0, 0, 0)


def _parse_commandline_arguments():
    parser = argparse.ArgumentParser(description='Makeblock mBot controller')

    parser.add_argument("-p", "--port", dest="serial_port", required=True,
                        help="Serial port for connecting to the robot")

    args = parser.parse_args()
    return args


def _install_signal_handler():
    for s in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(s, partial(lambda stop_event, *_args: stop_event.set(), _stop_main_event))


def _power_monitor():
    global _bus_voltage
    global _shunt_voltage
    global _current
    global _power
    global _battery

    ina219 = INA219.INA219(addr=0x42)

    while not _stop_main_event.is_set():
        _bus_voltage = ina219.getBusVoltage_V()  # voltage on V- (load side)
        _shunt_voltage = ina219.getShuntVoltage_mV() / 1000  # voltage between V+ and V- across the shunt
        _current = ina219.getCurrent_mA()  # current in mA
        _power = ina219.getPower_W()  # power in W
        p = (_bus_voltage - 6) / 2.4 * 100
        if (p > 100): p = 100
        if (p < 0): p = 0
        _battery = p


def main():
    args = _parse_commandline_arguments()

    pygame.init()
    try:
        pygame.joystick.init()

        clock = pygame.time.Clock()

        _install_signal_handler()
        try:
            threading.Thread(target=_power_monitor).start()

            bot = mBot.mBot()
            bot.createSerial(args.serial_port)
            try:
                _loop(bot, clock)
            finally:
                bot.close()
        finally:
            _stop_main_event.set()
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
