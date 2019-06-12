import json
import logging 
import requests

from timeit import default_timer as timer
from homeassistant.const import (ATTR_ENTITY_ID, STATE_IDLE, STATE_ON, STATE_OFF,    
    DEVICE_CLASS_TEMPERATURE, CONF_FRIENDLY_NAME, CONF_VALUE_TEMPLATE, CONF_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT)
from sonata_const import(CMND_POWER, CMND_POWER_OFF, CMND_POWER_ON, R_STATUS_CODE, R_CONTENT,R_POWER)

TIMEOUT_GET = 0.3
ERR_COUNT_LIMIT = 5
DOMAIN = 'sonata'

B_TIMESTAMP = 'timestamp'
B_COUNT = 'count'
_LOGGER = logging.getLogger(__name__)



class httpClass :
    def __init__(self, hass, ip_address, username, password):
        self._ip_address = ip_address
        self._base_url = 'http://'+ip_address+'/cm?'
        if len(username)>0:
            self._base_url += '&user='+username
        if len(password)>0:
            self._base_url += '&password='+password
        self._base_url += '&cmnd='
        self._first_call = True
        
        self._buffer = {}
        self._permanent_error = False        
        if DOMAIN not in hass.data:
            hass.data[DOMAIN]={}
        if ip_address not in hass.data[DOMAIN]:
            hass.data[DOMAIN][self._ip_address] = 0 
        self._hass = hass
        _LOGGER.debug("IP......"+self._ip_address)
        

    def _transfer_to_json(self, source) :
        """ Byte transforming to json. """
        my_json = source.decode('utf8').replace("'", '"')
        return json.loads(my_json)    

    def get_response(self, cmnd):
        to_get = self._base_url + cmnd        
        retVal = { R_STATUS_CODE: False, R_CONTENT: {} }
        if self._permanent_error:
            return retVal
        try:
            r = requests.get(to_get, timeout = TIMEOUT_GET)              
            if r.status_code == 200:
                retVal[R_STATUS_CODE] = True
                retVal[R_CONTENT] = self._transfer_to_json(r.content)
                self._buffer[cmnd] = retVal
                self._hass.data[DOMAIN][self._ip_address] = 0
            else:                 
                _LOGGER.debug('HTTP error code:'+str(r.status_code))                      
        except:
            _LOGGER.debug(cmnd + ' except error')          
            if cmnd in self._buffer.keys():
                retVal = self._buffer[cmnd]           
            else:
                retVal[R_STATUS_CODE] = False            
            self._hass.data[DOMAIN][self._ip_address] =  self._hass.data[DOMAIN][self._ip_address] + 1
            _LOGGER.debug("Failed: " + self._ip_address + " count: " + str(self._hass.data[DOMAIN][self._ip_address]))
            if self._hass.data[DOMAIN][self._ip_address] > ERR_COUNT_LIMIT:                    
                self._permanent_error = True                
                self._hass.components.persistent_notification.create(
                    self._ip_address + " has permanent error.<br/>You will need to restart Home Assistant after fixing.",
                    title="Sonata error")                
        return retVal    
    
    def get_raw_response(self, cmnd) :
        """
        Checked for state - ok        
        r.status_code
        r.headers
        r.content
        """
        response = self.get_response(cmnd)
        if response[R_STATUS_CODE]:
            return response[R_CONTENT]
        else:
            return None        

    def transform_response(self, cmnd, ret_val):
        _LOGGER.debug("Cmnd: " + cmnd + " Status code: " + str(ret_val[R_STATUS_CODE]))
        if ret_val[R_STATUS_CODE]:            
            try:
                if cmnd in [CMND_POWER, CMND_POWER_ON, CMND_POWER_OFF]:                
                    _LOGGER.debug('ret_val[R_CONTENT]') 
                    _LOGGER.debug(ret_val[R_CONTENT]) 
                    if ret_val[R_CONTENT][R_POWER] == 'ON':
                        return STATE_ON
                    else :
                        return STATE_OFF
            except:
                return STATE_OFF
        else :
            return None

    
    def get_state(self):       
        if self._first_call: 
            self._first_call = False
            return None
        else:
            result = self.get_response(CMND_POWER)        
            return self.transform_response(CMND_POWER, result)

    def get_state_boolean(self):
        if self._permanent_error:
             return STATE_IDLE
        return self.get_state() == STATE_ON
        
    def turn_on(self):
        if self._permanent_error:
             return None
        result  = self.get_response(CMND_POWER_ON)        
        return self.transform_response(CMND_POWER_ON, result)        

    def turn_off(self):
        if self._permanent_error:
             return None
        result = self.get_response(CMND_POWER_OFF)        
        return self.transform_response(CMND_POWER_OFF, result)        
        