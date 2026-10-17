suppressPackageStartupMessages(library(isoband))

# Fixed input lines: three curves, one circle, and a zigzag with 8 ids.
make_cases <- function() {
  n <- 200
  t <- (0:(n - 1)) / (n - 1) * 2 * pi
  curves <- list()
  for (k in 1:3) {
    curves[[k]] <- list(
      x = 0.5 + 0.45 * cos(t + k), y = 0.5 + 0.45 * sin(1.3 * t + k),
      id = rep(k, n)
    )
  }
  xa <- do.call(c, lapply(curves, function(cv) cv$x))
  ya <- do.call(c, lapply(curves, function(cv) cv$y))
  ida <- as.integer(do.call(c, lapply(curves, function(cv) cv$id)))

  m <- 300
  t2 <- (0:(m - 1)) / (m - 1) * 2 * pi
  xc <- 0.5 + 0.4 * cos(t2)
  yc <- 0.5 + 0.4 * sin(t2)
  idc <- rep(1L, m)

  zz <- 200
  i <- 0:(zz - 1)
  xz <- i / (zz - 1)
  yz <- ((i * 37) %% 101) / 100
  idz <- as.integer(i %/% 25 + 1)

  list(
    list(name = "curves", x = xa, y = ya, id = ida, asp = 1.25),
    list(name = "circle", x = xc, y = yc, id = idc, asp = 1.25),
    list(name = "zigzag", x = xz, y = yz, id = idz, asp = 0.8)
  )
}

boxes <- data.frame(
  x = c(0.5, 0.2, 0.8, 0.5, 0.35),
  y = c(0.5, 0.7, 0.3, 0.9, 0.2),
  width = c(0.3, 0.25, 0.4, 0.5, 0.2),
  height = c(0.2, 0.15, 0.1, 0.2, 0.3),
  theta = c(0.3, -0.8, 1.2, 0, 0.7)
)

run_all <- function(cases) {
  lapply(cases, function(cs) clip_lines(cs$x, cs$y, cs$id, boxes, asp = cs$asp))
}

emit <- function(res, cases) {
  for (k in seq_along(res)) {
    nm <- cases[[k]]$name
    cat(sprintf("G\t%s\t%d\n", nm, 1))
    el <- res[[k]]
    if (length(el$x) > 0) {
      cat(sprintf("P\t%s\t%d\t%.17g\t%.17g\t%d\n", nm, 1, el$x, el$y, as.integer(el$id)), sep = "")
    }
  }
}

cases <- make_cases()
res <- run_all(cases) # untimed call
times <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  invisible(run_all(cases))
  times[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(times) * 1000))
emit(res, cases)
