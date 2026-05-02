# User prompts for 03-reservation-generator

Extracted from transcript `fec1d6d6-3e05-4db6-99ec-6d712cea59ee.jsonl`. User-message indices 9 through 13.

## User prompt #9
_Saturday, May 2, 2026, 6:42 AM (UTC-4)_

```
Make a plan for another stand alone python program. It should read the selected nodes csv and generate a slurm reservation command with the options
MAINT 
and 
IGNORE_JOBS
the reservation should be for all the nodes in the csv.
The program should support arguments for a reservation start time and date and a reservation end time.and date.
The default example start should be 9AM, May 10, 2026 and should be 9AM, May 17, 2026 .
The reservation should have a name that is easy to understand, can be unique and includes "temp_power_reduce" in the name.
```

## User prompt #10
_Saturday, May 2, 2026, 6:45 AM (UTC-4)_

```
# Goal

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.
```

## User prompt #11
_Saturday, May 2, 2026, 6:50 AM (UTC-4)_

```
Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.
```

## User prompt #12
_Saturday, May 2, 2026, 6:50 AM (UTC-4)_

```
can you add the following flag
SPEC_NODES
to the generated reservation
```

## User prompt #13
_Saturday, May 2, 2026, 6:54 AM (UTC-4)_

```
can you undo the 
SPEC_NODES
that is not a flga a user sets, Slurm adds that
```

