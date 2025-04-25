
# Changelog

## [Unreleased]
### Changed
### Added
### Fixed


## [1.1.6] - 20205-04-25
- Fix memory leak with new drools_jpy


## [1.1.5] - 20205-04-11
### Changed
- Minor refactors
- Docs updates
### Added
- Log stacktrace with source filename, function and line number
- Log relevant version information at startup of worker
### Fixed


## [1.1.4 - 2025-04-01]
### Changed
- Update tests
### Added
### Fixed
- Bug fixes

## [1.1.3] - 2025-03-04
### Changed
### Added
- Add generic error message for unknown source errors
### Fixed
- Allow user to optionally include matching events
- Allow for fetching env and file contents from EDA server
- Overhead of running decryption before every usage


## [1.1.1] - 2024-09-19
### Changed
- Fixed documentation on matching events in multi condition
### Added
- Support for switching slugs to connect to controller via gateway
- Support passing in controller job id to server so it can build Job URL
### Fixed
- Fix log level for websocket

## [1.1.0] - 2024-05-15
### Added
- Support for vaulted variables
- Support for string interpolation from encrypted variables
- Added aiobotocore package needed for our SQS plugin

## [1.0.5] - 2024-02-07

### Changed
- Job template, workflow template, module and playbook output facts/events
  using banner style

### Added
- ssl_verify option now also supports "true" or "false" values
- Support for standalone boolean in conditions
- Add basic auth to controller
- Use token for websocket authentication
- skip-audit-events to disable sending audit events to server
- restrict drools async connection to localhost

### Changed
- Generic print as well as printing of events use new banner style

### Fixed
- Support a base path for the controller url

## [1.0.4] - 2023-10-30

### Added

### Fixed
- Job_template and workflow_template actions honor custom hosts limit
- Upgraded to 0.3.8 of drools_jpy
- Add missing watchdog dependency

### Removed

## [1.0.3] - 2023-10-17

### Added
- support for firing multiple rules

### Fixed
- bug fix in run_workflow_template


### Removed
## [1.0.2] - 2023-08-14

### Added
- rulebook and Drools bracket notation syntax
- new action called run_workflow_template

### Fixed

### Removed
## [1.0.1] - 2023-07-24

### Added
- Add source plugins best practices to the documentation

