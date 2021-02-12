#
# Borrowed from https://github.com/xeecos/python-for-mbot
#
# License: GNU GENERAL PUBLIC LICENSE
#

import serial
import struct
import threading
import hid
from time import sleep
from multiprocessing import Manager


class mSerial():
    def __init__(self, port):
        self._port = port
        sleep(0)

    def start(self):
        self._ser = serial.Serial(self._port, 115200)

    def writePackage(self, package):
        self._ser.write(package)
        sleep(0.01)

    def read(self):
        return self._ser.read()

    def isOpen(self):
        return hasattr(self, '_ser') and self._ser.isOpen()

    def inWaiting(self):
        return self._ser.inWaiting()

    def close(self):
        self._ser.close()


class mHID():
    def __init__(self, manager):
        sleep(0)
        self._manager = manager

    def start(self):
        self._dict = self._manager.dict()
        self._dict.device = hid.device()
        self._dict.device.open(0x0416, 0xffff)
        # self.dict.device.hid_set_nonblocking(self.device,1)
        self.__buffer = []
        self.__bufferIndex = 0

    def writePackage(self, package):
        buf = []
        buf += [0, len(package)]
        for i in range(len(package)):
            buf += [package[i]]
        n = self._dict.device.write(buf)
        sleep(0.01)

    def read(self):
        c = self.__buffer[0]
        self.__buffer = self.__buffer[1:]
        return chr(c)

    def isOpen(self):
        return True

    def inWaiting(self):
        buf = self._dict.device.read(64)
        l = 0
        if len(buf) > 0:
            l = buf[0]
        if l > 0:
            for i in range(0, l):
                self.__buffer += [buf[i + 1]]
        return len(self.__buffer)

    def close(self):
        self._dict.device.close()


