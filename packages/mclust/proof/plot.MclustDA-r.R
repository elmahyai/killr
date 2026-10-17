.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))

data <- matrix(c(-1,-1, -.5,-1, .5,1, 1,1, 1.5,1, 2,2), ncol=2, byrow=TRUE)
cl <- factor(c(1,1,1,2,2,2))
model <- function(mu, obs) list(
  modelName="EEE", n=3L, d=2L, G=1,
  parameters=list(pro=1, mean=matrix(mu, 2, 1),
    variance=list(modelName="EEE", d=2L, G=1, sigma=matrix(c(1,0,0,1),2,2),
                  Sigma=diag(2), cholSigma=diag(2))),
  classification=rep(1, 3), observations=obs)
fit <- list(data=data, class=cl, type="EDDA", n=6L, d=2L,
            prop=c("1"=.5, "2"=.5),
            models=list(model(c(-1,-1),1:3), model(c(1,1),4:6)))
class(fit) <- "MclustDA"
grid <- as.matrix(expand.grid(seq(-2, 2, length.out=25), seq(-2, 2, length.out=25)))
one <- function() {
  pred <- predict(fit, grid)$classification
  png(tempfile(), width=400, height=400)
  plot(fit, what="classification")
  dev.off()
  c(as.numeric(pred), as.numeric(predict(fit, data)$classification))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time()); one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
dir.create(file.path("docs", "output"), showWarnings=FALSE, recursive=TRUE)
writeLines(sprintf("%.17g", value), file.path("docs", "output", "plot.MclustDA-r.txt"))
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path("docs", "output", "plot.MclustDA-r-time.txt"))
