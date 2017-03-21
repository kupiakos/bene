#!/usr/bin/env bash

pushd "$(dirname "$0")"
rm -r report/graphs
mkdir -p report/graphs

plural() {
    echo "$1$([ $2 -eq 1 ] || echo s)"
}

simulate() {
    mkdir tmp
    ./transfer.py ${2:+-d} "$2" internet-architecture.pdf tmp/sequence.csv tmp/cwnd.csv
    ./tcp-plot.py tmp/sequence.csv tmp/cwnd.csv report/graphs/tahoe_${1} -t "Tahoe with $1 $(plural packet $1) dropped"
    rm -r tmp
}

simulate 0
simulate 1 14000
simulate 2 14000,28000
simulate 3 14000,26000,28000

popd
