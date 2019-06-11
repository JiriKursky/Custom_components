import logging
import os
import sys

import voluptuous as vol

import homeassistant.helpers.config_validation as cv

from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_PASSWORD, CONF_USERNAME, CONF_SWITCHES, CONF_FRIENDLY_NAME, CONF_IP_ADDRESS, DEVICE_CLASS_POWER)
from datetime import timedelta
from homeassistant.core import split_entity_id
from homeassistant.helpers.event import async_call_later, async_track_point_in_utc_time

DOMAIN = 'sonata'
ENTITY_ID_FORMAT = 'switch.{}'

if os.path.isdir('/config/custom_components/'+DOMAIN):
    sys.path.append('/config/custom_components/'+DOMAIN)

from http_class import httpClass
from sonata_const import SENSORS, S_UNIT, S_VALUE, S_CMND, S_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
SWITCH_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): cv.string,    
    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_USERNAME, default = ''): cv.string,    
    vol.Optional(CONF_PASSWORD, default = ''): cv.string,
    vol.Optional(CONF_SWITCHES, default={}):
        cv.schema_with_slug_keys(SWITCH_SCHEMA),
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Sonata platform - switches."""
 
    # Assign configuration variables.
    # The configuration check takes care they are present.

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    switches = config.get(CONF_SWITCHES)
    
    entities = []
    for object_id, pars in switches.items():        
        http_class = httpClass(pars[CONF_IP_ADDRESS], username, password)        
        entity = Sonoff(object_id, pars.get(CONF_FRIENDLY_NAME), http_class)
        entities.append(entity)
    add_entities(entities)

class Sonoff(SwitchDevice):
    def __init__(self, object_id, name, http_class):       
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self._name = name
        self._http_class = http_class
        self._is_on = self._http_class.get_state_boolean()

    @property
    def name(self):
        """Name of the device."""
        return self._name

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        _LOGGER.debug("get_state")
        self._is_on = self._http_class.get_state_boolean()
        return self._is_on

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._http_class.turn_on()        
        self._is_on = True

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self._http_class.turn_off()        
        self._is_on = False
    
    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_POWER