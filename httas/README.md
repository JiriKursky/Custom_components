# Httas

You can completely switch off MQTT on your Tasmonta device

in *configuration.yaml* section *switches*
```yaml
- platform: httas
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
- platform: httas
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
