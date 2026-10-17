args <- commandArgs(trailingOnly=TRUE)
out <- args[[1]]
time_out <- args[[2]]
lib <- Sys.getenv("LMOM_R_LIB", file.path(Sys.getenv("HOME"), ".cache/killr/Rlib-lmom-3.3"))
suppressPackageStartupMessages(library(lmom, lib.loc=lib))
x <- c(-.7,.2,1.1,2.4,3,4.8)
uq <- function(p, a=c(0,1)) a[1]+a[2]*p
up <- function(x, a=c(0,1)) pmin(pmax((x-a[1])/a[2],0),1)
f <- list(
  samlmu=function() samlmu(x,4,TRUE,TRUE),
  `samlmu.s`=function() samlmu.s(x,4,TRUE,TRUE),
  `.samlmu`=function() lmom:::.samlmu(x,4),
  lmrp=function() lmrp(up, bounds=c(0,1), order=1:4, ratios=TRUE),
  lmrq=function() lmrq(uq, order=1:4, ratios=TRUE),
  pelp=function() pelp(c(.5,1/6), up, c(0,1), type="ls")$para,
  pelq=function() pelq(c(.5,1/6), uq, c(0,1), type="ls")$para,
  evdistp=function() c(-log(-log(seq(1/12,11/12,length.out=11))), up(seq(1/12,11/12,length.out=11))),
  evdistq=function() c(-log(-log(seq(1/12,11/12,length.out=11))), uq(seq(1/12,11/12,length.out=11)))
)
z <- unlist(lapply(f, function(g) as.numeric(g())))
writeLines(sprintf("%.17g", z), out)
tim <- vapply(f, function(g) {
  g()
  z <- numeric(20)
  for (i in seq_len(20)) {
    t <- Sys.time(); g(); z[i] <- as.numeric(difftime(Sys.time(), t, units="secs"))
  }
  median(z) * 1000
}, numeric(1))
writeLines(sprintf("%.17g", tim), time_out)
