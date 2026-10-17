# Raw Cconcordance1 / Cconcordance2 counts from survival 3.8-12.
# The timed section is the .Call kernels only. Sys.time() wraps one untimed
# pass, then the median of 20 timed passes.
suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

fmt <- function(x) paste(sprintf("%.17g", as.numeric(x)), collapse = ",")

btree <- function(n) {
  ranks <- rep(0L, n)
  yet.to.do <- seq_len(n)
  depth <- floor(logb(n, 2))
  start <- as.integer(2^depth)
  lastrow.length <- 1L + n - start
  indx <- seq(1L, by = 2L, length = lastrow.length)
  ranks[yet.to.do[indx]] <- start + 0:(length(indx) - 1L)
  yet.to.do <- yet.to.do[-indx]
  while (start > 1) {
    start <- as.integer(start / 2)
    indx <- seq(1L, by = 2L, length = start)
    ranks[yet.to.do[indx]] <- start + 0:(start - 1L)
    yet.to.do <- yet.to.do[-indx]
  }
  ranks
}

pack_right <- function(time, status, x, wt) {
  ord <- order(time, -status)
  y <- cbind(time, status)[ord, , drop = FALSE]
  storage.mode(y) <- "double"
  ux <- sort(unique(x))
  n2 <- length(ux)
  index <- as.integer(btree(n2)[match(x[ord], ux)] - 1L)
  list(
    y = y,
    wt = as.double(wt[ord]),
    index = index,
    ntree = as.integer(n2)
  )
}

pack_count <- function(start, stop, status, x, wt) {
  y <- cbind(start, stop, status)
  storage.mode(y) <- "double"
  ux <- sort(unique(x))
  n2 <- length(ux)
  index <- as.integer(btree(n2)[match(x, ux)] - 1L)
  list(
    y = y,
    wt = as.double(wt),
    index = index,
    ntree = as.integer(n2),
    sort_stop = as.integer(order(-stop, status) - 1L),
    sort_start = as.integer(order(-start) - 1L)
  )
}

time <- c(1, 2, 2, 2, 3, 4, 4, 4, 5, 2)
status <- c(1, 0, 1, 0, 1, 0, 1, 1, 0, 1)
x <- c(5, 5, 4, 4, 3, 3, 7, 6, 5, 4)
s <- c("a", "a", "b", "b", "a", "b", "a", "b", "a", "b")
w <- c(1, 2, 1, 1, 2, 1, 1, 0.5, 1, 1)
start <- c(0, 0, 1, 2, 0, 3, 1, 2, 0, 4)
stop <- c(2, 3, 4, 4, 5, 6, 6, 7, 8, 9)
cstatus <- c(1, 0, 1, 1, 0, 1, 0, 1, 1, 0)
xc <- c(3, 5, 2, 4, 1, 5, 3, 2, 4, 1)
cs <- c("u", "v", "u", "v", "u", "u", "v", "v", "u", "v")
ones <- rep(1, length(time))

n_large <- 20000L
i_large <- 0:(n_large - 1L)
large_time <- as.double(i_large + 1L)
large_status <- ifelse(i_large %% 4L == 0L, 0, 1)
large_x <- as.double(i_large)
large_wt <- 1 + (i_large %% 5L) * 0.25
large_start <- as.double(i_large)
large_stop <- large_start + n_large

subset_right <- function(keep, wt) {
  pack_right(time[keep], status[keep], x[keep], wt[keep])
}
subset_count <- function(keep, wt) {
  pack_count(start[keep], stop[keep], cstatus[keep], xc[keep], wt[keep])
}

# Same order as packages/survival/proof/survconc.py.
cases <- list(
  list(kind = "right", pack = pack_right(time, status, x, ones)),
  list(kind = "right", pack = pack_right(time, status, x, w)),
  list(kind = "right", pack = subset_right(s == "a", ones)),
  list(kind = "right", pack = subset_right(s == "b", ones)),
  list(kind = "count", pack = pack_count(start, stop, cstatus, xc, ones)),
  list(kind = "count", pack = pack_count(start, stop, cstatus, xc, w)),
  list(kind = "count", pack = subset_count(cs == "u", ones)),
  list(kind = "count", pack = subset_count(cs == "v", ones)),
  list(kind = "count", pack = pack_count(c(0, 0, 2), c(2, 3, 4), c(1, 1, 1), c(1, 2, 0), c(1, 1, 1))),
  list(kind = "count", pack = pack_count(c(0, 0, 1), c(5, 3, 4), c(0, 1, 1), c(1, 2, 0), c(1, 1, 1))),
  list(kind = "right", pack = pack_right(large_time, large_status, large_x, large_wt)),
  list(kind = "count", pack = pack_count(large_start, large_stop, large_status, large_x, large_wt))
)

sym1 <- survival:::Cconcordance1
sym2 <- survival:::Cconcordance2

one <- function() {
  out <- vector("list", length(cases))
  for (k in seq_along(cases)) {
    p <- cases[[k]]$pack
    if (cases[[k]]$kind == "right") {
      out[[k]] <- .Call(sym1, p$y, p$wt, p$index, p$ntree)
    } else {
      out[[k]] <- .Call(sym2, p$y, p$wt, p$index, p$ntree, p$sort_stop, p$sort_start)
    }
  }
  out
}

raw <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(vapply(raw, fmt, ""), collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
