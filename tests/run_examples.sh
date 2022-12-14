#!/bin/bash


function run {
    echo "RUNNING $1"
    ansible-rulebook --rulebook "./${1}" --inventory ./playbooks/inventory.yml -S ./sources/ &>/dev/null
    if [[ $? -ne 0 ]]; then
        echo "PROBLEM with $1"
    fi
}

for file in examples/*.yml; do
    run $file
done
