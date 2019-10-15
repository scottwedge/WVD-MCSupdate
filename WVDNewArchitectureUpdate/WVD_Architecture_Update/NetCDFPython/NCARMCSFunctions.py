# Written By: Robert Stillwell
# Written For: National Center for Atmospheric Research
# The following functions are used to open and read the binary files the 
# labview code writes for the MicroPulse DIAL. Some data checks are run and if
# there is a recognized error, a string describing it will be returned; if no
# error is recognized, then data arrays containing all of the file information 
# are returned. 

import os
import sys
import struct
sys.dont_write_bytecode = True

#%%
def ParseMCSCountsHeader(Header,ChannelAssign):
    # Bytes 0 - 7 -> Timestamp
    Timestamp = struct.unpack('>d',Header[0:8])[0]
    # Bytes 8-10 -> null, Byte 11 -> Start of Text, Byte 12 -> CR, Byte 13 -> 
    # LF, Bytes 14-16 -> null, and Byte 17 -> "0", Bytes 18-27 -> "OnlineH2O " 
    OnlineH2OCh = ord(Header[29])-48 
    if ord(Header[28]) == 49: # a two digit channel assignment so add 10 
        OnlineH2OCh = OnlineH2OCh + 10  
    # Bytes 30-40 -> "OfflineH2O "
    OfflineH2OCh = ord(Header[42])-48
    if ord(Header[41]) == 49: 
        OfflineH2OCh = OfflineH2OCh + 10 
    # Bytes 43-55 -> "CombinedHSRL "
    CombinedHSRLCh = ord(Header[57])-48
    if ord(Header[56]) == 49: 
        CombinedHSRLCh = CombinedHSRLCh + 10  
    # Bytes 58-71 -> "MolecularHSRL "
    MolecularHSRLCh = ord(Header[73])-48
    if ord(Header[72]) == 49: 
        MolecularHSRLCh = MolecularHSRLCh + 10  
    # Bytes 74-82 -> "OnlineO2 "
    OnlineO2Ch = ord(Header[84])-48
    if ord(Header[83]) == 49: 
        OnlineO2Ch = OnlineO2Ch + 10 
    # Bytes 85-94 -> "OfflineO2 "
    OfflineO2Ch = ord(Header[96])-48
    if ord(Header[95]) == 49: 
        OfflineO2Ch = OfflineO2Ch + 10
    # Bytes 97-99 -> null, Byte 100 -> Start of text, Byte 101 -> CR, Byte  
    # 102 -> LF, Bytes 103-104 -> null, Bytes 105-106 -> ??????????
    # Bytes 107-110 -> Histogram Data Frame Header Word 
    # Checking that the header word is there and equal to 0x4D430000
    if ''.join('{:08b}'.format(ord(Header[i])) for i in range(107,111)) != \
       ''.join('{:08b}'.format(ord(x))         for x in '\x00\x00\x43\x4D'):
        
        print(''.join('{:08b}'.format(ord(Header[i])) for i in range(107,111)))
        print(''.join('{:08b}'.format(ord(x))         for x in '\x00\x00\x43\x4D'))
           
        ErrorResponse = 'The MCS data frame header word does not match the expected value. ~RS'
        print(ErrorResponse)
        return ([],[],[],[],[],[],[],[],[],ErrorResponse)
    # Bytes 111-112 -> Profiles per histogram
    ProfPerHist = ord(Header[112]) * 2**8 + ord(Header[111])
    # Bytes 113 -> null (from Josh)
    # Bytes 114 -> Sync and Channel
    Sync     = ord(Header[114])%16
    Channel  = (ord(Header[114])-Sync)/16
    # Bytes 115-116 -> Counts per bin * 5ns per count
    NsPerBin = (ord(Header[116])*2**8 + ord(Header[115]))*5
    # Bytes 117-118 -> Number of bins
    NBins    = ord(Header[118])*2**8 + ord(Header[117])
    # Bytes 119-121 - Relative time counter
    RTime    = ord(Header[121])*2**16 + ord(Header[120])*2**8 + ord(Header[119])
    # Bytes 122 -> Frame counter
    FCount   = ord(Header[122])
    # Bytes 123-126 = null
    # Saving 
    ChannelAssign[OnlineH2OCh] = str("WVOnline")
    ChannelAssign[OfflineH2OCh] = str("WVOffline")
    ChannelAssign[CombinedHSRLCh] = str("HSRLCombined")
    ChannelAssign[MolecularHSRLCh] = str("HSRLMolecular")
    ChannelAssign[OnlineO2Ch] = str("O2Online")
    ChannelAssign[OfflineO2Ch] = str("O2Offline")
    return(Channel,FCount,NBins,NsPerBin,ProfPerHist,RTime,Sync,Timestamp,ChannelAssign,'')

