import statistics

from survdiff2 import survdiff2, survdiff2_ms

tiny_time = [1.0, 2.0, 3.0, 4.0]
tiny_status = [1, 1, 0, 1]
tiny_group = [1, 2, 1, 2]
tiny_strata = [0, 0, 0, 1]

n1 = 90
i1 = list(range(1, n1 + 1))
n2 = 60
i2 = list(range(1, n2 + 1))
large_time = [float(((i - 1) // 3) + 1) for i in i1] + [float(((i - 1) // 2) + 1) for i in i2]
large_status = [0 if i % 5 == 0 else 1 for i in i1] + [0 if i % 4 == 0 else 1 for i in i2]
large_group = [((i - 1) % 3) + 1 for i in i1] + [((i - 1) % 3) + 1 for i in i2]
large_strata = [0] * (n1 - 1) + [1] + [0] * (n2 - 1) + [1]

calls = [
    (0.0, tiny_time, tiny_status, tiny_group, tiny_strata, 2, 1),
    (1.0, tiny_time, tiny_status, tiny_group, tiny_strata, 2, 1),
    (0.0, large_time, large_status, large_group, large_strata, 3, 2),
    (1.0, large_time, large_status, large_group, large_strata, 3, 2),
    (0.5, large_time, large_status, large_group, large_strata, 3, 2),
]


def one():
    values = []
    for rho, time, status, group, strata, ngroup, nstrat in calls:
        observed, expected, variance = survdiff2(rho, time, status, group, strata, ngroup, nstrat)
        values.extend(observed)
        values.extend(expected)
        values.extend(variance)
    return values


value = one()
elapsed = []
for _ in range(20):
    total = 0.0
    for rho, time, status, group, strata, ngroup, nstrat in calls:
        total += survdiff2_ms(rho, time, status, group, strata, ngroup, nstrat)
    elapsed.append(total)
print("\n".join(f"{item:.17g}" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
