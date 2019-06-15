"""
httpClass for communication with sensor
Not used asynchonned, timeout for communication setting according HA library

Version 1.5
15.6.2019

Jiri Kursky
"""
import json
import logging 
import requests
import datetime

from inspect import currentframe, getframeinfo
from timeit import default_timer as timer
from homeassistant.const import (ATTR_ENTITY_ID, STATE_IDLE, STATE_ON, STATE_OFF,    
    DEVICE_CLASS_TEMPERATURE, CONF_FRIENDLY_NAME, CONF_VALUE_TEMPLATE, CONF_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT)
from httas_const import(CMND_POWER, CMND_POWER_OFF, CMND_POWER_ON, R_STATUS_CODE, R_CONTENT,R_POWER)

TIMEOUT_GET = 0.3
ERR_COUNT_LIMIT = 5
DOMAIN = 'mates'

B_TIMESTAMP = 'timestamp'
B_COUNT = 'count'
B_START = 'start'
_LOGGER = logging.getLogger(__name__)

def get_linenumber():
    cf = currentframe()
    return cf.f_back.f_lineno

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
            hass.data[DOMAIN][self._ip_address] = { B_COUNT:0, B_START: None } 
        self._hass = hass                

    def _debug(self,line, s):
        if s is None:
             s = ''
        _LOGGER.debug('line:'+str(line) +' ' +self._ip_address + ': ' + s)

    def _log_exception(self, exception: BaseException, expected: bool = True):
        output = "[{}] {}: {}".format('EXPECTED' if expected else 'UNEXPECTED', type(exception).__name__, exception)
        _LOGGER.debug(output)
        #exc_type, exc_value, exc_traceback = sys.exc_info()
        #traceback.print_tb(exc_traceback)

    def _transfer_to_json(self, source) :
        """ Byte transforming to json. """
        my_json = source.decode('utf8').replace("'", '"')
        return json.loads(my_json)    

    def get_response(self, cmnd):
        to_get = self._base_url + cmnd        
        retVal = { R_STATUS_CODE: False, R_CONTENT: {} }
        if self._permanent_error:
            self._debug(get_linenumber(),"permanent error")
            return retVal
        is_error = False
        try:
            self._debug(get_linenumber(), to_get)
            r = requests.get(to_get, timeout = TIMEOUT_GET)                          
            if r.status_code == 200:
                retVal[R_STATUS_CODE] = True
                retVal[R_CONTENT] = self._transfer_to_json(r.content)
                self._buffer[cmnd] = retVal
                self._hass.data[DOMAIN][self._ip_address] = { B_COUNT:0, B_START: datetime.datetime.now() }
                self._debug(get_linenumber(), cmnd + 'OK')
            else:                 
                self._debug(get_linenumber(), 'HTTP error code:'+str(r.status_code))                      
        except SyntaxError as error:
            # Output expected SyntaxErrors.
            self._debug(get_linenumber(), "Syntax")
            _LOGGER.debug(error)                        
            is_error = True
        except Exception as error:
            self._debug(get_linenumber(), "Syntax")
            is_error = True
            self._log_exception(error)
        if is_error:
            self._debug(get_linenumber(), self._base_url + cmnd + ' except error')          
            if cmnd in self._buffer.keys():
                retVal = self._buffer[cmnd]           
            else:
                retVal[R_STATUS_CODE] = False            
            self._hass.data[DOMAIN][self._ip_address][B_COUNT] =  self._hass.data[DOMAIN][self._ip_address][B_COUNT] + 1
            self._debug(get_linenumber(), "Failed, count: " + str(self._hass.data[DOMAIN][self._ip_address][B_COUNT]))
        if (self._hass.data[DOMAIN][self._ip_address][B_COUNT] > ERR_COUNT_LIMIT) and (self._hass.data[DOMAIN][self._ip_address][B_START] is None):                    
            self._permanent_error = True                
            self._hass.components.persistent_notification.create(
                self._ip_address + " has permanent error from the start.<br/>You will need to restart Home Assistant after fixing.",
                title="Mates error")                
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
        self._debug(108, "Cmnd: " + cmnd + " Status code: " + str(ret_val[R_STATUS_CODE]))
        if ret_val[R_STATUS_CODE]:            
            try:
                if cmnd in [CMND_POWER, CMND_POWER_ON, CMND_POWER_OFF]:                                    
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
        