"""
Component for controlling devices in regular time

Version is still not stable and wrong configuration can lead to frozen system

Tested on under hass.io ver. 0.93.2 


Releaes:

https://github.com/JiriKursky/Hass.io_CZ_SK_custom_components/releases

Version 6.6.2019

"""

import logging
import datetime
import time
import os
import sys

import voluptuous as vol

from homeassistant.const import (ATTR_ENTITY_ID, CONF_ICON, CONF_NAME, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON, STATE_OFF, EVENT_HOMEASSISTANT_STOP,
CONF_COMMAND_ON, CONF_COMMAND_OFF, CONF_CONDITION)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util
from homeassistant.core import split_entity_id
from homeassistant.helpers.event import async_track_time_interval


DOMAIN = 'turnoffon'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

if os.path.isdir('/config/custom_components/'+DOMAIN):
    sys.path.append('/config/custom_components/'+DOMAIN)

import util_jk

_LOGGER = logging.getLogger(__name__)

LI_NO_DEFINITION = 'No entity added'

CONF_TIMERS = 'timers'
CONF_ACTION_ENTITY_ID = 'action_entity_id' # what to call as controlling entity during comand_on, comannd_off

# Navratove hodnoty z run_casovac
R_HASS = 'HASS'
R_TODO = 'TO_DO'
R_ENTITY_ID = "ENTITY_ID"

O_PARENT = 'PARENT'
O_CHILDREN = 'CHILDREN'

# Used attributes
ATTR_START_TIME         = 'start_time'
ATTR_TIME_DELTA         = 'run_len'
ATTR_END_TIME           = 'end_time'
ATTR_LAST_RUN           = 'last_run'
ATTR_START_TIME_INIT    = 'start_time_init'
ATTR_END_TIME_INIT      = 'end_time_init'

ATTR_ACTIVE_ENTITY_ID   = 'active_entity_id'
# There are several entities defined by this routine, but only one have to be active in interval

#-------------------------------------------------
def time_to_string(t_cas):
    return t_cas.strftime('%H:%M')

def string_to_time(s):
    try:
        return time.strptime(s, '%H:%M')         
    except:
        return None

def prevedCasPar(sCas, praveTed):    
    def_time = string_to_time(sCas)
    if def_time is None:
        return None
    praveTed = datetime.datetime.now()    
    return praveTed.replace(hour=def_time.tm_hour, minute=def_time.tm_min, second=0)

def prevedCas(sCas):
    # String to datetime now
    return prevedCasPar(sCas, datetime.datetime.now())

def get_end_time(start_time, end_time) :    
    if isinstance(end_time, int):        
        return time_to_string(prevedCas(start_time) + datetime.timedelta(minutes = end_time))
    return end_time

#-----------------------------------------------
# Service for running timer immediately
SERVICE_RUN_CASOVAC = 'run_turnoffon'
SERVICE_SET_RUN_CASOVAC_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id
})

# -----------------------------
# Service setting time run-time

def has_start_or_end(conf):
    """Check at least date or time is true."""
    if conf[ATTR_TIME_DELTA] and not conf[ATTR_START_TIME]:
        raise vol.Invalid("In case of delta "+ ATTR_START_TIME + " is required")                            
    if conf[ATTR_START_TIME] or conf[ATTR_END_TIME]:
         return conf    
    raise vol.Invalid("Entity needs at least a " + ATTR_START_TIME + "and a " + ATTR_END_TIME + " or a " + ATTR_TIME_DELTA)        

SERVICE_SET_TIME = 'set_time'
SERVICE_SET_TIME_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    vol.Optional(ATTR_START_TIME): cv.time,
    vol.Optional(ATTR_END_TIME): cv.time,        
    vol.Optional(ATTR_TIME_DELTA): vol.All(vol.Coerce(int), vol.Range(min=1, max=59), msg='Invalid '+ATTR_TIME_DELTA)},
    has_start_or_end
)

# Konstanta definice sluzby
SERVICE_SET_TURN_ON = SERVICE_TURN_ON
SERVICE_SET_TURN_ON_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id    
})

# Konstanta definice sluzby
SERVICE_SET_TURN_OFF = SERVICE_TURN_OFF
SERVICE_SET_TURN_OFF_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id    
})

SERVICE_RESET_TIMERS = 'reset_timers'
SERVICE_RESET_TIMERS_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id    
})


ERR_CONFIG_TIME_SCHEMA = 'Chybne zadefinovane casy'
ERR_CONFIG_TIME_2 = 'Delka musi byt v rozsahu 1 - 59'
#-----------------------------------------------------------------------------
# End serices

