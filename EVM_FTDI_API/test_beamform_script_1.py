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

print("##########################################################")
print("##########################################################")
#Device.RemoveAllDevices()

# Create the EVM Qport object
# The string passed is the address of the FTDI port
# Instructions to find the address is present in the attached document
deviceEvm = USBQPort('FT4232 Mini Module A')
print("Initialized USBQPort")
dev = deviceEvm.controller.instrument

def hardwareReset():
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

def deviceWrite(address,data,pageSelect=0):
    # First do the page select. Page select value needs to be written to register 2 in single lane SPI mode.
	# Page 0 for GBL_PAGE (Global Page), Page 1~16 for pattern mem channel 1~16, Page 17 for delay mem
    # Page select does not matter for GBL_PAGE (Refer datasheet)
    deviceEvm.writeReg(2,pageSelect)
    # Uncomment the below line if using 2 lane SPI mode. Register 3 corresponds to lane 2 page select
    #deviceEvm.writeReg(3,pageSelect)
    # Write the value into the required address
    deviceEvm.writeReg(address,data)
    # Set the page select value to 0. This step is not necessary.
    deviceEvm.writeReg(2,0)

def deviceRead(address,pageSelect=0):
    # First do the page select. Page select value needs to be written to register 2 in single lane SPI mode.
	# Page 0 for GBL_PAGE (Global Page), Page 1~16 for pattern mem channel 1~16, Page 17 for delay mem
    # Page select does not matter for GBL_PAGE (Refer datasheet)
    deviceEvm.writeReg(2,pageSelect)
    # Uncomment the below line if using 2 lane SPI mode. Register 3 corresponds to lane 2 page select
    #deviceEvm.writeReg(3,pageSelect)
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

def board_diagnostics():
	flag = True
	while flag == True:
		# Convert the number to a 32-bit binary string
		val = format(deviceRead(0x2B), '032b') # P96: 0x2B register includes error flags
		
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
				deviceWrite(0x08, 0x00000002)
			deviceWrite(0x2B, 1 << 26) # Set the ERROR_RST bit to 1 to reset the error flags
			time.sleep(1)
			deviceWrite(0x2B, 0) # Reset the ERROR_RST bit to 0
			flag = True # Try again
		elif flag == True:
			return

def mem_reset():
	print("Start to reset the memory! Please wait...")
	for addr in range(0x00, 0x40):  # 0x40 is excluded
		try:
			deviceWrite(addr, 0x00000000)
		except Exception as e:
			print("Failed to write 0 to register {}".format(e))
	print("Memory reset!")

