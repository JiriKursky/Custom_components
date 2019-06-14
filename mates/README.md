# This component substitue Sonoff MQTT broker server using http in internal link. No calling outside, no opening ports

Tested on hass.io ver. 0.93.2, 0.94.0

Installation: 
1. Create sub-folder *sonata* in folder *config/custom_components* and simply copy all [files](https://github.com/JiriKursky/Custom_components/tree/master/sonata)
2. Change your *configuration.yaml*. Platform *turnoffon*

You can completely switch off MQTT on your Tasmonta device

in *configuration.yaml* section *switches*
```yaml
- platform: mates
  switches:
    filtration:
      ip_address: xxx.xxx.x.xx # ip address sonnoff controlling filtration
      friendly_name: Filtration sonoff          
    subwoofer:
      friendly_name: Subwoofer
      ip_address: xxx.xxx.x.xx # ip address sonnoff controlling subwoofer        
```
In case of sensors. Just now supporting DS18B20 for temperature and current.

Sensors
```yaml
- platform: mates
  sensors:
    filtration:      
      ip_address: xxx.xxx.x.xx 
      friendly_name: Temperature
      sensor_type: temperature    
    subwoofer:      
      ip_address: xxx.xxx.x.xx
      friendly_name: Subwoofer current      
      sensor_type: current                  
```
In case of issues report it [here](https://github.com/JiriKursky/Hass.io_CZ_SK_custom_components/issues)
