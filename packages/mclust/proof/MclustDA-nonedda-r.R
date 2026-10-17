.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
output_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output"

make_data <- function() {
  n <- 60L
  t <- 0:(n - 1L)
  centers <- list(c(-3, -3), c(3, 3), c(-3, 3))
  x <- lapply(centers, function(center) {
    cbind(
      center[[1]] + 0.45 * sin(t * 0.71) + ifelse(t < 30, -0.8, 0.8),
      center[[2]] + 0.45 * cos(t * 0.53) + ifelse(t < 30, 0.7, -0.7)
    )
  })
  list(x = do.call(rbind, x), class = factor(rep(1:3, each = n)))
}

input <- make_data()
one <- function() {
  set.seed(1)
  fit <- MclustDA(
    input$x, input$class, G = 1:3,
    modelNames = c("EEE", "VEI"), modelType = "MclustDA",
    verbose = FALSE
  )
  predict(fit)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

writeLines(as.character(value$classification),
           file.path(proof_dir, "MclustDA-nonedda-r-labels.txt"))
write.table(value$z, file.path(proof_dir, "MclustDA-nonedda-r-z.csv"),
            sep = ",", row.names = FALSE, col.names = FALSE)
writeLines(sprintf("%.17g", median(elapsed) * 1000),
           file.path(proof_dir, "MclustDA-nonedda-r-ms.txt"))
writeLines(c(
  "MclustDA non-EDDA classification",
  "components 2/2/2",
  sprintf("r_ms %.17g", median(elapsed) * 1000)
), file.path(output_dir, "MclustDA-nonedda-r.txt"))
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
