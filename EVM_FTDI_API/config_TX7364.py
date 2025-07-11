# Yudong Xie 2025/7/10
# Including detailed explanations on how to make patterns and delays on TX7364
# =======================================================

delay_start_word = 0x2

all_delay_hex_values = [
[0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A,
 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A,
 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A,
 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A, 0x000A000A,],
]

# =======================================================
# Detailed explanation on how to set a delay on TX7364
# Step 1:
# Choose a location in the memory e.g. 0x2 (the starting location must be even)
# Write the delay info into reg 0x80 + 0x2 = 0x82 and 0x80 + 0x2 + 0x1 = 0x83
# 0x82: [31:16] -> channel 2N+31; [15:0] -> channel 2N-1
# 0x83: [31:16] -> channel 2N+32; [15:0] -> channel 2N
# For a Delay: Delay[13:0] -> DEL; Delay[14] -> FRAC_DEL (set to 1 for half a cycle); Delay[15] -> 0
# e.g. 0x82 = 0x000A400B -> delay for A = 10 BF_CLK cycles in channel 33
#                        -> 0x400B => 0100 0000 0000 1011 -> delay for 11.5 cycles in channel 1
#      0x83 = 0x000C000D -> delay for 12 cycles in channel 34, delay for 13 cycles in channel 2
# Step 2:
# Write 0x00020002 into 0xD~0x14 (responsible for memory block 1~16 respectively)
# e.g. 0x0002 -> choose 2 as the starting location for all the memory blocks (can change to any other even number by writing different values into reg 0xD~0x14)
#      with the starting location N (e.g. 2), the delay info for certain channels (2N-1, 2N, 2N+31, 2N+32) should be writen in the exact location of this memory block
# e.g. write 0x00020006 into 0x10 -> memory block 8 starts from 2, and memory block 7 starts from 6
#      memory block 8 is responsible for ch 47, 15, 48, 16
#      read 0x82 of memory block 8 (page 8): [31:16] -> ch 47; [15:0] -> ch 15
#      read 0x83 of memory block 8 (page 8): [31:16] -> ch 48; [15:0] -> ch 16
#      similarly, memory block 7 is responsible for ch 45, 13, 46, 14
#      read 0x86 of memory block 7 (page 7): [31:16] -> ch 45; [15:0] -> ch 13
#      read 0x87 of memory block 7 (page 7): [31:16] -> ch 46; [15:0] -> ch 14
#      Note: do not overlap with the pattern memory
# 8 reg -> 16 memory blocks (pages) -> each memory block responsible for 4 channels

# How to set a delay for a certain channel?
# e.g. set delay (2389.5 cycles) for channel 55:
# channel 55 -> memory block 12 (2*12+31=55) -> memory block 12
# find somewhere you want to put the delay info in memory block 12 (e.g. 0x4)
# write the delay info into 0x84 and 0x85 of memory block 12 (page 12)
# note, only 0x84[31:16] is responsible for channel 55
# 2389 = 00100101010101 (14 dig); .5 -> 1 -> 0100100101010101 -> 0x4955
# => write 0x4955xxxx into 0x84 of memory block 12 

# How to manage the all_delay_hex_values?
# Method 1: pre-define all the delay profiles in all the pages (all the same), but choose different starting locations
# Method 2: use the same starting location for all the memory blocks, but write different delay profiles in different pages
# arrangement:
# [[0x00010002, 0x00030004, ..., xxx, xxx],  (32 elements)
#  [xxx, xxx, xxx, xxx, ......., xxx, xxx],
#  ......,
# ] (each row for a complete delay profile for all 64 channels)
# where 0x0001 -> ch 33, 0x0002 -> ch 1, 0x0003 -> ch 34, 0x0004 -> ch 2; ....

# !! refer to P28~29 description on memory blocks and Table 7-3


pattern_start_word = 0x7

pattern = [0x00020002, 0x0000B5B1]

# =======================================================
# Detailed explanation on how to make a pattern on TX7364
# Step 1: 
# write in 0x33 for the starting word (e.g. 0x7) -> pattern reg starts reading from 0x80 + 0x7 = 0x87
# Step 2:
# 0x87: [29:16] -> PAT_LEN(pattern length); [7:0] -> GBL_REP_NUM (global repeat number)
#       e.g. 0x00030000 -> global repeat number = 0; pattern length = 3
# Step 3:
# 0x88: for every word (8bits), MSB 5bits -> PER (period => period + 1 cycles); LSB 3bits -> LVL (level)
#       e.g. 0x00CCC9CD -> 0000 0000 1100 1100 1100 1001 1100 1101
#            11001101 -> 11001 = 25 => 26 cycles, 101 = MHV
#            11001001 -> 11001 = 25 => 26 cycles, 001 = PHV
#            11001100 -> 11001 = 25 => 26 cycles, 100 = ground
#            00000000 -> HiZ
# 0x89: ...
# ...
# until the transitions being read == pattern length
# repeat for GBL_REP_NUM times

# =================================
# e.g. 2 cycles 5.6 MHz_3LVL_A Wave
# Method 1:
# GBL_REP_NUM = 2, PAT_LEN = 2
# 0x87 = 0x00020002
# under 250MHz clk, each transition period = 22 cycles (5.6MHz)
# 22 = 10110, PHV = 001 -> 10110001 = 0xB1
# 22 = 10110, PHV = 101 -> 10110001 = 0xB5
# 0x88 = 0x0000B5B1
# Method 2:
# GBL_REP_NUM = 1, PAT_LEN = 4
# 0x87 = 0x00040001
# 0x88 = 0xB5B1B5B1

# !! refer to P35~39 pipeline and detailed description