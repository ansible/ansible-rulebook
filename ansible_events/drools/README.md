This module is based on original work by Jesus Ruiz
found at https://github.com/jruizgit/rules

The `vendor` module has been adapted to substitute the
C library with a Python module that is redirecting
the internal procedure invocation to a custom REST service.

The REST service is implemented at https://github.com/mariofusco/drools-yaml-rules

## Development

You need maven, java installed on your machine

```
git clone https://github.com/mariofusco/drools-yaml-rules`
git clone https://github.com/kiegroup/drools
cd drools
mvn install -Dquickly
cd ../drools-yaml-rules
mvn install
cd drools-yaml-rules-durable
mvn quarkus:dev
```

to override the host port (default: 8080) you can pass
the config option: `-Dquarkus.http.port=NNNN`; e.g.:

```
mvn -Dquarkus.http.port=8888 quarkus:dev
```

You can also build a jar with `mvn package`; in this case,
you may run and override the port via:

```
java -Dquarkus.http.port=8888 quarkus:dev -jar target/drools-yaml-rules-durable-1.0.0-SNAPSHOT-runner.jar
```

```
To run the pytest with drools engine you can use
RULES_ENGINE=drools pytest

To run Ansible-events to run a ruleset please use
RULES_ENGINE=drools ansible-events --rules <your_rules_file> --inventory <your_inventory_file> --debug
```

to override host (default: `http://localhost:8080`) port use:

```
ANSIBLE_EVENTS_DROOLS_HOST=http://localhost:8888
```
