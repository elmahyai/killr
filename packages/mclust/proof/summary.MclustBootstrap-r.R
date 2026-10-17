suppressPackageStartupMessages(library(mclust))
x <- list(G=2, modelName="EEE", nboot=2, type="bs", nonfit=0,
          pro=matrix(c(.4,.6,.3,.7),2,2), mean=array(1:8,c(2,1,2)),
          variance=array(1:8,c(2,1,1,2)))
class(x) <- "MclustBootstrap"
for (what in c("se","ave","ci")) {
  y <- summary(x, what=what)
  cat(what, y$pro, y$mean, y$variance, "\n")
}
