library(mclust)
obj <- list(x=matrix(0, 5, 1), nc=c(1,2,2,1),
            con=list(list(1:5), list(1:2,3:5), list(1:2,3:4,5), list(1:5)))
value <- gmmhdClusterCores(obj)
print(value)
