

nlines=12

mkdir report

for percent in 0 1 2 5; do
    ./transfer.py -f 0 -l 0.$percent -w 3000 test.txt 2>&1 |
        tail -n $nlines | head -n-2 |
        tee report/small-${percent}0-basic.txt;
done


for percent in 0 5; do
    ./transfer.py -f 0 -l 0.$percent -w 10000 internet-architecture.pdf 2>&1 |
        tail -n $nlines | head -n-2 |
        tee report/large-${percent}0-basic.txt;
done


for f in 0 3; do
    for percent in 0 2; do
        ./transfer.py -f $f -l 0.$percent -w 10000 internet-architecture.pdf 2>&1 |
            tail -n $nlines | head -n-2 | 
            tee report/large-${percent}0-fast-${f}.txt;
    done
done

for t in 1 2 5 10 15 20; do
    printf "${t}000,";
    ./transfer.py -l 0 -w ${t}000 internet-architecture.pdf -q 100 2>&1 |
        tail -n 2 | cut -d' ' -f2 | paste -sd, ;
done | tee report/window-sizes.txt

