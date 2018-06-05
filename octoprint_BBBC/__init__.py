# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import logging
import time
import os
import sys
import time
import thread
from threading import Thread

import octoprint.plugin
import octoprint.settings
from octoprint.util import RepeatedTimer
#from octoprint.server import user_permission
#from flask import make_response
#from octoprint.printer import PrinterInterface



import Adafruit_BBIO.PWM as BPWM
import Adafruit_BBIO.ADC as BADC

class BBBC(octoprint.plugin.SettingsPlugin,
                 octoprint.plugin.AssetPlugin,
                 octoprint.plugin.TemplatePlugin,
                 #octoprint.plugin.ProgressPlugin,
                 octoprint.plugin.StartupPlugin,
                 octoprint.plugin.SimpleApiPlugin):

    def __init__(self):
        self.table_100k=[[23,300], [25,295], [27,290], [28,285], [31,280], [33,275], [35,270], [38,265], [41,260], [44,255], [48,250], [52,245], [56,240], [61,235], [66,230], [71,225], [78,220], [84,215], [92,210], [100,205], [109,200], [120,195], [131,190], [143,185], [156,180], [171,175], [187,170], [205,165], [224,160], [245,155], [268,150], [293,145], [320,140], [348,135], [379,130], [411,125], [445,120], [480,115], [516,110], [553,105], [591,100], [628,95], [665,90], [702,85], [737,80], [770,75], [801,70], [830,65], [857,60], [881,55], [903,50], [922,45], [939,40], [954,35], [966,30], [977,25], [985,20], [993,15], [999,10], [1004,5], [1008,0], [1012,-5], [1016,-10], [1020,-15]]
        #self.table_100k=[23, 25, 27, 28, 31, 33, 35, 38, 41, 44, 48, 52, 56, 61, 66, 71, 78, 84, 92, 100, 109, 120, 131, 143, 156, 171, 187, 205, 224, 245, 268, 293, 320, 348, 379, 411, 445, 480, 516, 553, 591, 628, 665, 702, 737, 770, 801, 830, 857, 881, 903, 922, 939, 954, 966, 977, 985, 993, 999, 1004, 1008, 1012, 1016, 1020]
        self.table_10k=[[1,430],[54,137],[107,107],[160,91],[213,80],[266,71],[319,64],[372,57],[425,51],[478,46],[531,41],[584,35],[637,30],[690,25],[743,20],[796,14],[849,7],[902,0],[955,-11],[1008,-35]]

        self.fan_definitions = {}
        self.temps=[]
        self._checkTemp = None
        self._autoPWM = None
        
  
    def get_settings_defaults(self):
        return dict(
            fan_definitions = [],
            temps=[],
            ProcessTimer = 2,
            DefaultDuty = 60,
            MinTemp = 30,
            MaxTemp = 50,
            C_factor = 2,
            PPC = 2,
            PWM1=0,
            PWM2=0,
            PWM3=0
        )
        
    def on_after_startup(self):
        self._mylogger("---------------------------Starting BBBPlugin---------------------------", forceinfo=True)
	self._init_BBB()   
        self.initialize_all()
 
        
    def on_settings_initialized(self):
        self.reload_fan_definitions()


    def _cal_temp(self, val, temp_type):
        table = []
        if temp_type == '1' : table = self.table_100k
        elif temp_type == '4': table = self.table_10k

        for i in range(len(table)):
            if(val < table[i][0]): break
        if val == table[i-1][0]:
            temp = table[i-1][1]
        else:
            offset = (table[i][0] - val)*(table[i-1][1] - table[i][1])*1.0 / (table[i][0] - table[i-1][0])
            temp = table[i][1] + offset
        return temp 

    def _cal_temp2(self, val, temp_type):
        table = []
        if tempy_type == 1 : table = self.table_100k
        elif temp_type == 4: table = self.table_10k
        for i in range(len(self.table_100k)):
            if(val < self.table_100k[i]): break
        if val == self.table_100k[i-1]:
            temp = 300 - (i-1)*5
        else:
            offset = 5 - (self.table_100k[i] - val)*5. / (self.table_100k[i] - self.table_100k[i-1])*1.
            temp = 300 - (i*5) + 5 - offset
        return temp

    def _get_temp(self):
        temps=[]
        for j in range(len(self.fan_definitions)):  
            if self.fan_definitions[j]['has_temp'] == False :
                temps.append('undefined')
            else :
                value = BADC.read_raw(self.fan_definitions[j]['temp_pin'])*1.0/4
                temps.append(round(self._cal_temp(value, self.fan_definitions[j]['temp_type']),1))
                #tempp.append(value)
        return temps

    def _init_BBB(self):
        self._mylogger("---------------------------Initializing BBB Hardware---------------------------", forceinfo=True)
        BADC.setup()
        duty = self._settings.getInt(['DefaultDuty'])
        for j in range(len(self.fan_definitions)):
            if self.fan_definitions[j]['fan_pin'] == 'None' : continue
            else: BPWM.start(self.fan_definitions[j]['fan_pin'], self._settings.getInt(['DefaultDuty']), 22000, 0)
            #self._mylogger("started pwm pin %s" %self.fan_definitions[j]['fan_pin'], forceinfo=True)

    def _resetting_fans_BBB(self):
        BPWM.cleanup()
        for j in range(len(self.fan_definitions)):
            if self.fan_definitions[j]['fan_pin'] == 'None' : continue
            else: BPWM.start(self.fan_definitions[j]['fan_pin'], self.fan_definitions[j]['PWM'], 22000, 0)

    def on_settings_save(self, data):
        self._checkTemp.cancel()
        self._autoPWM.cancel()
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.reload_fan_definitions()
	self._resetting_fans_BBB()
        self.initialize_all()

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True),
            dict(type='tab', custom_bindings=True, template='BBBC_tab.jinja2', name='BBB Fan&Temp'),
            dict(type='tab', custom_bindings=True, template='filemanager_tab.jinja2', name='BBB SDCard', div='tab_plugin_filemanager')
        ]

    def get_assets(self):
        return dict(
            js=["js/BBBC.js", "js/filemanager.js"],
            css=["css/BBBC.css", "css/fileManager-generated.min.css"],
            less=["less/fileManager.less"]
        )      

    def _mylogger(self,message, forceinfo=False):			# this is to be able to change the logging without a large change

        if self._settings is not None:
            if self._settings.get_boolean(['debuglogging']) or forceinfo:
                self._logger.info(message)
            else:
                self._logger.debug(message)
        else:
            print(message) 

    @staticmethod
    def _settimer(timervar, timeval, methodcall):
        worktimer = None

        if timervar is not None:
            timervar.cancel()

        worktimer = RepeatedTimer(timeval, methodcall, None, None, True)
        worktimer.start()

        return worktimer               
        
    def initialize_all(self):
        processtimer = self._settings.get_float(['ProcessTimer'])
        ppc = self._settings.get_float(['PPC'])
		#self.initialize_fan()
		#self.initialize_epo()
        self._checkTemp = BBBC._settimer(self._checkTemp, processtimer, self.check_temp)
        self._autoPWM = BBBC._settimer(self._autoPWM, ppc, self.auto_pwm)

    def auto_pwm(self):
        self._mylogger("BBBC auto_pwm called")
        dutys=[]
        for j in range(len(self.fan_definitions)):
            if self.fan_definitions[j]['fan_pin'] != 'None' and self.fan_definitions[j]['manual_fan'] == False and self.fan_definitions[j]['has_temp'] == True :
                value = BADC.read_raw(self.fan_definitions[j]['temp_pin'])*1.0/4
                temp = round(self._cal_temp(value, self.fan_definitions[j]['temp_type']),1)
                if  self._settings.get_float(['MinTemp']) < temp and temp <= self._settings.get_float(['MaxTemp']):
                    duty = int(self._settings.get_float(['C_factor']) * temp)
                    if duty > 100 : duty = 100
                    dutys.append([j,duty])
                    BPWM.set_duty_cycle(self.fan_definitions[j]['fan_pin'], duty)
                elif temp <=  self._settings.get_float(['MinTemp']):
                    dutys.append([j,0])
                    BPWM.set_duty_cycle(self.fan_definitions[j]['fan_pin'], 0)
                elif temp > self._settings.get_float(['MaxTemp']):
                    dutys.append([j,100])
                    BPWM.set_duty_cycle(self.fan_definitions[j]['fan_pin'], 100)
           # else: dutys.append([j,self.fan_definitions[j]['PWM']])
           
        #self._mylogger("Here my dutys %s" % dutys, forceinfo=True)
        self._plugin_manager.send_plugin_message(self._identifier, dict(msg="dutyupdate", field2=dutys))    

    def check_temp(self):
        self._mylogger("BBBC check_temp called")
        #temps=[0] *len(self.fan_definitions)
        temps=[]

        temps=self._get_temp()           
        #self._mylogger("Here my temp %s" % temps, forceinfo=True)
        #self._mylogger("Here my raw temp %s" % tempp, forceinfo=True)
        self._plugin_manager.send_plugin_message(self._identifier, dict(msg="tempupdate", field1=temps))            
            
    def get_api_commands(self):
        self._mylogger(u"BBB get_api_command()", forceinfo=True)
        return dict(
            updatepwm=['PWMS']
		)
        
    def on_api_command(self, command, data):
        self._mylogger(u"BBB on_api_command() - %s" % command, forceinfo=True)

        if command.lower() == "updatepwm":
            if 1:#data['PWM1'] > -1 and data['PWM2'] > -1 and data['PWM3'] > -1:
                #self._mylogger("Status Sent - {PWM1} - {PWM2} - {PWM3}".format(**data))
                self._mylogger(u"BBB on_api_command() - %s" % data, forceinfo=True)
                data.pop('command', 0)
                #self._settings.set(["PWM1"], int(data['PWMS'][0]))
                #self._settings.set(["PWM2"], int(data['PWMS'][1]))
                #self._settings.set(["PWM3"], int(data['PWMS'][2]))
                #self._settings.save()

        for j in range(len(self.fan_definitions)):
            if self.fan_definitions[j]['fan_pin'] == 'None' or self.fan_definitions[j]['manual_fan'] == False: continue
            else: BPWM.set_duty_cycle(self.fan_definitions[j]['fan_pin'],data['PWMS'][j] )
            self._mylogger("pwm duty changed %s" %self.fan_definitions[j]['fan_pin'], forceinfo=True)
                
				#self.initialize_leds()

    
    def reload_fan_definitions(self):
        self.fan_definitions = {}

        fan_definitions_tmp = self._settings.get(["fan_definitions"])
        #self._logger.info("fan_definitions: %s" % fan_definitions_tmp)

        i=0
        for definition in fan_definitions_tmp:
            self.fan_definitions[i] = dict(fan_name =definition['fan_name'], fan_pin=definition['fan_pin'], manual_fan=definition['manual_fan'], has_temp=definition['has_temp'], temp_type=definition['temp_type'], temp_pin=definition['temp_pin'], temp_text=definition['temp_text'], PWM=definition['PWM'])
            i= i +1
            #self._logger.info("Added fan setting 'fan :%s' is allocated to pin %s" % (definition['fan_name'], definition['fan_pin']))
        #self._logger.info("fan_definitions: %s" % fan_definitions_tmp)#self.fan_definitions[1])
        #self._logger.info("fan_definitions22222222222222: %s" % self.fan_definitions)#self.fan_definitions[1])
            

            
            
	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			BBBC=dict(
				displayName="Bbbc Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="letgo04",
				repo="BBB-Controller",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/letgo04/BBB-Controller/archive/{target_version}.zip"
			)
		)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "BBB Controller"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = BBBC()

	#global __plugin_hooks__
	#__plugin_hooks__ = {
		#"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	#}

