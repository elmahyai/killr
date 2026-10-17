suppressPackageStartupMessages(library(mclust))
x <- list(modelName="EEE", G=2, nboot=2, type="bs", d=1, what="ave",
          pro=c(.5,.5), mean=matrix(c(1.5,3.5),1,2),
          variance=array(c(1.5,3.5),c(1,1,2)))
class(x) <- "summary.MclustBootstrap"
cat(capture.output(print(x)), sep="\n")
