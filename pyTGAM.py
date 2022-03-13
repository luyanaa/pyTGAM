##Copyright (c) 2013, sahil singh
##Copyright (c) 2022, Robin Lu(https://github.com/luyanaa)
##All rights reserved.
##
##Redistribution and use in source and binary forms, with or without modification,
##are permitted provided that the following conditions are met:
##
##    * Redistributions of source code must retain the above copyright notice,
##      this list of conditions and the following disclaimer.
##    * Redistributions in binary form must reproduce the above copyright notice,
##      this list of conditions and the following disclaimer in the documentation
##      and/or other materials provided with the distribution.
##    * Neither the name of NeuroPy nor the names of its contributors
##      may be used to endorse or promote products derived from this software
##      without specific prior written permission.
##
##THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
##"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
##LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
##A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
##CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
##EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
##PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
##PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
##LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
##NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
##SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging
from multiprocessing.sharedctypes import RawArray
import serial
import numpy
import time
import mne
import _thread

class NeuroPy(object):
    """NeuroPy library, to get data from neurosky mindwave.
    Initialising: object1=NeuroPy("COM6",57600) #windows
    After initialising , if required the callbacks must be set
    then using the start method the library will start fetching data from mindwave
    i.e. object1.start()
    similarly stop method can be called to stop fetching the data
    i.e. object1.stop()
\]
    The data from the device can be obtained using either of the following methods or both of them together:
    
    Obtaining value: variable1=object1.attention #to get value of attention
    #other variables: attention,meditation,rawValue,delta,theta,lowAlpha,highAlpha,lowBeta,highBeta,lowGamma,midGamma, poorSignal and blinkStrength
    
    Setting callback:a call back can be associated with all the above variables so that a function is called when the variable is updated. Syntax: setCallBack("variable",callback_function)
    for eg. to set a callback for attention data the syntax will be setCallBack("attention",callback_function)"""
    __rawValue=0 
    __poorSignal=0
    __blinkStrength=0
    srl=None
    __port=None
    __baudRate=None
    logging = False
    rawArray = numpy.array([])
    stimulus = []
    threadRun=True #controlls the running of thread
    callBacksDictionary={} #keep a track of all callbacks
    def __init__(self,port,baudRate=57600):
        self.__port,self.__baudRate=port,baudRate
        
    def __del__(self):
        self.srl.close()
    
    def start(self):
        """starts packetparser in a separate thread"""
        self.threadRun=True
        self.srl=serial.Serial(self.__port,self.__baudRate)
        _thread.start_new_thread(self.__packetParser,(self.srl,))
   
    def __packetParser(self,srl):
        "packetParser runs continously in a separate thread to parse packets from mindwave and update the corresponding variables"
        while self.threadRun:
            p1=srl.read(1).hex() #read first 2 packets
            p2=srl.read(1).hex()
            while p1!='aa' or p2!='aa':
                p1=p2
                p2=srl.read(1).hex()
            else:
                #a valid packet is available
                payload=[]
                checksum=0;
                payloadLength=int(srl.read(1).hex(),16)
                for i in range(payloadLength):
                    tempPacket=srl.read(1).hex()
                    payload.append(tempPacket)
                    checksum+=int(tempPacket,16)
                checksum=~checksum&0x000000ff
                if checksum==int(srl.read(1).hex(),16):
                   i=0
                   while i<payloadLength:
                       code=payload[i]
                       if(code=='02'):#poorSignal
                           i=i+1; self.poorSignal=int(payload[i],16)
                       elif(code=='16'):#blink strength
                           i=i+1; self.blinkStrength=int(payload[i],16)
                       elif(code=='80'):#raw value
                           i=i+1 #for length/it is not used since length =1 byte long and always=2
                           i=i+1; val0=int(payload[i],16)
                           i=i+1; self.rawValue=val0*256+int(payload[i],16)
                           if self.rawValue>32768 :
                               self.rawValue=self.rawValue-65536
                           if self.logging:
                               self.RawArray.append(self.rawValue)
                       else:
                           pass
                       i=i+1

        
    def stop(self):
        "stops packetparser's thread and releases com port i.e disconnects mindwave"
        self.threadRun=False
        self.srl.close()
                    
    # def setCallBack(self,variable_name,callback_function):
    #     """Setting callback:a call back can be associated with all the above variables so that a function is called when the variable is updated. Syntax: setCallBack("variable",callback_function)
    #        for eg. to set a callback for attention data the syntax will be setCallBack("attention",callback_function)"""
    #     self.callBacksDictionary[variable_name]=callback_function

    def stimulus(self, value):
        if self.logging:
            self.stimulus[time.time()] = value
    #log
    @property
    def logging(self):
        return self.logging
    
    @logging.setter
    def logging(self, boolValue: bool):
        self.logging = boolValue
        if boolValue and (not self.logging):
            self.loggingStartTime = time.time()
        elif (not boolValue) and self.logging:
            self.loggingEndTime = time.time()
        else:
            raise("logging error here")
        
    def outputMNE(self, description=None):
        # Channel: EEG for the logged data, STI 014 for external stimulus
        channel_names = ['EEG1', 'STI 014']
        # Channel Type
        channel_types = ['eeg', 'stim']
        # sfreq: 512Hz Sampling Frequency
        sfreq = 512
        # description
        info = mne.create_info(channel_names, channel_types, sfreq)
        info['description'] = description
        rawMNE = mne.io.RawArray(numpy.array([self.rawArray, numpy.array(self.stimulus)] , info)
        return rawMNE

    #rawValue
    @property
    def rawValue(self):
        "Get value for rawValue"
        return self.__rawValue
    @rawValue.setter    
    def rawValue(self,value):
        self.__rawValue=value
        if "rawValue" in self.callBacksDictionary: #if callback has been set, execute the function
            self.callBacksDictionary["rawValue"](self.__rawValue)
    
    #poorSignal
    @property
    def poorSignal(self):
        "Get value for poorSignal"
        return self.__poorSignal
    @poorSignal.setter
    def poorSignal(self,value):
        self.__poorSignal=value
        if "poorSignal" in self.callBacksDictionary: #if callback has been set, execute the function
            self.callBacksDictionary["poorSignal"](self.__poorSignal)
    
    #blinkStrength
    @property
    def blinkStrength(self):
        "Get value for blinkStrength"
        return self.__blinkStrength
    @blinkStrength.setter
    def blinkStrength(self,value):
        self.__blinkStrength=value
        if "blinkStrength" in self.callBacksDictionary: #if callback has been set, execute the function
            self.callBacksDictionary["blinkStrength"](self.__blinkStrength)
    
    


