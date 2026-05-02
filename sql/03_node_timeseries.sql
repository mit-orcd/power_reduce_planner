-- Spec task #2 continued: per-host bucketed time series for the (host, sensor)
-- pairs produced by 02_host_sensor_map.sql.
--
-- Parameters (named):
--   start, end   - ISO-8601 time bounds (psycopg2 named binding)
--   bucket       - timescaledb interval string, e.g. '10m'
--   pairs        - list of (host, sensor) tuples; rendered into the SQL
--                  string by the Python caller via the {pairs_values}
--                  literal marker (mogrify-quoted).
SELECT
    time_bucket(%(bucket)s::interval, i.time) AS time,
    i.host                                     AS host,
    MAX(i.value)                               AS power_watts
FROM telegraf.ipmi_sensor i
JOIN (VALUES {pairs_values}) AS pref(host, sensor)
  ON pref.host   = i.host
 AND pref.sensor = i.name
WHERE i.time BETWEEN %(start)s AND %(end)s
GROUP BY 1, 2
ORDER BY 1, 2;
