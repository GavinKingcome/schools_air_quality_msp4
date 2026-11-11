# Sensor distance and the adjusted method

*Notes on whether a reference sensor up to 2 km away can give a fair estimate for a school or nursery. Written 4 November 2026, updated 10 November 2026.*

## The question

`assign_sensors` lets a school use a reference-grade sensor (LAQN, the London Air Quality Network, or AQE, Air Quality England) up to 2 km away. In a city, a lot can change pollution levels over 2 km. Sensors are sparse, so a long distance is needed to cover many schools. But does a sensor that far away lose its value?

## The short answer

Less than you might expect, because of **what** the method takes from the sensor. **The type of site matters more than the distance.**

## The sensor isn't telling you the school's pollution level

In the "adjusted" method, the school's pollution level comes from **LAEI** (the London Atmospheric Emissions Inventory), at the school's own 20 m square. That's where the street-by-street detail is found.

The sensor only supplies a **ratio**: how pollution right now compares with a normal day at that sensor.

```
school estimate = LAEI value at the school × (sensor now ÷ sensor annual average)
```

So a sensor 2 km away isn't saying "the school has 48 µg/m³ of NO₂". It's saying "right now, pollution is about 20% above normal". That's different, and it holds over a much wider area.

## Why the ratio holds over a distance

Much of what makes pollution rise and fall hour by hour is shared across a wide area:

- **Weather.** Still, cold, foggy days trap pollution everywhere. Windy days clear it everywhere.
- **The daily rhythm.** Morning and evening rush hours happen across the whole city at about the same time.
- **Pollution blown in.** Some particles come from far outside London, sometimes from mainland Europe.

So a school and a sensor 2 km apart often rise and fall together, even when their actual levels are very different. Background sites across London tend to track each other closely in this way, and that's the idea the method relies on. (This is worth confirming with published comparisons of LAQN sites for the methods write-up.)

## Where it breaks down: site type

**A roadside site reacts to its own road.** Brixton Road (LB4) is a busy roadside site. Its 2025 annual NO₂ average was 48 µg/m³, nearly three times Streatham Green's (LB6) 17 µg/m³. Its ups and downs include things that only happen on that road: a traffic jam, a bus queue, a closed lane. A school on a quiet street 1 km away doesn't share those, so the ratio can mislead, even from nearby.

**An urban background site reflects the general air of the area.** Its ratio is much more likely to match a school's, even from further away.

So **an urban background site 1.8 km away may be a better guide than a roadside site 500 m away.**

## Ways to make it better

1. **Prefer background sites.** When choosing a reference, favour urban background sites. Only fall back to a roadside site if there's no background site in range.
2. **Use more than one site.** Average the ratios from the two or three nearest reference sites, so a one-off spike on one road gets diluted.
3. **Smooth the hour.** A single hourly reading can jump about. Using the average of the last three hours makes the ratio steadier.

## Testing it with our own data

Four "direct" schools each have a Breathe London sensor within 62 metres, so for those schools we know the actual level at the school:

| School | Sensor | Distance |
|---|---|---|
| Oliver Goldsmith Primary | BL0084 | 61.7 m |
| St Anne's Catholic Primary | BL0057 | 15.6 m |
| Stockwell Primary | BL0068 | 14.9 m |
| Sunnyhill Primary | BL0100 | 44.7 m |

For each one, work out what the adjusted method **would have** estimated, using LAEI and the nearest reference site. Then compare it with what the school's own Breathe sensor measured. Do that over a few weeks, and there's real evidence of how well the method works. The same test can compare a background reference against a roadside one.

## Added 10 November 2026: Breathe London sensors as a fallback

When no reference sensor is within 2 km, a Breathe London sensor (a lower-cost, calibrated sensor) within 2 km can supply the ratio instead.

**Why that works.** The top and bottom of the ratio come from the **same device**. If a sensor always reads, say, 10% high, its "now" reading and its annual average are both 10% high, and the error cancels:

| Sensor | Reads | Now | Annual average | Ratio |
|---|---|---|---|---|
| Perfect | exactly right | 40 | 30 | 1.33 |
| Reference | 2% high | 40.8 | 30.6 | 1.33 |
| Breathe | 10% high | 44 | 33 | 1.33 |

**What doesn't cancel:**

- **A fixed offset.** A sensor that always reads 5 µg/m³ too high gives (40 + 5) ÷ (30 + 5) = 1.29, not 1.33. Real changes look smaller than they are.
- **Errors that change with the weather.** Particle sensors read high in damp air; NO₂ sensors are affected by temperature. Reference instruments are built to avoid this.
- **Drift, or a swapped device.** If the sensor has drifted or been replaced since its annual average was measured, the error differs between top and bottom.

So reference and Breathe sensors both benefit from the cancelling, but a reference sensor has much less error left over. That's why Breathe-adjusted schools should show a **lower confidence**, and name the network in the popup.

**A note on Breathe data.** The Breathe London network changed operator and hardware: the Imperial College network ended on 14 December 2024, and a Vodafone-led consortium installed new devices between March and July 2025. Data from before and after the change come from different devices, so they must never be mixed in one ratio. The Breathe averages therefore use the last 12 full months (November 2025 to October 2026), all from the new devices.

## Related roadmap items

- Better reference sensors: prefer background sites, average the nearest two or three, smooth over three hours.
- Validation test at the four direct schools.
- "Reference first, or nearest first?": test whether a distant reference sensor or a nearby Breathe sensor gives better adjusted estimates.
