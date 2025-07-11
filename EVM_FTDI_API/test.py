# Import necessary modules
import matplotlib.pyplot as plt
import os
from datetime import datetime
import subprocess
import sys
import time
import numpy as np
import ftd2xx

import time
import os
import subprocess

from deviceController import USBQPort
from pyftdi.gpio import GpioController

RESET = 0x08
TR_BF_SYNC = 0x80

deviceEvm = USBQPort('FT4232 Mini Module A')
print("Initialized USBQPort")
dev = deviceEvm.controller.instrument

print("Device list:", ftd2xx.listDevices())
print("Device info:", dev.getDeviceInfo())
print("Bit mode (before):", dev.getBitMode())

dev.setBitMode(0xFF, 0x01)
time.sleep(0.1)
print("Bit mode:", dev.getBitMode())  # 应输出 1
time.sleep(0.1)

# 全部拉低
dev.write(bytes([0x00]))

# RESET 拉高 50 µs
dev.write(bytes([RESET]))
time.sleep(0.00005)
dev.write(bytes([0x00]))

# 等 1 ms
time.sleep(0.001)

# TR_BF_SYNC 拉高 10 µs
dev.write(bytes([TR_BF_SYNC]))
time.sleep(0.00001)
dev.write(bytes([0x00]))

dev.close()
print("Device closed")