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
# WAKE_UP has no connection, can only control it through FPGA or other microcontrollers


def hardwareReset(dev):
	dev.setBitMode(0xFF, 0x01)

	# Pull Low all pins
	dev.write(bytes([0x00]))

	# RESET pull up for 100 µs (min 50 us)
	dev.write(bytes([RESET]))
	time.sleep(0.0001)
	dev.write(bytes([0x00]))

	# Wait for WAKE_UP (200 us pulse), need an external microcontroller to control
	#================
	print("Waiting for WAKE_UP signal for 5s...")
	print("Please send a pulse to WAKE_UP pin (200 us pulse)...")
	time.sleep(5)
	print("Stop waiting for WAKE_UP signal, continuing...")
	#================

	time.sleep(0.001)  # Wait for 1 ms

def deviceWrite(deviceEvm,address,data,pageSelect=0):
    # First do the page select. Page select value needs to be written to register 2 in single lane SPI mode.
	# Page 0 for GBL_PAGE (Global Page), Page 1~16 for pattern mem channel 1~16, Page 17 for delay mem
    # Page select does not matter for GBL_PAGE (Refer datasheet)
    deviceEvm.writeReg(2,pageSelect)
    # Uncomment the below line if using 2 lane SPI mode. Register 3 corresponds to lane 2 page select
    # deviceEvm.writeReg(3,pageSelect)
    # Write the value into the required address
    deviceEvm.writeReg(address,data)
    # Set the page select value to 0. This step is not necessary.
    deviceEvm.writeReg(2,0)

def deviceRead(deviceEvm,address,pageSelect=0):
    # First do the page select. Page select value needs to be written to register 2 in single lane SPI mode.
	# Page 0 for GBL_PAGE (Global Page), Page 1~16 for pattern mem channel 1~16, Page 17 for delay mem
    # Page select does not matter for GBL_PAGE (Refer datasheet)
    deviceEvm.writeReg(2,pageSelect)
    # Uncomment the below line if using 2 lane SPI mode. Register 3 corresponds to lane 2 page select
    # deviceEvm.writeReg(3,pageSelect)
    # Enable read mode in the device by setting 2nd bit to 1 in register 0 (Reg 0[1:1])
    deviceEvm.writeReg(0,2)
    # Read the register value
    value = deviceEvm.readReg(address)
    # Disable read mode in the device by setting 2nd bit to 0 in register 0 (Reg 0[1:1])
    deviceEvm.writeReg(0,0)
    # Set the page select value to 0. This step is not necessary.
    deviceEvm.writeReg(2,0)
    return value

# TODO: Not sure how to initialize register map yet, but seems not need so far
# prat_dev = mTX7516_QPort.TX7516(regProgDevice=qport_TX7516, fileName=PROJECTS_LIB + r"\DMLs\Datasheet_TX7516_PG2P0_Rev4_ver1.dml", name="TX7516 Register Map")
# print("Initialized TX7516 with register map")

def boardDiagnostics(deviceEvm):
	flag = True
	while flag == True:
		# Convert the number to a 32-bit binary string
		val = format(deviceRead(deviceEvm, 0x2B), '032b') # P96: 0x2B register includes error flags
		
		# Define the error checks in the desired order; Index = 31 - Bit (Bit31, Bit30, ..., Bit1, Bit0)
		checks = [
		(int(val[-12:], 2) > 0, "TEMP_SHUT_ERR: FAILED", "TEMP_SHUT_ERR: PASSED"),
		(val[19] != '1', "NO_CLK_ERR: FAILED", "NO_CLK_ERR: PASSED"),
		(val[9] != '0', "SINGLE_LVL_ERR: FAILED", "SINGLE_LVL_ERR: PASSED"),
		(val[8] != '0', "LONG_TRAN_ERR: FAILED", "LONG_TRAN_ERR: PASSED"),
		(val[17] != '0', "P5V_SUP_ERR: FAILED", "P5V_SUP_ERR: PASSED"),
		(val[16] != '0', "M5V_SUP_ERR: FAILED", "M5V_SUP_ERR: PASSED"),
		(val[15] != '0', "PHV_SUP_ERR: FAILED", "PHV_SUP_ERR: PASSED"),
		(val[14] != '0', "MHV_SUP_ERR: FAILED", "MHV_SUP_ERR: PASSED"),
		(val[11] != '0', "PHVA_RANGE_ERR: FAILED", "PHVA_RANGE_ERR: PASSED"),
		(val[13] != '0', "PHVB_RANGE_ERR: FAILED", "PHVB_RANGE_ERR: PASSED"),
		(val[18] != '0', "TRIG_ERR: FAILED", "TRIG_ERR: PASSED"),
		(int(val[:5], 2) != 21, "VALID_FLAG: FAILED", "VALID_FLAG: PASSED"),
		(val[5] != '0', "ERROR_RST: FAILED", "ERROR_RST: PASSED")
		]
		
		# Perform the checks
		for condition, fail_msg, pass_msg in checks:
			print(fail_msg if condition else pass_msg)
			flag = flag and not condition  # If any condition fails, set flag to False

		if flag == False:
			print("Diagnostics failed, reset the error flags")
			if val[19] != '1': # NO_CLK_ERR
				deviceWrite(deviceEvm, 0x08, 0x00000002)
			deviceWrite(deviceEvm, 0x2B, 1 << 26) # Set the ERROR_RST bit to 1 to reset the error flags
			time.sleep(1)
			deviceWrite(deviceEvm, 0x2B, 0) # Reset the ERROR_RST bit to 0
			flag = True # Try again
		elif flag == True:
			return

def memReset(deviceEvm):
	print("Start to reset the memory! Please wait...")
	for addr in range(0x00, 0x40):  # 0x40 is excluded
		try:
			deviceWrite(deviceEvm, addr, 0x00000000)
		except Exception as e:
			print("Failed to write 0 to register {}".format(e))
	print("Memory reset!")