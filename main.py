# -*- coding: utf-8 -*-
"""
Created on Sun Jun  7 17:39:44 2020

@author: LattePanda
"""

# Globals
# Constants
_sdp_ip_address = b"192.168.11.1"
_sdp_port = 1445
_execute = True# False for debugging, must be True to run as: >python Hoot.py
_run_flag = True # setting this to false kills all threads for shut down
_eyes_flag = False # should eyes be displayed or not
_person = "Jim"
_new_person_flag = False
_people = {"Evi":5, "Jim":8, "stranger":1, "nobody":0}
_mood = "happy"
_moods = {"happy":50, "bored":20, "hungry":10}
_place = "office"
_places = ["kitchen", "living room", "dining area", "office", "front door"]
_locations = { "kitchen" : (9.157, -3.269), "living room" : (0.061, -3.775), 
              "dining area" : (3.329, -2.849),  "office" : (0,0), "front door": (0,0),
              "test" : (-1, 0)}
_goal = ""
_time = "morning"
_times = ["morning", "noon", "afternoon", "evening", "night"]
_phrase = "" # set by whatever speech recognition heard
_last_phrase = "nothing"
_listen_flag = True
_action = "" # this will be set to whatever specific action is being attempted
_action_flag = False # True means some action is in progress
_request = "" # comes from someone telling the robot to do something
_thought = "" # comes from the robot thinking that it wants to do something
_do_something_flag = False
_main_battery_voltage = 100.0 # this gets reset immediately
_motion_flag = False  # set by monitor_motion thread, looking for humans in motion
_robot_is_moving = False # set by robotMotion thread: True when robot is in motion
_last_motion_time = 0 # the time.time() motion was last detected
_ser6 = ""
_internet = False # True when connected to the internet


import tts.sapi
import time
from ctypes import *
import os
import sys
import threading
from threading import Thread
#from playsound import playsound
from word2number import w2n
import math
from enum import Enum

###############################################################
# Text input to Google Assistant for web based queries

import logging
import json
import click
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials

from google.assistant.embedded.v1alpha2 import (
    embedded_assistant_pb2,
    embedded_assistant_pb2_grpc
)


###############################################################
# Movement releated
    
class ActionStatus(Enum):
    def __init__(self, number):
        self._as_parameter__ = number
        
    # The action is created but not started
    WaitingForStart = 0
    # The action is running
    Running = 1
    # The action is finished successfully
    Finished = 2
    # The action is paused
    Paused = 3
    # The action is stopped
    Stopped = 4
    # The action is under error
    Error = 5        
        
def getMoveActionStatus():
    global _sdp
    status = _sdp.getMoveActionStatus()
    if status == ActionStatus.Finished.value:
        print("move action finished: ", _sdp.getMoveActionError())
    elif status == ActionStatus.Error.value:
        print("move action error: ", _sdp.getMoveActionError())
    elif status == ActionStatus.Stopped.value:
        print("action completed successfully")
    return status

################################################################
def turn(degrees):
    global _sdp, _action_flag, _action, _robot_is_moving
    _action_flag = True # The robot is being commanded to move
    _sdp.rotate(math.radians(degrees))

    result = _sdp.waitUntilMoveActionDone()
    if result == ActionStatus.Error.value or result == ActionStatus.Finished.value:
        print(slamtec.getMoveActionError())
        speak("Something is wrong. I could not turn.")
        
    _action_flag = False # the robot's done turning
    _action = ""

################################################################
# function to calculate the distance between 2 points (XA YA) and (XB YB)
def distance_A_to_B(XA, YA, XB, YB):
    dist = math.sqrt((XB - XA)**2 + (YB - YA)**2)
    return dist


#x == _sdp.getX() and
#y == _sdp.getY()
################################################################

def nearest_location(x, y):
    global _locations
    
    location = ""
    distance = 1000000
    for loc, coord in _locations.items():
        dist = distance_A_to_B(x, y, coord[0], coord[1])
        if ( dist < distance):
            location = loc
            distance = dist
    return location, distance
 

