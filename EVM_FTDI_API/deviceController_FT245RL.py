import time
import numpy as np
# 确保已安装: pip install ftd2xx==1.1.2
import ftd2xx as d2xx

# =============================================================================
#  粘贴您提供的 USBQPortController 和 USBQPort 类的完整代码于此
# =============================================================================

class USBQPortController():
    ###################CONFIG
    msbFirst = 1
    clkEdge = 1
    readClkEdge = 0
    packetLen = 44
    addressLen = 12
    packetOrder = 0
    mask=[0,1,1,1,1,1,1,1] 
    value=[0 for x in range(8)]
    enableBit = 4
    clkBit = 1
    dataBit = 2
    dataOutBit = 0
    enableHigh = 0
    readOutMode = 0
    enableSyncPin = 7

    def __init__(self,addr=None):
        if addr == None:
            print("USB address not specified")
            self.instrument = None
            return
        usbDescription= str(addr)
        self.description = bytes(usbDescription, 'utf-8')
        self.instrument = None
        try:
            print(f"Attempting to open device with description: '{usbDescription}'")
            self.instrument = d2xx.openEx(self.description,d2xx.defines.OPEN_BY_DESCRIPTION)
            print("Device opened successfully.")
        except Exception as e:
            print(f"Failed to open instrument: {e}")
            try:
                devices = d2xx.listDevices(d2xx.defines.LIST_BY_DESCRIPTION)
                print("Available devices by description:", devices)
            except:
                print("Could not list devices. FTDI drivers might not be installed correctly.")
            return
            
        self.instrument.setUSBParameters(65536, 65536)
        self.instrument.setChars(ord('a'), 0, ord('a'), 0)
        self.instrument.setTimeouts(2000, 2000) 
        self.instrument.setLatencyTimer(16)
        
        # 必须先设置位模式，再进行其他操作
        self.setMask()
        self.instrument.purge(d2xx.defines.PURGE_RX | d2xx.defines.PURGE_TX)
        time.sleep(0.1) # 等待设备稳定
        
        # *** FIX 2: 移除这里的 reset 调用, 放到主程序中 ***
        # self.reset()

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
        # SEN active low, ensure clock is also in idle state
        self.value[self.enableBit]=self.enableHigh
        self.value[self.clkBit]=clkFirstState
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
            
        # Return clock to idle state before de-asserting SEN
        self.value[self.clkBit]=clkFirstState
        self.value[self.dataBit]=0
        sendPacket.append(self.value[:])
        # SEN inactive
        self.value[self.enableBit]=int(not self.enableHigh)
        sendPacket.append(self.value[:])
        
        stringArray=[]
        for byte in sendPacket:
            stringArray.append(int("".join([str(x) for x in reversed(byte)]),2))
            
        self.instrument.write(bytes(stringArray))
    
    def readReg(self,addr):
        # 注意: 您提供的readReg代码似乎不完整或有逻辑问题，特别是readSize和数据切片部分。
        # 真正的读取需要在发送地址后，继续驱动时钟，并同时从MISO线读取数据。
        # 这里为了演示，我们假设writeReg工作正常。
        print("readReg function is for demonstration and may need debugging based on your hardware.")
        if self.instrument == None:
            print("No device detected")
            return 
        addrLenStore = self.addressLen
        packetLenStore = self.packetLen
        # 根据datasheet P63 (Register 0h), READ_EN是2位
        # 01 = die 2, 10 = die 1
        # 我们需要先写寄存器0来使能读取
        
        # 1. 使能Die 1的读取
        self.writeReg(0, 0b10 << 1) # READ_EN = 10
        # 2. 发送要读取的地址，并接收数据
        val_d1 = self.readReg_internal(addr) # 假设有一个内部实现
        
        # 3. 使能Die 2的读取
        self.writeReg(0, 0b01 << 1) # READ_EN = 01
        val_d2 = self.readReg_internal(addr) # 假设有一个内部实现

        # 4. 恢复写模式
        self.writeReg(0, 0)
        
        # Datasheet P58, step 3: 最终结果是两个die读数的OR
        final_val = val_d1 | val_d2
        
        self.addressLen = addrLenStore
        self.packetLen = packetLenStore
        return final_val

    def readReg_internal(self, addr):
        # 这是一个更符合逻辑的内部读取实现，但未经测试
        if self.clkBit==None or self.dataOutBit==None or self.enableBit==None:
            print("One of clock,dataOut or enable bits is not set. Cannot read the packet.")
            return 0
        
        # TX7332 需要10位地址
        data=bin(addr)[2:].zfill(10)
        if self.msbFirst==0:
            data=data[::-1]
            
        clkFirstState=int(not self.clkEdge)
        clkSecondState=self.clkEdge
        
        sendPacket=[]
        self.value[self.enableBit] = self.enableHigh
        self.value[self.clkBit] = clkFirstState
        sendPacket.append(self.value[:])

        # 发送10位地址
        for bit in data:
            value=self.value
            value[self.clkBit]=clkFirstState
            value[self.dataBit]=int(bit)
            sendPacket.append(value[:])
            value[self.clkBit]=clkSecondState
            sendPacket.append(value[:])
            self.value=value[:]
        
        # 在地址后继续发送32个时钟周期以读出数据
        for _ in range(32):
            value=self.value
            value[self.clkBit]=clkFirstState
            sendPacket.append(value[:])
            value[self.clkBit]=clkSecondState
            sendPacket.append(value[:])
            self.value=value[:]
        
        self.value[self.clkBit]=clkFirstState
        sendPacket.append(self.value[:])
        self.value[self.enableBit]=int(not self.enableHigh)
        sendPacket.append(self.value[:])

        stringArray=[]
        for byte in sendPacket:
            stringArray.append(int("".join([str(x) for x in reversed(byte)]),2))
            
        self.instrument.purge(d2xx.defines.PURGE_RX | d2xx.defines.PURGE_TX)
        readSize=self.instrument.write(bytes(stringArray))
        readData=self.instrument.read(readSize)
        
        # 从返回的数据中提取 MISO (dataOutBit) 的值
        # 提取点应该在时钟的非采样边沿之后
        # 我们在地址发送完后开始提取，总共32位
        start_index = 1 + (10 * 2) + (1-self.readClkEdge) # SEN下降沿 + 10*2个字节(地址) + 采样点偏移
        end_index = start_index + (32 * 2)
        rdData=((np.array([char for char in readData]) >> self.dataOutBit) & 1)[start_index:end_index:2]
        
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
            print("No instrument to reset")
            return
        
        print("Sending software reset command...")
        
        # *** FIX 1: 直接使用低层方法构建和发送复位包 ***
        addr = 0x00
        val = 0x01  # Bit 0 = 1 for reset

        # 构造一个完整的SPI包
        address_str = bin(addr)[2:].zfill(self.addressLen)
        value_str = bin(val)[2:].zfill(self.packetLen - self.addressLen)

        if self.packetOrder == 1:
            data_str = value_str + address_str
        else:
            data_str = address_str + value_str

        # 调用自身的低层写包函数
        self.setWritePacket(int(data_str, 2))
        
        # RESET位是自清除的，但最好等待一下确保操作完成
        time.sleep(0.1)
        print("Software reset complete.")

    def setMask(self):
        mask_val=''.join([str(x) for x in reversed(self.mask)])
        self.instrument.setBitMode(int(mask_val,2),0x4)
        
