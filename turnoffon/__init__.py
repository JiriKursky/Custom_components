"""
Component for controlling devices in regular time

Version is still not stable and wrong configuration can lead to frozen system

Tested on under hass.io ver. 0.93.2 


Releases:

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
from homeassistant.helpers.event import async_call_later

DOMAIN = 'turnoffon'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

from inspect import currentframe, getframeinfo
_LOGGER = logging.getLogger(__name__)

LI_NO_DEFINITION = 'No entity added'

CONF_TIMERS             = 'timers'
CONF_FORCE_TURN         = 'force_turn'
CONF_TIMERS_MEMORY      = 'timers_memory'
CONF_ACTION_ENTITY_ID   = 'action_entity_id'    # what to call as controlling entity during comand_on, comannd_off
REFRESH_INTERVAL = 59
SHUT_DOWN = False                               # shutting down on stop HA

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

ATTR_ACTIVE_CHILD_ID   = 'active_child_id'
# There are several entities defined by this routine, but only one have to be active in interval


def my_debug(s):
    cf = currentframe()
    line = cf.f_back.f_lineno
    if s is None:
            s = ''
    _LOGGER.debug("line: {} -> {}".format(line, s))

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
            vol.Optional(CONF_TIMERS_MEMORY): cv.boolean,
            vol.Required(CONF_ACTION_ENTITY_ID): cv.entity_id,            
            vol.Optional(CONF_CONDITION): cv.entity_id,
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_COMMAND_ON, default = SERVICE_TURN_ON): cv.string,
            vol.Optional(CONF_COMMAND_OFF, default = SERVICE_TURN_OFF): cv.string,
            vol.Optional(CONF_FORCE_TURN, default = True): cv.boolean,
        })
    )
}, extra=vol.ALLOW_EXTRA)

def get_child_object_id(parent, number):
    """ Returning child object entity_id """
    if number < 10:
        s_number = "0" + str(number) 
    else:
        s_number = str(number) 
    return "{}_{}".format(parent, s_number)

async def async_setup(hass, config):
    """First setup."""
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
            i += 1            
            new_object_id = get_child_object_id(object_id, i)
            name = "{} {}".format(parent_name, i)
            
            # definition of children
            entity = Casovac(hass, new_object_id, name, start_time, end_time)
            my_debug("entity: {} setting up: {}".format(entity, new_object_id))              
            hass.data[DOMAIN][O_CHILDREN][new_object_id] = entity            
            entities.append(entity)
        
        # Create entity_id
        casovacHlavni = CasovacHlavni(hass, object_id, parent_name, i, cfg)

        # Push to store
        hass.data[DOMAIN][O_PARENT][object_id] = casovacHlavni        

        # Setting main timer - loop for checking interval
        """
        memory = cfg.get(CONF_TIMERS_MEMORY)
        if memory is None:
            memory = False
        if memory:
            async_call_later(hass, REFRESH_INTERVAL, casovacHlavni.set_to_memory())
        else:
            async_call_later(hass, REFRESH_INTERVAL, casovacHlavni.regular_loop())
        """
        async_call_later(hass, REFRESH_INTERVAL, casovacHlavni.regular_loop())
        entities.append(casovacHlavni)        
    if not entities:
        _LOGGER.info(LI_NO_DEFINITION)    
        return False
    

    # Musi byt pridano az po definici vyse - je potreba znat pocet zaregistrovanych casovacu    
    async def async_run_casovac_service(entity, call):
        """Main procedure. Called from parent entity """                
        # entity is parent entity
        #----------------------------
        # main procedure
        my_debug("calling get us what to do")
        await entity.run_casovac()
        #----------------------------
        
        # what will be controlled
        try:        
            action_entity = entity.hass.states.get(entity.action_entity_id)
            target_domain, _ = split_entity_id(action_entity.entity_id)
            to_do = entity.to_do
        except:
            _LOGGER.error("Wrong entity {}".format(entity.action_entity_id))
            return
        

        # volam sluzbu, ktera zapne nebo vypne danou entitu               
                
        call_service =  ((entity._set_on(to_do) and not is_on(action_entity)) or (not entity._set_on(to_do) and is_on(action_entity))) or entity.force_turn
        my_debug('>>>>>>>>>>>>> what: {} set_on: {} is_on: {} {} {} <<<<<<<<<<<<<<'.format(call_service, entity._set_on(to_do), is_on(action_entity), entity.force_turn, entity.entity_id))
                
        
        if call_service:
            my_debug("calling service {} {} {}".format(target_domain, to_do, action_entity.entity_id))
                    
            """
            state = entity.action_entity_id.get_state()
            my_debug("Called {} is in state {}".format(calling_entity_id, state))
            """
            # Calling entity to switch off or on
            await hass.services.async_call(target_domain, to_do, { "entity_id": action_entity.entity_id }, blocking=True)
        else:
            my_debug("entity {} in right state, {} not necessary".format(action_entity.entity_id, to_do))

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
                            
            my_debug("Called service for: {}".format(entity.entity_id))
            entity.set_time(start_time, end_time)        
        except:
            raise ValueError('Wrong time parametres')        
    component.async_register_entity_service(
        SERVICE_SET_TIME, SERVICE_SET_TIME_SCHEMA, 
        async_set_time_service
    )
    
    async def async_set_turn_on_service(entity, call):        
        """Calling entity to turn_on."""        
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
        my_debug("Shutting down")
        SHUT_DOWN = True                
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_turnoffon)

    return True

def is_on(entity):
    return entity.state == STATE_ON

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
"""
# configuration example
filtrace:
  name: Filtrace
  action_entity_id: input_boolean.filtrace
  # what will be controlled
  
  timers: { "6:10":50, "10:10":30, "12:00":50, "13:10":2, "15:00":20, "16:00":30, "17:00":20, "17:30":20, "18:00":50, "20:00":30, "21:20":5 }        
  #from timers will be children

  condition: input_boolean.filtrace_timer
  # parent      turnoffon.filtrace
  # children    turnoffon.filtrace_01,....
