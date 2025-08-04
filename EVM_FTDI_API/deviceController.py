import time
import numpy as np
# ftd2xx==1.1.2
# https://ftd2xx.github.io/ftd2xx/
import ftd2xx as d2xx

class USBQPortController():
    ###################CONFIG
    msbFirst = 1
    '''MSB first or LSB first'''
    clkEdge = 1
    '''Clock detected on positive rising edge (1) or falling edge(0)'''
    readClkEdge = 0
    '''Clock detected on positive rising edge (1) or falling edge(0) (Read mode)'''
    packetLen = 44
    '''Total packet length. address + data lengths'''
    addressLen = 12
    '''Length of address in bits'''
    packetOrder = 0
    '''Address first (0) or data first (1)'''
    mask=[0,1,1,1,1,1,1,1]
    '''mask - 0 - input pin, 1 - output pin. Each value maps to each of the 8 pins of the port'''
    value=[0 for x in range(8)]
    '''Variable to store temp write value'''
    enableBit = 4
    '''Which pin of the port is SEN'''
    clkBit = 1
    '''Which pin of the port is clk'''
    dataBit = 2
    '''Which pin of the port is data'''
    dataOutBit = 0
    '''Which pin is SDOUT from device'''
    enableHigh = 0
    '''SEN is active high or active low'''
    readOutMode = 0
    '''1 -> 3 wire SPI'''
    enableSyncPin = 7
    '''Enable sync pin is Port A Pin 7 by default'''

    def __init__(self,addr=None):
        if addr == None:
            print("USB address not specified")
            self.instrument = None
            return
        usbDescription= str(addr)
        self.description = bytes(usbDescription, 'utf-8')
        self.instrument = None
        try:
            self.instrument = d2xx.openEx(self.description,d2xx.defines.OPEN_BY_DESCRIPTION)
        except:
            print("No instrument")
            return
        self.instrument.setUSBParameters(65536, 65536)
        self.instrument.setChars(ord('a'), 0, ord('a'), 0)
        self.instrument.setTimeouts(2000, 2000) 
        self.instrument.setLatencyTimer(16)	
        time.sleep(1)
        self.reset()
    
    def setWritePacket(self,val):
        if self.clkBit==None or self.dataBit==None or self.enableBit==None:
            print("One of clock,data or enable bits is not set. Cannot write the packet.")
            return
        data=bin(val)[2:].zfill(self.packetLen)
        if self.msbFirst==0:
            data=data[::-1]
        clkFirstState=int(not self.clkEdge)
        clkSecondState=self.clkEdge
        
        sendPacket=[]
        self.value[self.enableBit]=self.enableHigh
        self.value[self.clkBit]=0
        self.value[self.dataBit]=0
        sendPacket.append(self.value[:])
        for index,bit in enumerate(data):
            value=self.value
            value[self.clkBit]=clkFirstState
            value[self.dataBit]=int(bit)
            sendPacket.append(value[:])
            value[self.clkBit]=clkSecondState
            sendPacket.append(value[:])
            self.value=value[:]
        self.value[self.clkBit]=0
        self.value[self.dataBit]=0
        sendPacket.append(self.value[:])
        self.value[self.enableBit]=int(not self.enableHigh)
        sendPacket.append(self.value[:])
        stringArray=[]
        for byte in sendPacket:
            stringArray.append(int("".join([str(x) for x in reversed(byte)]),2))
        self.setMask()
        self.instrument.write(bytes(stringArray))
    
    def readReg(self,addr):
        if self.clkBit==None or self.dataOutBit==None or self.enableBit==None:
            print("One of clock,dataOut or enable bits is not set. Cannot read the packet.")
            return
        data=bin(addr)[2:].zfill(self.addressLen)
        if self.msbFirst==0:
            data=data[::-1]
        clkFirstState=int(not self.clkEdge)
        clkSecondState=self.clkEdge
        
        sendPacket=[]
        self.value[self.enableBit]=self.enableHigh
        self.value[self.clkBit]=0
        self.value[self.dataBit]=0
        sendPacket.append(self.value[:])
        for index,bit in enumerate(data):
            value=self.value
            value[self.clkBit]=clkFirstState
            value[self.dataBit]=int(bit)
            sendPacket.append(value[:])
            value[self.clkBit]=clkSecondState
            sendPacket.append(value[:])
            self.value=value[:]
        clkFirstState=int(not self.readClkEdge)
        clkSecondState=self.readClkEdge
        self.value[self.clkBit]=0
        self.value[self.dataBit]=0
        sendPacket.append(self.value[:])
        for index in range(self.packetLen-self.addressLen):
            if self.readOutMode==1:
                #TODO: Support 3 wire SPI here.
                value=self.value
                value[self.clkBit]=clkFirstState
                value[self.dataBit]=0
                sendPacket.append(value[:])
                value[self.clkBit]=clkSecondState
                sendPacket.append(value[:])
                self.value=value[:]
            else:
                value=self.value
                value[self.clkBit]=clkFirstState
                value[self.dataBit]=0
                sendPacket.append(value[:])
                value[self.clkBit]=clkSecondState
                sendPacket.append(value[:])
                self.value=value[:]
                
        self.value[self.clkBit]=0
        self.value[self.dataBit]=0
        sendPacket.append(self.value[:])
        self.value[self.enableBit]=int(not self.enableHigh)
        sendPacket.append(self.value[:])
        stringArray=[]
        for byte in sendPacket:
            stringArray.append(int("".join([str(x) for x in reversed(byte)]),2))
        self.setMask()
        self.instrument.purge()
        readSize=self.instrument.write(bytes(stringArray))
        readData=self.instrument.read(readSize)
        rdData=((np.array([char for char in readData]) >> self.dataOutBit) & 1)[-1+(self.readClkEdge)-(2*(self.packetLen-self.addressLen)):-1:2]
        if self.msbFirst==1:
            no=int(''.join([str(bit) for bit in rdData]),2)
        else:
            no=int(''.join([str(bit) for bit in reversed(rdData)]),2)
        return no
    
    def writeValue(self):
        value=bytes([(int("".join([str(x) for x in reversed(self.value)]),2))])
        self.instrument.write(value)
    
    def reset(self):
        if self.instrument == None:
            print("No instrument")
            return
        return

    def setMask(self):
        mask=''.join([str(x) for x in reversed(self.mask)])
        self.instrument.setBitMode(int(mask,2),0x4)

