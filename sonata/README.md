# This component substitue Sonoff MQTT broker server using http in internal link. No calling outside, no opening ports

Tested on hass.io ver. 0.93.2, 0.94.0

Installation: 
1. Create sub-folder *sonata* in folder *config/custom_components* and simply copy all [files](https://github.com/JiriKursky/Custom_components/tree/master/sonata)
2. Change your *configuration.yaml*. Platform *turnoffon*

in *configuration.yaml* section *switches*
```yaml
- platform: sonata
  username: access
  password: !secret password_mqtt
  switches:
    filtration:
      ip_address: 192.168.1.54
      friendly_name: Filtration sonoff          
    subwoofer:
      friendly_name: Subwoofer
      ip_address: 192.168.1.57        
```
In case of sensors. Just now supporting DS18B20 for temperature and current.

Sensors
```yaml
- platform: sonata
  username: access
  password: !secret password_mqtt
  sensors:
    filtration:      
      ip_address: 192.168.1.54
      friendly_name: Temperature
      sensor_type: temperature    
    subwoofer:      
      ip_address: 192.168.1.57
      friendly_name: Subwoofer current      
      sensor_type: current                  
```
