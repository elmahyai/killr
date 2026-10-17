import statistics

from nlmerecalc import (
    ar1_recalc,
    ar1_recalc_ms,
    comp_symm_recalc,
    comp_symm_recalc_ms,
    nat_recalc,
    nat_recalc_ms,
    symm_recalc,
    symm_recalc_ms,
)

xy = [
    0.5, -1.2, 0.3, 2.0, -0.7, 1.1, 0.0, 0.4,
    1.5, 0.2, -0.4, 0.8, 3.0, -1.0, 0.6, -0.3,
]
pdims = [8, 3, 4, 26, 4, 1, 3, 0, 4, 5]
time = [0, 2, 1, 3, 0, 1, 0, 2]
pars_symm = [-0.8, 0.3, 1.1, -0.4, 0.6, -1.5]
pars_nat = [0.4, -0.2, 0.1, 0.3, -0.5, 0.2]


def report(kernel, value, elapsed):
    body = ",".join(f"{item:.17g}" for item in value)
    print(
        f'{{"kernel":"{kernel}","value":[{body}],"median_ms":{statistics.median(elapsed):.17g}}}'
    )


xy_out, logdet = symm_recalc(xy, pdims, 2, pars_symm, time, 4, 0.0)
elapsed = [symm_recalc_ms(xy, pdims, 2, pars_symm, time, 4, 0.0) for _ in range(20)]
report("symm_recalc", list(xy_out) + [logdet], elapsed)

xy_out, logdet = nat_recalc(xy, pdims, 2, pars_nat, time, 4, 0.0)
elapsed = [nat_recalc_ms(xy, pdims, 2, pars_nat, time, 4, 0.0) for _ in range(20)]
report("nat_recalc", list(xy_out) + [logdet], elapsed)

xy_out, par, logdet = ar1_recalc(xy, pdims, 2, 1.2, 0.0)
elapsed = [ar1_recalc_ms(xy, pdims, 2, 1.2, 0.0) for _ in range(20)]
report("ar1_recalc", list(xy_out) + [par, logdet], elapsed)

xy_out, par, logdet = comp_symm_recalc(xy, pdims, 2, 0.55, -1.0 / 3.0, 0.0)
elapsed = [comp_symm_recalc_ms(xy, pdims, 2, 0.55, -1.0 / 3.0, 0.0) for _ in range(20)]
report("comp_symm_recalc", list(xy_out) + [par, logdet], elapsed)
