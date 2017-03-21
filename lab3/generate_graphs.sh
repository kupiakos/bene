#!/usr/bin/env bash

pushd "$(dirname "$0")" >/dev/null
rm -r report/graphs 2>/dev/null
mkdir -p report/graphs 2>/dev/null

plural() {
    echo "$1$([ $2 -eq 1 ] || echo s)"
}

simulate() {
    mkdir tmp 2>/dev/null
    for type in '' reno; do
        ./transfer.py ${type:+-r} ${2:+-d $2} \
            internet-architecture.pdf tmp/sequence.csv tmp/cwnd.csv || exit
        ./tcp-plot.py tmp/sequence.csv tmp/cwnd.csv report/graphs/${type:=tahoe}-${1} \
            -t "${type^} with $1 $(plural packet $1) dropped"
    done
    rm -r tmp
}

simulate 0
simulate 1 14000
simulate 2 14000,28000
simulate 3 14000,26000,28000

popd > /dev/null
echo 'Finished!'
