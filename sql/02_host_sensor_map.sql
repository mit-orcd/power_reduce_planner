-- Spec task #2: for each compute node in (row, pod), find the telegraf host it
-- maps to and decide which power sensor we should read from it.
--
-- Two domain rules are encoded here, in one place:
--   1. Host-name irregularity: dcim node "XXXX-YYYY" matches telegraf host
--      "XXXX". We use split_part(node_name, '-', 1) to capture both the
--      already-matching nodes (no dash) and the dashed ones.
--   2. -chassis rows in dcim_nodes have no telegraf counterpart -- exclude.
--   3. sys_power is authoritative when a host reports both sys_power and
--      instantaneous_power_reading. Priority order:
--         sys_power > instantaneous_power_reading > pwr_consumption
--
-- Output: one row per compute node host, with the rack it lives in and the
-- sensor name a downstream query should use. preferred_sensor IS NULL means
-- the host reports no power data in the requested time window.

WITH node_hosts AS (
    SELECT DISTINCT
        split_part(n.node_name, '-', 1) AS host,
        n.cabinet_number                AS rack
    FROM public.dcim_nodes n
    WHERE n.row_number = %(row)s
      AND n.pod        = %(pod)s
      AND n.node_name NOT LIKE '%%-chassis'
),
host_sensors AS (
    SELECT DISTINCT
        i.host,
        i.name AS sensor
    FROM telegraf.ipmi_sensor i
    JOIN node_hosts nh ON nh.host = i.host
    WHERE i.name IN ('sys_power', 'instantaneous_power_reading', 'pwr_consumption')
      AND i.time BETWEEN %(start)s AND %(end)s
)
SELECT
    nh.host,
    nh.rack,
    CASE
        WHEN bool_or(hs.sensor = 'sys_power')                   THEN 'sys_power'
        WHEN bool_or(hs.sensor = 'instantaneous_power_reading') THEN 'instantaneous_power_reading'
        WHEN bool_or(hs.sensor = 'pwr_consumption')             THEN 'pwr_consumption'
        ELSE NULL
    END AS preferred_sensor
FROM node_hosts nh
LEFT JOIN host_sensors hs USING (host)
GROUP BY nh.host, nh.rack
ORDER BY nh.rack, nh.host;
