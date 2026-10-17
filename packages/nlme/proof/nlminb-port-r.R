## R 4.5.0 stats::nlminb with no gradient, the reference for crates/nlminb_port.
## Each problem: one untimed call, then the median of 20 timed calls.
## Output: one JSON object on stdout, saved to docs/output/nlminb-port-r.txt.
## Objectives use only + - * and exp/sin-free loops, so R and Python compute
## bit-identical values; sums are explicit double accumulations (R's sum() uses
## long double and would differ in the last bit).

## Rosenbrock, 2 parameters.
rosen2 <- function(x) {
  t <- x[2] - x[1] * x[1]
  100 * (t * t) + (1 - x[1]) * (1 - x[1])
}

## Extended Rosenbrock, any length.
rosenN <- function(x) {
  n <- length(x)
  s <- 0
  for (i in 1:(n - 1)) {
    t <- x[i + 1] - x[i] * x[i]
    s <- s + (100 * (t * t) + (1 - x[i]) * (1 - x[i]))
  }
  s
}

## Three-parameter exponential-decay least squares, y = a exp(-b t) + c.
## Data are deterministic: 2.5 exp(-0.4 t) + 0.8 + 0.03 sin(1.7 t), t = 0..9.
tt <- c(0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
yy <- c(3.3, 2.505550059402673, 1.9156561772322491, 1.5252110893106732,
        1.319564695520797, 1.1622928214702366, 1.0057986425957248,
        0.9334810431959338, 0.9276803643916104, 0.8802115233121498)
nls3 <- function(p) {
  a <- p[1]; b <- p[2]; cc <- p[3]
  s <- 0
  for (i in 1:10) {
    r <- yy[i] - (a * exp((-b) * tt[i]) + cc)
    s <- s + r * r
  }
  s
}

## Bounded quadratic: unconstrained minimum (3, 2) lies outside x1 <= 2, so the
## bounded minimum (2, 2) is on the bound.
bquad <- function(x) {
  d1 <- x[1] - 3
  d2 <- x[2] - 2
  d1 * d1 + d2 * d2
}

problems <- list(
  list(name = "rosenbrock_2d", fn = rosen2, start = c(-1.2, 1),
       lower = -Inf, upper = Inf, control = list()),
  list(name = "nls_3par", fn = nls3, start = c(1, 0.1, 0.5),
       lower = -Inf, upper = Inf, control = list()),
  list(name = "bounded_quadratic_on_bound", fn = bquad, start = c(0.5, 0.5),
       lower = c(0, 0), upper = c(2, 5), control = list()),
  list(name = "rosenbrock_5d", fn = rosenN, start = c(-1.2, 1, -1.2, 1, -1.2),
       lower = -Inf, upper = Inf, control = list()),
  list(name = "rosenbrock_5d_upper_bound", fn = rosenN,
       start = c(-1.2, 0.8, -1.2, 0.8, -1.2),
       lower = -2, upper = 0.9, control = list()),
  list(name = "rosenbrock_2d_control", fn = rosen2, start = c(-1.2, 1),
       lower = -Inf, upper = Inf,
       control = list(eval.max = 300, iter.max = 150, rel.tol = 1e-12, x.tol = 1.5e-10))
)

one_problem <- function(p) {
  nlminb(p$start, p$fn, lower = p$lower, upper = p$upper, control = p$control)
}

json_one <- function(p) {
  res <- one_problem(p)
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    one_problem(p)
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  sprintf(
    "{\"name\":\"%s\",\"par\":[%s],\"objective\":%.17g,\"convergence\":%d,\"iterations\":%d,\"evaluations_function\":%d,\"evaluations_gradient\":%d,\"message\":\"%s\",\"median_ms\":%.17g}",
    p$name,
    paste(sprintf("%.17g", res$par), collapse = ","),
    res$objective,
    as.integer(res$convergence),
    as.integer(res$iterations),
    as.integer(res$evaluations[["function"]]),
    as.integer(res$evaluations[["gradient"]]),
    res$message,
    median(elapsed) * 1000
  )
}

cat("{\"problems\":[\n")
cat(paste(vapply(problems, json_one, character(1)), collapse = ",\n"))
cat("\n]}\n")
