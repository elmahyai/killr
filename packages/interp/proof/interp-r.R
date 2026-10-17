# Proof: R interp::interp on the default path and the common options.
# Run from packages/interp: Rscript proof/interp-r.R
source("proof/interp_proof_common.R")

f <- function(x, y) sin(2 * x) + cos(3 * y)

s60 <- lcg(120, 42)
s200 <- lcg(400, 7)
s30 <- lcg(60, 5)
s80 <- lcg(80, 99)
x30 <- s30[1:30]
y30 <- s30[31:60]
dupi <- c(2, 7, 11)
xdup <- c(x30, x30[dupi])
ydup <- c(y30, y30[dupi])
zdup <- f(xdup, ydup) + 0.1 * seq_along(xdup) # duplicates carry different z values

# Output points: 150 Park-Miller points in the box grown by 0.2 around rand200.
rq <- lcg(300, 1234)
x200 <- s200[1:200]
y200 <- s200[201:400]
pts_x <- min(x200) - 0.2 + (max(x200) - min(x200) + 0.4) * rq[1:150]
pts_y <- min(y200) - 0.2 + (max(y200) - min(y200) + 0.4) * rq[151:300]

gx <- seq(0, 1, length.out = 6)
gy <- seq(0, 2, length.out = 5)
zgrid <- outer(gx, gy, function(a, b) sin(3 * a) + b^2)

cases <- list(
  list(id = "rand60", x = s60[1:60], y = s60[61:120], z = f(s60[1:60], s60[61:120]), args = list()),
  list(id = "rand200", x = x200, y = y200, z = f(x200, y200), args = list()),
  list(id = "grid5", x = as.numeric(rep(1:5, times = 5)), y = as.numeric(rep(1:5, each = 5)),
       z = as.numeric(rep(1:5, times = 5)) * as.numeric(rep(1:5, each = 5)) + as.numeric(rep(1:5, times = 5)),
       args = list()),
  list(id = "scaled", x = s80[1:40] * 100 - 50, y = s80[41:80], z = f(s80[1:40] * 100 - 50, s80[41:80]), args = list()),
  list(id = "dups-mean", x = xdup, y = ydup, z = zdup, args = list(duplicate = "mean")),
  list(id = "dups-median", x = xdup, y = ydup, z = zdup, args = list(duplicate = "median")),
  list(id = "dups-strip", x = xdup, y = ydup, z = zdup, args = list(duplicate = "strip")),
  list(id = "dups-user", x = xdup, y = ydup, z = zdup, args = list(duplicate = "user", dupfun = function(v) max(v))),
  list(id = "grid-input", x = gx, y = gy, z = zgrid, args = list(input = "grid")),
  list(id = "points-out", x = x200, y = y200, z = f(x200, y200),
       args = list(xo = pts_x, yo = pts_y, output = "points")),
  list(id = "custom-grid", x = s60[1:60], y = s60[61:120], z = f(s60[1:60], s60[61:120]),
       args = list(xo = seq(0.1, 0.9, length.out = 25), yo = seq(0.05, 0.95, length.out = 31))),
  list(id = "akima-lin", x = s60[1:60], y = s60[61:120], z = f(s60[1:60], s60[61:120]),
       args = list(method = "akima", linear = TRUE)),
  list(id = "extrap-on", x = s60[1:60], y = s60[61:120], z = f(s60[1:60], s60[61:120]),
       args = list(extrap = TRUE))
)

run_case <- function(cs) do.call(interp, c(list(x = cs$x, y = cs$y, z = cs$z), cs$args))

run_all <- function() lapply(cases, run_case)

res <- run_all() # one untimed call, used for the records

rec <- list()
for (i in seq_along(cases)) {
  id <- cases[[i]]$id
  zv <- as.vector(res[[i]]$z)
  zv[is.na(zv)] <- NaN
  rec[[paste0(id, "/xo")]] <- res[[i]]$x
  rec[[paste0(id, "/yo")]] <- res[[i]]$y
  rec[[paste0(id, "/z")]] <- zv
}

ms <- median_ms(run_all, reps = 20)
write_record("docs/output/interp-r.txt", rec, ms)
nna <- sum(vapply(res, function(r) sum(is.na(r$z)), 1))
cat("R interp cases:", length(cases), " NA cells:", nna, " median ms:", ms, "\n")
