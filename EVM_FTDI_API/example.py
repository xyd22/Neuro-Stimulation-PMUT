from deviceController import USBQPort


# Create the EVM Qport object
# The string passed is the address of the FTDI port
# Instructions to find the address is present in the attached document
# deviceEvm = USBQPort('FT4232 Mini Module A')
deviceEvm = USBQPort('TX7332') # For TX7332 only

def deviceWrite(address,data,pageSelect=0):
    # First do the page select. Page select value needs to be written to register 2 in single lane SPI mode.
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

#Disable sync before any SPI operation
deviceEvm.enableSync(False)
# Read register 48 in GBL page
regVal = deviceRead(48)
print(regVal)   # Will print 0 or junk value
# Write 0xf to register 48 in GBL page
deviceWrite(48,0xf)
# Read register 48 in GBL page
regVal2 = deviceRead(48)
print(regVal2)  # Should print 15 (0xf)


# Read from memory page 5 address 128
pageSel = 1<<5 # Make bit 5 high to select page 5
regVal = deviceRead(128,pageSel)
print(regVal)   # Will print 0 or junk value
# Write 0xff to register 128 in page 5
deviceWrite(128,0xff,pageSel)
# Read register 128 in page 5
regVal2 = deviceRead(128,pageSel)
print(regVal2)  # Should print 255 (0xff)

# When reading back, you should read from each page individualy. But when writing to the device, multiple pages can be selected and written to simultneously.
# Read from memory page 5 address 200
regVal = deviceRead(200,1<<5)
print(regVal)   # Will print 0 or junk value
# Read from memory page 8 address 200
regVal = deviceRead(200,1<<8)
print(regVal)   # Will print 0 or junk value
# Write 0xff to register 200 in page 5 and 8
deviceWrite(200,0xff,(1<<5)+(1<<8))
# Read from memory page 5 address 200
regVal = deviceRead(200,1<<5)
print(regVal)   # Should print 255 (0xff)
# Read from memory page 8 address 200
regVal = deviceRead(200,1<<8)
print(regVal)   # Should print 255 (0xff)
