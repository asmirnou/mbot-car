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

        bot.requestUltrasonicSensor(10, 3, on_distance)
        # bot.requestLineFollower(20, 2, on_line_follow)
        bot.requestLightOnBoard(30, on_light)

        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _run = False

        keys = pygame.key.get_pressed()

        direction = keys[pygame.K_UP] - keys[pygame.K_DOWN]
        steering = keys[pygame.K_LEFT] - keys[pygame.K_RIGHT]

        speed = obstacle_avoidance(direction, _distance, distance_min, distance_max, velocity_min, velocity_max)

        left_speed = round(direction * speed * (1 - steering / curve))
        right_speed = round(direction * speed * (1 + steering / curve))

        headlights = True if _light is not None and _light < light_threshold \
                             or (old_headlights and time.time() - headlights_time < headlight_time_sec) else False

        horn = keys[pygame.K_SPACE] == 1

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
        pygame.display.set_caption('Makeblock mBot')
        pygame.display.set_mode((300, 300))

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