class mBot():
    def __init__(self):
        self._manager = Manager()
        self._selectors = self._manager.dict()

    def createSerial(self, port):
        self._device = mSerial(port)

    def createHID(self):
        self._device = mHID(self._manager)

    def start(self, silent=False):
        try:
            self.__exiting = False
            self.__buffer = []
            self.__bufferIndex = 0
            self.__isParseStart = False
            self.__isParseStartIndex = 0
            self._selectors.clear()

            if self._device.isOpen():
                self._device.close()
            self._device.start()

            self._th = threading.Thread(target=self._onRead, args=(self._onParse,))
            self._th.start()
            return True
        except Exception as e:
            if silent:
                print(e)
                return False
            else:
                raise

    def is_alive(self):
        return hasattr(self, '_th') and self._th.is_alive()

    def close(self):
        self.__exiting = True
        self._device.close()

    def _onRead(self, callback):
        try:
            while 1:
                if self.__exiting:
                    break
                if self._device.isOpen():
                    n = self._device.inWaiting()
                    for i in range(n):
                        r = self._device.read()
                        if r is None:
                            break
                        callback(ord(r))
                    sleep(0.01)
                else:
                    sleep(0.5)
        except Exception:
            if self.__exiting:
                pass
            else:
                raise

    def _writePackage(self, pack):
        self._device.writePackage(pack)

    def doRGBLed(self, port, slot, index, red, green, blue):
        self._writePackage(bytearray([0xff, 0x55, 0x9, 0x0, 0x2, 0x8, port, slot, index, red, green, blue]))

    def doRGBLedOnBoard(self, index, red, green, blue):
        self.doRGBLed(0x7, 0x2, index, red, green, blue)

    def doMotor(self, port, speed):
        self._writePackage(bytearray([0xff, 0x55, 0x6, 0x0, 0x2, 0xa, port] + self._short2bytes(speed)))

    def doMove(self, leftSpeed, rightSpeed):
        self._writePackage(
            bytearray([0xff, 0x55, 0x7, 0x0, 0x2, 0x5] + self._short2bytes(-leftSpeed) + self._short2bytes(rightSpeed)))

    def doServo(self, port, slot, angle):
        self._writePackage(bytearray([0xff, 0x55, 0x6, 0x0, 0x2, 0xb, port, slot, angle]))

    def doBuzzer(self, buzzer, time=0):
        self._writePackage(
            bytearray([0xff, 0x55, 0x7, 0x0, 0x2, 0x22] + self._short2bytes(buzzer) + self._short2bytes(time)))

    def doSevSegDisplay(self, port, display):
        self._writePackage(bytearray([0xff, 0x55, 0x8, 0x0, 0x2, 0x9, port] + self._float2bytes(display)))

    def doIROnBoard(self, message):
        self._writePackage(bytearray([0xff, 0x55, len(message) + 3, 0x0, 0x2, 0xd, message]))

    def requestLightOnBoard(self, extID, callback):
        self.requestLight(extID, 8, callback)

    def requestLight(self, extID, port, callback):
        if self._doCallback(extID, callback):
            self._writePackage(bytearray([0xff, 0x55, 0x4, extID, 0x1, 0x3, port]))

    def requestButtonOnBoard(self, extID, callback):
        if self._doCallback(extID, callback):
            self._writePackage(bytearray([0xff, 0x55, 0x4, extID, 0x1, 0x1f, 0x7]))

    def requestIROnBoard(self, extID, callback):
        if self._doCallback(extID, callback):
            self._writePackage(bytearray([0xff, 0x55, 0x3, extID, 0x1, 0xd]))

    def requestUltrasonicSensor(self, extID, port, callback):
        if self._doCallback(extID, callback):
            self._writePackage(bytearray([0xff, 0x55, 0x4, extID, 0x1, 0x1, port]))

    def requestLineFollower(self, extID, port, callback):
        if self._doCallback(extID, callback):
            self._writePackage(bytearray([0xff, 0x55, 0x4, extID, 0x1, 0x11, port]))

    def _onParse(self, byte):
        value = 0
        self.__buffer += [byte]
        bufferLength = len(self.__buffer)
        if bufferLength >= 2:
            if self.__buffer[bufferLength - 1] == 0x55 \
                    and self.__buffer[bufferLength - 2] == 0xff:
                self.__isParseStart = True
                self.__isParseStartIndex = bufferLength - 2
            if self.__buffer[bufferLength - 1] == 0xa and \
                    self.__buffer[bufferLength - 2] == 0xd and self.__isParseStart == True:
                self.__isParseStart = False
                position = self.__isParseStartIndex + 2
                extID = self.__buffer[position]
                position += 1
                type = self.__buffer[position]
                position += 1
                # 1 byte 2 float 3 short 4 len+string 5 double
                if type == 1:
                    value = self.__buffer[position]
                if type == 2:
                    value = self._readFloat(position)
                    if (value < -255 or value > 1023):
                        value = 0
                if type == 3:
                    value = self._readShort(position)
                if type == 4:
                    value = self._readString(position)
                if type == 5:
                    value = self._readDouble(position)
                if (type <= 5):
                    self._responseValue(extID, value)
                self.__buffer = []

    def _readFloat(self, position):
        v = [self.__buffer[position], self.__buffer[position + 1], self.__buffer[position + 2],
             self.__buffer[position + 3]]
        return struct.unpack('<f', struct.pack('4B', *v))[0]

    def _readShort(self, position):
        v = [self.__buffer[position], self.__buffer[position + 1]]
        return struct.unpack('<h', struct.pack('2B', *v))[0]

    def _readString(self, position):
        l = self.__buffer[position]
        position += 1
        s = ""
        for i in range(l):
            s += self.__buffer[position + i].charAt(0)
        return s

    def _readDouble(self, position):
        v = [self.__buffer[position], self.__buffer[position + 1], self.__buffer[position + 2],
             self.__buffer[position + 3]]
        return struct.unpack('<f', struct.pack('4B', *v))[0]

    def _responseValue(self, extID, value):
        key = "callback_" + str(extID)
        if key in self._selectors:
            callback = self._selectors.pop(key)
            callback(value)

    def _doCallback(self, extID, callback):
        key = "callback_" + str(extID)
        if key not in self._selectors:
            self._selectors[key] = callback
            return True
        else:
            return False

    def _float2bytes(self, fval):
        val = struct.pack("f", fval)
        return [val[0], val[1], val[2], val[3]]

    def _short2bytes(self, sval):
        val = struct.pack("h", sval)
        return [val[0], val[1]]
