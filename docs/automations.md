# Automation Examples

Practical automation blueprints using Stroomprijsprognose sensors.

## Run Appliance When Price is Low

Triggers when the current hour price drops below a threshold:

```yaml
alias: "Dishwasher on cheap power"
description: "Start dishwasher when electricity price drops below 18 ct/kWh"
trigger:
  - platform: numeric_state
    entity_id: sensor.stroomprijsprognose_current_price
    below: 18
condition:
  - condition: state
    entity_id: input_boolean.dishwasher_ready
    state: "on"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.dishwasher
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.dishwasher_ready
mode: single
```

## Schedule Appliance at Cheapest Time

Use the cheapest slot timestamp to schedule an appliance:

```yaml
alias: "Schedule washing machine at cheapest hour"
description: "Start washing machine at the cheapest forecast hour"
trigger:
  - platform: time_pattern
    minutes: "/5"
condition:
  - condition: template
    value_template: >
      {% set t = state_attr('sensor.stroomprijsprognose_current_price', 'cheapest_slots')[0].timestamp %}
      {{ as_datetime(t).hour == now().hour + 1 }}
action:
  - service: switch.turn_on
    target:
      entity_id: switch.washing_machine
mode: single
```

## Notify When Negative Prices

Send a phone notification when prices go negative:

```yaml
alias: "Negative electricity price alert"
description: "Notify when electricity price drops below zero"
trigger:
  - platform: numeric_state
    entity_id: sensor.stroomprijsprognose_current_price
    below: 0
action:
  - service: notify.mobile_app_my_phone
    data:
      title: "Free electricity!"
      message: >
        Current price: {{ states('sensor.stroomprijsprognose_current_price') }} ct/kWh.
        Lowest today: {{ state_attr('sensor.stroomprijsprognose_current_price', 'cheapest_slots')[0].timestamp }}
```

## Price Dashboard Card

Lovelace card showing price forecast as a bar chart:

```yaml
type: custom:apexcharts-card
graph_span: 24h
span:
  start: hour
header:
  show: true
  title: Electricity Price Forecast
  show_states: true
series:
  - entity: sensor.stroomprijsprognose_current_price
    attribute: hourly_prices
    data_generator: |
      return entity.attributes.hourly_prices.map((slot) => {
        return [new Date(slot.timestamp), slot.retail_total_ct_kwh];
      });
    type: column
    color: "#FF9800"
    unit: ct/kWh
```

## Charge EV at Cheapest 4 Hours

For EV chargers with scheduled charging:

```yaml
alias: "EV charge at cheapest hours"
description: "Find cheapest 4-hour block and charge EV"
trigger:
  - platform: time_pattern
    hours: "22"
condition: []
action:
  - variables:
      cheapest: >
        {% set slots = state_attr('sensor.stroomprijsprognose_current_price', 'cheapest_slots') %}
        {% set sorted = slots | sort(attribute='timestamp') %}
        {{ sorted[:4] | map(attribute='timestamp') | list }}
  - service: ev_smart_charging.set_schedule
    data:
      times: "{{ cheapest }}"
mode: single
```

## Heat Pump Optimization

Avoid running heat pump during expensive hours:

```yaml
alias: "Reduce heat pump during price peaks"
description: "Lower heat pump target when price is high"
trigger:
  - platform: numeric_state
    entity_id: sensor.stroomprijsprognose_current_price
    above: 30
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.heat_pump
    data:
      temperature: 18
mode: single
```

## Price-Based Battery Control

Discharge battery when prices are high:

```yaml
alias: "Battery discharge on high price"
description: "Force battery discharge when price exceeds threshold"
trigger:
  - platform: numeric_state
    entity_id: sensor.stroomprijsprognose_current_price
    above: 35
action:
  - service: select.select_option
    target:
      entity_id: select.battery_operation_mode
    data:
      option: "Force discharge"
```

## Best Time Helper

Template sensor that shows a human-readable "best time to run appliances" string:

```yaml
template:
  - sensor:
      - name: "Best Time for Appliances"
        state: >
          {% set cheapest = state_attr('sensor.stroomprijsprognose_current_price', 'lowest_next_8h') %}
          {% if cheapest %}
            {% set t = as_datetime(cheapest[0].timestamp) %}
            {{ t.strftime('%H:%M') }} ({{ cheapest[0].retail_total_ct_kwh }} ct/kWh)
          {% else %}
            No data
          {% endif %}
```