################################################################
# if the robt is within half a meter of the goal, then success:
# return the closest location and the distance to it and if it is close enough
def where_am_i():
    global _sdp
    
    pose = _sdp.pose()
    location, distance = nearest_location(pose.x, pose.y)
    if (distance <= 500):
        closeEnough = True
    else:
        closeEnough = False
    return location, distance, closeEnough
    
################################################################
# This cancels an ongoing action - which may be a goto or something else.
def cancelAction():
    global _sdp, _action_flag, _action
    try:
        _sdp.cancelMoveAction()
        _action_flag = False
        _action = ""
    except:
        _action_flag = False
        _action = "" # may want to keep this to see what action got cancelled?
        print("An error occurred canceling the action.")
        return

def startrun():
    global _run_flag
    _run_flag = True

def stoprun():
    global _run_flag
    _run_flag = False    
    
def testgoto(str):
    global _goal
    _goal = str
    
################################################################
# This is where goto actions are initiated and get carried out.
# If the robot is in the process of going to a  location, but
# another goto action request is receved, the second request will
# replace the earlier request
def handleGotoLocation():
    global _place, _run_flag, _goal, _place, _action_flag, _sdp
    while _run_flag:
        if _goal == "" or _action_flag: # no goal or some action is currently in progress, so sleep.
            time.sleep(0.5)
            continue
            
        print("I'm free and A new goal arrived: ", _goal)
        coords = _locations.get(_goal);
        if coords == None:
            speak("Sorry, I don't know how to get there.")
            print("unknown location")
            _goal = ""
            continue
        if _goal == _place:
            speak("I'm already at the " + _goal)
            _goal = ""
            continue
        _action_flag = True
        speak("I'm going to the " + _goal)
        _sdp.moveToFloat(coords[0], coords[1])
    
        while(1):
            maStatus = getMoveActionStatus()
            if maStatus == ActionStatus.Stopped.value or maStatus == ActionStatus.Error.value or maStatus == ActionStatus.Finished.value:
                break;
            
        # reaching this point, the robot first moved, then stopped - so check where it is now
        location, distance, closeEnough = where_am_i()
                                          
        # and now check to see if it reached the goal
        if (location == _goal and closeEnough):
            speak("I've arrived!")
            _place = location
            _goal = "" # reset _goal
        else:
            speak("I didn't make it to my goal. I blame my programming.")
            _place = lost
            _goal = "" # reset _goal ????
        
        # finally clear the _action and _action_flag
        _action_flag = False # you've arrived somewhere, so no further action
        _action = ""            
        time.sleep(0.5)
        
################################################################
# Pretty print all currently active robot threads
def pretty_print_threads():
    i = 1
    for item in threading.enumerate():
        print(i,":",item)
        i += 1

################################################################
#ts = time.localtime()
#print(time.strftime("%H", ts)) # a 24 hour clock hour only
# This runs in it's own thread updating the time every ten seconds
def time_update():
    global _run_flag, _time
    while _run_flag:
        hour = int(time.strftime("%H", time.localtime()))
        if hour >= 6 and hour < 12:
            _time = "morning"
        elif hour == 12:
            _time = "noon"
        elif hour > 12 and hour < 17:
            _time = "afternoon"
        elif hour >= 17 and hour < 23:
            _time = "evening"
        else:
            _time = "night"
        time.sleep(10)

###############################################################
# Speech Related
            
def speak(phrase):
    global _last_phrase, voice

    voice = tts.sapi.Sapi()
    print(phrase)
    #voice.set_voice("Andy")
    voice.voice.Volume = 80
    voice.voice.SynchronousSpeakTimeout = 1 # timeout in milliseconds

    try:
        voice.say(phrase)
    except Exception:
        print("Speak has timed out.")
        pass

    if phrase != "I said":
        _last_phrase = phrase

