import argparse
import pygame
import time
import signal
import mBot

velocity_max = 150
velocity_min = 75
distance_max = 20
distance_min = 5
curve_max = 2.5
curve_min = 1.0
light_threshold = 200
headlight_time_sec = 30

_distance: float = None
_light: float = None
_line_follow: float = None
_button: float = None
_run = True


def stop(signal, frame):
    global _run
    _run = False


def on_distance(value):
    global _distance
    _distance = value


def on_light(value):
    global _light
    _light = value


def on_button(value):
    global _button
    _button = value


def on_line_follow(value):
    global _line_follow
    _line_follow = value


def obstacle_avoidance(direction, distance, distance_min, distance_max, velocity_min, velocity_max):
    return velocity_max if direction < 0 \
                           or distance is None \
                           or distance > distance_max \
        else 0 if distance < distance_min \
        else velocity_min if distance_max <= distance_min \
        else velocity_min + (min(distance, distance_max) - distance_min) * \
             (velocity_max - velocity_min) / (distance_max - distance_min)


def loop(bot, clock):
    old_left_speed = 0
    old_right_speed = 0
    old_headlights = False
    horn_time = 0
    headlights_time = 0
    curve = curve_max
    global _run
    while _run:
        if not bot.is_alive() and not bot.start(True):
            time.sleep(1)
            continue

        #bot.requestLineFollower(10, 2, on_line_follow)
        bot.requestUltrasonicSensor(20, 3, on_distance)
        bot.requestLightOnBoard(30, on_light)
        bot.requestButtonOnBoard(40, on_button)

        clock.tick(20)

        horn = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _run = False
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

        speed = obstacle_avoidance(direction, _distance, distance_min, distance_max, velocity_min, velocity_max)

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
            _run = False

        old_left_speed = left_speed
        old_right_speed = right_speed
        old_headlights = headlights

    bot.doMove(0, 0)
    bot.doRGBLedOnBoard(0, 0, 0, 0)


def parse_commandline_arguments():
    parser = argparse.ArgumentParser(description='Makeblock mBot controller')

    parser.add_argument("-p", "--port", dest="serial_port", required=True,
                        help="Serial port for connecting to the robot")

    args = parser.parse_args()
    return args


def main():
    args = parse_commandline_arguments()

    pygame.init()
    try:
        pygame.joystick.init()

        clock = pygame.time.Clock()

        signal.signal(signal.SIGINT, stop)

        bot = mBot.mBot()
        bot.createSerial(args.serial_port)
        try:
            loop(bot, clock)
        finally:
            bot.close()
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
