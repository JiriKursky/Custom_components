# Simple defining several timers for controlling devices during day
For instance filtration in swimming pool
Tested on *hass.io* ver. 0.93.2 
> **Warning:**
> Still not absolutely safe for wrong config. Be sure that you backup your HA.

Installation: 
1. Create sub-folder *turnoffon* in folder *config/custom_components* and simply copy files 
2. Change your *configuration.yaml*. Platform *turnoffon*

Example of turn_on/turn_of of filtration in intervals:
10:20 - 20 minutes
17:00 - 20:50

In these intervals will each minute calling service *turn_on* - *input_boolean.filtration". Outside then *turn_off*. 

You can stop calling with condition explained below or with state = 'off' of parent entity.

Add to your *configuration.yaml*
```yaml
turnoffon:
    filtration:
      action_entity_id: input_boolean.filtration
      timers: { "10:20":20, "17:00":"20:50" }      
```
Compomnent automatically create *turnoffon.filtration* - main (parent for controlling) and *turnoffon.filtration_01* , *turnoffon.filtration_02* (children). "Automation is automatically" in component
That's all!

*You can use more complex solution with several parents and their children*
*configuration.yaml*:

```yaml
turnoffon:
    filtration:
      action_entity_id: input_boolean.filtration
      timers: { "6:10":50, "10:10":30, "12:00":30, "13:10":2, "15:00":20, "17:00":20, "18:00":50, "20:00":30, "21:20":5 }      
      condition_run: input_boolean.filtration_timer
    pump:
      action_entity_id: input_boolean.pump
      timers: { "6:05":15, "07:00":15, "08:05":15, "08:45":15, "09:30":15, "10:15":15, "14:00":15, "16:05":15, "18:00":15, "19:00":15, "20:15":15, "21:05":15, "22:15":15, "22:55":15 }      
      condition_run: input_boolean.pump_timer
    sprinkler_1:
      action_entity_id: input_boolean.sprinkler_1
      name: Area 1
      timers: { "12:00":"16:00","21:00":"22:00" }      
    sprinkler_2:
      action_entity_id: input_boolean.sprinkler_2
      name: Area 2
      timers: { "8:00":"10:00","16:00":"18:00" }      
    sprinkler_3:
      action_entity_id: input_boolean.sprinkler_3
      name: Area 3
      timers: { "6:00":"8:00","18:00":"20:00" }      
    sprinkler_4:
      action_entity_id: input_boolean.sprinkler_4
      name: Area 4
      timers: { "10:00":"12:00","22:00":"23:59" }
```
Explanation
```yaml
turnoffon:    
    # Entity domain - do not change
    #
    filtration:
    # Entity_id. Will be created turnoffon.filtration
    #
      action_entity_id: input_boolean.filtration
      # Will be called with turn_on in defined interval and with turn_off outside this interval      
      #
      timers: { "6:10":50, "10:10":30, "12:00":30, "13:10":2, "15:00":20, "17:00":20, "18:00":50, "20:00":30, "21:20":5 }      
      # Definition turn_on intervals 
      # "6:10":50 start at 6:10 for 50 minutes - do not exceed 59 minutes! do not put commas etc 
      # warning do not use "24:00"
      # ----------------
      # Second possibilty of define timer "6:10":"8:00" 
      condition_run: input_boolean.filtration_timer
      # App is testing this for 'on' or 'off'. You will stop automatisation. I am using for instance for sprinkler in rainy days      
```

You can find useful attributes in entities. There are several serices.
