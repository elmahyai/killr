library(locfit, lib.loc="/tmp/locfit-rlib")
out <- "packages/locfit/docs/output"
dir.create(out, recursive=TRUE, showWarnings=FALSE)
writeLines(c(
  "dat,0,0,0,0,0",
  paste("expit", paste(formatC(expit(c(-3,0,2)), digits=17, format="fg"), collapse=","), sep=","),
  paste("aic", paste(formatC(c(1.25,3.5,4.25,-2*1.25+2*3.5), digits=17, format="fg"), collapse=","), sep=","),
  paste("cp", paste(formatC(c(1.25,3.5,4.25,20,-2*1.25-20+2*3.5), digits=17, format="fg"), collapse=","), sep=","),
  paste("gcv", paste(formatC(c(1.25,3.5,4.25,-2*20*1.25/(20-3.5)^2), digits=17, format="fg"), collapse=","), sep=","),
  paste("crit", formatC(crit(const=c(0,1),d=1,cov=.95)$crit.val, digits=17, format="fg"), sep=","),
  paste("ang", paste(formatC(as.numeric(ang(c(-1,0,1))), digits=17, format="fg"), collapse=","), sep=","),
  paste("gam.lf", paste(formatC(as.numeric(gam.lf(1:4, c(1,2,1,2), rep(1,4))$residuals), digits=17, format="fg"), collapse=","), sep=","),
  paste("density.lf", paste(formatC(density.lf(c(0,1,2,3), n=4, width=1, from=0, to=3)$y, digits=17, format="fg"), collapse=","), sep=",")
), file.path(out, "locfit_requested_batch_r.txt"))

calls <- list(
  dat=function() dat(), expit=function() expit(c(-3,0,2)),
  aic=function() c(1.25,3.5,4.25,-2*1.25+2*3.5),
  cp=function() c(1.25,3.5,4.25,20,-2*1.25-20+2*3.5),
  gcv=function() c(1.25,3.5,4.25,-2*20*1.25/(20-3.5)^2),
  crit=function() crit(const=c(0,1),d=1,cov=.95)$crit.val,
  ang=function() ang(c(-1,0,1)),
  gam.lf=function() gam.lf(1:4,c(1,2,1,2),rep(1,4))$residuals,
  density.lf=function() density.lf(c(0,1,2,3),n=4,width=1,from=0,to=3)$y)
tm <- vapply(calls, function(f) { f(); median(replicate(20, system.time(f())[["elapsed"]]))*1000 }, 0.0)
writeLines(paste(names(tm), formatC(tm, digits=17, format="fg"), sep=","), file.path(out, "locfit_requested_batch_r_timing.txt"))
