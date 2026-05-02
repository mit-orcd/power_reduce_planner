-- Spec task #3 input: per-host min / mean / max from raw (un-bucketed)
-- samples, restricted to the host's preferred sensor.
--
-- Parameters:
--   start, end   - ISO-8601 time bounds (psycopg2 named binding)
--   pairs        - same (host, sensor) values list as 03; rendered via
--                  the {pairs_values} marker by the caller.
SELECT
    i.host                                            AS host,
    MIN(i.value)                                      AS min_power,
    AVG(i.value)                                      AS avg_power,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY i.value) AS median_power,
    MAX(i.value)                                      AS max_power,
    COUNT(*)                                          AS sample_count
FROM telegraf.ipmi_sensor i
JOIN (VALUES {pairs_values}) AS pref(host, sensor)
  ON pref.host   = i.host
 AND pref.sensor = i.name
WHERE i.time BETWEEN %(start)s AND %(end)s
GROUP BY i.host
ORDER BY i.host;