all_delay_hex_values = [
[0x1EE71ED5, 0x5F0A5EF8, 0x1F2E5F1C, 0x1F521F40, 0x5F995F87, 0x1FBD1FAB, 0x1FE11FCF, 0x20005FF2],
# [0x5EEF1EDE, 0x1F125F00, 0x5F341F23, 0x1F571F46, 0x5F9C1F8B, 0x1FBF1FAE, 0x5FE15FD0, 0x20001FF3],
# [0x1EF81EE7, 0x5F195F08, 0x1F3B1F2A, 0x5F5C1F4C, 0x5F9F1F8F, 0x1FC15FB0, 0x5FE21FD2, 0x20005FF3],
# [0x5F005EF0, 0x1F211F11, 0x5F415F31, 0x1F625F51, 0x1FA35F92, 0x1FC31FB3, 0x5FE35FD3, 0x20001FF4],
# [0x5F091EFA, 0x5F281F19, 0x1F485F38, 0x5F675F57, 0x1FA65F96, 0x5FC55FB5, 0x5FE41FD5, 0x20005FF4],
# [0x5F121F03, 0x5F305F21, 0x5F4E5F3F, 0x1F6D5F5D, 0x1FA91F9A, 0x5FC75FB8, 0x5FE55FD6, 0x20005FF4],
# [0x1F1B5F0C, 0x5F385F29, 0x5F551F47, 0x5F721F64, 0x5FAC1F9E, 0x5FC91FBB, 0x5FE61FD8, 0x20001FF5],
# [0x1F245F16, 0x1F401F32, 0x1F5C1F4E, 0x1F781F6A, 0x1FB01FA2, 0x5FCB5FBD, 0x5FE75FD9, 0x20005FF5],
# [0x5F2D1F20, 0x1F485F3A, 0x1F635F55, 0x5F7D1F70, 0x1FB35FA5, 0x1FCE5FC0, 0x5FE81FDB, 0x20001FF6],
# [0x5F365F29, 0x1F501F43, 0x5F691F5D, 0x1F835F76, 0x5FB65FA9, 0x1FD01FC3, 0x5FE91FDD, 0x20005FF6],
# [0x5F3F5F33, 0x1F581F4C, 0x5F705F64, 0x1F895F7C, 0x1FBA5FAD, 0x1FD21FC6, 0x5FEA5FDE, 0x20001FF7],
# [0x1F491F3D, 0x1F605F54, 0x5F771F6C, 0x5F8E1F83, 0x1FBD5FB1, 0x5FD41FC9, 0x5FEB1FE0, 0x20005FF7],
# [0x1F521F47, 0x5F681F5D, 0x5F7E5F73, 0x5F945F89, 0x5FC05FB5, 0x5FD65FCB, 0x5FEC5FE1, 0x20005FF7],
# [0x5F5B1F51, 0x5F701F66, 0x5F851F7B, 0x1F9A1F90, 0x1FC45FB9, 0x1FD95FCE, 0x5FED5FE3, 0x20001FF8],
# [0x1F651F5B, 0x5F781F6F, 0x5F8C5F82, 0x1FA01F96, 0x5FC75FBD, 0x1FDB1FD1, 0x1FEF1FE5, 0x20005FF8],
# [0x5F6E1F65, 0x1F815F77, 0x5F931F8A, 0x1FA65F9C, 0x1FCB5FC1, 0x5FDD1FD4, 0x1FF05FE6, 0x20001FF9],
# [0x1F785F6F, 0x1F895F80, 0x5F9A1F92, 0x1FAC1FA3, 0x5FCE5FC5, 0x5FDF1FD7, 0x1FF11FE8, 0x20005FF9],
# [0x5F815F79, 0x5F915F89, 0x5FA15F99, 0x5FB15FA9, 0x1FD21FCA, 0x1FE21FDA, 0x1FF21FEA, 0x20001FFA],
# [0x1F8B5F83, 0x1F9A5F92, 0x1FA95FA1, 0x5FB71FB0, 0x5FD51FCE, 0x1FE45FDC, 0x1FF35FEB, 0x20005FFA],
# [0x5F941F8E, 0x5FA25F9B, 0x1FB01FA9, 0x5FBD5FB6, 0x1FD91FD2, 0x5FE65FDF, 0x1FF45FED, 0x20001FFB],
# [0x5F9E1F98, 0x5FAA5FA4, 0x1FB71FB1, 0x5FC35FBD, 0x5FDC1FD6, 0x5FE85FE2, 0x1FF51FEF, 0x20005FFB],
# [0x1FA85FA2, 0x1FB35FAD, 0x5FBE1FB9, 0x5FC91FC4, 0x1FE05FDA, 0x1FEB5FE5, 0x1FF65FF0, 0x20001FFC],
# [0x5FB15FAC, 0x5FBB5FB6, 0x5FC55FC0, 0x5FCF5FCA, 0x5FE35FDE, 0x5FED5FE8, 0x5FF75FF2, 0x20005FFC],
# [0x5FBB1FB7, 0x1FC41FC0, 0x1FCD5FC8, 0x5FD51FD1, 0x1FE75FE2, 0x5FEF5FEB, 0x5FF81FF4, 0x20005FFC],
# [0x1FC55FC1, 0x5FCC1FC9, 0x1FD45FD0, 0x5FDB1FD8, 0x5FEA1FE7, 0x1FF25FEE, 0x5FF95FF5, 0x20001FFD],
# [0x1FCF1FCC, 0x1FD51FD2, 0x5FDB5FD8, 0x5FE15FDE, 0x1FEE1FEB, 0x5FF41FF1, 0x5FFA5FF7, 0x20005FFD],
# [0x1FD95FD6, 0x5FDD5FDB, 0x5FE21FE0, 0x5FE71FE5, 0x5FF11FEF, 0x5FF61FF4, 0x5FFB1FF9, 0x20001FFE],
# [0x5FE25FE0, 0x5FE65FE4, 0x1FEA1FE8, 0x1FEE1FEC, 0x5FF55FF3, 0x1FF91FF7, 0x5FFC1FFB, 0x20005FFE],
# [0x5FEC1FEB, 0x1FEF5FED, 0x5FF11FF0, 0x1FF45FF2, 0x1FF95FF7, 0x5FFB1FFA, 0x1FFE5FFC, 0x20001FFF],
# [0x1FF65FF5, 0x5FF71FF7, 0x5FF81FF8, 0x1FFA5FF9, 0x5FFC1FFC, 0x5FFD1FFD, 0x1FFF5FFE, 0x20005FFF],
# [0x20002000, 0x20002000, 0x20002000, 0x20002000, 0x20002000, 0x20002000, 0x20002000, 0x20002000],
# [0x5FFF2000, 0x1FFE1FFF, 0x1FFD5FFD, 0x5FFB5FFC, 0x1FF91FFA, 0x1FF85FF8, 0x5FF65FF7, 0x5FF51FF6],
# [0x1FFF2000, 0x5FFC5FFD, 0x1FFA1FFB, 0x5FF75FF8, 0x5FF25FF3, 0x1FF01FF1, 0x5FED5FEE, 0x1FEB1FEC],
# [0x1FFE2000, 0x5FFA5FFC, 0x5FF65FF8, 0x1FF31FF5, 0x5FEB5FED, 0x5FE75FE9, 0x1FE41FE6, 0x5FE01FE2],
# [0x5FFD2000, 0x5FF81FFB, 0x5FF31FF6, 0x5FEE1FF1, 0x5FE41FE7, 0x5FDF1FE2, 0x5FDA1FDD, 0x5FD61FD8],
# [0x1FFD2000, 0x5FF61FFA, 0x5FF05FF3, 0x1FEA5FED, 0x1FDE1FE1, 0x5FD75FDA, 0x5FD15FD4, 0x1FCC1FCE],
# [0x5FFC2000, 0x1FF55FF8, 0x5FED1FF1, 0x1FE65FE9, 0x1FD75FDA, 0x5FCF1FD3, 0x1FC85FCB, 0x5FC15FC4],
# [0x5FFB2000, 0x1FF35FF7, 0x1FEA5FEE, 0x5FE11FE6, 0x1FD05FD4, 0x5FC71FCC, 0x5FBE1FC3, 0x1FB75FBA],
# [0x1FFB2000, 0x1FF11FF6, 0x1FE71FEC, 0x1FDD1FE2, 0x5FC95FCE, 0x5FBF5FC4, 0x5FB55FBA, 0x5FAC5FB0],
# [0x5FFA2000, 0x1FEF1FF5, 0x1FE45FE9, 0x1FD95FDE, 0x5FC21FC8, 0x5FB71FBD, 0x1FAC1FB2, 0x5FA25FA6],
# [0x1FFA2000, 0x5FED5FF3, 0x1FE11FE7, 0x5FD41FDB, 0x1FBC1FC2, 0x5FAF5FB5, 0x1FA31FA9, 0x1F981F9D],
# [0x1FF92000, 0x5FEB5FF2, 0x1FDE5FE4, 0x5FD01FD7, 0x1FB51FBC, 0x5FA71FAE, 0x1F9A5FA0, 0x1F8E1F93],
# [0x5FF82000, 0x5FE91FF1, 0x1FDB5FE2, 0x1FCC5FD3, 0x5FAE5FB5, 0x5F9F1FA7, 0x5F901F98, 0x5F831F89],
# [0x1FF82000, 0x1FE81FF0, 0x1FD81FE0, 0x1FC81FD0, 0x5FA75FAF, 0x5F975F9F, 0x5F875F8F, 0x5F795F7F],
# [0x5FF72000, 0x1FE65FEE, 0x1FD55FDD, 0x5FC31FCC, 0x1FA15FA9, 0x5F8F5F98, 0x5F7E1F87, 0x5F6F1F76],
# [0x1FF72000, 0x5FE45FED, 0x1FD21FDB, 0x5FBF5FC8, 0x5F9A5FA3, 0x1F881F91, 0x5F755F7E, 0x1F651F6C],
# [0x1FF62000, 0x5FE25FEC, 0x1FCF5FD8, 0x1FBB1FC5, 0x5F935F9D, 0x1F801F8A, 0x5F6C1F76, 0x1F5B5F62],
# [0x5FF52000, 0x5FE01FEB, 0x1FCC1FD6, 0x1FB75FC1, 0x1F8D5F97, 0x5F785F82, 0x5F631F6E, 0x1F511F59],
# [0x1FF52000, 0x1FDF1FEA, 0x1FC91FD4, 0x5FB21FBE, 0x5F865F91, 0x5F705F7B, 0x5F5A5F65, 0x1F475F4F],
# [0x5FF42000, 0x1FDD5FE8, 0x1FC65FD1, 0x5FAE1FBA, 0x1F805F8B, 0x1F695F74, 0x5F511F5D, 0x1F3D1F46],
# [0x1FF42000, 0x5FDB5FE7, 0x1FC31FCF, 0x5FAA5FB6, 0x5F791F86, 0x1F615F6D, 0x1F491F55, 0x5F335F3C],
# [0x1FF32000, 0x5FD95FE6, 0x1FC01FCD, 0x5FA61FB3, 0x1F731F80, 0x5F595F66, 0x1F401F4D, 0x5F291F33],
# [0x5FF22000, 0x1FD81FE5, 0x1FBD5FCA, 0x5FA25FAF, 0x1F6D1F7A, 0x1F525F5F, 0x5F375F44, 0x1F201F2A],
# [0x1FF22000, 0x1FD61FE4, 0x1FBA1FC8, 0x5F9E5FAC, 0x5F665F74, 0x5F4A5F58, 0x5F2E5F3C, 0x5F165F20],
# [0x5FF12000, 0x5FD41FE3, 0x5FB71FC6, 0x5F9A1FA9, 0x1F605F6E, 0x1F435F51, 0x1F265F34, 0x5F0C5F17],
# [0x1FF12000, 0x5FD21FE2, 0x5FB45FC3, 0x5F965FA5, 0x1F5A1F69, 0x1F3C1F4B, 0x5F1D5F2C, 0x1F035F0E],
# [0x5FF02000, 0x1FD15FE0, 0x5FB15FC1, 0x5F921FA2, 0x1F545F63, 0x5F341F44, 0x1F151F25, 0x1EFA5F05],
# [0x1FF02000, 0x5FCF5FDF, 0x1FAF1FBF, 0x5F8E5F9E, 0x5F4D1F5E, 0x1F2D5F3D, 0x1F0D1F1D, 0x5EF05EFC],
# [0x1FEF2000, 0x5FCD5FDE, 0x1FAC1FBD, 0x5F8A5F9B, 0x5F475F58, 0x1F261F37, 0x5F045F15, 0x1EE75EF3],
# [0x5FEE2000, 0x1FCC5FDD, 0x5FA95FBA, 0x1F871F98, 0x5F411F53, 0x1F1F1F30, 0x5EFC5F0D, 0x1EDE1EEB],
# [0x1FEE2000, 0x5FCA5FDC, 0x5FA65FB8, 0x1F831F95, 0x5F3B5F4D, 0x1F185F29, 0x1EF41F06, 0x1ED55EE2],
]
# take reg 0x40 as an example -> channel 2&1 
# delay profile: PDN_RX_2_1(31), FRA_DEL_2_1(30), DEL_2_1(29:16), PDN_RX_1_1(15), FRA_DEL_1_1(14), DEL_1_1(13:0)
# PDN_RX: power down receiving (generally 0 -> keep receiving)
# FRA_DEL: 0.5 cycle of delay
# DEL: 14 bits to controll delay (in cycles)
# e.g. write 0x1EE71ED5 into reg 0x40:
# 	0x1EE71ED5 -> 0001 1110 1110 0111 0001 1110 1101 0101
# 	-> FRA_DEL_2 = 0, DEL_2 = 7911(0x1EE7); FRA_DEL_1 = 0, DEL_1 = 7893(0x1ED5)
# !! refer to P102~103 for registers and examples


