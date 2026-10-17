library(mclust)
obj <- list(Mclust=list(G=2, modelName="VVV"),
            MclustDR=list(G=2, modelName="EEE"), numClusters=2)
class(obj) <- "gmmhd"
print(obj)
