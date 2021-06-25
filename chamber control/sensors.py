import subprocess
import datetime
import gpiozero

class LIS3DHAccelerometer:

    __CTRL_REG1 = 0x20
    __CTRL_REG2 = 0x21
    __CTRL_REG3 = 0x22
    __CTRL_REG4 = 0x23
    __CTRL_REG5 = 0x24
    __CTRL_REG6 = 0x25

    __OUT_X_L = 0x28
    __OUT_X_H = 0x29

    __OUT_Y_L = 0x2A
    __OUT_Y_H = 0x2B

    __OUT_Z_L = 0x2C
    __OUT_Z_H = 0x2D

    __axes_reg = [__OUT_X_L,__OUT_X_H,__OUT_Y_L,__OUT_Y_H,__OUT_Z_L,__OUT_Z_H]

    def __init__(self,address,bus):

        self.address = address
        self.bus = bus

    def enable(self):

        self.bus.write_byte_data(self.address,LIS3DHAccelerometer.__CTRL_REG1,0x2F)
        self.bus.write_byte_data(self.address,LIS3DHAccelerometer.__CTRL_REG4, 0x00)

    def readAllAxes(self) -> list:

        axes = LIS3DHAccelerometer.__axes_reg
        results = []
        for axis in range(3):
            dataL = self.bus.read_byte_data(self.address,axes[axis*2])
            dataH = self.bus.read_byte_data(self.address,axes[axis*2+1])
            accel = 256 * dataH + dataL
            if accel > 2**15-1:  # Symmetric values range
                accel -= 2**16-1
            results.append(accel)
        return results


class MCP9808Thermometer:

    __AMBIENT_TEMP_REG = 0x05

    def __init__(self,address,bus):
        self.address = address
        self.bus = bus

    def read(self):

        data = self.bus.read_i2c_block_data(self.address,MCP9808Thermometer.__AMBIENT_TEMP_REG,2)
        print((((data[0] << 8) + data[1]) & 0x0FFF)/16.0)


class ADS1115ADC:

    __CONVERSION_REG = 0x00
    __CONFIG_REG = 0x01
    __LO_THRESH_REG = 0x02
    __HU_THRESH_REG = 0x03

    def __init__(self,address,bus):
        self.address = address
        self.bus = bus

    def readChannel(self,channel):
        # Read channel voltage in reference to ground. ADS1115 also has a differential measuring mode, which
        # has been omitted, but would be trivial to implement.

        LSbyte = 0b11100011  # Comparators disabled, 860SPS data rate
        MSbyte = 0b0011 + ((channel+4) << 4) + 128  # Amplifier gain set to 1, start single conversion, pick channel.
        self.bus.write_i2c_block_data(self.address, ADS1115ADC.__CONFIG_REG,[MSbyte,LSbyte])
        while self.convertingStatus():
            pass
        data = self.bus.read_i2c_block_data(self.address,ADS1115ADC.__CONVERSION_REG,2)
        reading = (data[0] << 8) + data[1]
        # res = vals.to_bytes(2,byteorder="big",signed=False) Two's complement conversion not needed because of
        # measurements in respect to GND.
        return reading

    def convertingStatus(self):

        config = self.bus.read_i2c_block_data(self.address,ADS1115ADC.__CONFIG_REG,2)
        
        if config[1] >= 128:
            return False
        else:
            return True


class HumiditySensorCircuit:

    def __init__(self,gate_pin):
        self._gate_control = gpiozero.LED(gate_pin)

    def powerOn(self):
        self._gate_control.on()

    def powerOff(self):
        self._gate_control.off()

class Camera:

    # Cameras are accessible via /dev/videoCam1 and /dev/videoCam2

    def __init__(self,port,res):
        self.port = port
        self.resolution = res

    def captureFrame(self,image_path):
        timestamp = str(datetime.datetime.now()).replace(" ","-").replace(":","-").replace(".","-")
        path = image_path + timestamp + ".jpg"
        subprocess.call(f"./take_pic.sh {self.port} {self.resolution} {path}",shell=True)


class ImageFlash:

    def __init__(self):
        pass




