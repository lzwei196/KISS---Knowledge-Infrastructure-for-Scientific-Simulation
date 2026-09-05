# Cross-platform installation probe for the model implementation used by this KI.
.libPaths(c("KISSPATH_HOME/R/library", .libPaths()))
suppressPackageStartupMessages(library(airGR))
cat(as.character(packageVersion("airGR")), "\n")
