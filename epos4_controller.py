#!/usr/bin/Python3
'''Encoding - UTF-8'''
'''@Author jmKuusinen'''

import time
import clr # pythonnet [pip install pythonnet]
import ctypes # module to open dll files
clr.AddReference('EposCmd.Net') # Net and dll files have to be in the working directory
EposCmd64 = ctypes.CDLL('.\EposCmd64.dll')
from EposCmd.Net.VcsWrapper import Device # Wrapper for C-lang commands
import tkinter as tk # Gui module
from tkinter import *
from tkinter import messagebox
from tkinter import simpledialog
import threading # Multithreading
from threading import Thread as Process
from queue import Queue # Messagehandling
import queue
from PIL import ImageTk, Image # For Canvas background 
import sys
Device.Init() # Init wrapper



class MAXON():
    def __init__(self, keyHandle, velocity, acceleration, deceleration, nodeID, baudrate, timewait, timeout, errorCode, duration, GetVelocityIsAveraged):
        self.velocity = velocity
        self.acceleration = acceleration
        self.deceleration = deceleration
        self.nodeID = nodeID
        self.baudrate = baudrate
        self.timewait = timewait
        self.timeout = timeout
        self.errorCode = errorCode
        self.keyHandle = keyHandle
        self.duration = duration
        self.GetVelocityIsAveraged = GetVelocityIsAveraged 

    def InitSystem(self): # Establish connection with Epos4
        ''' DEFAULT VALUES '''
        # nodeID = 1
        # baudrate = 1000000
        # timeout = 500
        # errorCode = 0
        # timewait = 2000 # Max time to reach position
        self.keyHandle, error = Device.VcsOpenDevice('EPOS4', 'MAXON SERIAL V2', 'USB', 'USB0', self.errorCode) # open EPOS4
        Device.VcsSetProtocolStackSettings(self.keyHandle, self.baudrate, self.timeout, self.errorCode) # set baudrate
        Device.VcsClearFault(self.keyHandle, self.nodeID, self.errorCode) # clear all faults
        Device.VcsSetVelocityProfile(self.keyHandle, self.nodeID, self.acceleration, self.deceleration, self.errorCode) # set profile parameters
        Device.VcsSetMaxProfileVelocity(self.keyHandle, self.nodeID, self.velocity, self.errorCode) # set max velocity parameter
        Device.VcsSetMaxAcceleration(self.keyHandle, self.nodeID, self.acceleration, self.errorCode) # set max acceleration // non zero if succesful - otherwise '0'
        Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode) # init velocitychecker
        Device.VcsSetEnableState(self.keyHandle, self.nodeID, self.errorCode) # enable device        
            
        
    
    def Move(self): # Function for maxon motor velocity control
        

        running = True
        runTime = self.duration # Define running time from user input
        counter = 0
        safeLimit = 400 # [rpm] If velocity drops below this limit, motor will shut down

        ''' We are using two separate while-loops here,
        because motor needs time to reach set speed whilst keeping eye on stalling '''
        
        
        while running:
            Device.VcsMoveWithVelocity(self.keyHandle, self.nodeID, self.velocity, self.errorCode) # starts moving
            client.queue.put("Motor spooling up..>>")
           
            Device.VcsWaitForTargetReached(self.keyHandle, self.nodeID, self.timewait, self.errorCode)
            start = time.time()
            client.queue.put("START")
            try:
                for i in range(1,70):
                    time.sleep(0.1)
                    # print(Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode)) # debug

                    if Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode) < (self.nodeID, safeLimit, self.errorCode):
                        raise ValueError()

            except ValueError:
                client.queue.put("Stalling protection triggered! --- Shutting down")
                Device.VcsSetDisableState(self.keyHandle, self.nodeID, self.errorCode)
                running = False
                
            
                
                

            while counter < runTime: # Run as long as user defined
                try:
                    Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode)
                    client.queue.put("RPM: ", Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode))
                    rpm = str(Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode))
                    client.queue.put(rpm)
                    time.sleep(1)
                    counter += 1

                # Failsafe for the event when dut_motor stalls'

                    if Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode) < (self.nodeID, safeLimit, self.errorCode):
                        raise ValueError()

                except ValueError:
                    client.queue.put("Stalling protection triggered! --- Shutting down")
                    Device.VcsSetDisableState(self.keyHandle, self.nodeID, self.errorCode)
                    running = False
                    
            running = False
                
        Device.VcsMoveWithVelocity(self.keyHandle, self.nodeID, 0, self.errorCode) # Stop motor
        Device.VcsWaitForTargetReached(self.keyHandle, self.nodeID, self.timewait, self.errorCode) # Check that it has stopped

        end = time.time()
        sec =  int((end-start)%60)
        client.queue.put("Elapsed time [s]: ", sec)

    def torQ(self): # Function for torque control

        running = True
        runTime = self.duration # Define running time from user input
        torqPercentage = self.velocity # Local variable from velocity-input so we don't have to pass this as argument for every instance
        counter = 0
        CurrentMust = int((55.543 * torqPercentage + 1.5217)) # Linear regression equation of torque% vs amps
        safeLimit = -2500 # [rpm] If velocity drops below this limit, motor will shut down
        
        Device.VcsSetCurrentMust(self.keyHandle, self.nodeID, CurrentMust, self.errorCode) # set specified current value
        start = time.time()
        client.queue.put("START")
        client.queue.put("Applied torque [%]:", torqPercentage)

        while counter < runTime and running: # Run as long as user defined
            try:
                time.sleep(1)
                counter += 1

                # Failsafe for the event when dut_motor stalls'

                if Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode) > (self.nodeID, safeLimit, self.errorCode):
                    raise ValueError()

            except ValueError:
                client.queue.put("Stalling protection triggered! --- Shutting down")
                Device.VcsSetDisableState(self.keyHandle, self.nodeID, self.errorCode)
                running = False                
                 
        
                
        Device.VcsSetCurrentMust(self.keyHandle, self.nodeID, 0, self.errorCode) # Cut current

        end = time.time()
        sec =  int((end-start)%60)
        client.queue.put("Elapsed time [s]: ", sec)

    
    def testCycle(self, velocity): # Function for pre-defined test cycle [maxon]
        running = True
        n_cycles = 0 # number of cycles
        client.queue.put("START", "RPM: ", self.velocity)
        start = time.time()
        safeLimit = 200 # [rpm] If velocity drops below this limit, motor will shut down
        self.velocity = velocity # local variable for speed manipulation
        

 
           
        while n_cycles < 60 and running: # Defines how many cycles there are, eg. 60 = 6 cycles
            Device.VcsSetMaxProfileVelocity(self.keyHandle, self.nodeID, velocity, self.errorCode) # Sets max velocity limit
            Device.VcsMoveWithVelocity(self.keyHandle, self.nodeID, velocity, self.errorCode) # starts moving
            Device.VcsWaitForTargetReached(self.keyHandle, self.nodeID, self.timewait, self.errorCode)
            try:
                for i in range(1,100):
                    time.sleep(0.1)

                    # Failsafe for the event when dut_motor stalls'

                    if Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode) < (self.nodeID, safeLimit, self.errorCode): # Failsafe for the event if dut_motor stalls
                        raise ValueError()

                if n_cycles % 10 == 0: # If n_cycles divided by 10 leaves no remainder
                    velocity = velocity + 250
                    client.queue.put("RPM raised to: ", velocity)

                n_cycles += 10
            except ValueError:
                client.queue.put("Stalling protection triggered! --- Shutting down")
                Device.VcsSetDisableState(self.keyHandle, self.nodeID, self.errorCode)
                running = False
               
                   
                

        Device.VcsMoveWithVelocity(self.keyHandle, self.nodeID, 0, self.errorCode) # Stop motor
        Device.VcsWaitForTargetReached(self.keyHandle, self.nodeID, self.timewait, self.errorCode) # Check that is has stopped

        end = time.time()
        
        sec =  int((end-start)%60)
        client.queue.put("Elapsed time [s]: ", sec)

    def closeDevice(self):
        Device.VcsSetDisableState(self.keyHandle, self.nodeID, self.errorCode) # Disable state
        Device.VcsCloseDevice(self.keyHandle, self.errorCode) # Disable connection
        Device.Cleanup() # Cleanup        

    # def getRpm(self): # For debug only
    #     n = 0
    #     while n < 30:
    #         client.queue.put("RPM: ", Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode))
    #         time.sleep(1)
    #         n += 1

    def TorqueCycle(self): # Function for pre-defined test cycle [maxon + dut_motor]
        running = True
        CurrentMust = 140 # mA
        n_cycles = 0
        torquePercentage = 2.5 # %
        safeLimit = -2500

        client.queue.put(Device.VcsGetCurrentMust(self.keyHandle, self.nodeID, CurrentMust, self.errorCode))
        Device.VcsSetCurrentMust(self.keyHandle, self.nodeID, CurrentMust, self.errorCode)
        start = time.time()
        client.queue.put("Starting torque [%]:", torquePercentage)
        time.sleep(2.5)
        client.queue.put("Starting current [mA]:", CurrentMust)
        while n_cycles < 200 and running: # Defines how many cycles there are, eg. 60 = 6 cycles
            Device.VcsSetCurrentMust(self.keyHandle, self.nodeID, CurrentMust, self.errorCode)
            try:
                for i in range(1,200):
                    time.sleep(0.1)

                    # Failsafe for the event when dut_motor stalls'

                    if Device.VcsGetVelocityIsAveraged(self.keyHandle, self.nodeID, self.GetVelocityIsAveraged, self.errorCode) > (self.nodeID, safeLimit, self.errorCode): # Failsafe for the event if dut_motor stalls
                        raise ValueError()

                if n_cycles % 10 == 0 and torquePercentage < 50: # If n_cycles divided by 10 leaves no remainder
                    CurrentMust = (55.543 * torquePercentage + 1.5217) # Linear regression equation of torque% vs amps
                    torquePercentage += 2.5
                    client.queue.put("Next torque level [%]: ", torquePercentage)
                    
            except ValueError:
                client.queue.put("Stalling protection triggered! --- Shutting down")
                Device.VcsSetDisableState(self.keyHandle, self.nodeID, self.errorCode)
                running = False
                
                

            n_cycles += 10
        Device.VcsSetCurrentMust(self.keyHandle, self.nodeID, 0, self.errorCode)

        end = time.time()
        sec =  int((end-start)%60)
        client.queue.put("Elapsed time [s]: ", sec)

