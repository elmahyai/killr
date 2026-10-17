library(mclust)
obj <- list(Mclust=list(G=2, modelName="VVV"),
            MclustDR=list(G=2, modelName="EEE"),
            clusterCores=c(1,1,2,NA), cluster=c(1,1,2,2))
print(summary(obj))
