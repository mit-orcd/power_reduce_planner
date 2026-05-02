-- Spec task #1: dump every dcim_nodes row with the four columns the spec asks
-- for (name, row, pod, rack). Includes -chassis rows; downstream consumers
-- decide whether to filter them out.
SELECT
    n.node_name      AS name,
    n.row_number     AS "row",
    n.pod            AS pod,
    n.cabinet_number AS rack
FROM public.dcim_nodes n
ORDER BY n.row_number, n.pod, n.cabinet_number, n.node_name;