def kontrolaCasy(hodnota):
    """ Checking timers during config """
    try:    
        for start, cosi in hodnota.items():        
            cv.time(start)        
            if  isinstance(cosi, int):                
                if (cosi<0) or (cosi > 59):
                    raise vol.Invalid(ERR_CONFIG_TIME_2)    
            else:                
                cv.time(cosi)            
        return hodnota
    except:
        raise vol.Invalid(ERR_CONFIG_TIME_SCHEMA)    
              
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: cv.schema_with_slug_keys(
        vol.All({                        
            vol.Required(CONF_TIMERS): kontrolaCasy,
            vol.Required(CONF_ACTION_ENTITY_ID): cv.entity_id,            
            vol.Optional(CONF_CONDITION): cv.entity_id,
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_COMMAND_ON, default = SERVICE_TURN_ON): cv.string,
            vol.Optional(CONF_COMMAND_OFF, default = SERVICE_TURN_OFF): cv.string
        })
    )
}, extra=vol.ALLOW_EXTRA)

def get_child_object_id(parent, number):
    if number < 10:
        s_number = "0" + str(number) 
    else:
        s_number = str(number) 
    return parent + "_" + s_number

async def async_setup(hass, config):
    """Uvodni nastaveni pri zavedeni."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []

    # Store entities. I think it is sick, should use call service instead, but loops and loops
    hass.data[DOMAIN] = { O_PARENT: {}, O_CHILDREN: {}}
    

    # Reading in config
    for object_id, cfg in config[DOMAIN].items():    
        if cfg is None:            
            return False        
        casy = cfg.get(CONF_TIMERS)
        if casy is None:
            _LOGGER.info(LI_NO_DEFINITION)
            return False
        
        # Default creation of name or from config        
        parent_name = cfg.get(CONF_NAME) 
        if parent_name is None:
            parent_name = object_id
        
        # citac
        i = 0    
        for start_time, end_time in casy.items():
            i = i + 1
            
            new_object_id = get_child_object_id(object_id, i)
            name = parent_name + ' ' + str(i)
            entity = Casovac(hass, new_object_id, name, start_time, end_time)
            _LOGGER.debug(entity)
            _LOGGER.info('Setting up ' + new_object_id)
            hass.data[DOMAIN][O_CHILDREN][new_object_id] = entity            
            entities.append(entity)

        
        # Create entity_id
        casovacHlavni = CasovacHlavni(hass, object_id, parent_name, i, cfg)

        # Push to store
        hass.data[DOMAIN][O_PARENT][object_id] = casovacHlavni        

        # Setting main timer - loop for checking interval
        async_track_time_interval(hass,casovacHlavni.pravidelny_interval, datetime.timedelta(minutes = 1))
        
        entities.append(casovacHlavni)        
    if not entities:
        _LOGGER.info(LI_NO_DEFINITION)    
        return False
    

    # Musi byt pridano az po definici vyse - je potreba znat pocet zaregistrovanych casovacu    

    async def async_run_casovac_service(entity, call):
        """Spusteni behu."""        
        _LOGGER.debug("Volam hledani")

        #----------------------------
        # main procedure
        retVal = entity.run_casovac()
        #----------------------------

        _LOGGER.debug("Navrat:")
        _LOGGER.debug(retVal)
        hass = retVal[R_HASS]        
        if hass == None :
            _LOGGER.debug("Nenalezen hass: "+ entity.entity_id)
            return
        target_domain, _ = split_entity_id(retVal[R_ENTITY_ID])

        # volam sluzbu, ktera zapne nebo vypne danou entitu               
        await hass.services.async_call(target_domain, retVal[R_TODO], { "entity_id": retVal[R_ENTITY_ID] }, False)

    # ------------- Service registering     
    # Velmi nebezpecna registrace - zde udelat chybu pri volani druheho parametru hrozi spadnuti celeho systemu
    component.async_register_entity_service(
        SERVICE_RUN_CASOVAC, SERVICE_SET_RUN_CASOVAC_SCHEMA, 
        async_run_casovac_service
    )

    async def async_set_time_service(entity, call):
        """Spusteni behu."""
        try: 
            start_time = call.data.get(ATTR_START_TIME)
            end_time = call.data.get(ATTR_END_TIME)   
            if end_time is None:                     
                end_time = get_end_time(start_time, end_time)
                            
            _LOGGER.debug("Called service for: " + entity.entity_id)        
            entity.set_time(start_time, end_time)        
        except:
            raise ValueError('Wrong time parametres')        
    component.async_register_entity_service(
        SERVICE_SET_TIME, SERVICE_SET_TIME_SCHEMA, 
        async_set_time_service
    )
    
    async def async_set_turn_on_service(entity, call):
        """Spusteni behu."""        
        entity.set_turn_on()        
    component.async_register_entity_service(
        SERVICE_SET_TURN_ON, SERVICE_SET_TURN_ON_SCHEMA, 
        async_set_turn_on_service
    )

    async def async_set_turn_off_service(entity, call):
        """Setting turn_off."""        
        entity.set_turn_off()        
    component.async_register_entity_service(
        SERVICE_SET_TURN_OFF, SERVICE_SET_TURN_OFF_SCHEMA, 
        async_set_turn_off_service
    )

    async def async_reset_timers(entity, call):
        entity.reset_timers()
    component.async_register_entity_service(
        SERVICE_RESET_TIMERS, SERVICE_RESET_TIMERS_SCHEMA, 
        async_reset_timers
    )
    #--------------------------------------------------------
    # Adding all entities
    await component.async_add_entities(entities)

    # Stopping with Homeassistant
    def stop_turnoffon(event):
        """Disconnect."""
        _LOGGER.debug("Shutting down ")
        # @TODO Should be done
        

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_turnoffon)
    return True


class TurnonoffEntity(RestoreEntity):
    """ Prototype entity for both. Parent and children """
    def __init__(self, hass, object_id, parent, name):
        self.entity_id = ENTITY_ID_FORMAT.format(object_id) # definice identifikatoru        
        self._name = name
        self._parent = parent
        self._last_run = None        

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return 'mdi:timer'

        
    def set_turn_on(self):
        raise ValueError('For children entity not allowed')

    def set_turn_off(self):
        raise ValueError('For children entity not allowed')

    def set_last_run(self):
        """ Update attributu ATTR_LAST_RUN """
        self._last_run = datetime.datetime.now() 
        self.async_schedule_update_ha_state()
    
    async def async_added_to_hass(self):        
        """Run when entity about to be added."""
        await super().async_added_to_hass()        
        old_state = await self.async_get_last_state()
        if old_state is not None:                            
            self._last_run =  old_state.attributes.get(ATTR_LAST_RUN, self._last_run)                       

class CasovacHlavni(TurnonoffEntity):
    def __init__(self, hass, object_id, name, pocet, cfg):
        """Inicializace hlavni ridici class"""
        super().__init__(hass, object_id, True, name)        
        self._pocet = pocet                                 # pocet zadefinovanych casovacu
        self._cfg = cfg                                     # konfigurace v dane domene
        self._hass = hass                                   # uschovani classu hass
        self._active_entity_id = None                       # active child
        self._state = STATE_ON                              

    def reset_timers(self):
        for _, entity in self._hass.data[DOMAIN][O_CHILDREN]:
            entity.reset_timers()

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Navrat nazvu hlavniho casovace"""
        return self._name

    def pravidelny_interval(self, now):        
        # prohibited to be async - not working in loop
        # missing of parameter 'now' caused not working without warning

        _LOGGER.debug("Pravidelny interval:" + self.entity_id)
        podminka = self._cfg.get(CONF_CONDITION)
        if podminka != None:
            if self.hass.states.get(podminka).state != "on":                
                _LOGGER.debug("Podminka shodila volani")
                return        
        _LOGGER.debug("Volam sluzbu "+ DOMAIN + " - " + SERVICE_RUN_CASOVAC + " pro: " + self.entity_id)
        self._hass.services.call(DOMAIN, SERVICE_RUN_CASOVAC, { "entity_id": self.entity_id }, False) 
    
    def set_turn_on(self):
        self._state = STATE_ON
        self.async_schedule_update_ha_state()

    def set_turn_off(self):
        self._state = STATE_OFF
        self.async_schedule_update_ha_state()

    @property
    def state(self):
        """Return the state of the component."""
        return self._state

    def run_casovac(self):        
        """ Hlavni funkce, ktera vraci jaka sluzba se bude volat v zavislosti na casovych intervalech """
        self._active_entity_id = None

        if self._state == STATE_OFF:
            return

        _LOGGER.debug("Hledam aktivni interval pro: "+self.entity_id)

        # Vlastni hledani aktivniho intervalu
        i = 1
        
        praveTed = datetime.datetime.now() 

        while (self._active_entity_id == None) and (i <= self._pocet):        
            entity_id = get_child_object_id(self.entity_id, i)
            
            entity = self.hass.states.get(entity_id)
            # Nacitam atributy dane entity
            if (entity == None) :
                _LOGGER.error("FATAL! Not found entity: " + entity_id)
                return
            attr = entity.attributes

            start_time = attr[ATTR_START_TIME]
            end_time = attr[ATTR_END_TIME]
            if (praveTed >= prevedCasPar(start_time, praveTed)) and (praveTed <= prevedCasPar(end_time, praveTed)):        
                # aktivni cas a nasel jsem
                self._active_entity_id = entity_id
            i = i + 1

        # V zavislosti je-li v casovem intervalu spoustim prikaz
        if self._active_entity_id == None :
            toDo = self._cfg.get(CONF_COMMAND_OFF)
        else:
            # Bude se nastavovat
            toDo =self._cfg.get(CONF_COMMAND_ON)
            # Dame jeste posledni beh
            # _LOGGER.debug(">>>>>Pokus  o zavolani:"+SERVICE_SET_TIME+"....."+aktivni_entity.entity_id)
            # self.hass.services.async_call(DOMAIN, SERVICE_SET_TIME, { "entity_id": aktivni_entity.entity_id}, False)
            # bez sance
            # nahrazeno pres hass.data
            _ , entity_id = split_entity_id(self._active_entity_id)
            active_object = self.hass.data[DOMAIN][O_CHILDREN][entity_id]
            active_object.set_last_run()   # children
            self.set_last_run()            # parent
        
        # navratova hodnota
        retVal = {
            R_HASS: self.hass,                                  # mozna to jde jinak, ale neumim            
            R_TODO: toDo,                                       # volany prikaz (turn_off/turn_on)
            R_ENTITY_ID: self._cfg.get(CONF_ACTION_ENTITY_ID)   # volana entita
        }        
        self.async_schedule_update_ha_state()                        
        return retVal
    
    def set_time(self, start_time, end_time):
        """ Prazdna funkce v pripade volani pro tuto entitu """ 
        _LOGGER.debug("FATAL")
        return

    async def async_added_to_hass(self):        
        """Run when entity about to be added."""
        await super().async_added_to_hass()        
        old_state = await self.async_get_last_state()
        if old_state is not None:                        
            self._state  = old_state.state
            
    @property
    def state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_LAST_RUN: self._last_run,
            ATTR_ACTIVE_ENTITY_ID : self._active_entity_id
        }
        return attrs
    
            

