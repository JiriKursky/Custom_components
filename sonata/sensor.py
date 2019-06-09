import logging
import os
import sys

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.const import (CONF_PASSWORD, CONF_USERNAME,  CONF_FRIENDLY_NAME, CONF_IP_ADDRESS, DEVICE_CLASS_POWER, CONF_SENSORS, CONF_SENSOR_TYPE)

DOMAIN = 'sonata'
ENTITY_ID_FORMAT = 'sensor.{}'
_LOGGER = logging.getLogger(__name__)

if os.path.isdir('/config/custom_components/'+DOMAIN):
    sys.path.append('/config/custom_components/'+DOMAIN)

from http_class import httpClass
from timer_class import TimerJaroslavaSoukupa
from sonata_const import SENSORS, S_UNIT, S_VALUE, S_CMND, S_SCAN_INTERVAL

# Validation of the user's configuration
SENSOR_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): cv.string,    
    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
    vol.Required(CONF_SENSOR_TYPE, default=[]): [vol.In(SENSORS.keys())]
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,    
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_SENSORS, default={}):
        cv.schema_with_slug_keys(SENSOR_SCHEMA),
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Awesome Light platform."""
 
    # Assign configuration variables.
    # The configuration check takes care they are present.

    username = config[CONF_USERNAME]
    password = config.get(CONF_PASSWORD)

    sensors = config.get(CONF_SENSORS)
    
    entities = []
    for object_id, pars in sensors.items():        
        http_class = httpClass(pars[CONF_IP_ADDRESS], username, password)        
        for sensor_type in pars.get(CONF_SENSOR_TYPE):
            entity = SonoffSensor(hass, object_id, pars[CONF_FRIENDLY_NAME], sensor_type, http_class)
            entities.append(entity)
    add_entities(entities)

class SonoffSensor(Entity):
    """Representation of a Sonoff device sensor."""

    def __init__(self, hass, object_id, name, sensor_type, http_class):        
        """Initialize the sensor."""
        self._name = name
        self.entity_id = ENTITY_ID_FORMAT.format(object_id+'_'+sensor_type)
        self._state = None        
        self._is_available = False
        self._sensor_type = sensor_type        
        self._http_class = http_class
        self._interval = SENSORS[sensor_type][S_SCAN_INTERVAL]        
        self._unit_of_measurement = SENSORS[sensor_type][S_UNIT]
        self._cmnd = SENSORS[sensor_type][S_CMND]
        self._state = None
        self._tjs = TimerJaroslavaSoukupa(hass, self, self.update, self._interval)
        

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def available(self):
        """Return True if entity is available."""
        return self._is_available

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    def _json_key_value(self, def_array, value):
        if value is None:
            return None        
        for key in def_array:
            if key in value.keys():
                value = value[key]
            else :
                return None
        return value

    def update(self):
        """Get the latest data from the sensor."""
        value = self._get_value()
        if value is None:
            self._state = None
            self._is_available = False
            self.async_schedule_update_ha_state()
            return
        self._state = value
        self._is_available = True
        self.async_schedule_update_ha_state()

    def _get_value(self):
        ret_val = None        
        data = self._http_class.get_raw_response(self._cmnd)                    
        if data is not None :                                
            # @TODO need to investigate, how to use it
            ret_val = self._json_key_value(SENSORS[self._sensor_type][S_VALUE], data)                                            
        return ret_val        