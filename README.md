# Simple defining several timers for controlling devices during day
For instance filtration in swimming pool
Tested on *hass.io* ver. 0.93.2 
> **Warning:**
> Still not absolutely safe with bad config. Be sure that you backup your HA.

Installation: 
1. Create sub-folder *turnoffon* in folder *config/custom_components* and simply copy files 
2. Change your *configuration.yaml*. Platform *turnoffon*

> Basically app check intervals each minutesProgram se chová tak, že v definovaný interval volá každou minutu službu *turn_on*, mimo něj *turn_off*.

Exapmle of turn_on/turn_of of filtration in intervals:
10:20 - 20 minutes
17:00 - 20:50

In these intervals will each minute calling service *turn_on* - *input_boolean.filtration". Outside then *turn_off*. This helps with restart of HA etc.

Add to your *configuration.yaml*
```yaml
turnoffon:
    filtration:
      action_entity_id: input_boolean.filtration
      timers: { "10:20":20, "17:00":"20:50" }      
```
Compomnent automatically create *turnoffon.filtration* - main (parent for controlling) and *turnoffon.filtration_01* (child). "Automation is automatically" in component
That's all!

*You can use more complex solution with several parents and their children*
*configuration.yaml*:

```yaml
turnoffon:
    filtration:
      action_entity_id: input_boolean.filtration
      timers: { "6:10":50, "10:10":30, "12:00":30, "13:10":2, "15:00":20, "17:00":20, "18:00":50, "20:00":30, "21:20":5 }      
      condition_run: input_boolean.filtrace_timer
    pump:
      action_entity_id: input_boolean.pump
      timers: { "6:05":15, "07:00":15, "08:05":15, "08:45":15, "09:30":15, "10:15":15, "14:00":15, "16:05":15, "18:00":15, "19:00":15, "20:15":15, "21:05":15, "22:15":15, "22:55":15 }      
      condition_run: input_boolean.cerpadlo_timer
    sprinlger_1:
      action_entity_id: input_boolean.postrikovac_1
      name: Spodek
      timers: { "12:00":"16:00","21:00":"22:00" }      
    postrik_2:
      action_entity_id: input_boolean.postrikovac_2
      name: Horejsek
      timers: { "8:00":"10:00","16:00":"18:00" }      
    postrik_3:
      action_entity_id: input_boolean.postrikovac_4
      name: Jahody
      timers: { "6:00":"8:00","18:00":"20:00" }      
    postrik_4:
      action_entity_id: input_boolean.postrikovac_3
      name: Zadek
      timers: { "10:00":"12:00","22:00":"23:59" }
```
Význam jednotlivých položek
```yaml
turnoffon:    
    # Nazev entity - nemenit
    #
    filtrace:
    # Libovolny nazev entity. V tomto pripade bude automaticky zalozena entita s nazvem turnoffon.filtrace
    #
      action_entity_id: input_boolean.filtrace_zapni
      # Co se ma zapnout v danem casovem intervalu volanim turn_on a vypnout volanim turn_off
      # musite zadefinovat v sekci input_boolean a navazat prislusnou automatizaci
      #
      timers: { "6:10":50, "10:10":30, "12:00":30, "13:10":2, "15:00":20, "17:00":20, "18:00":50, "20:00":30, "21:20":5 }      
      # Casovace. Musi zacinat slozenou zavorkou a taktez koncit.
      # co carka, to novy interval
      # vyznam "6:10":50 - bude začínat v 6:10 a zapnuto po dobu 50 minut
      # druhy interval nesmi byt mensi nebo roven nule a nesmi byt vetsi nez 59
      # Pozor na cas 24:00 - nefunguje
      # ----------------
      # Druhy zpusob zapisu je "6:10":"7:00" 
      # Znamena od 6:10 - 7:00. Pokud to nejak prehodite, program to nehlida, nepokouset
      # S druhym zapisem muzete v pohode prekrocit 59 minut
      # ----------------
      # Kazda carka znamena novy interval. Program zalozi turnoffon.filtrace_1, turnoffon.filtrace_2, ...
      # Vzdy pridava _01, _02..._10, _11... , _101, _102 .. _n
      # Pomoci automaticky zalozenych entit - muzete je zobrazit
      #
      condition_run: input_boolean.filtrace_timer
      # Timto je mozno rucne vypnout. Nastavite-li input_boolean v condition run na "off" nebude se nic provadet
      # Pouzivam, pro cerpadlo zavlahy, pokud sensor ukazuje dest - nezalevam
```
