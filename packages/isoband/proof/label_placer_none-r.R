suppressPackageStartupMessages(library(isoband))

# Three curves (ids 1 to 3, open), a closed circle (first point equals last), and a
# zigzag with 80 sections of 25 points each.
make_lines <- function() {
  n <- 2000
  t <- (0:(n - 1)) / (n - 1) * 2 * pi
  xa <- numeric(0)
  ya <- numeric(0)
  ida <- integer(0)
  for (k in 1:3) {
    xa <- c(xa, 0.5 + 0.45 * cos(t + k))
    ya <- c(ya, 0.5 + 0.45 * sin(1.3 * t + k))
    ida <- c(ida, rep(k, n))
  }
  m <- 3000
  t2 <- (0:(m - 1)) / (m - 1) * 2 * pi
  xc <- 0.5 + 0.4 * cos(t2)
  yc <- 0.5 + 0.4 * sin(t2)
  xc[m] <- xc[1]
  yc[m] <- yc[1]
  zz <- 2000
  i <- 0:(zz - 1)
  xz <- i / (zz - 1)
  yz <- ((i * 37) %% 101) / 100
  idz <- as.integer(i %/% 25 + 1)
  list(
    list(x = xa, y = ya, id = ida),
    list(x = xc, y = yc, id = rep(1L, m)),
    list(x = xz, y = yz, id = idz)
  )
}

make_labels <- function() {
  data.frame(
    index = c(1L, 1L, 2L, 3L, 3L, 2L, 1L, 3L),
    break_index = c(1L, 1L, 1L, 2L, 2L, 2L, 1L, 2L),
    break_id = c("0.5", "0.5", "0.5", "0.25", "0.75", "0.5", "0.25", "0.75"),
    label = c("a", "b", "c", "d", "e", "f", NA, "h"),
    stringsAsFactors = FALSE
  )
}

make_cases <- function() {
  list(
    list(name = "no_labels", placer = label_placer_none(), lines = make_lines(), labels = make_labels())
  )
}

run_all <- function(cases) {
  lapply(cases, function(cs) cs$placer(cs$lines, cs$labels))
}

emit_vec <- function(case, name, v) {
  n <- length(v)
  cat(sprintf("L\t%s\t%s\t%d\n", case, name, n), sep = "")
  if (n == 0) return(invisible())
  if (is.character(v)) {
    cat(sprintf("T\t%s\t%s\t%d\t%s\n", case, name, seq_len(n), v), sep = "")
  } else {
    cat(sprintf("V\t%s\t%s\t%d\t%.17g\n", case, name, seq_len(n), as.double(v)), sep = "")
  }
}

emit <- function(res, cases) {
  for (k in seq_along(cases)) {
    df <- res[[k]]
    for (nm in names(df)) emit_vec(cases[[k]]$name, nm, df[[nm]])
  }
}

cases <- make_cases()
timing_cases <- rep(cases, 200)
res <- run_all(cases) # untimed call
times <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  invisible(run_all(timing_cases))
  times[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(times) * 1000))
emit(res, cases)
