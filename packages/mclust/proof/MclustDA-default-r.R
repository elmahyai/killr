# Proof: R mclust::MclustDA with the default modelType (MclustDA) on fixed inputs.
# Run from packages/mclust:
#   Rscript proof/MclustDA-default-r.R
# Writes docs/output/MclustDA-default-r.txt: one record per line,
# "key<TAB>type<TAB>values", type n = numeric, s = string. The last record is the
# median of 20 timed calls (Sys.time, milliseconds) of fit + predict.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Fixed inputs. No duplicate rows and n <= 2000 for every case.
# Case A: two-dimensional, n = 90, three classes of 30 (default G = 1:5, all models).
# Case B: one-dimensional, n = 60, two classes of 30 (modelNames E, V).
# Case C: three-dimensional, n = 120, two classes of 60.
# Case D: three-dimensional, n = 83, classes of 40, 40 and 3 (n_k <= d drops the
#         non-diagonal models for the class of 3).
i_a <- seq_len(90L); g_a <- (i_a - 1L) %/% 30L
xa <- cbind(((i_a * 37L) %% 11L) / 11 + 2.5 * g_a + 0.05 * i_a / 90,
            ((i_a * 23L) %% 13L) / 13 + 1.5 * g_a + 0.4 * (((i_a * 37L) %% 11L) / 11) + 0.01 * i_a)
ya <- factor(c("a", "b", "c")[g_a + 1L])

i_b <- seq_len(60L); g_b <- (i_b - 1L) %/% 30L
xb <- matrix(sin(0.37 * i_b) + 2.5 * g_b + 0.05 * i_b / 60, ncol = 1L)
yb <- factor(c("hi", "lo")[g_b + 1L], levels = c("hi", "lo"))

mk3 <- function(i, g) {
  n <- length(i)
  x <- matrix(0, n, 3L)
  for (j in 1:3) x[, j] <- sin(0.37 * i + 1.3 * j) + 0.4 * cos(0.11 * i * j) +
    1.5 * g * (j / 3) + 0.05 * i / n * j
  x
}
i_c <- seq_len(120L); g_c <- (i_c - 1L) %/% 60L
xc <- mk3(i_c, g_c)
yc <- factor(c("u", "v")[g_c + 1L])

i_d <- seq_len(83L); g_d <- ifelse(i_d <= 40L, 0L, ifelse(i_d <= 80L, 1L, 2L))
xd <- mk3(i_d, g_d)
yd <- factor(c("p", "q", "r")[g_d + 1L])

cases <- list(
  A = list(x = xa, y = ya),
  B = list(x = xb, y = yb),
  C = list(x = xc, y = yc),
  D = list(x = xd, y = yd)
)
for (cs in cases) {
  if (anyDuplicated(cs$x)) stop("duplicate rows in a proof input")
}

num_rec <- function(key, x) {
  x <- as.numeric(x)
  sprintf("%s\tn\t%s", key, paste(ifelse(is.na(x), "NA", sprintf("%.17g", x)), collapse = " "))
}
str_rec <- function(key, x) sprintf("%s\ts\t%s", key, paste(as.character(x), collapse = " "))

emit_matrix <- function(key, x) {
  if (is.null(x)) return(character(0))
  c(num_rec(paste0(key, "|dim"), dim(x)), num_rec(key, x))
}

emit_pred <- function(prefix, pred, levs) {
  c(num_rec(paste0(prefix, "|classification"), match(as.character(pred$classification), levs)),
    emit_matrix(paste0(prefix, "|z"), unclass(pred$z)))
}

emit_fit <- function(case, fit, nd_pred, levs) {
  p <- function(k) paste0(case, "|", k)
  out <- c(
    num_rec(p("n"), fit$n),
    num_rec(p("d"), fit$d),
    num_rec(p("prop"), fit$prop),
    num_rec(p("loglik"), fit$loglik),
    num_rec(p("df"), fit$df),
    num_rec(p("bic"), fit$bic),
    str_rec(p("type"), fit$type),
    str_rec(p("labels"), levs)
  )
  out <- c(out, emit_pred(p("train"), attr(fit, "pred"), levs))
  out <- c(out, emit_pred(p("newdata"), nd_pred, levs))
  for (l in seq_along(fit$models)) {
    m <- fit$models[[l]]
    q <- function(k) paste0(case, "|class", l, "|", k)
    out <- c(out,
      str_rec(q("modelName"), m$modelName),
      num_rec(q("G"), m$G),
      num_rec(q("n"), m$n),
      num_rec(q("loglik"), m$loglik),
      num_rec(q("observations"), m$observations),
      num_rec(q("classification"), m$classification),
      emit_matrix(q("z"), m$z),
      num_rec(q("uncertainty"), m$uncertainty),
      emit_matrix(q("BIC"), unclass(m$BIC)),
      str_rec(q("BIC|modelNames"), colnames(m$BIC)),
      str_rec(q("BIC|G"), rownames(m$BIC)),
      emit_matrix(q("mean"), m$parameters$mean),
      num_rec(q("pro"), m$parameters$pro)
    )
    v <- m$parameters$variance
    for (nm in c("sigma", "sigmasq", "scale", "shape", "orientation", "Sigma",
                 "cholSigma", "cholsigma")) {
      if (!is.null(v[[nm]])) out <- c(out, emit_matrix(q(paste0("variance|", nm)), v[[nm]]))
    }
  }
  out
}

one_case <- function(nm) {
  cs <- cases[[nm]]
  fit <- MclustDA(cs$x, cs$y, verbose = FALSE)
  levs <- levels(cs$y)
  attr(fit, "pred") <- predict.MclustDA(fit, newdata = cs$x)
  nd <- cs$x[seq(1, nrow(cs$x), by = 3), , drop = FALSE] + 0.07
  nd_pred <- predict.MclustDA(fit, newdata = nd)
  list(fit = fit, nd = nd_pred, levs = levs, case = nm)
}

one <- function() lapply(names(cases), one_case)

results <- one()
lines <- character(0)
for (r in results) {
  lines <- c(lines, emit_fit(r$case, r$fit, r$nd, r$levs))
}

elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[k] <- (as.numeric(Sys.time()) - t0) * 1000
}
# Per case: one untimed call, then the median of 20 timed calls of fit + predict.
for (nm in names(cases)) {
  one_case(nm)
  el <- numeric(20)
  for (k in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    one_case(nm)
    el[k] <- (as.numeric(Sys.time()) - t0) * 1000
  }
  lines <- c(lines, sprintf("%s|time_ms\tn\t%.17g", nm, median(el)))
}
lines <- c(lines, sprintf("time_ms\tn\t%.17g", median(elapsed)))
writeLines(lines, file.path("docs", "output", "MclustDA-default-r.txt"))
cat(lines[length(lines)], "\n")
