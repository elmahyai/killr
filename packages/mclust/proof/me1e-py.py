import importlib.util
import statistics

SO = (
    "/home/ahmed/killr_projects/killr/crates/mclust/target/release/libmclust_kernels.so"
)
spec = importlib.util.spec_from_file_location("mclust_kernels", SO)
mclust_kernels = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mclust_kernels)


def inputs():
    x = [1.0, 1.2, 0.8, 5.0, 5.5, 4.7, 1.1, 5.2]
    z = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0]
    return (
        0,
        x,
        8,
        2,
        -1.0,
        z,
        100,
        1e-5,
        2.2204460492503131e-16,
        [0.0, 0.0],
        0.0,
        [0.0, 0.0],
    )


def flatten(out):
    values = []
    for item in out:
        if isinstance(item, list):
            values.extend(float(v) for v in item)
        else:
            values.append(float(item))
    return values


def one():
    return flatten(mclust_kernels.me1e(inputs()))


value = one()
elapsed = [mclust_kernels.me1e_ms(inputs()) for _ in range(20)]
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