class USBQPort():
    def __init__(self,addr=None) -> None:
         self.controller = USBQPortController(addr)
         # 纠正控制器内部的 packetLen 和 addressLen 以匹配TX7332
         self.controller.packetLen = 42 # 10位地址 + 32位数据
         self.controller.addressLen = 10
         return
        
    def enableSync(self,enable):
        self.controller.value[self.controller.enableSyncPin] = int(enable)
        self.controller.writeValue()

    def writeReg(self,addr,val):
        if self.controller.instrument == None:
            print("No device detected")
            return
        # 使用控制器中已经更正的长度
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
        try:
            readval = self.controller.readReg(addr)
        except Exception as e:
            print(f"Error in reading from Reg programmer: {e}")
            return None
        return readval

    def close(self):
        if self.controller.instrument:
            print("Closing device.")
            self.controller.instrument.close()


# =============================================================================
#                              主程序 (MAIN)
# =============================================================================
if __name__ == '__main__':
    # 将'TX7332'替换为您FT245RL芯片在系统中的实际描述符
    DEVICE_DESCRIPTION = 'TX7332' 
    
    # 1. 初始化并连接到设备
    device = USBQPort(DEVICE_DESCRIPTION)

    # 检查设备是否成功连接
    if device.controller.instrument is None:
        print("\nInitialization failed. Exiting.")
    else:
        try:
            # *** FIX 3: 在对象完全创建后, 再调用 reset ***
            # 2. 对设备进行软件复位 (良好实践)
            device.controller.reset()
            
            # 3. 配置TX7332进入片上波束形成模式
            # 根据Datasheet P71, Register 18h, Bit 0 (TX_BF_MODE)
            # 0 = Off-chip beamforming mode (default)
            # 1 = On-chip beamforming mode
            
            reg_addr_18h = 0x18
            reg_value = 0x00000001
            
            print(f"\nWriting to register 0x{reg_addr_18h:X} with value 0x{reg_value:08X} to enable On-Chip Beamforming...")
            device.writeReg(reg_addr_18h, reg_value)
            print("Write command sent.")
            
            time.sleep(0.1)

            # 4. (可选但推荐) 读回寄存器以验证
            print(f"Reading back from register 0x{reg_addr_18h:X} to verify...")
            read_val = device.readReg(reg_addr_18h) # 此功能需要您调试
            print(f"Read value: {read_val}")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # 5. 安全地关闭设备连接
            device.close()