#%%
def ReadMCSCounts(Bins,File,ReadIndex,ExpectedChannel):
    # Reading the data from the MCS
    DataArray = []
    for v in range(0, Bins):
        data = File.read(4)
        ReadIndex = ReadIndex+4          
        if ord(data[3:4])/16 != ExpectedChannel:
            # Write warning that says the header and data main body do not
            # have the same channel number
            ReadError = 'The MCS count channel and header channel do not match. ~RS'
            print(ReadError)
            return([],[],ReadError)
        # Reading photon counting data
        DataArray.append(ord(data[2:3])*2**16 + ord(data[1:2])*2**8 + ord(data[0:1]))
    return (DataArray,ReadIndex,'')

#%%
def ReadMCSPhotonCountFile(MCSFile, Channels=12, headerBytes=127):
    # Constants
    ReadIndex = 0
    # Pre-allocating data arrays 
    Timestamp = []; ProfPerHist = []; Channel = []; DataArray = []; Sync = []
    CntsPerBin = []; NBins = []; RTime = []; FrameCtr = []; ChannelAssign = []
    # Pre-allocating Channel asignment array
    for i in range(Channels):
        ChannelAssign.append("Unassigned")
    del i
    # Opening the file and reading its data contents
    with open(MCSFile , 'rb') as file:
        file_length=len(file.read())
        file.seek(0)
        # Looping over the availible bytes
        while ReadIndex+headerBytes < file_length:
            # Reading and saving header information and photon counting information  
            (Ch,FC,Bins,NPB,PPH,TRel,sync,TStamp,ChannelAssign,HeaderError) = ParseMCSCountsHeader(file.read(headerBytes),ChannelAssign)
            ReadIndex = ReadIndex+headerBytes
            if HeaderError == '':
                (DataReturn,ReadIndex,ReadError) = ReadMCSCounts(Bins,file,ReadIndex,Ch)
                if ReadError == '':
                    Channel.append(Ch); del Ch
                    CntsPerBin.append(NPB); del NPB
                    DataArray.append(DataReturn); del DataReturn
                    FrameCtr.append(FC); del FC
                    NBins.append(Bins); del Bins
                    ProfPerHist.append(PPH); del PPH
                    RTime.append(TRel); del TRel
                    Sync.append(sync); del sync
                    Timestamp.append(TStamp); del TStamp  
                    # Confirming footer word was where it is expected and that it is what 
                    # it is expected to be (0xFFFFFFFF)
                    if '\xff\xff\xff\xff' != file.read(4).format(2):
                        #Write warning that footer is not equal to what it should be
                        FooterError = 'The MCS data frame footer word does not match the expected value. ~RS'
                        print(FooterError)
                        return([],[],[],[],[],[],[],[],[],[],FooterError)
                else:
                    return([],[],[],[],[],[],[],[],[],[],ReadError)
                ReadIndex = ReadIndex+4
                # Seeking forward 8 bytes from current location (throwing away 
                # extra bits on end of data frame so next is alligned)
                file.seek(8,1)
                ReadIndex = ReadIndex+8
            else:
                return([],HeaderError)
    # If there are no observed errors, return the data as a tuple
    return(Channel, ChannelAssign, CntsPerBin, DataArray, FrameCtr, NBins, ProfPerHist, RTime, Sync, Timestamp, '')