class USBQPort():

    def __init__(self,addr=None) -> None:
         self.controller = USBQPortController(addr)
         return
        
    def enableSync(self,enable):
        self.controller.value[self.controller.enableSyncPin] = int(enable)
        self.controller.writeValue()

    def writeReg(self,addr,val):
        if self.controller.instrument == None:
            print("No device detected")
            return
        address=bin(addr)[2:].zfill(self.controller.addressLen)	
        value=bin(val)[2:].zfill(self.controller.packetLen-self.controller.addressLen)
        if self.controller.packetOrder==1:
            data=value+address
        else:
            data=address+value
        self.controller.setWritePacket(int(data,2))
        return
    
    def readReg(self,addr):	
        if self.controller.instrument == None:
            print("No device detected")
            return 
        addrLenStore = self.controller.addressLen
        packetLenStore = self.controller.packetLen
        self.controller.addressLen = 56
        self.controller.packetLen = 88
        time.sleep(0.1)
        try:
            readval = self.controller.readReg(addr*2**44+addr)
        except Exception:
            print("Error in reading from Reg programmer")
            return None
        readval = readval & 0xFFFFFFFF
        print("Device readback -> Address {} : {}".format(addr,readval))
        time.sleep(0.1)
        self.controller.addressLen = addrLenStore
        self.controller.packetLen = packetLenStore
        return readval