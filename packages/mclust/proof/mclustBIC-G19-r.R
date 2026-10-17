# Verification (not recorded): R mclust::mclustBIC with G = 1:9 on the Mclust-gaps inputs:
# the six inputs of Mclust-r.R, faithful, BIG (n = 2400, set.seed(2026)), and the noise
# cases NB, NC, NBV (noise rows as in Mclust-gaps-r.R). Run from packages/mclust:
#   Rscript proof/mclustBIC-G19-r.R
# Writes docs/output/mclustBIC-G19-r.txt: the BIC matrix (column-major) and the
# returnCodes for each input, and the median of 20 timed calls (Sys.time) as time_ms.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

xa_bank <- as.matrix(read.csv(file.path("proof", "mclust_fit_banknote6.csv"), header = FALSE))
ib <- seq_len(60L)
xb <- cbind(((ib * 37L) %% 11L) / 11 + 0.05 * ib / 60,
            ((ib * 23L) %% 13L) / 13 - 0.1 * ib / 60)
ia <- seq_len(40L)
xc <- ((ia * 37L) %% 11L) / 11 + 0.1 * ia / 40
xf <- c(((ia * 37L) %% 11L) / 11 + 0.1 * ia / 40, 5 + ((ia * 23L) %% 13L) / 13 - 0.1 * ia / 40)
xfa <- as.matrix(read.csv(file.path("proof", "mclust_faithful.csv"), header = FALSE))

ig <- seq_len(2400L)
xg <- cbind(sin(0.37 * ig + 1.3) + 0.4 * cos(0.11 * ig) + 3 * (ig > 1200L),
            cos(0.23 * ig) + 0.5 * sin(0.07 * ig))
noise_b <- c(3L, 17L, 29L, 44L, 58L)
noise_c <- c(2L, 5L, 9L)

fmt <- function(x) ifelse(is.na(x), "NA", sprintf("%.17g", as.numeric(x)))

one <- function() {
  list(
    A = suppressWarnings(mclustBIC(xa_bank, G = 1:9)),
    B = suppressWarnings(mclustBIC(xb, G = 1:9)),
    C = suppressWarnings(mclustBIC(xc, G = 1:9)),
    D = suppressWarnings(mclustBIC(xb, G = 1:9, modelNames = c("EII", "VII", "EEE", "VVV"))),
    E = suppressWarnings(mclustBIC(xc, G = 1:9, modelNames = c("E", "V"))),
    F = suppressWarnings(mclustBIC(xf, G = 1:9)),
    FA = suppressWarnings(mclustBIC(xfa, G = 1:9)),
    BIG = { set.seed(2026); suppressWarnings(mclustBIC(xg, G = 1:9)) },
    NB = suppressWarnings(mclustBIC(xb, G = 1:9, initialization = list(noise = noise_b))),
    NC = suppressWarnings(mclustBIC(xc, G = 1:9, initialization = list(noise = noise_c))),
    NBV = suppressWarnings(mclustBIC(xb, G = 1:9, initialization = list(noise = noise_b), Vinv = 0.5))
  )
}

fits <- one()
lines <- character(0)
for (k in c("A", "B", "C", "D", "E", "F", "FA", "BIG", "NB", "NC", "NBV")) {
  b <- fits[[k]]
  lines <- c(lines,
             paste(k, "BIC", sep = "\t"), paste(k, "BICdim", sep = "\t"),
             paste(k, "values", sep = "\t"),
             paste(k, "returnCodes", sep = "\t"))
  lines[length(lines) - 3] <- paste(k, "BIC", paste(fmt(dim(b)), collapse = "\t"), sep = "\t")
  lines[length(lines) - 2] <- paste(k, "BICdim", paste(fmt(dim(b)), collapse = "\t"), sep = "\t")
  lines[length(lines) - 1] <- paste(k, "values", paste(fmt(as.vector(unclass(b))), collapse = "\t"), sep = "\t")
  lines[length(lines)] <- paste(k, "returnCodes", paste(fmt(as.vector(attr(b, "returnCodes"))), collapse = "\t"), sep = "\t")
}

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
lines <- c(lines, paste("time_ms", fmt(median(elapsed)), sep = "\t"))

dir.create(file.path("docs", "output"), recursive = TRUE, showWarnings = FALSE)
writeLines(lines, file.path("docs", "output", "mclustBIC-G19-r.txt"))
cat("R mclustBIC G=1:9 median ms:", median(elapsed), "\n")
