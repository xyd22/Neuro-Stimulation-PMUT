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
from tools import hardwareReset, deviceWrite, deviceRead, memReset, boardDiagnostics_TX7516
from config_TX7516 import delay_start_word, all_delay_hex_values, pattern_start_word, pattern


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
			deviceWrite(deviceEvm, 0x08, 0x00000000) # Disable Detect Clock Sync; P78, register 8h Bit1 EN_SYNC_DET
			
			# Memory reset
			memReset(deviceEvm)
			
			# Software reset; P71, register 0h Bit0 RESET
			if first_run:
				deviceWrite(deviceEvm, 0x0, 0x00000001)
			
			# Diagnose the board
			boardDiagnostics_TX7516(deviceEvm)
			
			# Set some limits for power supplies (A/B)
			deviceWrite(deviceEvm, 0x2C, 0x7FC00F07) # Supply limits for AVDDP_HV_A
			deviceWrite(deviceEvm, 0x2D, 0x00400F07) # Supply limits for AVDDP_HV_B
			# 7FC->max duration; 00F->fixed; 0->lower limit; 7->upper limit (F for 100V, guess 7 for ~50V)
			# 004->max transition count; 00F->fixed; 0->lower limit; 7->upper limit (F for 100V, guess 7 for ~50V)
			
			# Choose the starting point of the memory (further choose the pattern)
			# we can pre-define a lot of patterns in mem words for each channel,
			# by setting the start word we choose the one to output
			# in config.py pattern_start_word = 0x001E -> 0x001E001E
			# 1E -> Memory Word starts from 1E -> waveforms reads from 30th mem word (m for MEM_WORD_n_m)
			for reg_index in range(0x0C, 0x14): # Register 0x0C to 0x13
				deviceWrite(deviceEvm, reg_index, (pattern_start_word << 16) | pattern_start_word)
				# Write the same pattern_start_word to all registers from 0x0C to 0x13
				# Each register corresponds to two memory words
				# (e.g., 0x0C -> Mem. Start Word for channel 2 and 1;...; 0x0F -> 8 and 7;...; 0x13 -> 16 and 15)
			# Why not use Register 08 Bit6 GBL_PAT_START_ADD	
					
			# deviceWrite(deviceEvm, 0x02, 0x0000FFFF) # Pattern Page Select for all 16 channels; P103

			# Mem word starts from 1E, so the pattern generator starts to search from 0x40+0x1E=0x5E
			# 0x0000FFFF -> Page Select for all 16 channels
			for i, pat in enumerate(pattern):
				deviceWrite(deviceEvm, 0x40 + pattern_start_word + i, pat, pageSelect=0x0000FFFF)
			# Refer to config.py for detailed pattern examples and explanations

			first_run = False # Set the flag to False after the first run
			
			print("==========================================================")		
			print("Processing delay set for angle index {}".format(idx))		
			print("==========================================================")		

			# Choose the starting point of the memory (further choose the delays)
			deviceWrite(deviceEvm, 0x0B, delay_start_word)
							
			# deviceWrite(deviceEvm, 0x02, 0x00010000) # Delay Page Select; P103
			# if e.g. delay_start_word = 0x2, choose delay 3 -> search reg 0x50~0x57
			for index, reg_index in enumerate(range(0x40, 0x48)): # Register 0x40 to 0x47
				deviceWrite(deviceEvm, reg_index + delay_start_word * 8, delays_int[index], pageSelect=0x00010000)
				# Write the delays to registers 0x40 to 0x47
				# Each register corresponds to a specific delay value
				# e.g., 0x40 -> Delay 2 1; 0x41 -> Delay 4 3; ...; 0x47 -> Delay 16 15
			
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