###############################################################
# Miscellaneous

def statusReport():
    global _place, _person, _main_battery_voltage, _mood, _sdp
    
    speak("This is my current status.")
    if _place == "lost":
        answer = "Unfortunately I'm currently lost."
        speak(answer)
    else:
        answer = "I'm at the " + _place + " location."
        speak(answer)
        answer = "I'm with " + _person
        speak(answer)
    answer = "Battery is at "
    answer = answer + str(_sdp.battery()) + " percent"
    speak(answer)
    if _place != "lost":
        answer = "And I'm feeling " + _mood
        speak(answer)
    time.sleep(5)

###############################################################
# Speech recognition using Google over internet connection
def listen():
    import speech_recognition as sr
    global _run_flag, _listen_flag, _phrase, _last_phrase, _motion_flag
    global _thought, _person, _new_person_flag, _place, _mood, _time
    global _request, _action, _internet, _action_flag, _main_battery_voltage
    global _eyes_flag
    
    ###########################################################
    # Text input to Google Assistant for web based queries
    ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
    DEFAULT_GRPC_DEADLINE = 60 * 3 + 5
    PLAYING = embedded_assistant_pb2.ScreenOutConfig.PLAYING

    api_endpoint = ASSISTANT_API_ENDPOINT
    credentials = os.path.join(click.get_app_dir('google-oauthlib-tool'), 'credentials.json')
    device_model_id = "orbital-clarity-197305-marvin-hcmekv"
    device_id = "orbital-clarity-197305"
    lang = 'en-US'
    display = False
    verbose = False
    grpc_deadline = DEFAULT_GRPC_DEADLINE
    
    class TextAssistant(object):
        """Text Assistant that supports text based conversations.
        Args:
          language_code: language for the conversation.
          device_model_id: identifier of the device model.
          device_id: identifier of the registered device instance.
          display: enable visual display of assistant response.
          channel: authorized gRPC channel for connection to the
            Google Assistant API.
          deadline_sec: gRPC deadline in seconds for Google Assistant API call.
        """
        
        def __init__(self, language_code, device_model_id, device_id,
                     display, channel, deadline_sec):
            self.language_code = language_code
            self.device_model_id = device_model_id
            self.device_id = device_id
            self.conversation_state = None
            # Force reset of first conversation.
            self.is_new_conversation = True
            self.display = display
            self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(channel)
            self.deadline = deadline_sec
        
        def __enter__(self):
            return self
        
        def __exit__(self, etype, e, traceback):
            if e:
                return False
        
        def assist(self, text_query):
            """Send a text request to the Assistant and playback the response.
            """
            def iter_assist_requests():
                config = embedded_assistant_pb2.AssistConfig(
                    audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                        encoding='LINEAR16',
                        sample_rate_hertz=16000,
                        volume_percentage=0,
                    ),
                    dialog_state_in=embedded_assistant_pb2.DialogStateIn(
                        language_code=self.language_code,
                        conversation_state=self.conversation_state,
                        is_new_conversation=self.is_new_conversation,
                    ),
                    device_config=embedded_assistant_pb2.DeviceConfig(
                        device_id=self.device_id,
                        device_model_id=self.device_model_id,
                    ),
                    text_query=text_query,
                )
                # Continue current conversation with later requests.
                self.is_new_conversation = False
                if self.display:
                    config.screen_out_config.screen_mode = PLAYING
                req = embedded_assistant_pb2.AssistRequest(config=config)
                #assistant_helpers.log_assist_request_without_audio(req)
                yield req

            text_response = None
            html_response = None
            
            for resp in self.assistant.Assist(iter_assist_requests(),
                                              self.deadline):
                #assistant_helpers.log_assist_response_without_audio(resp)
                if resp.screen_out.data:
                    html_response = resp.screen_out.data
                if resp.dialog_state_out.conversation_state:
                    conversation_state = resp.dialog_state_out.conversation_state
                    self.conversation_state = conversation_state
                if resp.dialog_state_out.supplemental_display_text:
                    text_response = resp.dialog_state_out.supplemental_display_text
            return text_response, html_response
    
    
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    
    # Load OAuth 2.0 credentials.
    try:
        with open(credentials, 'r') as f:
            credentials = google.oauth2.credentials.Credentials(token=None, **json.load(f))
            http_request = google.auth.transport.requests.Request()
            credentials.refresh(http_request)
    except Exception as e:
        logging.error('Error loading credentials: %s', e)
        logging.error('Run google-oauthlib-tool to initialize '
                      'new OAuth 2.0 credentials.')
    
    # Create an authorized gRPC channel.
    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(credentials, http_request, api_endpoint)
    speak("I'm connected to Google Assistant.")
    #logging.info('Connecting to %s', api_endpoint)

    # create a recognizer object
    r = sr.Recognizer()
    
    speak("Okay, I'm ready!")
    
    while _run_flag:
        # obtain audio from the microphone
        try:
            with sr.Microphone() as source:
                # adjust microphone for ambient noise:
                # first, turn off dynamic thresholding,
                # eg: r.adjust_for_ambient_noise(source)
                # then, set a volume threshold at 500 where
                # 0 = it hears everything. 4000 = it hears nothing.
                r.dynamic_energy_threshold = False
                r.energy_threshold = 500
                print("Say something!")
                audio = r.listen(source)
        except:
            continue
        
        # recognize speech using Google Speech Recognition
        try:
            _phrase = r.recognize_google(audio)
            _internet = True
            print("I heard: " + _phrase)
        except sr.UnknownValueError:
            _phrase = ""
            _internet = True
            print("What?")
            continue
        except sr.RequestError:
            _phrase = ""
            _internet = False
            print("I lost my internet connection.")
            #if _place == "office":
            #    continue
            #_thought = "go to the office"
            #time.sleep(1.0)
            continue
        except:
            print("Unknown speech recognition error.")
            continue
        
        # some verbal commands are handled inside the listen thread

        if (_phrase == "resume listening" or
            _phrase == "start listening" or
            _phrase == "start listening again"):
            _listen_flag = True
            speak("Okay, I'm listening.")
            continue
        
        if _listen_flag == False:
            continue
        
        if (_phrase == "pause listening" or
            _phrase == "stop listening"):
            _listen_flag = False
            print("Okay, pause listening.")
            continue
        
        if (_phrase == "what" or
            _phrase == "what did you say" or
            _phrase == "please repeat what you just said"):
            speak("I said")
            speak(_last_phrase)
            continue
        
        if (_phrase == "what's your name" or
            _phrase == "what is your name" or
            _phrase == "who are you"):
            speak("My name is Big Orange. Easy to remember, right?")
            continue
        
        if _phrase == "this is Evi":
            if _person != "Evi":
                _new_person_flag = True
            _person = "Evi"
            continue
        
        if _phrase == "this is Jim":
            if _person != "Jim":
                _new_person_flag = True
            _person = "Jim"
            continue

        if _phrase == "goodbye":
            answer = "See you later, " + _person
            speak(answer)
            if _person != "nobody":
                _new_person_flag = True
            _person = "nobody"
            continue

        if _phrase == "who are you with":
            answer = "I'm with " + _person
            speak(answer)
            continue

        if (_phrase == "how are you" or
            _phrase == "how are you feeling"):
            answer = "I'm feeling " + _mood
            speak(answer)
            continue
        
        if _phrase == "where are you":
            if _place == "lost":
                answer = "I'm afraid that I'm lost."
                speak(answer)
                continue
            answer = "I'm at the " + _place + " location."
            speak(answer)
            continue
                    
        if _phrase == "what time is it":
            day = time.strftime("%A", time.localtime())
            month = time.strftime("%B", time.localtime())
            date = str(int(time.strftime("%d", time.localtime())))
            hour = str(int(time.strftime("%I", time.localtime())))
            minutes = time.strftime("%M", time.localtime())
            ampm = time.strftime("%p", time.localtime())
            if ampm == "AM":
                ampm = "a.m."
            else:
                ampm = "p.m."
            answer = "It is " + day + " " + month + " " + date + " at " + hour + " " + minutes + " " + ampm
            speak(answer)
            answer = "It's " + _time + "."
            speak(answer)
            continue
        
        if "stop" in _phrase:
            cancelAction()
            speak("Okay.")
            location, distance = where_am_i() # sets _place to either:
                                              # the closest landmark if < 500mm away
                                              # or "lost"
            if location == "lost":
                speak("I'm lost. What should I do now? ")
            else:
                ans = "I am now near the " + location + " location."
                speak(ans)
                speak("What should I do now?")
            continue
        
        if "status" in _phrase:
            statusReport()
            continue
                            
        if _phrase == "go to the kitchen": # this is an example of a request
            _goal = "kitchen"
            continue
        
        if _phrase == "go to the office":
            _goal = "office"
            continue
                        
        if _phrase == "go to the front door": 
            _goal = "front door"
            continue

        if _phrase == "go to the living room": 
            _goal = "living room"
            continue
        
        if _phrase == "go to the dining area": 
            _goal = "dining area"
            continue
                
        if _phrase == "list your threads":
            print()
            pretty_print_threads()
            print()
            continue
        
        # if _phrase == "open your eyes":
        #     if _eyes_flag == True:
        #         continue
        #     _eyes_flag = True
        #     Thread(target = eyes, name = "Display eyes").start()
        #     continue
        
        if _phrase == "close your eyes":
            _eyes_flag = False
            continue
        
        if (_phrase == "initiate shut down" or
            _phrase == "initiate shutdown" or
            _phrase == "begin shut down" or
            _phrase == "begin shutdown"):
            _eyes_flag = False
            speak("Okay, I'm shutting down.")
            #playsound("C:/Users/bjwei/wav/R2D2d.wav")
            # List all currently running threads
            print("\nClosing these active threads:")
            pretty_print_threads()
            # Have them terminate and close
            _run_flag = False
            continue        

        if "battery" in _phrase:
            ans = "My battery is currently at "
            ans = ans + str(_sdp.battery()) + " percent"
            speak(ans)
            continue
            
        if "motion" in _phrase:
            if _motion_flag:
                speak("I am detecting motion.")
            else:
                speak("I'm not detecting any motion.")
            continue
        
        temp = _phrase # special case requiring parsing
        temp = temp.replace('\xb0', ' degrees') # convert '90°' to '90 degrees'
        phrase_split = temp.split() # split string into individual words
        if (phrase_split != [] and phrase_split[0] == "turn"):
            try:
                deg = int(w2n.word_to_num(phrase_split[1]))
            except:
                None
            if phrase_split[2] == "clockwise":
                deg = -deg
            turn(deg)
            continue
        
        with TextAssistant(lang, device_model_id, device_id, display,
                     grpc_channel, grpc_deadline) as assistant:
            response_text, response_html = assistant.assist(text_query = _phrase)
            if response_text:
                speak(response_text)
            continue    

