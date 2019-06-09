import logging 
from homeassistant.core import split_entity_id
from homeassistant.helpers.event import async_call_later, async_track_point_in_utc_time
from homeassistant.util import dt as dt_util


_LOGGER = logging.getLogger(__name__)


START_DELAY = 15

def async_call_later_timedelta(hass, interval_delta, action):
    """Add a listener that is called in <delay>."""
    return async_track_point_in_utc_time(
        hass, action, dt_util.utcnow() + interval_delta)


class TimerJaroslavaSoukupa:
    def __init__(self, hass, entity, action, interval):
        # interval must be delta
        self._interval = interval
        self._entity = None
        self._timer_started = False        
        self._in_timer = False
        self._hass = hass                          
        self._entity = entity
        self.action = action
        self._domain, _ =  split_entity_id(entity.entity_id)
        async_call_later(hass, START_DELAY, self._main_loop)        
    
    
    def _main_loop(self, now):                        
        """Regular called"""
        # missing of parameter 'now' caused not working without warning
        # not async!
        #                 

        def _repeat_call(*time_delay):            
        # if no time_dela = standard
            if len(time_delay) == 0:
                 _time_delay = self._interval
            else:
                _time_delay = time_delay[0] # arg            
            async_call_later_timedelta(self._hass, _time_delay, self._main_loop)
            self._in_timer = False
            # To be sure
            return True
        
        # Just to avoid cycle, can be omitted...maybe
        if self._in_timer:
             return True
        self._in_timer = True     
        if self.action is not None:
            self._hass.async_run_job(self.action)  
            _repeat_call()
        self._inTimer = False