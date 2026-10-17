A <- matrix(c(.8,.1,.2,.2,.7,.1,.1,.2,.9,.6,.2,.3,.2,.8,.4),5,3,byrow=TRUE)
Target <- matrix(0, nrow(A), ncol(A))
W <- matrix(1, nrow(A), ncol(A))
if (!requireNamespace("GPArotation", quietly=TRUE)) stop("Install GPArotation 2026.8-2 before running proof")
cases <- list(
  oblimin=function() GPArotation:::oblimin(A,maxit=200),
  quartimax=function() GPArotation:::quartimax(A,maxit=200),
  GPFRSoblq=function() GPArotation:::GPFRSoblq(A,maxit=200),
  GPFRSorth=function() GPArotation:::GPFRSorth(A,maxit=200),
  GPFoblq.lp=function() GPArotation:::GPFoblq.lp(A,maxit=200),
  GPForth.lp=function() GPArotation:::GPForth.lp(A,maxit=200),
  bentlerT=function() GPArotation:::bentlerT(A,maxit=200),
  bentlerQ=function() GPArotation:::bentlerQ(A,maxit=200),
  tandemI=function() GPArotation:::tandemI(A,maxit=200),
  tandemII=function() GPArotation:::tandemII(A,maxit=200),
  bigeominT=function() GPArotation:::bigeominT(A,maxit=200),
  bigeominQ=function() GPArotation:::bigeominQ(A,maxit=200),
  infomaxT=function() GPArotation:::infomaxT(A,maxit=200),
  infomaxQ=function() GPArotation:::infomaxQ(A,maxit=200),
  mccammon=function() GPArotation:::mccammon(A,maxit=200),
  bifactorT=function() GPArotation:::bifactorT(A,maxit=200),
  bifactorQ=function() GPArotation:::bifactorQ(A,maxit=200),
  equamax=function() GPArotation:::equamax(A,maxit=200),
  parsimax=function() GPArotation:::parsimax(A,maxit=200),
  varimin=function() GPArotation:::varimin(A,maxit=200),
  lpT=function() GPArotation:::lpT(A,maxit=200),
  lpQ=function() GPArotation:::lpQ(A,maxit=200),
  targetT=function() GPArotation:::targetT(A,Target=Target,maxit=200),
  targetQ=function() GPArotation:::targetQ(A,Target=Target,maxit=200),
  pstT=function() GPArotation:::pstT(A,W=W,Target=Target,maxit=200),
  pstQ=function() GPArotation:::pstQ(A,W=W,Target=Target,maxit=200),
  oblimax=function() GPArotation:::oblimax(A,maxit=200),
  binormamin=function() GPArotation:::binormamin(A,maxit=200),
  entropy=function() GPArotation:::entropy(A,maxit=200),
  simplimax=function() GPArotation:::simplimax(A,maxit=200)
)
vals <- list()
for (nm in names(cases)) { r <- cases[[nm]](); vals[[nm]] <- c(as.numeric(r$loadings), r$Table[nrow(r$Table),2]); z <- numeric(20); for(i in 1:20) {t <- Sys.time(); cases[[nm]](); z[i] <- as.numeric(difftime(Sys.time(),t,units="secs"))*1000}; cat(nm, sprintf(" %.6f\n",median(z))) }
write.table(do.call(rbind, vals), "packages/GPArotation/docs/output/r_values.csv", sep=",", col.names=FALSE, row.names=names(vals))
