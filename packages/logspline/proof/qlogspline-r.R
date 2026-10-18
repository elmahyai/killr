source("packages/logspline/proof/_batch_common.R")
print(qlogspline(c(.1,.5,.9), structure(fit, class="logspline")))
