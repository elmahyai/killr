library(mclust)
obj <- list(title="GMM with high-density connected components for clustering",
            Mclust=list(G=2, modelName="VVV"),
            MclustDR=list(G=2, modelName="EEE"),
            clusterCores=table(c(1,1,2)), cluster=table(c(1,1,2,2)))
class(obj) <- "summary.gmmhd"
print(obj)