class Gui:
    def __init__(self, master, Queue, endCommand):
        self.queue = Queue
        # Set up the GUI

        # Using canvas to get background pic
        self.myCanvas = Canvas(master, width = 600, height = 400)
        self.myCanvas.grid(sticky=N+S+E+W)
        self.myCanvas.create_image(0, 0, image = background, anchor = "nw")
        # self.v1 = DoubleVar() # For the slider widget      
        
        
        
        # *** BUTTONS ***

        self.maxonButton1 = Button(master, text = "Enable constant speed mode", command = self.maxonMoveHandler)
        self.maxonButton2 = tk.Button(master, text = "Start test cycle", state= tk.NORMAL, command = self.maxonHandler)
        self.dut_motorButton1 = tk.Button(master, text = "Start test cycle", state= tk.NORMAL, command = self.dut_motorHandler)
        self.dut_motorButton2 = Button(master, text = "Enable torque-control mode", command = self.dut_motorTorqHandler)
        self.quitButton = Button(master, text = "Exit", relief = "ridge", command = endCommand, padx = 8, pady = 2)
        

        # *** LABELS ***

        self.myCanvas.create_text(250,25, text="EPOS4 commander", font=("Intel Clear",22), anchor = "nw")
        self.myCanvas.create_text(50,125, text="Maxon motor only", font=("Intel Clear",16), anchor = "nw")
        self.myCanvas.create_text(400,125, text="Maxon + dut_motor", font=("Intel Clear", 16), anchor = "nw")
        # self.myCanvas.create_text(400,180, text = "Adjust torque %", font = ("Intel Clear", 10), anchor = "nw") // Maybe on next revision
       

        # *** Widgets ***

        # self.s1 = Scale(master, variable = self.v1, from_ = 0, to = 60, orient = HORIZONTAL) // Maybe on further revision


        # *** Put widgets and buttons on the screen ***
        
        # self.myCanvas.create_window(400,215, anchor = "nw", window = self.s1) // Maybe on further revision
        self.myCanvas.create_window(50,175, anchor = "nw", window = self.maxonButton1)
        self.myCanvas.create_window(50,295, anchor = "nw", window = self.maxonButton2)
        self.myCanvas.create_window(400,295, anchor = "nw", window = self.dut_motorButton1)
        self.myCanvas.create_window(400,175, anchor = "nw", window = self.dut_motorButton2)
        self.myCanvas.create_window(50,350, anchor = "nw", window = self.quitButton)

    def processIncoming(self):
        '''Handle all messages currently in the queue'''
        infoScreen = self.myCanvas.create_text(100,100, text = "", anchor = "nw", tags = 'label') # Init infoscreen
        while self.queue.qsize():
            try:
                msg = self.queue.get(0) # Check waiting messages
                self.myCanvas.delete('label') # Delete previous text to avoid overlapping since this is a canvas 
                infoScreen = self.myCanvas.create_text(75,75, text = msg,  font=("Intel Clear",16), anchor = "nw", tags = 'label') # Update Gui display
                

            except queue.Empty:
                # just on general principles, although we don't
                # expect this branch to be taken in this case
                pass
            except AttributeError:
                pass

    def maxonHandler(self): # Function handles button interface and starts a new thread when called

        if self.maxonButton2['text'] == 'Start test cycle':
            self.maxonButton2['state'] = tk.DISABLED
            self.maxonButton2["text"] = 'Cycle in progress'
            self.dut_motorButton1["text"] = 'Cycle in progress'
            self.dut_motorButton1.config(state = tk.DISABLED)

            Process(target= client.workerThread3).start() # Spawn new thread

        else:
            self.maxonButton2.config(state = tk.NORMAL)
            self.maxonButton2['text'] = 'Start test cycle'
            self.dut_motorButton1["text"] = 'Start test cycle'
            self.dut_motorButton1.config(state = tk.NORMAL)

    def maxonMoveHandler(self): # Function handles button interface and starts a new thread when called

        if self.maxonButton1["text"] == 'Enable constant speed mode':
            self.maxonButton1["text"] = 'Disable constant speed mode'
            self.maxonButton1["relief"] = 'sunken'

            Process(target= client.workerThread1).start() # Spawn new thread

        else:
            self.maxonButton1["text"] = 'Enable constant speed mode'
            self.maxonButton1["relief"] = 'raised'
    
    def dut_motorHandler(self): # Function handles button interface and starts a new thread when called

        if self.dut_motorButton1['state'] == tk.NORMAL:
                self.dut_motorButton1["text"] = 'Cycle in progress'
                self.dut_motorButton1.config(state = tk.DISABLED)
                self.maxonButton2["text"] = 'Cycle in progress'
                self.maxonButton2.config(state = tk.DISABLED)

                Process(target= client.workerThread4).start() # Spawn new thread
        else:

            self.dut_motorButton1["text"] = 'Start test cycle'
            self.dut_motorButton1.config(state = tk.NORMAL)
            self.maxonButton2["text"] = 'Start test cycle'
            self.maxonButton2.config(state = tk.NORMAL)
    
    def dut_motorTorqHandler(self): # Function handles button interface and starts a new thread when called

        if self.dut_motorButton2["text"] == 'Enable torque-control mode':
            self.dut_motorButton2["text"] = 'Disable torque-control mode'
            self.dut_motorButton2["relief"] = 'sunken'

            Process(target= client.workerThread2).start() # Spawn new thread

        else:
            self.dut_motorButton2["text"] = 'Enable torque-control mode'
            self.dut_motorButton2["relief"] = 'raised'
            