################################################################   
# This is where data gets initialized from information stored on disk
# and threads get started
def initialize_robot():
    global _moods, _people, _ser6, _internet, _eyes_flag
    
    # speak("Initializing data from memory.")
    
    # with open('moods_data_file') as json_file:  
    #     _moods = json.load(json_file)

    # with open('people_data_file') as json_file:  
    #     _people = json.load(json_file)
        
    # _ser6 = serial.Serial('COM6', 9600, timeout=1.0)
    
    _internet = True
    
    
    Thread(target = listen, name = "Listen").start()
    
    Thread(target = time_update, name = "Time").start()
    
#    Thread(target = monitor_battery, name = "Battery Monitor").start()
    
#    Thread(target = monitor_motion, name = "People Motion Monitor").start()
    
#    Thread(target = behaviors, name = "Behaviors").start()
    
    Thread(target = handleGotoLocation, name = "Handle Goto Location").start()
#    Thread(target = actions, name = "Actions").start()
    
#    Thread(target = robotMoving, name = "Is Robot Moving").start()
    
#    Thread(target = megaCOM7, name = "megaCOM7").start()
    
    _eyes_flag = True # this is needed to start the display and to keep it open
#    Thread(target = eyes, name = "Display eyes").start()
    
    #Thread(target = display, name = "Display").start()

    
