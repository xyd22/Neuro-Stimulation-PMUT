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
from tools import hardwareReset, deviceWrite, deviceRead, memReset, boardDiagnostics_TX7364
from config_TX7364 import delay_start_word, all_delay_hex_values, pattern_start_word, pattern


if __name__ == "__main__":

	print("##########################################################")
	print("##########################################################")

	# Create the EVM Qport object
	# The string passed is the address of the FTDI port
	# Instructions to find the address is present in the attached document
	deviceEvm = USBQPort('FT4232 Mini Module A')
	print("Initialized USBQPort")
	dev = deviceEvm.controller.instrument


	# Initialize necessary components before the loop
	first_run = True # Initialize a flag

	hardwareReset(dev) # Perform hardware reset

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
			deviceWrite(deviceEvm, 0x08, 0x00000000) # Disable Detect Clock Sync;
			
			# Memory reset
			# memReset(deviceEvm)
			
			# Software reset;
			if first_run:
				deviceWrite(deviceEvm, 0x0, 0x00000001)

			# Setting CONST_1 and CONST_2 bits to '1'
			deviceWrite(deviceEvm, 0x51, 0x00050000)
			
			# Diagnose the board
			boardDiagnostics_TX7364(deviceEvm)

			# Setting the T/R Switch ON delays of channels to 0.
			deviceWrite(deviceEvm, 0x80, 0x0)
			deviceWrite(deviceEvm, 0x81, 0x0)
			
			# Choose the starting point of the memory for pattern
			deviceWrite(deviceEvm, 0x33, pattern_start_word)

			# Choose the starting point of the memory for delay
			for reg_index in range(0x0D, 0x15): # Reg 0x0D to 0x14
				deviceWrite(deviceEvm, reg_index, (delay_start_word << 16) | delay_start_word)
			# assume the starting point is the same for all memory blocks
			
			# deviceWrite(deviceEvm, 0x02, 0x0000FFFF) # Pattern Page Select for all 16 channels; P103

			# Mem word starts from 0x7, so the pattern generator starts to search from 0x80+0x7=0x87
			# 0x0000FFFF -> Page Select for all 16 channels
			for i, pat in enumerate(pattern):
				deviceWrite(deviceEvm, 0x80 + pattern_start_word + i, pat, pageSelect=0x0000FFFF)
			# Refer to config.py for detailed pattern examples and explanations

			first_run = False # Set the flag to False after the first run
			
			print("==========================================================")		
			print("Processing delay set for angle index {}".format(idx))		
			print("==========================================================")			
							
			# deviceWrite(deviceEvm, 0x02, 0x00010000) # Delay Page Select
			# same starting point, different content for different pages
			for pageNum in range(1, 17): # 16 pages
				pageSel = 1 << pageNum
				deviceWrite(deviceEvm, 0x80 + delay_start_word, delays_int[2*pageNum-2], pageSelect=pageSel)
				deviceWrite(deviceEvm, 0x80 + delay_start_word + 1, delays_int[2*pageNum-1], pageSelect=pageSel)
			# Keep in mind of the arrangement of all_delay_hex_values in config.py
			
			# deviceWrite(deviceEvm, 0x02, 0x00000000) # Deselect Pages
			# This is written in definition of deviceWrite function
			
			deviceEvm.enableSync(True)
			deviceWrite(deviceEvm, 0x08, 0x00000002) # Enable Detect Clock Sync (EN_SYNC_DET)
			
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