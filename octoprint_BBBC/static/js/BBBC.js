/*
 * View model for BBB-Controller
 *
 * Author: elcu
 * License: AGPLv3
 */
$(function() {   
    var workingurl = API_BASEURL + "plugin/BBBC";
    
    function ProcessPWMs(data) {
        // This is a fail safe to stop partial processing of the javascript
        if (data == undefined)
            return;

        //var PWMs = duty1 + ',' + duty2 + ',' + duty3;
        //$('#LEDFinalRGBCell').css('backgroundColor', 'rgb(' + RGBColors + ')');
        //$('#LEDFinalRGB').text(RGBColors);

        $.ajax({
            url: workingurl,
            type: "POST",
            dataType: "json",
            data: JSON.stringify({
                command: "updatepwm",
               //PWM1: duty1,
               //PWM2: duty2,
               //PWM3: duty3
                 PWMS: data
            }),
            contentType: "application/json; charset=UTF-8"
        });
    }
    
    function Datum(data) {
        var self = this;

        self.fan_name = ko.observable(data.fan_name);
        self.fan_pin = ko.observable(data.fan_pin);
        self.manual_fan = ko.observable(data.manual_fan);
        self.has_temp = ko.observable(data.has_temp);
        self.temp_type = ko.observable(data.temp_type);
        self.temp_pin = ko.observable(data.temp_pin);
	self.temp_text= ko.observable(data.temp_text);
        self.PWM = ko.observable(data.PWM);
    }
    
  //  function ResetPWMSlider(PWMSliderTag, percent) {
  //      $(PWMSliderTag).find("div.slider-selection").css('width', percent + '%');
  //      $(PWMSliderTag).find("div.slider-handle").css('left', percent + '%');
  // }
    
    function BBBCViewModel(parameters) {
        var self = this;

        self.global_settings = parameters[0];
        self.settings = undefined;
        self.loginState = parameters[1];
        self.cvm = parameters[2];

        self.PWM1 = ko.observable();
        self.PWM2 = ko.observable();
        self.PWM3 = ko.observable();
        self.fan_definitions = ko.observableArray([]);
        self.pwms = ko.observableArray([]);

      /*  self.PWMText = ko.computed(function () {
            return self.PWM1() + ", " + self.PWM2() + ", " + self.PWM3();
        });
        self.PWMText.subscribe(function () {
            ProcessPWMs(self.PWM1(), self.PWM2(), self.PWM3());
        });*/
        
        self.SetPWMs = function () {
            //   self.PWM1=self.fan_definitions()[0].PWM;
            //   self.PWM2=self.fan_definitions()[1].PWM;
            //   self.PWM3=self.fan_definitions()[2].PWM;
            self.pwms.removeAll();
            for(i=0; i< Object.keys(self.fan_definitions()).length; i++){
                self.pwms.push(self.fan_definitions()[i].PWM());
		}        
            //ProcessPWMs(self.fan_definitions()[0].PWM(), self.fan_definitions()[1].PWM(),self.fan_definitions()[2].PWM());
            ProcessPWMs(self.pwms());
        };     
        
        self.addCommandDefinition = function() {
            self.fan_definitions.push(new Datum({fan_name:'', fan_pin:'', manual_fan: false, has_temp:true , temp_type:'', temp_pin:'', PWM:60, temp_text:0}));
        };

        self.removeCommandDefinition = function(definition) {
            self.fan_definitions.remove(definition);
        };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin != "BBBC") {return;}
 
            if ((data != undefined) && (data.msg != undefined)) {
                if (data.msg.toLowerCase() == "tempupdate") {
                    for(i=0; i< Object.keys(self.fan_definitions()).length; i++){
                        self.fan_definitions()[i].temp_text(data.field1[i]);//.toFixed(1));
                }
               // self.refresh();
                 // self.temp(data.field1);
                //return;
                }
                if (data.msg.toLowerCase() == "dutyupdate") {
			//console.log(data.field2)
                    for(i=0; i< data.field2.length; i++){
                        self.fan_definitions()[data.field2[i][0]].PWM(data.field2[i][1]);
                }

                }
            }
        };
        self.refresh = function(){
            var data = self.fan_definitions().slice(0);
            self.fan_definitions([]);
            self.fan_definitions(data);
        };
       
        self.onBeforeBinding = function () {
            self.settings = self.global_settings.settings.plugins.BBBC;
            self.fan_definitions(self.settings.fan_definitions.slice(0));
            self.PWM1(self.settings.PWM1());
            self.PWM2(self.settings.PWM2());
            self.PWM3(self.settings.PWM3());
            //self.fan_definitions()[0].PWM(self.settings.fan_definitions()[1].PWM());
          //  self.fan_definitions()[0].PWM(self.settings.PWM1());
          //  self.fan_definitions()[1].PWM(self.settings.PWM2());
          //  self.fan_definitions()[2].PWM(self.settings.PWM3());
          //  self.pwms.removeAll();
          //  self.pwms.push(self.fan_definitions()[0].PWM());
         //   self.pwms.push(self.fan_definitions()[1].PWM());
          //  self.pwms.push(self.fan_definitions()[2].PWM());           
         //   ProcessPWMs(self.pwms());
        };
        
        self.onSettingsHidden = function () {
            self.settings = self.global_settings.settings.plugins.BBBC; // flag began to invert well for visible, but in slider enabled flag not changed without this api.
            self.fan_definitions(self.settings.fan_definitions.slice(0));
        };
        
        self.onSettingsBeforeSave = function () {
            self.global_settings.settings.plugins.BBBC.fan_definitions(self.fan_definitions.slice(0));
        }
    }


    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: BBBCViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: ["settingsViewModel", "loginStateViewModel", "connectionViewModel"],
        // Elements to bind to, e.g. #settings_plugin_BBBC, #tab_plugin_BBBC, ...
        elements: ["#settings_plugin_BBBC", "#tab_plugin_BBBC"]
    });
});
