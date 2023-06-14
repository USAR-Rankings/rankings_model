#Preload
options(repos = list(CRAN="http://cran.rstudio.com/"))

# suppressPackageStartupMessages(install.packages('tibble'))
# suppressPackageStartupMessages(install.packages('dplyr'))
suppressMessages(library(RSelenium))
suppressMessages(library(jsonlite))
suppressMessages(library(rvest))
suppressMessages(library(stringr))
suppressMessages(library(dplyr))
suppressMessages(library(tidyr))
suppressMessages(library(tidyverse))
suppressMessages(library(RecordLinkage))
suppressMessages(library(DescTools))
suppressMessages(library(plotly))
suppressMessages(library(viridis))
suppressMessages(library(lme4))
# suppressMessages(library(googlesheets4))
# suppressMessages(library(googledrive))
suppressMessages(library(lubridate))
# suppressPackageStartupMessages(install.packages('reticulate'))
suppressMessages(library(reticulate))
suppressMessages(library(readxl))
# suppressPackageStartupMessages(install.packages('dotenv'))
suppressMessages(library(dotenv))

# Loading variables from this module
load_dot_env(file="../../.env")
input_dir <- Sys.getenv("input_dir")
output_dir <- Sys.getenv("output_dir")
tourney_data_dir <- Sys.getenv("tourney_data_dir")
source_python("../configs/constants.py")
source('../utils/read_write.R')

timeouts <- function (remDr, milliseconds){
  qpath <- sprintf("%s/session/%s/timeouts", remDr$serverURL,
                   remDr$sessionInfo[["id"]])
  remDr$queryRD(qpath, method = "POST", qdata = toJSON(list(type = "implicit", ms = milliseconds), 
                                                       auto_unbox = TRUE))
}