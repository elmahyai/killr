library(mclust)
tryCatch(gmmhd(list()), error=function(e) {
  cat(conditionMessage(e), "\n")
})
