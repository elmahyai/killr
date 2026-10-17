library(mclust)
tryCatch(gmmhdClassify(list()), error=function(e) {
  cat(conditionMessage(e), "\n")
})
