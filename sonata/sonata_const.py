from datetime import timedelta
from homeassistant.const import  TEMP_CELSIUS

R_STATUS_CODE = 'STATUS_CODE'
R_CONTENT = 'CONTENT'
R_POWER = 'POWER'

CMND_STATUS = 'status%208'
CMND_POWER = 'POWER'
CMND_POWER_ON = 'Power%20On'
CMND_POWER_OFF = 'Power%20Off'

S_CMND = "CMND"
S_VALUE = "VALUE"
S_UNIT = "UNIT"
S_SCAN_INTERVAL = "SCAN_INTERVAL"
S_ICON = 'ICON'

ST_TEMPERATURE = 'temperature'
ST_CURRENT = 'current'
ST_VOLTAGE = 'voltage'

SENSORS = {
    ST_TEMPERATURE :{ 
        S_CMND: CMND_STATUS,
        S_VALUE:  ["StatusSNS", "DS18B20","Temperature"] ,
        S_SCAN_INTERVAL: timedelta(seconds=30),
        S_UNIT:   TEMP_CELSIUS,
        S_ICON: ''
    },
    ST_VOLTAGE: {
        S_CMND: CMND_STATUS,
        S_VALUE:  ["StatusSNS","ENERGY", "Voltage"] ,
        S_SCAN_INTERVAL: timedelta(seconds=30),
        S_UNIT:   'V',
        S_ICON: ''
    }, 
    ST_CURRENT: {
        S_CMND: CMND_STATUS,
        S_VALUE:  ["StatusSNS", "ENERGY", "Current"] ,
        S_SCAN_INTERVAL: timedelta(seconds=10),
        S_UNIT: 'A',
        S_ICON: 'mdi:current-ac'
    }
}


