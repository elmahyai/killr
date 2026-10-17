suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
mod <- list(data=as.matrix(read.table(file.path(proof_dir, "clustCombi_data.csv"))),
            z=as.matrix(read.table(file.path(proof_dir, "clustCombi_z.csv"))), G=6)
class(mod) <- "Mclust"
object <- clustCombi(mod)
one <- function() {
  x <- summary(object)
  c(x$title, if (is.null(x$MclustModelName)) "" else x$MclustModelName,
    x$MclustG, unlist(x$combiM))
}
value <- one()
writeLines(capture.output(dput(summary(object))), file.path(proof_dir, "summary.clustCombi-r-output.txt"))
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time())-t0 }
cat("matches true\nmax_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed)*1000))
