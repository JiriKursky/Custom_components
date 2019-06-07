import logging 
import json
import requests
import datetime
import time

from homeassistant.const import (ATTR_ENTITY_ID, CONF_ENTITY_ID, CONF_ICON, CONF_NAME, SERVICE_TURN_ON,  
    SERVICE_TURN_OFF, STATE_ON, STATE_OFF, EVENT_COMPONENT_LOADED, EVENT_STATE_CHANGED,     
    DEVICE_CLASS_TEMPERATURE, CONF_FRIENDLY_NAME, CONF_VALUE_TEMPLATE, CONF_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT)
from homeassistant.setup import ATTR_COMPONENT
from homeassistant.core import callback
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_call_later, async_track_time_interval
import homeassistant.components.input_boolean as input_boolean


DOMAIN = 'sonata'
ENTITY_ID_FORMAT = DOMAIN + '.{}'
_LOGGER = logging.getLogger(__name__)

CONF_URL = 'url'
CONF_USER = 'user'
CONF_PASSWORD = 'password'
CONF_CONTROL = 'control'

CMND_STATUS = 'status%208'
CMND_POWER = 'POWER'
CMND_POWER_ON = 'Power%20On'
CMND_POWER_OFF = 'Power%20Off'

S_CMND = "CMND"
S_VALUE = "VALUE"
S_UNIT = "UNIT"

SENSOR_PARS = 'PARS'
DEVICE_BASIC    = 'sonoff'
DEVICE_WITH_SENSORS  = 'sonoff_sensor'
SENSORS = {
    "sensor_temperature":{ 
        S_CMND: CMND_STATUS,
        S_VALUE:  ["StatusSNS", "DS18B20","Temperature"] ,
        S_UNIT:   'C'
    },
    "sensor_voltage": {
        S_CMND: CMND_STATUS,
        S_VALUE:  ["StatusSNS","ENERGY", "Voltage"] ,
        S_UNIT:   "V"
    }, 
    "sensor_current": {
        S_CMND: CMND_STATUS,
        S_VALUE:  ["StatusSNS", "ENERGY", "Current"] ,
        S_UNIT:   "A"
    }
} 

        

CONF_ENTITIES   = [ DEVICE_BASIC, DEVICE_WITH_SENSORS ]


ATTR_CURRENT = 'Current'

LI_NO_DEFINITION = 'No entity added'

R_STATUS_CODE = 'STATUS_CODE'
R_CONTENT = 'CONTENT'
R_POWER = 'POWER'

O_CHILDREN = 'CHILDREN'

TIME_INTERVAL_DEVICE_ON = 3
TIME_INTERVAL_DEVICE_STATUS = 8
TIME_INTERVAL_DEVICE_ERROR = 30

S_VOLTAGE = 'Voltage'
S_CURRENT = 'Current'

