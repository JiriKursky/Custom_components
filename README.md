# Časovač pro řízení filtrace nebo čehokoli a vůbec
Testováno na *hass.io* ver. 0.93.2 
Navazuje na původní [python_script verzi](https://github.com/JiriKursky/Hass.io_CZ_SK), která byla šílená na konfiguraci.
V tomto případě stačí jen stáhnout komponentu a provést konfiguraci. Žádné *automations.yaml* mimo volané entity k zapnutí a vypnutí zařízení.

> **Upozornění:**
_Prosím pozor na verzi z 2.6.2019. Oproti předchozí je změna ve tvorbě entit, kde se místo přidání k základní připojovalo k enitě _1, _2 teď je _01, _02. Nemá to vliv, pokud jste to nevyužili jako zobrazení state. Vzhledem k tomu, že jsem nepřítelem těchto změn, slibuji, že dále již budu zachovávat kompatibilitu.

> **Upozornění:**
> Konfigurace není úplně blbovzdorná, i když jsem to testoval, může shodit systém.
Kde se může stát chyba je v konfiguraci, proto si zazálohujte *configuration.yaml* než do něj sáhnete. Doporučuji mít zvenku přístup na soubory pomocí [Samby](https://www.home-assistant.io/addons/samba/) nebo [SSH](https://www.home-assistant.io/addons/ssh/). Přinejhorším vrátíte zálohu konfigurace nebo smažete komponentu *turnoffon* ve složce *config/custom_components*.

Pro instalaci potřebujete následující znalosti: 
1. Vytvořit složku *turnoffon* ve složce *config/custom_components* soubory, který naleznete [zde](https://github.com/JiriKursky/Hass.io_CZ_SK_custom_components/tree/master/turnoffon)
2. Upravit soubor *configuration.yaml*. (Jak na to, naleznete na youtube, například [zde](https://youtu.be/7mhFcJf6WqQ))

> Program se chová tak, že v definovaný interval volá každou minutu službu *turn_on*, mimo něj *turn_off*.

Minimalistické řešení. Filtrace bude ve dvou intervalech 10:20 - 20 minut a pak od 17:00 do 20:50.
Zapíná se a vypíná entita *input_boolean.filtrace_zapni*
Příklad co přidat do *configuration.yaml*:
```yaml
turnoffon:
    filtrace:
      action_entity_id: input_boolean.filtrace_zapni
      timers: { "10:20":20, "17:00":"20:50" }      
```
Toť vše.

Složitější řešení - několik intervalů
*configuration.yaml*:

```yaml
turnoffon:
    filtrace:
      action_entity_id: input_boolean.filtrace_zapni
      timers: { "6:10":50, "10:10":30, "12:00":30, "13:10":2, "15:00":20, "17:00":20, "18:00":50, "20:00":30, "21:20":5 }      
      condition_run: input_boolean.filtrace_timer
    cerpadlo:
      action_entity_id: input_boolean.cerpadlo_zapni
      timers: { "6:05":15, "07:00":15, "08:05":15, "08:45":15, "09:30":15, "10:15":15, "14:00":15, "16:05":15, "18:00":15, "19:00":15, "20:15":15, "21:05":15, "22:15":15, "22:55":15 }      
      condition_run: input_boolean.cerpadlo_timer
    postrik_1:
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
