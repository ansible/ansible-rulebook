#!/bin/bash
ulimit -Sn 10000
#Argtest
#

now=$(date +"%Y%m%d%H%M%S")

./perf_test.py "perf${now}.csv" x x x x --only-header
for t in rules.yml null_rules.yml 1k_event_rules.yml 10k_event_rules.yml 100k_event_rules.yml 1M_event_rules.yml 10M_event_rules.yml 100M_event_rules.yml
do
for n in 1 10 100
do
./perf_test.py "perf${now}.csv" "ansible-rulebook -i inventory${n}.yml -S sources --rulebook ${t}" ansible-rulebook ${t} ${n} --no-header
done
done
