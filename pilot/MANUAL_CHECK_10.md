# Manual check of the 10 pilot events (template)

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
| P01 | Brahmaputra near Guwahati | | | | | | |
| P02 | Godavari lower reach | | | | | | |
| P03 | Ganges near Malda | | | | | | |
| P04 | Kosi, Bihar | | | | | | |
| P05 | Jamuna at Bahadurabad | | | | | | |
| P06 | Indus near Sukkur | | | | | | |
| P07 | Mekong near Kratie | | | | | | |
| P08 | Chao Phraya near Nakhon Sawan | | | | | | |
| P09 | Ayeyarwady near Pyay | | | | | | |
| P10 | Brahmaputra near Dibrugarh | | | | | | |

**Go / no-go** (written in `pilot/PILOT_NOTES.md`): the main run starts only if questions 2–4
are Yes for at least 8 of 10 events, or the failures are traced to a fixable bug, fixed, and the
fix recorded.

Also recorded in the pilot notes: time and Earth Engine requests per event; whether the plan issue
time from the file name matches the ZIP entry times; TIGGE and GloFAS request field names that had
to change; and whether Guwahati 2024 reproduces the replay's 227.9 h.