#%%
def ReadMCSPowerFile(Powerfile, Channels=12):
    # Processing constants
    MeasurementBytes = 146 # this is the number of bytes per power measurement
    StartByte        = 78  # this is the location of the first byte in the 
                           # power monitoring data frame (see Josh's document
                           # for details about this data frame)               
    ChannelAssign = []
    for index in range(Channels):
        ChannelAssign.append("Unassigned")
    # Pre-allocating data arrays
    AccumExp  = []; Demux = []; PowerCh = []; RTime = [];Timestamp = [];
    HSRLPowCh = []; OnlineH2OCh = []; OfflineH2OCh = []; OnlineO2Ch = []; OfflineO2Ch = [];
    # Opening the file as a binary file and looping over availible data bytes
    with open(Powerfile, "rb") as file:
        file.seek(0)  # Go to beginning of the file
        for k in range(int(os.path.getsize(Powerfile)/MeasurementBytes)):
            # Reading next chunk of data
            Data = file.read(MeasurementBytes)
            # Reading the data time stamp
            Timestamp.append(struct.unpack('>d',Data[0:8])[0])
            # For reference the next several bytes are: 8-10 (null), 11 (Start of Text),
            # 12 (Carrage Return), 13 (Line feed), 14-16 (null), 17 (2)
            # Reading the channel numbers
            # For reference now...Bytes 18-22 are the word "HSRL "
            HSRLPowCh.append(ord(Data[23:24])-48)
            # For reference now...Bytes 24-33 are the word "OnlineH2O "
            OnlineH2OCh.append(ord(Data[34:35])-48) 
            # For reference now...Bytes 35-45 are the word "OfflineH2O "
            OfflineH2OCh.append(ord(Data[46:47])-48)
            # For reference now...Bytes 47-55 are the word "OnlineO2 "
            OnlineO2Ch.append(ord(Data[56:57])-48)
            # For reference now...Bytes 57-66 are the word "OfflineO2 "
            OfflineO2Ch.append(ord(Data[67:68])-48)
            # Temp variable to match the current output
            ChannelAssign[ord(Data[23:24])-48] = str("HSRL")
            ChannelAssign[ord(Data[34:35])-48] = str("OnlineH2O")
            ChannelAssign[ord(Data[46:47])-48] = str("OfflineH2O")
            ChannelAssign[ord(Data[56:57])-48] = str("OnlineO2")
            ChannelAssign[ord(Data[67:68])-48] = str("OfflineO2")
            # For reference the next several bytes are: 68-70 (null), 71 (Start of Text),
            # 72 (Carrage Return), 73 (Line feed), 74-76 (null), 77 (<)
            # Checking that the header word is there and equal to 0x4D430000
            if ''.join('{:08b}'.format(ord(Data[i:i+1])) for i in range(StartByte,StartByte+4)) != \
               ''.join('{:08b}'.format(ord(x))       for x in '\x00\x00\x50\x4D'):
                   HeaderError = 'The MCS power frame header word does not match the expected value. ~RS'
                   print(HeaderError)
                   return([],[],[],[],[],[],HeaderError)
            # Pulling out the relative time counter
            RTime.append(ord(Data[StartByte+4:StartByte+5])+
                         ord(Data[StartByte+5:StartByte+6])*2**8+ 
                         ord(Data[StartByte+6:StartByte+7])*2**16)
            # byte (StartByte + 7) is empty
            # Looping over all the channels to pull out channel specific data
            for m in range(Channels):
                # Pre-allocating the power channel list, accumulation exponent
                # list and the demux select list
                if k == 0:
                    PowerCh.append([])
                    AccumExp.append([])
                    Demux.append([])
                # Pulling power channel data out of the file
                PowerCh[m].append(ord(Data[4*m+StartByte+8:4*m+StartByte+9]) + 
                                  ord(Data[4*m+StartByte+9:4*m+StartByte+10])*2**8 + 
                                  ord(Data[4*m+StartByte+10:4*m+StartByte+11])*2**16)
                # Pulling the accumulation exponent out of the file
                AccumExp[m].append(ord(Data[4*m+StartByte+11:4*m+StartByte+12])%2**4)
                # Pulling the demux selection out of the file
                Demux[m].append(ord(Data[4*m+StartByte+11:4*m+StartByte+12])/2**4)
            # Checking that the footer word is there and equal to 0xFFFFFFFF
            # For reference bytes 134-137 should be the footer word
            if ''.join('{:08b}'.format(ord(Data[4*m+StartByte+12+i:4*m+StartByte+13+i])) for i in range(0,4)) != \
               ''.join('{:08b}'.format(ord(x))                        for x in '\xFF\xFF\xFF\xFF'):
                   FooterError = 'The MCS power frame footer word does not match the expected value. ~RS'
                   print(FooterError)
                   return([],[],[],[],[],[],FooterError)
            # For reference the end of each measurement is as follows:
            # Bytes 138-140 (null), 141 (End of transmission), 142 (Carriage 
            # return), 143 (Line Feed), 144 (Carriage return), 145 (Line Feed)
    # Return the data arrays read from the file
    return(AccumExp,Demux,PowerCh,RTime,Timestamp,ChannelAssign,'')