# Manual check of the 10 pilot events

Adapted from TRACE `pilot/MANUAL_CHECK_10.md`. Filled in after the pilot run. Janice answers
the four questions for each pilot event using the checking page (hydrograph, the floodplain point
on a map, and the first usable image and the acquisitions around it), **before** seeing the pipeline's
reading in the last column.

Questions:

1. **Real flood?** Is there a report (DFO, ReliefWeb, news) of flooding within 50 km within 7 days
   of the GloFAS peak? (Yes / No / Can't tell)
2. **Floodplain point?** Is the chosen point on low, normally dry land next to the river, not in
   the channel, a town or a hill? (Yes / No / Can't tell)
3. **First usable image right?** Does the image the pipeline calls the first usable one actually
   cover the point with valid, cloud-free data? (Yes / No / Can't tell)
4. **Nothing earlier missed?** Looking at all acquisitions between the peak and that image, is
   there an earlier one that should have counted as usable? (No = correct / Yes / Can't tell)

| Event | Place | GloFAS peak | 1 Real flood | 2 Floodplain point | 3 First usable right | 4 Nothing earlier | Pipeline's reading |
|---|---|---|---|---|---|---|---|
| P01 | Brahmaputra near Guwahati | 1 Jul 2024 | Yes | Yes | Yes | No (correct)* | S1, 228 h |
| P02 | Godavari lower reach | 26 Jul 2024 | Yes | Yes | Yes | No (correct) | S1, 168 h |
| P03 | Ganges near Malda | | not checked | n/a | n/a | n/a | below the 5-year flow, no event |
| P04 | Kosi, Bihar | 13 Aug 2017 | Yes | Yes | Yes | No (correct) | S1, 156 h |
| P05 | Jamuna at Bahadurabad | 12 Jul 2020 | Yes | Yes | Yes | No (correct) | S1, 12 h |
| P06 | Indus near Sukkur | | not checked | n/a | n/a | n/a | below the 5-year flow, no event |
| P07 | Mekong near Kratie | | not checked | n/a | n/a | n/a | below the 5-year flow, no event |
| P08 | Chao Phraya near Nakhon Sawan | | not checked | n/a | n/a | n/a | below the 5-year flow, no event |
| P09 | Ayeyarwady near Pyay | | not checked | n/a | n/a | n/a | below the 5-year flow, no event |
| P10 | Brahmaputra near Dibrugarh | | not checked | n/a | n/a | n/a | below the 5-year flow, no event |

Checked by Janice on 23 Nov 2026 on the checking page. \* P01 question 4 was answered with
the assistant's help, so it is not an independent judgment; the other 15 answers are hers alone.
The six events that never reached the 5-year flow have no event to check (PILOT_REPORT.md section 1).

**Go / no-go** (written in `pilot/PILOT_NOTES.md`): the main run starts only if questions 2–4
are Yes for at least 8 of 10 events, or the failures are traced to a fixable bug, fixed, and the
fix recorded.

Also recorded in the pilot notes: time and Earth Engine requests per event; whether the plan issue
time from the file name matches the ZIP entry times; TIGGE and GloFAS request field names that had
to change; and whether Guwahati 2024 reproduces the replay's 227.9 h.