################################################################
# This is where data gets saved to disk
# and by setting _run_flag to False, threads are told to terminate
def shutdown_robot():
    global _run_flag, _moods, _people, _ser6, _sdp
    
    # # Save "memories" to disk    
    # with open('moods_data_file', 'w') as outfile:  
    #     json.dump(_moods, outfile)
    
    # with open('people_data_file', 'w') as outfile:  
    #     json.dump(_people, outfile)
    
    _run_flag = False
    
    # TBD join threads
    
    # Close all open threads
    #while (threading.active_count() > 1):
    #    print("\nClosing... ")
    #    pretty_print_threads()
    #    time.sleep(1)

    # Close the serial port
#    _ser6.close()
   
#    playsound("C:/Users/bjwei/wav/R2D2.wav")
    _sdp.disconnect()
    del _sdp
    print("\nDone!")

   
################################################################
# This initializes and runs the robot
def robot():
    global _run_flag, _ser6
    
    initialize_robot()
    
    while _run_flag:
        time.sleep(1)
    
    shutdown_robot()

def con2sdp():
    errStr = create_string_buffer(255)
    res = _sdp.connectSlamtec(_sdp_ip_address, _sdp_port, errStr, 255);
    if res == 1 :
        print("Could not connect to SlamTec, time out: ", errStr.value)
    elif res == 2:
        print("Could not connect to SlamTec, connection fail: ", errStr.value)

        
