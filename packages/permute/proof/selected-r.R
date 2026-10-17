library(permute)
options(error = function() {
  traceback(3)
  q(status = 1)
})

dir <- dirname(sub("^--file=", "", commandArgs()[grep("^--file=", commandArgs())]))
out <- file.path(dir, "..", "docs", "output")
dir.create(out, recursive = TRUE, showWarnings = FALSE)

ctrl <- how(within = Within(type = "free"), nperm = 5, observed = TRUE)
mat <- allPerms(4, ctrl)

value <- list(
  getHow = function() {
    x <- getHow(mat)
    paste(x$nperm, x$observed, x$within$type, x$plots$type, sep = "|")
  },
  how = function() {
    x <- how(within = Within(type = "series", mirror = TRUE),
            plots = Plots(type = "free"), nperm = 17, complete = TRUE)
    paste(x$nperm, x$complete, x$within$type, x$within$mirror,
          x$plots$type, sep = "|")
  },
  numPerms = function() as.character(numPerms(4, ctrl)),
  permute = function() paste(permute(2, 4,
    how(complete = TRUE, all.perms = mat)), collapse = ","),
  Plots = function() {
    x <- Plots(strata = c(1, 1, 2, 2), type = "free",
               mirror = TRUE, ncol = 2, nrow = 2)
    paste(paste(as.character(x$strata), collapse = ","), x$type,
          x$mirror, x$ncol, x$nrow,
          sep = "|")
  },
  `setBlocks<-` = function() {
    x <- how(); setBlocks(x) <- c("a", "a", "b", "b")
    paste(as.character(getStrata(x, which = "blocks")), collapse = ",")
  },
  `setWithin<-` = function() {
    x <- how(); setWithin(x) <- Within(type = "series", mirror = TRUE)
    paste(x$within$type, x$within$mirror, sep = "|")
  },
  `setStrata<-` = function() {
    x <- how(); setStrata(x) <- c("a", "a", "b", "b")
    paste(as.character(getStrata(x)), collapse = ",")
  },
  `setType<-` = function() {
    x <- Within(); setType(x) <- "series"; x$type
  },
  `setMirror<-` = function() {
    x <- Within(); setMirror(x) <- TRUE; as.character(x$mirror)
  },
  `setConstant<-` = function() {
    x <- Within(); setConstant(x) <- TRUE; as.character(x$constant)
  }
)

vals <- vapply(names(value), function(nm) {
  tryCatch(value[[nm]](), error = function(e) {
    stop(sprintf("%s: %s", nm, conditionMessage(e)))
  })
}, character(1))
writeLines(vals, file.path(out, "selected-r-values.txt"))
timings <- vapply(names(value), function(nm) {
  tryCatch({
    f <- value[[nm]]
    f()
    z <- numeric(20)
    for (i in seq_len(20)) {
      t <- Sys.time()
      f()
      z[i] <- as.numeric(difftime(Sys.time(), t, units = "secs")) * 1000
    }
    median(z)
  }, error = function(e) {
    stop(sprintf("%s: %s", nm, conditionMessage(e)))
  })
}, numeric(1))
names(timings) <- names(value)
write.table(data.frame(name = names(timings), r_ms = unname(timings)),
            file = file.path(out, "selected-r-timings.txt"),
            row.names = FALSE, col.names = TRUE, sep = "\t", quote = FALSE)
if (FALSE) {
lib <- "/tmp/permute-lib"
if (dir.exists(lib)) .libPaths(c(lib, .libPaths()))
library(permute)

out <- dirname(sub("^--file=", "", commandArgs()[grep("^--file=", commandArgs())]))
out <- file.path(out, "..", "docs", "output")
dir.create(out, recursive = TRUE, showWarnings = FALSE)

writeLines(c(
  paste0("Within=", paste(capture.output(str(unclass(Within()))), collapse = " ")),
  paste0("nobs_scalar=", nobs(7)),
  paste0("nobs_vector=", nobs(1:4))
), file.path(out, "selected-r-values.txt"))

set.seed(1729)
random <- list(
  shuffle = shuffle(4, how(within = Within(type = "free"))),
  shuffleFree = shuffleFree(4, 4),
  shuffleGrid = shuffleGrid(2, 2),
  shuffleSeries = shuffleSeries(1:4),
  shuffleSet = shuffleSet(4, 2, how(within = Within(type = "free"))),
  shuffleStrata = shuffleStrata(rep(1:2, 2), "free")
)
writeLines(vapply(names(random), function(n)
  paste0(n, "=", paste(capture.output(dput(random[[n]])), collapse = "")),
  character(1)), file.path(out, "selected-r-random.txt"))

metrics <- data.frame(
  name = c("shuffle", "shuffleFree", "shuffleGrid", "shuffleSeries",
           "shuffleSet", "shuffleStrata", "Within", "nobs"),
  matches = c(rep("blocked", 6), "yes", "yes"),
  max_abs_diff = c(rep(NA, 6), 0, 0),
  r_ms = c(rep(NA, 6), NA, NA),
  translated_ms = c(rep(NA, 6), NA, NA),
  speedup = c(rep(NA, 8)),
  blocked_by = c(rep("R RNG algorithm cannot be reproduced exactly by NumPy",
                     6), "", "")
)
write.csv(metrics, file.path(out, "selected-metrics-r.csv"), row.names = FALSE,
          quote = FALSE, na = "NA")
}
