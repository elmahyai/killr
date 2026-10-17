suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
one <- list(
 checkModelName=function() checkModelName("EEE"),
 decomp2sigma=function() decomp2sigma(2,1,2,c(1,3)),
 defaultPrior=function() defaultPrior(matrix(c(1,2,2,4,3,6),3,2,byrow=TRUE),2,"EEE")$dof,
 dupPartition=function() dupPartition(c(1,1,2,2)),
 mclustModel=function() { d <- matrix(c(1,2,2,3,3,4),3,2,byrow=TRUE); b <- matrix(1,2,1,dimnames=list(c("1","2"),"EEE")); mclustModel(d,b,G=1,modelNames="EEE") },
 mclustModelNames=function() mclustModelNames("EEE"),
 mclustVariance=function() mclustVariance("VVI",2,3),
 nMclustParams=function() nMclustParams("VVV",2,3),
 nVarParams=function() nVarParams("EEE",2,3),
 partconv=function() partconv(c(4,2,4,7)),
 partuniq=function() partuniq(matrix(c(1,2,1,2,2,3),3,2,byrow=TRUE)),
 priorControl=function() priorControl(shrinkage=.1),
 sigma2decomp=function() sigma2decomp(diag(c(2,8)))
)
for (nm in names(one)) {
 value <- one[[nm]]()
 elapsed <- numeric(20)
 for (i in seq_len(20)) { t <- as.numeric(Sys.time()); one[[nm]](); elapsed[i] <- as.numeric(Sys.time())-t }
 cat(nm, ": ", capture.output(str(value)), " median_ms=", median(elapsed)*1000, "\n", sep="")
}
