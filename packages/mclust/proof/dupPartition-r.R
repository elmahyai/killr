# Proof: R mclust::dupPartition and hc with that partition (mclust 6.1.3).
# Run from packages/mclust:
#   Rscript proof/dupPartition-r.R
# dupPartition uses kmeans (Hartigan-Wong) on the distinct rows. Writes
# docs/output/dupPartition-r.txt and the median of 20 timed calls (Sys.time) as time_ms.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

ia <- seq_len(40L)
xc <- ((ia * 37L) %% 11L) / 11 + 0.1 * ia / 40
xfa <- as.matrix(read.csv(file.path("proof", "mclust_faithful.csv"), header = FALSE))

fmt <- function(x) ifelse(is.na(x), "NA", sprintf("%.17g", as.numeric(x)))
rec <- function(key, x) paste(c(key, fmt(as.vector(x))), collapse = "\t")

one <- function() {
  list(
    DPfa = dupPartition(xfa),
    DPsmall = dupPartition(c(1, 1, 2, 2)),
    DPc = dupPartition(xc),
    HCdefault = hc(xfa, modelName = "VVV", use = "SVD"),
    HCpart = hc(xfa, modelName = "VVV", use = "SVD", partition = dupPartition(xfa))
  )
}

fits <- one()
lines <- c(
  rec("DPfa", fits$DPfa),
  rec("DPsmall", fits$DPsmall),
  rec("DPc", fits$DPc),
  rec("HCdefault", unclass(fits$HCdefault)),
  rec("HCdefault.initialPartition", attr(fits$HCdefault, "initialPartition")),
  rec("HCpart", unclass(fits$HCpart)),
  rec("HCpart.initialPartition", attr(fits$HCpart, "initialPartition"))
)

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
lines <- c(lines, paste("time_ms", fmt(median(elapsed)), sep = "\t"))

dir.create(file.path("docs", "output"), recursive = TRUE, showWarnings = FALSE)
writeLines(lines, file.path("docs", "output", "dupPartition-r.txt"))
cat("R dupPartition median ms:", median(elapsed), "\n")