### Fixed
- Minor documentation fixes
- Fix an issue where rule_run_at field is not send to the websocket
- Don't try to connect with AWX when no run_job_template action is used
- Limits the number of simultaneously open connections to controller to 30
- Fixes a wrong 401 response from AWX when 443 port is present in CONTROLLER_URL (<https://github.com/ansible/ansible-rulebook/issues/554>)


### Removed
- Remove official support for Python 3.8


## [1.0.0] - 2023-06-13

### Added
- Sending heartbeat to the server with the session stats
- Added command line option --execution-strategy
- Rulesets in rulebook can have execution_strategy attribute

### Fixed
- In a collection look for playbook in playbooks directory
- Support .yaml and .yml extension for playbooks
- Retract fact for partial and complete matches
- Checking of controller url and token at startup
- rule_uuid and ruleset_uuid provided even when an action fails
- Drools intermittently misses firing of rules
- Resend events lost during websocket disconnect

### Removed

##  [0.13.0] - 2023-04-25

### Added
- Support for default_events_ttl at ruleset level and globally
- Added --websocket-ssl-verify

### Fixed
- Support singular event_source and event_filter in collections
- Find job template by name

##  [0.12.0] - 2023-04-12

### Added
- Support all file formats for static inventories as ansible does.
- Support for controller url via env var EDA_CONTROLLER_URL
- Support for controller token via env var EDA_CONTROLLER_TOKEN
- Support for controller token ssl verify via env var EDA_CONTROLLER_SSL_VERIFY
- Support for bulitin filter eda.builtin.insert_meta_info added to every source

### Fixed
- actions in different rules to run in parallel
- actions within a single rule to execute sequentially
- comparing 2 different attributes in the same event
- select with search option on delayed evaluation

##  [0.11.0] - 2023-03-08

### Added

- Scheduled workflow and split long-run tests
- Ansible_eda top key in variables
- Temporal use cases and handle async responses from Drools
- Time constraints in rules schema
- group_by_attributes
- Support multiple actions for a rule
- Support for search/match/regex
- Support for graceful shutdown, timeout to allow actions to complete
- Removed the echo command in favor of debug with msg
- Support for null type in conditions
- Support Jinja2 substitution in rule names
- Support booleans in lists, which can contain mixed data types
- Support for identifiers in select and selectattr

### Fixed

- get_java_version, add compatibility with macs and tests for check_jvm
- selectattr operator with negation using greater/less than operators
- select operator and comparing ints and floats
- Preserve native types when doing jinja substitution
- Inventory argument to the CLI is optional
- select works with null
- a race condition between threads in drools rule engine

### Removed

- Redis and durability
- envvar for rules_engine


## [0.10.1] - 2023-01-25

### Added

- Support for vars namespace
- Support for negation
- Support for Floats
- Log format and set the log stream for debug/verbose
- A builtin action : echo
- Cmdline option --print_events
- New action: run_job_template
- Support for in and contains in condition
- Add more info to --version flag
- Add EDA prefix to environment variables
- Enable drools for python 3.11
- Combine hosts when running a module
- Combine the same playbook on multiple hosts

### Fixed

- Schema validation for empty additionalProperties
- Drools dependency for python3.11
- Remove the temporary directory

### Changed

- Configure controller API access
- Switch the default rules engine back to drools
- Print help if run without arguments

### Removed

- Removed durable rules
- Remove call_action
- Removes get_facts

## [0.9.4] - 2022-10-18

## [0.9.3] - 2022-10-18

### Changed

Update minimal python version
Improves error messages for unhandled events

### Removed

- get_facts for now

## [0.9.2] - 2022-10-15

## [0.9.1] - 2022-10-15

### Added

- Job details for eda-server usage
- add arg to install devel collection

### Fixed

- Duplicate para after merge
- Shutdown action and add test for it

### Changed

- Always log each retry
- Disable gather facts
- Don't use {{ }} in conditions

## [0.9.0] - 2022-10-12

### Added

- Adds support for non-async event plugins using put_nowait
- Support storing facts per host

### Fixed

### Changed

- Cmdline --rules to --rulebook
- Lookup directory to rulebooks in collections
- Rename assert_fact to set_fact

## [0.8.0] - 2022-10-11

### Added

- Support for any and all conditions
- Log every run_playbook or run_module retry

### Fixed

- Multiple operator expressions

### Changed

- Rename ansible-events to ansible-rulebook
- One shutdown event stops all rulesets
- Run each ruleset in a separate asyncio task

## [0.7.0] - 2022-09-14

### Added

- Quotes around is defined
- Worker mode
- Allow to rerun a playbook on failure

### Removed

- Plus syntax of is defined

### Fixed

- An error msg

## [0.6.0] - 2022-08-24

### Added

- Support for executing ansible modules as part of action
- Support to post_event for Drools
- Support var_root in multi events
- Support for embedded spaces

### Fixed

- Sending ansible events as they are received
- Error handling for the websocket connection

### Changed

- Use a dictionary for var_root with the old key: new key

## [0.5.1] - 2022-08-10

### Added

- `durable-rules` adapter invoking a REST service
- Support events in print\_event

### Fixed

-  a bug in non string type in facts

### Removed

- event\_filters folder under ansible\_events

## [0.5.0] - 2022-07-28


### Added

- Or operator
- Fact namespace to variable lookup
- Add operator
- json\_mode option for run\_playbook action
- Coroutine based event sources

### Fixed

- Async sources of hosts and range2

### Changed

- Argument for post\_event to event

## [0.4.0] - 2022-06-23

### Added

- Websocket event log

### Changed

- Converts actions to async functions


## [0.3.0] - 2022-05-06

### Added

- Error message for missing rules
- Collection support
- Schema for the ruleset files


## [0.2.0] - 2022-05-02

### Added

- Support for multiple sources
- Back plan
- Variable substitution to list args
- Greater than operator to conditions
- Copy files and fixes post\_events
- Support for comparing events and facts
- Booleans to condition parser
- Lists\_to\_dicts
- Event\_filters

### Fixed

- Log scraper
- Multiple hosts tests

### Changed

- Rules to a optional argument

## [0.1.2] - 2022-03-16

### Fixed

- Flushes standard output

## [0.1.1] - 2022-03-16

### Added

- Project structure
- Initial version of rule engine
- Tests for multiple and statements
- Support for enabled flag on rules
- Event source filters
- Fact as synonym for event in conditions
- Fact assignment in conditions
- Dpath to value access
- Check for size of dictionaries due to durable rules limitation
- Support for multiple conditions
- Support for 'is defined'
- Docopt to test requirements
- Dpath to requirements
- Rule parsing test
- Asserting facts from ansible facts
- Assert\_facts option to run\_playbook
- Pass by value in substitute\_variables
- Support substituting variables in dictionaries
- Support for matching all to inventory
- Performance tests
- Variables and facts to actions
- Support for host-specific rulesets
- Example rules
- Cli
- Requirements

### Fixed

- Filters with no args
- Typing
- URL on pypi
- Types

### Changed

- Fact to event in conditions
- Glob to var\_root
- Host\_ruleset to ruleset in ActionContext
- Generate\_rulesets to generate\_host\_rulesets
