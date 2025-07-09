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
from tools import hardwareReset, deviceWrite, deviceRead, memReset, boardDiagnostics
from config import all_delay_hex_values, mem_start_word, pattern


if __name__ == "__main__":

	print("##########################################################")
	print("##########################################################")
	#Device.RemoveAllDevices()

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
			
			memReset(deviceEvm)
			
			if first_run:
				deviceWrite(deviceEvm, 0x0, 0x00000001) # Software reset; P71, register 0h Bit0 RESET
			
			boardDiagnostics(deviceEvm)
			
			deviceWrite(deviceEvm, 0x2C, 0x7FC00F07) # Supply limits for AVDDP_HV_A
			deviceWrite(deviceEvm, 0x2D, 0x00400F07) # Supply limits for AVDDP_HV_B
			# 7FC->max duration; 00F->fixed; 0->lower limit; 7->upper limit (F for 100V, guess 7 for ~50V)
			# 004->max transition count; 00F->fixed; 0->lower limit; 7->upper limit (F for 100V, guess 7 for ~50V)
			
			# choose 1E to select the starting point (further choose the pattern)
			# we can pre-define a lot of patterns in mem words for each channel,
			# by setting the start word we choose the one to output
			# in config.py mem_start_word = 0x001E -> 0x001E001E
			deviceWrite(deviceEvm, 0x0C, (mem_start_word << 16) | mem_start_word) # Mem. Start Word 2 and 1 respectively
			deviceWrite(deviceEvm, 0x0D, (mem_start_word << 16) | mem_start_word) # Mem. Start Word 4 and 3 respectively		
			deviceWrite(deviceEvm, 0x0E, (mem_start_word << 16) | mem_start_word) # Mem. Start Word 6 and 5 respectively		
			deviceWrite(deviceEvm, 0x0F, (mem_start_word << 16) | mem_start_word) # Mem. Start Word 8 and 7 respectively		
			deviceWrite(deviceEvm, 0x10, (mem_start_word << 16) | mem_start_word) # Mem. Start Word 10 and 9 respectively		
			deviceWrite(deviceEvm, 0x11, (mem_start_word << 16) | mem_start_word) # Mem. Start Word 12 and 11 respectively		
			deviceWrite(deviceEvm, 0x12, (mem_start_word << 16) | mem_start_word) # Mem. Start Word 14 and 13 respectively		
			deviceWrite(deviceEvm, 0x13, (mem_start_word << 16) | mem_start_word) # Mem. Start Word 16 and 15 respectively	
			# 1E -> Memory Word starts from 1E -> waveforms reads from 30th mem word (m for MEM_WORD_n_m)
			# Why not use Register 08 Bit6 GBL_PAT_START_ADD	
					
			# deviceWrite(deviceEvm, 0x02, 0x0000FFFF) # Pattern Page Select for all 16 channels; P103
			# Mem word starts from 1E, so the pattern generator starts to search from 0x40+0x1E=0x5E
			# deviceWrite(deviceEvm, 0x5C, 0xA0A00000, pageSelect=0x0000FFFF) # TRSW Glitch --OURS--nothing		
			# deviceWrite(deviceEvm, 0x5D, 0x0000FF00, pageSelect=0x0000FFFF) # TRSW Glitch --OURS--		
			# deviceWrite(deviceEvm, 0x5E, 0xB5B10000, pageSelect=0x0000FFFF) # 5.6 MHz_3LVL_A Wave --OURS-- 5.6
			# deviceWrite(deviceEvm, 0x5F, 0xFF00B5B1, pageSelect=0x0000FFFF) # 5.6 MHz_3LVL_A Wave --OURS--		
			# deviceWrite(deviceEvm, 0x52, 0x31f90000, pageSelect=0x0000FFFF) # 3.4 MHz_2LVL_A Wave --OURS-- 1.66 2.4 3.4 0xf9f90001 0xa9f90000 0x31f90000		
			# deviceWrite(deviceEvm, 0x53, 0x31f935fd, pageSelect=0x0000FFFF) # 3.4 MHz_2LVL_A Wave --OURS-- 0x6dfdfd69 0xa9f9adfd 0x31f935fd
			# deviceWrite(deviceEvm, 0x54, 0xff0035fd, pageSelect=0x0000FFFF) # 3.4 MHz_2LVL_A Wave --OURS-- 0x0000ff00 0xff00adfd 0xff0035fd		
			for i, pat in enumerate(pattern):
				deviceWrite(deviceEvm, 0x40 + mem_start_word + i, pat, pageSelect=0x0000FFFF)
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
							
			# deviceWrite(deviceEvm, 0x02, 0x00010000) # Delay Page Select; P103
			deviceWrite(deviceEvm, 0x40, delays_int[0], pageSelect=0x00010000) # Delay 2 1
			deviceWrite(deviceEvm, 0x41, delays_int[1], pageSelect=0x00010000) # Delay 4 3		
			deviceWrite(deviceEvm, 0x42, delays_int[2], pageSelect=0x00010000) # Delay 6 5
			deviceWrite(deviceEvm, 0x43, delays_int[3], pageSelect=0x00010000) # Delay 8 7		
			deviceWrite(deviceEvm, 0x44, delays_int[4], pageSelect=0x00010000) # Delay 10 9		
			deviceWrite(deviceEvm, 0x45, delays_int[5], pageSelect=0x00010000) # Delay 12 11		
			deviceWrite(deviceEvm, 0x46, delays_int[6], pageSelect=0x00010000) # Delay 14 13		
			deviceWrite(deviceEvm, 0x47, delays_int[7], pageSelect=0x00010000) # Delay 16 15
					
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