"""

class CasovacHlavni(TurnonoffEntity):
    """ Parent entity """
    def __init__(self, hass, object_id, name, pocet, cfg):
        """Inicializace hlavni ridici class"""
        super().__init__(hass, object_id, True, name)        
        self._pocet = pocet                                 # pocet zadefinovanych casovacu
        self._cfg = cfg                                     # konfigurace v dane domene
        self._hass = hass                                   # uschovani classu hass
        self._active_child_id = None                       # active child
        self._state = STATE_ON  
        self._turn_on = cfg.get(CONF_COMMAND_ON)
        self._turn_off = cfg.get(CONF_COMMAND_OFF)
        self.action_entity_id = cfg.get(CONF_ACTION_ENTITY_ID)
        self._condition = cfg.get(CONF_CONDITION)
        self.force_turn = cfg.get(CONF_FORCE_TURN)        
        
    def _set_on(self, to_do):
        """ Returning if set command """
        return self._turn_on == to_do

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

    async def set_to_memory(self):
        my_debug("Setting to memory: {}".format(self.entity_id))

    async def regular_loop(self):        
        """ Regular interval for turn_on turn_off """

        if SHUT_DOWN:
            my_debug("Shutting down")
            return

        my_debug("Regular interval: {}".format(self.entity_id))        
        if self._condition != None:
            try:
                entity = self.hass.states.get(self._condition)                
                entity_is_on = is_on(entity)
            except:
                my_debug("Not found conditional entity. Setting to off - nothing will happen")
                entity_is_on = False
            if not entity_is_on:                
                my_debug("Condition stop calling")
                async_call_later(self.hass, REFRESH_INTERVAL, self.regular_loop())
                return        
        my_debug("Calling service: {} - {} for: {} ".format(DOMAIN, SERVICE_RUN_CASOVAC, self.entity_id))  
        await self.hass.services.async_call(DOMAIN, SERVICE_RUN_CASOVAC, { "entity_id": self.entity_id })            
        my_debug("asking for call later after {} seconds".format(REFRESH_INTERVAL))        
        async_call_later(self.hass, REFRESH_INTERVAL, self.regular_loop())
    
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

    async def run_casovac(self):        
        """  """
        my_debug("running timer searching")
        self._active_child_id = None

        # It means if state of parent
        if self.state != STATE_ON:
            my_debug("{} is not on. Not seaching".format(self.entity_id))
            return

        my_debug("Searching interval for: {}".format(self.entity_id))

        # Searching for active interval
        i = 1        
        praveTed = datetime.datetime.now() 

        while (self._active_child_id == None) and (i <= self._pocet):        
            entity_id = get_child_object_id(self.entity_id, i)
            
            entity = self.hass.states.get(entity_id)
            # Nacitam atributy dane entity
            if (entity == None) :
                my_debug("FATAL! Not found entity: {}".format(entity_id))
                return
            attr = entity.attributes

            start_time = attr[ATTR_START_TIME]
            end_time = attr[ATTR_END_TIME]
            if (praveTed >= prevedCasPar(start_time, praveTed)) and (praveTed <= prevedCasPar(end_time, praveTed)):        
                my_debug("active entity in period: {}".format(entity_id))
                self._active_child_id = entity_id
            i = i + 1

        # V zavislosti je-li v casovem intervalu spoustim prikaz
        if self._active_child_id == None :
            self.to_do = self._turn_off
        else:
            # Bude se nastavovat
            self.to_do = self._turn_on
            # Dame jeste posledni beh
            # _LOGGER.debug(">>>>>Pokus  o zavolani:"+SERVICE_SET_TIME+"....."+aktivni_entity.entity_id)
            # self.hass.services.async_call(DOMAIN, SERVICE_SET_TIME, { "entity_id": aktivni_entity.entity_id}, False)
            # bez sance
            # nahrazeno pres hass.data
            _ , entity_id = split_entity_id(self._active_child_id)
            active_object = self.hass.data[DOMAIN][O_CHILDREN][entity_id]
            active_object.set_last_run()   # children
            self.set_last_run()            # parent
                
        self.async_schedule_update_ha_state()                        
        return self
    
    def set_time(self, start_time, end_time):
        """ Prazdna funkce v pripade volani pro tuto entitu """ 
        my_debug("FATAL")
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
            ATTR_ACTIVE_CHILD_ID : self._active_child_id
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
        return "{} - {}".format(self._start_time,  self._end_time)


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
        my_debug("Setting new start_time: {}".format(start_time))        
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