class Casovac(TurnonoffEntity):
    """Casovac entita pro jednotlive zadefinovane casy."""

    def __init__(self, hass, object_id, name, start_time, end_time):
        """Inicializace casovac"""
        super().__init__(hass, object_id, True, name)                        
        self._start_time = start_time                         # zacatek casoveho intervalu
        self._end_time = get_end_time(start_time, end_time)   # konecny cas                
        self._start_time_init = self._start_time
        self._end_time_init = self._end_time
        
    async def async_added_to_hass(self):        
        """Run when entity about to be added."""
        await super().async_added_to_hass()                
        old_state = await self.async_get_last_state()
        if old_state is not None:                        
            self._start_time  = old_state.attributes.get(ATTR_START_TIME, self._start_time)           
            self._end_time  = old_state.attributes.get(ATTR_END_TIME, self._end_time)           
            

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Navrat jmena pro Casovac."""
        return self._name

    @property
    def state(self):
        """Return the state of the component."""
        return self._start_time + " - " + self._end_time


    @property
    def state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_START_TIME:        self._start_time,
            ATTR_END_TIME:          self._end_time,
            ATTR_LAST_RUN:          self._last_run,
            ATTR_START_TIME_INIT:   self._start_time_init,
            ATTR_END_TIME_INIT:     self._end_time_init
        }
        return attrs

    def reset_timers(self):
        """Reseting time from initialisation"""
        self._start_time = self._start_time_init
        self._end_time = self._end_time_init
        self.async_schedule_update_ha_state()
                
    def set_time(self, start_time, end_time):
        """ Service uvnitr jednotliveho casovace. """        
        _LOGGER.debug("Setting new start_time:")
        _LOGGER.debug(start_time)
        if start_time is None:
            start_time = self._start_time
        else:
            self._start_time = time_to_string(start_time)
            
        if end_time is not None:            
            self._end_time = time_to_string(end_time)            
        self.async_schedule_update_ha_state()


    def async_run_casovac(self):
        """V tomto pripade se nepouziva."""        
        return 