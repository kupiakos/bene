
from operator import attrgetter

# Note: these functions all assume a step of 1

def range_overlap(x, y):
    """Return the range that the two ranges overlap on"""
    return range(max(x.start, y.start), min(x.stop, y.stop))


def range_contains(x, y):
    """Return whether x is entirely contained in y"""
    return x.start <= y.start and x.stop >= y.stop


def range_merge(ranges):
    """Return ranges sorted, merging contiguous/overlapping ranges"""
    sorted_by_lower_bound = sorted(ranges, key=attrgetter('start'))
    merged = []

    for higher in sorted_by_lower_bound:
        if not merged:
            merged.append(higher)
            continue
        lower = merged[-1]
        if higher.start <= lower.stop:
            upper_bound = max(lower.stop, higher.stop)
            merged[-1] = range(lower.start, upper_bound)
        else:
            merged.append(higher)
    return merged


def range_subtract(x, *ranges):
    """Return a sorted, non-overlapping list of ranges from removing each of the ranges from x"""
    ranges = range_merge(ranges)
    result = []
    start = x.start
    for remove in ranges:
        if start > remove.stop:
            # We've passed the end
            break
        if remove.start > start:
            result.append(range(start, remove.start))
        start = remove.stop
    if start < x.stop:
        result.append(range(start, x.stop))
    return result


def range_format(*ranges):
    return ','.join('%d-%d' % (r.start, r.stop - 1) for r in ranges)