class ThreadedClient(Gui):
    '''
    Launch the main part of the GUI and the worker thread. periodicCall and
    endApplication could reside in the GUI part, but putting them here
    means that you have all the thread controls in a same place.
    '''
    def __init__(self, master):
       
        
        '''
        Start the GUI and the asynchronous threads. This is the main 
        thread of the application, which will later be used by
        the GUI as well. We spawn a new thread for the workers (I/O).
        '''
        self.master = master

        # Create the queue
        self.queue = Queue()

        # Set up the GUI part
        self.gui = Gui(master, self.queue, self.endApplication)
        
        # Set up the thread to do asynchronous I/O
        # More threads can also be created and used, if necessary
        self.running = 1
        self.thread1 = threading.Thread(target= self.workerThread1) #TODO: Check if these are needed
        self.thread2 = threading.Thread(target= self.workerThread2)
        self.thread3 = threading.Thread(target= self.workerThread3)
        self.thread4 = threading.Thread(target= self.workerThread4)

        

        # Start the periodic call in the GUI to check if the queue contains
        # anything
        self.periodicCall()

    def periodicCall(self):
        '''
        Check every 200 ms if there is something new in the queue.
        '''
        self.gui.processIncoming()
        if not self.running:
            # This is the brutal stop of the system.
            # Maybe some cleanup before actually shutting it down.
            Motor = MAXON(0, 0, 500, 500, 1, 1000000, 10000, 500, 1, 0, 0)
            Motor.InitSystem() # Required for keyhandle
            Motor.closeDevice() # Disable connection & clean
            sys.exit(1)
        self.master.after(200, self.periodicCall)

    def workerThread1(self): # Thread for MAXON - Move with constant speed

        newWin = Tk() # New Temporary parent // simpledialog throws error w/o this because of threading
        newWin.withdraw() # Make it invisible

        
        try:
            target = simpledialog.askinteger(title = "Define parameters", prompt = "Please enter desired speed [rpm]", parent = newWin)
            duration = simpledialog.askinteger(title = "Define parameters", prompt = "Please enter desired duration [s]", parent = newWin)
            if target > 6000 or target < 400:
                    raise ValueError()                                
            if duration > 500 or target < 5:
                    raise ValueError()
            Motor = MAXON(0, target, 500, 500, 1, 1000000, 3000, 500, 1, duration, 0)
            Motor.InitSystem()
            Motor.Move()
        except ValueError:
            messagebox.showwarning("ValueError", "Please enter a valid value. Range: 400-6000 [rpm] or 5-500 [s]")
        except TypeError:
            pass # Pressing 'cancel' on dialogbox raises this for unknown reasons
 

        newWin.destroy() # Destroy temporary parent
        self.gui.maxonMoveHandler() # Return to update GUI

    def workerThread2(self): # Thread for dut_motor - Torque control mode

        newWin = Tk() # New Temporary parent // simpledialog throws error w/o this because of threading
        newWin.withdraw() # Make it invisible            

        try:
                target = simpledialog.askinteger(title = "Define parameters", prompt = "Please enter desired torque [%]", parent = newWin)
                duration = simpledialog.askinteger(title = "Define parameters", prompt = "Please enter desired duration [s]", parent = newWin)
                if target > 60 or target < 0:
                        raise ValueError()                                
                if duration > 500 or target < 5:
                        raise ValueError()
                Motor = MAXON(0, target, 500,500, 1, 1000000, 3000, 500, 1, duration, 0)
                Motor.InitSystem()
                Motor.torQ()
        except ValueError:
            messagebox.showwarning("ValueError", "Please enter a valid value. Range: 0-60 [%] or 5-500 [s]")
        except TypeError:
            pass # Pressing 'cancel' on dialogbox raises this for unknown reasons

        newWin.destroy() # Destroy temporary parent
        self.gui.dut_motorTorqHandler() # Return to update GUI                           



    def workerThread3(self): # Thread for test cycle maxon


        Motor = MAXON(0, 1500, 500,500, 1, 1000000, 3000, 500, 1, 1, 0)
        Motor.InitSystem()
        Motor.testCycle(1500)
        Motor.closeDevice()
        self.gui.maxonHandler() # Return to update GUI


    def workerThread4(self): # Thread for test cycle maxon + dut_motor

        Motor = MAXON(0, 1500, 500,500, 1, 1000000, 3000, 500, 1, 1, 0)
        Motor.InitSystem()
        Motor.TorqueCycle()
        Motor.closeDevice()

        self.gui.dut_motorHandler() # Return to update GUI




    def endApplication(self):
        self.running = 0



if __name__ == "__main__":
    root = tk.Tk()
    background = PhotoImage(file='‪C:/Users/J/Pictures/bc_epos4.jpg') # Insert a background photo of your choice here
    client = ThreadedClient(root)
    root.mainloop()
