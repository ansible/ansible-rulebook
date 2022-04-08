ulimit -Sn 10000
#Argtest

./perf_test.py x x x x --only-header
for t in rules.yml
do
for n in 1 10 100
do
./perf_test.py "ansible-events -i inventory${n}.yml -S sources ${t}" ansible-events ${t} ${n} --no-header
done
done
