# Proof: R mclust::plot.MclustBootstrap (mclust 6.1.3), the drawn data.
# Run from packages/mclust:
#   Rscript proof/plot.MclustBootstrap-r.R
#
# The bootstrap objects are fitted here and written to
# docs/output/plot.MclustBootstrap-input.txt, so the Python plot check reads the
# same numbers and does not depend on the resampling code.
#
# The plot is run with a recorder: an environment E whose parent is the mclust
# namespace. hist, abline, lines and points are E's versions, so the records are
# the calls R makes: the hist breaks, counts, density and the drawn heights
# (XLAB, HIST), the usr box after hist (USR), the estimate line (ABLINE), the
# percentile interval (LINES) and the average (POINTS). hist draws on a null
# device so par("usr") is R's own.
#
# Output: docs/output/plot.MclustBootstrap-r.txt, one record per line, tab-separated,
# "CASE name" headers, and the last line time_ms: the median of 20 timed calls
# (Sys.time) to the timed case after one untimed call. In time mode the
# recorder draws nothing, as the Python side does with no figure.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
if (RNGkind()[1] != "Mersenne-Twister" || RNGkind()[3] != "Rejection") stop("expected default RNG kinds")

# Same fixed input as proof/MclustBootstrap-r.R.
ib <- seq_len(60L)
xb <- cbind(((ib * 37L) %% 11L) / 11 + 0.05 * ib / 60,
            ((ib * 23L) %% 13L) / 13 - 0.1 * ib / 60)
fit <- suppressWarnings(Mclust(xb))

fmtn <- function(x) ifelse(is.na(x), "NA", sprintf("%.17g", as.numeric(x)))
fmtf <- function(v) {
  if (is.null(v)) return("")
  if (is.character(v)) return(paste(v, collapse = " "))
  v <- as.numeric(v)
  if (length(v) == 0) return("")
  paste(vapply(v, function(z) if (is.na(z)) "NA" else sprintf("%.17g", z), ""), collapse = " ")
}

out_dir <- file.path("docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# ---- bootstrap inputs -------------------------------------------------------
dump_arr <- function(prefix, key, x) {
  dims <- if (is.null(dim(x))) length(x) else dim(x)
  paste(prefix, key, paste(dims, collapse = " "),
        paste(vapply(as.numeric(x), function(z) if (is.na(z)) "NA" else sprintf("%.17g", z), ""),
              collapse = " "), sep = "\t")
}
dump_obj <- function(prefix, b) {
  c(
    paste(prefix, "modelName", b$modelName, sep = "\t"),
    paste(prefix, "type", b$type, sep = "\t"),
    dump_arr(prefix, "G", b$G),
    dump_arr(prefix, "nboot", b$nboot),
    dump_arr(prefix, "nonfit", b$nonfit),
    dump_arr(prefix, "pro", b$pro),
    dump_arr(prefix, "mean", b$mean),
    dump_arr(prefix, "variance", b$variance),
    dump_arr(prefix, "par_pro", b$parameters$pro),
    dump_arr(prefix, "par_mean", b$parameters$mean),
    dump_arr(prefix, "par_variance", b$parameters$variance)
  )
}

set.seed(42)
b_bs <- MclustBootstrap(fit, nboot = 199, type = "bs")
b_jk <- MclustBootstrap(fit, type = "jk")
set.seed(7)
b_pb <- MclustBootstrap(fit, nboot = 199, type = "pb")
writeLines(c(dump_obj("bs", b_bs), dump_obj("jk", b_jk), dump_obj("pb", b_pb)),
           file.path(out_dir, "plot.MclustBootstrap-input.txt"))

# ---- recorder ---------------------------------------------------------------
E <- new.env(parent = asNamespace("mclust"))
E$mode <- "record"
E$log <- character(0)
put <- function(tag, ...) {
  fields <- vapply(list(...), fmtf, "")
  E$log <- c(E$log, paste(c(tag, fields), collapse = "\t"))
  invisible(NULL)
}

E$hist <- function(x, breaks, xlim = NULL, ylim = NULL, main = NULL, xlab = NULL,
                   ylab = NULL, border = NULL, col = NULL, ...) {
  if (E$mode == "time")
    return(invisible(graphics::hist(x, breaks = breaks, plot = FALSE)))
  h <- graphics::hist(x, breaks = breaks, xlim = xlim, ylim = ylim, main = main,
                      xlab = xlab, ylab = ylab, border = border, col = col, ...)
  put("XLAB", xlab)
  put("HIST", h$breaks, h$counts, h$density, if (h$equidist) h$counts else h$density)
  put("USR", par("usr"))
  invisible(h)
}
E$box <- function(...) invisible(NULL)
E$abline <- function(a = NULL, b = NULL, h = NULL, v = NULL, col = "black", lwd = 1,
                     lty = 1, ...) {
  if (E$mode == "time") return(invisible(NULL))
  put("ABLINE", v, col, lwd, lty)
  invisible(NULL)
}
E$lines <- function(x, y = NULL, col = "black", lwd = 1, ...) {
  if (E$mode == "time") return(invisible(NULL))
  put("LINES", x, y, col, lwd)
  invisible(NULL)
}
E$points <- function(x, y = NULL, pch = 1, col = "black", ...) {
  if (E$mode == "time") return(invisible(NULL))
  put("POINTS", x, y, pch, col)
  invisible(NULL)
}

pl <- get("plot.MclustBootstrap", envir = asNamespace("mclust"))
environment(pl) <- E
E$plot <- pl

# ---- cases ------------------------------------------------------------------
cases <- list(
  bs_pro_default = function() E$plot(b_bs, what = "pro"),
  bs_mean_noint = function() E$plot(b_bs, what = "mean", show.parest = FALSE, show.confint = FALSE),
  bs_var_custom = function() E$plot(b_bs, what = "var", xlim = c(0, 0.6), breaks = 6,
                                    xlab = "sd of var", col = "red", lwd = 1, lty = 2,
                                    hist.col = "lightblue", hist.border = "black"),
  jk_mean_default = function() E$plot(b_jk, what = "mean"),
  pb_pro_scalarbreaks = function() E$plot(b_pb, what = "pro", breaks = 12),
  # R's Mclust sets colnames(data) to "xb1", "xb2" (deparsed names), so the labels
  # start with them. Without rownames the label starts with a blank.
  pb_mean_nonames = function() {
    b <- b_pb
    rownames(b$parameters$mean) <- NULL
    E$plot(b, what = "mean")
  },
  bs_pro_ylim = function() E$plot(b_bs, what = "pro", ylim = c(0, 100),
                                  show.confint = FALSE, xlab = "p")
)
timed_case <- function() {
  E$plot(b_bs, what = "pro")
  E$plot(b_bs, what = "mean")
  E$plot(b_bs, what = "var")
}

pdf(NULL)
out <- character(0)
for (nm in names(cases)) {
  E$log <- character(0)
  E$mode <- "record"
  cases[[nm]]()
  out <- c(out, paste("CASE", nm), E$log)
}

E$mode <- "time"
timed_case()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  timed_case()
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
E$mode <- "record"
dev.off()

out <- c(out, paste("time_ms", fmtn(median(elapsed)), sep = "\t"))
writeLines(out, file.path(out_dir, "plot.MclustBootstrap-r.txt"))
cat("R plot.MclustBootstrap median ms:", median(elapsed), "\n")