async def async_setup(hass, config) :
    """Starting."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    hass.data[DOMAIN] = { O_CHILDREN: {} }

    entities = []
    
    for key, cfg in config[DOMAIN].items():
        if not (key in CONF_ENTITIES):            
            hass.data[DOMAIN][key]=cfg

    # Reading in config
    _LOGGER.debug('-------------')
    _LOGGER.debug(config[DOMAIN])
    for key, cfg in config[DOMAIN].items():
        if key in CONF_ENTITIES:                  
            for object_id, object_cfg in cfg.items():
                entity = None
                if key == DEVICE_BASIC:
                    entity = sonoff_basic(hass, object_id, object_cfg)
                if key == DEVICE_WITH_SENSORS:
                    entity = sonoff_sensor(hass, object_id, object_cfg)                                        
                if entity is None:
                    raise ValueError('Fatal')
                hass.data[DOMAIN][O_CHILDREN][object_id] = entity
                _LOGGER.info('Setting up ' + object_id)
                entities.append(entity)                    
    if not entities:
        _LOGGER.info(LI_NO_DEFINITION)    
        return False
    await component.async_add_entities(entities)       



    # This is not necessary however to be sure
    timer_defined = False     
    @callback       
    def component_loaded(event):
        """Handle a new component loaded."""   
        nonlocal timer_defined    
        component_name = event.data[ATTR_COMPONENT]
        if (component_name == DOMAIN) :
            _LOGGER.debug("My component loaded: "+component_name)
            if timer_defined:
                return
            timer_defined = True
            # Prevent to more calling - dangerous, but should not happened
            for entity in entities :
                _LOGGER.debug("15 seconds to start")                                
                async_call_later(hass, 15, entity.start_time_interval)                
    
    # fired in courutine _async_setup_component setup.py
    hass.bus.async_listen_once(EVENT_COMPONENT_LOADED, component_loaded)    
    
    return True



class _httpClass :
    def __init__(self, base_url):
        self._base_url = base_url                

    def _transfer_to_json(self, source) :
        """ Byte transforming to json. """
        my_json = source.decode('utf8').replace("'", '"')
        return json.loads(my_json)    

    def get_response(self, cmnd) :
        """
        Checked for state - ok        
        r.status_code
        r.headers
        r.content
        """
        to_get = self._base_url + cmnd
        _LOGGER.debug("to get:" + to_get)
        
        retVal = { R_STATUS_CODE: False, R_CONTENT: {} }

        try:
            r = requests.get(to_get)            
            if r.status_code == 200:
                retVal[R_STATUS_CODE] = True
                retVal[R_CONTENT] = self._transfer_to_json(r.content)
        except:
            retVal[R_STATUS_CODE] = False
        return retVal


    def transform_response(self, cmnd, ret_val):
        if ret_val[R_STATUS_CODE] :
            if cmnd in [CMND_POWER, CMND_POWER_ON, CMND_POWER_OFF]:                 
                if ret_val[R_CONTENT][R_POWER] == 'ON':
                    return STATE_ON
                else :
                    return STATE_OFF
        else :
            return None

    def get_state(self):        
        result = self.get_response(CMND_POWER)
        return self.transform_response(CMND_POWER, result)
        
    def turn_on(self):
        result  = self.get_response(CMND_POWER_ON)
        return self.transform_response(CMND_POWER_ON, result)        

    def turn_off(self):
        result = self.get_response(CMND_POWER_OFF)
        return self.transform_response(CMND_POWER_OFF, result)        
        

class sonoff_basic(RestoreEntity) :        
    def __init__(self, hass, object_id, cfg):                
        self._hass = hass
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)     # definice identifikatoru        
        self._name = cfg.get(CONF_NAME)
        if self._name is None:
            self._name = object_id
        self._url = cfg.get(CONF_URL)
        self._user = hass.data[DOMAIN][CONF_USER]
        self._password = hass.data[DOMAIN][CONF_PASSWORD]
        self.http_class =_httpClass('http://'+self._url+'/cm?&user='+self._user+'&password='+self._password+'&cmnd=')        
        self._state = None
        self._control = cfg.get(CONF_CONTROL)
        self._time_interval_running = False
        self._time_delay = TIME_INTERVAL_DEVICE_STATUS
        self._time_error_delay = TIME_INTERVAL_DEVICE_ERROR
        self.refresh_state(False)                

    @property
    def time_delay(self):
        return self._time_delay

    @time_delay.setter
    def set_time_delay(self, time_delay) :
        self._time_delay = time_delay

    @property
    def time_error_delay(self):
        return self._time_error_delay

    @time_error_delay.setter
    def set_time_error_delay(self, time_delay) :
        self._time_error_delay = time_delay

    def set_turn_on(self):        
        _LOGGER.debug('Setting on:' + self.entity_id)
        return self.http_class.turn_on()        

    def set_turn_off(self):
        _LOGGER.debug('Setting off:' + self.entity_id)
        return self.http_class.turn_off()        

    @property
    def is_on(self):
        """Return true if entity is on."""
        return self._state

    @property
    def name(self):
        """Get friendly name"""
        return self._name

    @property
    def should_poll(self):
        """If entity should be polled."""        
        return False

    def get_state(self) :
        return self.http_class.get_state()
        
    def refresh_state(self, publish):        
        new_state = self.get_state()
        if new_state is None :
            new_state = "N/A"
            return False
        if self._state != new_state:            
            self._state = new_state                
            if publish:
                 self.async_schedule_update_ha_state()
        return True

    def handle_event(self, event):        
        if event.data.get(ATTR_ENTITY_ID) != self._control:
            return
        if input_boolean.is_on(self.hass, self._control):
            self._state = self.set_turn_on()                
        else:
            self._state = self.set_turn_off()            
        self.async_schedule_update_ha_state()
    
    def start_time_interval(self, now):                        
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self.handle_event)
        self.time_interval(now)

    def exec_loop(self):
        return self.refresh_state(True)

    def time_interval(self, now):                        
        """Regular called"""
        # missing of parameter 'now' caused not working without warning
        # not async!
        
        def _repeat_call(*time_delay):            
            if len(time_delay) == 0:
                 _time_delay = self.time_delay
            else:
                _time_delay = time_delay[0]
            async_call_later(self._hass, _time_delay, self.time_interval)
            self._time_interval_running = False
            # To be sure
            return True
        
        # Just to avoid cycle, can be omitted...maybe
        if self._time_interval_running:
             return True
        self._time_interval_running = True        
        if self.exec_loop():
            return _repeat_call()
        else:
            _LOGGER.error("Timeout trying for 30 seconds")        
            return _repeat_call(self.time_error_delay)            
        
    @property
    def state(self):
        """Return the state of the component."""                                
        return self._state    
        
class sonoff_sensor(sonoff_basic):
    def __init__(self, hass, object_id, cfg):                
        super().__init__(hass, object_id, cfg)        
        self._sensors = []
        for key, value in cfg.items():
            _LOGGER.debug("Hledam: "+key)
            if key in SENSORS.keys() :                                
                sensor_cfg = SENSORS[key]
                self._sensors.append({ ATTR_ENTITY_ID: value, SENSOR_PARS: sensor_cfg })                
        _LOGGER.debug(self._sensors)

    def _json_key_value(self, def_array, value):
        if value is None:
            return None        
        for key in def_array:
            if key in value.keys():
                value = value[key]
            else :
                return None
        return value
        

    def exec_loop(self):
        result = self.refresh_state(True)
        if not result :
            return result
        sent_cmnd = None
        for sensor in self._sensors :
            sensor_pars = sensor[SENSOR_PARS]
            cmnd = sensor_pars[S_CMND]
            if cmnd != sent_cmnd :
                ret = self.http_class.get_response(cmnd)
                if not ret[R_STATUS_CODE]:
                     return False
                content = ret[R_CONTENT]
                sensor_entity_id = sensor[ATTR_ENTITY_ID]
                value = self._json_key_value(sensor_pars[S_VALUE], content)                
                _LOGGER.info("Vysledek")
                _LOGGER.info(content)
                self.hass.states.async_set(sensor_entity_id, value, { ATTR_UNIT_OF_MEASUREMENT: sensor_pars[S_UNIT] })
        return True
                

    @property
    def state_attributes(self):
        """Return the state attributes."""
        attrs = { ATTR_CURRENT: 0 }
        return attrs