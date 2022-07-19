========================
Matching Multiple events
========================

In a rule you can match one or more events from the same source. Once all the events match it executes the action. Two extra variables are passed into the playbook
  - events
  - facts

Example::

   condition:
     all:
      - events.first << event.i == 1
      - events.second << event.i == 2


The following caveats apply:

1. The same event expression cannot be used more than once In the case below event.i == 1 has been used twice so it wont match anything::
   
   condition:
     all:
      - events.first << event.i == 1
      - event.i == 1


In the below case event.i == 2 has been used twice so it wont match anything::

   condition:
        all:
          - events.saveme << event.i == 2 and event.i > 0
          - event.i == 2


Once an event matches it is removed and wont match any subsequent conditions. This case would work since the event expression is different::

   condition:
        all:
          - events.saveme << event.i == 2 and event.i > 0
          - event.i == 0

2. var_root is used to extract a subset of the event data. This is
   currently unsupported for multiple events.

3. The action: print_event doesn't handle multiple events since it is
   looking for the key **event**

4. Currently there is no time constraint when satisfying multiple event conditions. We are planning on implementing a **within** syntax which will be aking to all with the added time constraint::
   
   condition:
     within(10):
      - events.first << event.i == 1
      - events.second << event.i == 2