# Initialize necessary components before the loop

first_run = True # Initialize a flag

hardwareReset() # Perform hardware reset

# Repeat the entire process 5 times
for repeat_idx in range(1):
	print("Starting repetition:", repeat_idx + 1)


	# Loop through each set of delays in all_delay_hex_values
	for idx, delays in enumerate(all_delay_hex_values):
	
		# Convert hex strings to integers only if they are not already integers
		delays_int = [value if isinstance(value, int) else int(value, 16) for value in delays]
		
		print("Starting main program for delay set index:", idx)
		
		# Disable sync before any SPI operation
		deviceEvm.enableSync(False)
		deviceWrite(0x08, 0x00000000) # Disable Detect Clock Sync; P78, register 8h Bit1 EN_SYNC_DET
		
		mem_reset()
		
		if first_run:
			deviceWrite(0x0, 0x00000001) # Software reset; P71, register 0h Bit0 RESET
		
		board_diagnostics()
		
		deviceWrite(0x2C, 0x7FC00F07) # Supply limits for AVDDP_HV_A
		deviceWrite(0x2D, 0x00400F07) # Supply limits for AVDDP_HV_B
		# 7FC->max duration; 00F->fixed; 0->lower limit; 7->upper limit (F for 100V, guess 7 for ~50V)
		# 004->max transition count; 00F->fixed; 0->lower limit; 7->upper limit (F for 100V, guess 7 for ~50V)
		
		# choose 1E to select the starting point (further choose the pattern)
		# we can pre-define a lot of patterns in mem words for each channel,
		# by setting the start word we choose the one to output
		deviceWrite(0x0C, 0x001E001E) # Mem. Start Word 2 and 1 respectively
		deviceWrite(0x0D, 0x001E001E) # Mem. Start Word 4 and 3 respectively		
		deviceWrite(0x0E, 0x001E001E) # Mem. Start Word 6 and 5 respectively		
		deviceWrite(0x0F, 0x001E001E) # Mem. Start Word 8 and 7 respectively		
		deviceWrite(0x10, 0x001E001E) # Mem. Start Word 10 and 9 respectively		
		deviceWrite(0x11, 0x001E001E) # Mem. Start Word 12 and 11 respectively		
		deviceWrite(0x12, 0x001E001E) # Mem. Start Word 14 and 13 respectively		
		deviceWrite(0x13, 0x001E001E) # Mem. Start Word 16 and 15 respectively	
		# 1E -> Memory Word starts from 1E -> waveforms reads from 30th mem word (m for MEM_WORD_n_m)
		# Why not use Register 08 Bit6 GBL_PAT_START_ADD	
				
		# deviceWrite(0x02, 0x0000FFFF) # Pattern Page Select for all 16 channels; P103

		# Mem word starts from 1E, so the pattern generator starts to search from 0x40+0x1E=0x5E
		deviceWrite(0x5C, 0xA0A00000, pageSelect=0x0000FFFF) # TRSW Glitch --OURS--nothing		
		deviceWrite(0x5D, 0x0000FF00, pageSelect=0x0000FFFF) # TRSW Glitch --OURS--		
		deviceWrite(0x5E, 0xB5B10000, pageSelect=0x0000FFFF) # 5.6 MHz_3LVL_A Wave --OURS-- 5.6
		deviceWrite(0x5F, 0xFF00B5B1, pageSelect=0x0000FFFF) # 5.6 MHz_3LVL_A Wave --OURS--		
		deviceWrite(0x52, 0x31f90000, pageSelect=0x0000FFFF) # 3.4 MHz_2LVL_A Wave --OURS-- 1.66 2.4 3.4 0xf9f90001 0xa9f90000 0x31f90000		
		deviceWrite(0x53, 0x31f935fd, pageSelect=0x0000FFFF) # 3.4 MHz_2LVL_A Wave --OURS-- 0x6dfdfd69 0xa9f9adfd 0x31f935fd
		deviceWrite(0x54, 0xff0035fd, pageSelect=0x0000FFFF) # 3.4 MHz_2LVL_A Wave --OURS-- 0x0000ff00 0xff00adfd 0xff0035fd		
		# e.g. 0xB5B10000 -> 1011 0101 1011 0001 0000 0000 0000 0000 
		# 		-> PER1 = 10110 = 22; LVL1 = 101 -> AVDDM_HV_A (2A drive)
		#		-> PER2 = 10110 = 22; LVL2 = 001 -> AVDDP_HV_A (2A drive)
		# 		-> GLB_REP_NUM = 0; LOCAL_REP_NUM = 0
		# 	   0xFF00B5B1 -> B5B1 continously read byte by byte -> another waveform -> 2 cycles of pulse
		#		-> 00 -> LOCAL_REP_END; FF -> GBL_REP_END
		# 	   default 250MHz -> f = 250MHz / (2*22) = 5.68MHz; 2 cycles of square wave
		# e.g. 0x31f90000 -> 0011 0001 1111 1001 ...
		#		-> PER1 = 6; LVL1 = 001; PER2 = 31; LVL2 = 001; -> 37 cycles of AVDDP_HV_A
		#	   0x31f935fd -> 31f9 0011 0101 1111 1101
		# 		-> PER3 = 6; LVL4 = 101; PER4 = 31; LVL4 = 101; -> 37 cycles of AVDDM_HV_A
		#		repeat for 2 cycles
		#		ff00 -> glb & local end
		# 	   default 250MHz -> f = 250MHz / (2*37) = 3.38MHz; 2 cycles of square wave
		# !! refer to P34~36 pipeline and Table 8-5

		first_run = False # Set the flag to False after the first run
		
		print("==========================================================")		
		print("Processing delay set for angle index {}".format(idx))		
		print("==========================================================")			
						
		# deviceWrite(0x02, 0x00010000) # Delay Page Select; P103
		
		deviceWrite(0x40, delays_int[0], pageSelect=0x00010000) # Delay 2 1
		deviceWrite(0x41, delays_int[1], pageSelect=0x00010000) # Delay 4 3		
		deviceWrite(0x42, delays_int[2], pageSelect=0x00010000) # Delay 6 5
		deviceWrite(0x43, delays_int[3], pageSelect=0x00010000) # Delay 8 7		
		deviceWrite(0x44, delays_int[4], pageSelect=0x00010000) # Delay 10 9		
		deviceWrite(0x45, delays_int[5], pageSelect=0x00010000) # Delay 12 11		
		deviceWrite(0x46, delays_int[6], pageSelect=0x00010000) # Delay 14 13		
		deviceWrite(0x47, delays_int[7], pageSelect=0x00010000) # Delay 16 15
				
		# deviceWrite(0x02, 0x00000000) # Deselect Pages
		# This is written in definition of deviceWrite function
		
		deviceEvm.enableSync(True)
		deviceWrite(0x08, 0x00000002) # Enable Detect Clock Sync (EN_SYNC_DET)
		
		print("Finished sending signal for delay set index:", idx)
	
		#script_dir = "C:\\Users\\vitalsense\\MyCode\\pico-readout\\Lukhanin_Nikita"
		
		#os.chdir(script_dir)
		
		#subprocess.call('pdm run python3 .\\ps5000a_run_auto_long_data.py --config .\\config\\pico5000a_config__2_channel_long_data.yaml --output_dir ".\\test_result" --testee "nikita" --description "test;"', shell=True)
		
		print("Finished processing signal for delay set index:", idx)
	
	
	# Wait for 5 minutes before repeating the loop
	if repeat_idx < 4: # To avoid waiting after the last repetition
		print("Waiting for 5 minutes before the next repetition...")
		time.sleep(0)

print("All repetitions completed.")