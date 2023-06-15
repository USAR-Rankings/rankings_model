#Preload
options(repos = list(CRAN="http://cran.rstudio.com/"))

# Package names
packages <- c("RSelenium",
              "jsonlite",
              "stringr",
              "dplyr",
              "tidyr",
              "tidyverse",
              "RecordLinkage",
              "DescTools",
              "plotly",
              "viridis",
              "lme4",
              "lubridate",
              "reticulate",
              "readxl",
              "dotenv")
# Install packages not yet installed
installed_packages <- packages %in% rownames(installed.packages())
if (any(installed_packages == FALSE)) {
  invisible(install.packages(packages[!installed_packages]))
}

# Packages loading
invisible(lapply(packages, library, character.only = TRUE))

# Loading variables from this module
load_dot_env(file=".env")
input_dir <- Sys.getenv("input_dir")
output_dir <- Sys.getenv("output_dir")
tourney_data_dir <- Sys.getenv("tourney_data_dir")
source_python("src/configs/constants.py")
source('src/utils/read_write.R')

timeouts <- function (remDr, milliseconds){
  qpath <- sprintf("%s/session/%s/timeouts", remDr$serverURL,
                   remDr$sessionInfo[["id"]])
  remDr$queryRD(qpath, method = "POST", qdata = toJSON(list(type = "implicit", ms = milliseconds), 
                                                       auto_unbox = TRUE))
}