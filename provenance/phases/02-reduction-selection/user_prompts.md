# User prompts for 02-reduction-selection

Extracted from transcript `fec1d6d6-3e05-4db6-99ec-6d712cea59ee.jsonl`. User-message indices 5 through 8.

## User prompt #5
_Friday, May 1, 2026, 10:50 PM (UTC-4)_

```
Now make a plan for a downstream process that does the following
1. select nodes randomly from each cabinet subject to the following restrictions
2. choose enough nodes bring the instantaneous max power bars in each cabinet down by 40%
3. ensure that after the selected nodes have been "removed" that the all of the partitions in the file scontrol_show_node.json file  have at least two nodes remaining (or one if the partition only has one node). 

The file scontrol_show_node.json shows what partitions each node is a member of. nodes can be members of more than one partition.
```

## User prompt #6
_Friday, May 1, 2026, 10:58 PM (UTC-4)_

```
# Goal

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.
```

## User prompt #7
_Friday, May 1, 2026, 11:13 PM (UTC-4)_

```
Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.
```

## User prompt #8
_Friday, May 1, 2026, 11:13 PM (UTC-4)_

```
Make three changes to the node reduction computation. 
1. if, after making a final node selection, some partitions have zero remaining nodes then add back one node from that partition.
2. on the cabinet_power_bars_with_reduction.png include another bar which shows the new average based on the reduction.
3. include some summary statistics on the cabinet_power_bars_with_reduction.png plot to show reductions in node counts and inst max and average power.
```

