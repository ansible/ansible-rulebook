========================
Matching multiple events
========================


In a rule you can match one or more events from the same source. Once all the events match it executes the action. Two extra variables are passed into the playbook:

- events
- facts

Example:

.. code-block:: yaml

   condition:
     all:
      - event.i == 1
      - event.i == 2

The variables passed into the playbook would have the following values:

.. code-block:: json

    {
        "variables": {
            "events": {
                "m_0": {
                    "i": 1
                },
                "m_1": {
                    "i": 2
                }
            },
            "facts": {
                "m_0": {
                    "i": 1
                },
                "m_1": {
                    "i": 2
                }
            }
        }
    }

Example with assignments:

.. code-block:: yaml

   condition:
     all:
      - events.first << event.i == 1
      - events.second << event.i == 2

The variables passed into the playbook would have the following values:

.. code-block:: json

    {
        "variables": {
            "events": {
                "first": {
                    "i": 1
                },
                "second": {
                    "i": 2
                }
            },
            "facts": {
                "first": {
                    "i": 1
                },
                "second": {
                    "i": 2
                }
            }
        }
    }


**Notes:**

The same event expression cannot be used more than once. In the case below ``event.i == 1`` has been used twice so it wont match anything:

.. code-block:: yaml

       condition:
         all:
          - events.first << event.i == 1
          - event.i == 1


In the below case event.i == 2 has been used twice so it wont match anything:

.. code-block:: yaml

   condition:
        all:
          - events.saveme << event.i == 2 and event.i > 0
          - event.i == 2


Once an event matches it is removed and wont match any subsequent conditions. This case would work since the event expression is different:

.. code-block:: yaml

   condition:
        all:
          - events.saveme << event.i == 2 and event.i > 0
          - event.i == 0
