# Original AGENT_INSTRUCTIONS (pre-session)

This is the verbatim text of `telegraf_data/AGENT_INSTRUCTIONS.md` as it
existed at the start of the session, before any updates were made by the
agentic work. The post-session version (which preserves this text in a
trailing "Original spec" blockquote and adds new sections above) is in
`updated_AGENT_INSTRUCTIONS.md` next to this file.

---

This project uses the following sources:

    public.dcim_nodes: a database table with names of computer nodes and their row, pod and rack location within a datacenter.

    telegraf.ipmi_sensor: a timeseries database table with readings from sensors
                          the timeseries host names map to computer node names in public.dcim_nodes, but the match has some
                          irregularities. Some computer nodes have names XXXX-YYYY where the timeseries "host" name is just XXXX.
                          There are some XXXX-chassis names in computer nodes that are not in the timeseries db.
                          The sensors of interest in the time series measue power use, they have different names
                          pwr_consumption
                          instantaneous_power_reading
                          sys_power
                          some hosts have both "sys_power" and "instantaneous_power_reading"
                          for thise the "sys_power" value is the authoratative value

    scontrol_show_node.json: a file of JSON output from the Slurm command "scontrol show nodes" on the HPC cluster


Tools:

   the database can be accessed by
       PGPASSWORD=orcd_rw psql -h 127.0.0.1 -p 5433 -U readonly_user -d timedb

   there is a virutal environment .venv/ in which python tools can be found and that can be updated

Project Tasks:
   I want a set of python code written to a new git sub-directory.
   The python codes should
   1. get all the rows from public.dcim_nodes into a local CSV with values for
       name of compute node
       row
       pod
       rack

   2. get all the sensor time series from nodes in row 9, pod A into a set of CSV files,
      one for each host that matches a node (following the macthing rules with irregularities)

   3. write python code to produce a bar plot with 4 bars for each cabinet (aka rack).
      one bar should show the instantaneous minimum power for the cabinet, one should show the average power,
      one should show the instantaneous max power, one should show the "potential" max power - which is
      the sum of the per computer max for all the computers in that rack - not all at the same time.


Process:
  Create several agents.
  1. a database expert agent who will develop queries for the database
  2. a very experienced software engineer who will develop python to execute the database queries and write CSVs in a
     logical structure
  3. a system architect who will review the way in which the code is orchestrated and what items are paramterized
     so that the code can be applied to different problems.
  4. a documentation expert who will write clear explanations of how the code works so that an agent or a human
     can check the approach