if __name__ == '__main__':
    global _sdp
    # Load SlamtecDLL
    DllsPath = os.getcwd() + r"\..\DLLs\\"
    
    cdll.LoadLibrary(DllsPath + "libeay32.dll")
    cdll.LoadLibrary(DllsPath + "ssleay32.dll")
    
    _sdp = cdll.LoadLibrary(DllsPath + "SlamtecDll.dll")
    
    # Set up C function input and output types
    _sdp.connectSlamtec.argtypes = c_char_p, c_int, c_char_p
    _sdp.slamtecLocation.restype = c_char_p
    
    _sdp.loadSlamtecMap.argtypes = c_char_p,
    _sdp.loadSlamtecMap.restype = c_int
    
    _sdp.moveToFloat.argtypes = c_float, c_float
    _sdp.moveToFloat.restype = None
    _sdp.home.restype = None
    _sdp.disconnect.restype = None
    _sdp.getMoveActionStatus.restype = c_int
    _sdp.rotate.argtypes = c_float,
    
    class POSE(Structure):
        _fields_ = [("x", c_float),
                    ("y", c_float),
                    ("yaw", c_float)]
    
    _sdp.pose.restype = POSE
    
    if _execute:
        speak("Initializing robot.")
    
        res = connectToSlamtec()
        
        if (res == 0) :
            speak("I'm now connected to Slamtec.")
            print("Loading map")
            res = _sdp.loadSlamtecMap(b'HCR-MyHouse.stcm')
            print("Done loading map")
            if (res == 0) :
                speak("I've loaded the map.");
            else:
                speak("Something is wrong. I could not load the map.")
            
        else:
            speak("Something is wrong. I could not connect to Slamtec.")
        robot()
    else:
        print("Program is in DEBUG mode.")
