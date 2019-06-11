import json
import logging 
import requests

from homeassistant.const import (ATTR_ENTITY_ID, STATE_ON, STATE_OFF,    
    DEVICE_CLASS_TEMPERATURE, CONF_FRIENDLY_NAME, CONF_VALUE_TEMPLATE, CONF_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT)
from sonata_const import(CMND_POWER, CMND_POWER_OFF, CMND_POWER_ON, R_STATUS_CODE, R_CONTENT,R_POWER)

TIMEOUT_GET = 0.3

_LOGGER = logging.getLogger(__name__)
class httpClass :
    def __init__(self, ip_address, username, password):
        self._base_url = 'http://'+ip_address+'/cm?'
        if len(username)>0:
            self._base_url += '&user='+username
        if len(password)>0:
            self._base_url += '&password='+password
        self._base_url += '&cmnd='
        self._first_call = True

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
        
        retVal = { R_STATUS_CODE: False, R_CONTENT: {} }

        try:
            r = requests.get(to_get, timeout = TIMEOUT_GET)              
            if r.status_code == 200:
                retVal[R_STATUS_CODE] = True
                retVal[R_CONTENT] = self._transfer_to_json(r.content)
        except:
            _LOGGER.debug("*************Exception")
            retVal[R_STATUS_CODE] = False
        return retVal

    def get_raw_response(self, cmnd) :
        """
        Checked for state - ok        
        r.status_code
        r.headers
        r.content
        """
        retVal = None
        to_get = self._base_url + cmnd
        _LOGGER.debug("Get: "+ to_get)
        try:
            r = requests.get(to_get, timeout = TIMEOUT_GET)              
            if r.status_code == 200:                
                retVal = self._transfer_to_json(r.content)
                return retVal
        except:
            _LOGGER.warning('Internal warning for get')
            retVal = None
        return retVal


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
        return self.get_state() == STATE_ON
        
    def turn_on(self):
        result  = self.get_response(CMND_POWER_ON)        
        return self.transform_response(CMND_POWER_ON, result)        

    def turn_off(self):
        result = self.get_response(CMND_POWER_OFF)        
        return self.transform_response(CMND_POWER_OFF, result)        
        