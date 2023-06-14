"
R script to define the same read write helper functions as that in the python version
"


# Function to read all CSV files from a given directory
read_all_data_in_dir <- function(file_path_list){
    # Creating the entire file path name
    full_path = paste(file_path_list, collapse='/' )
    # Reading in and concatting all the files
    df <-
      list.files(path = full_path, pattern = "*.csv", full.names=TRUE) %>%
      map_df(~read.csv(.))
    return(df)
}


# Function to read specific CSV file from a given directory
read_data <- function(file_path_list, file_name, sheet_name=""){
    # Creating the entire file path name
    full_path = paste(file_path_list, collapse='/' )
    full_path_w_file = paste(c(full_path, file_name), collapse='/' )
    # Checking the file type and reading in
    if (grepl('xlsx', file_name, fixed=TRUE)){
        # Reading in the excel file
        df <- read_excel(full_path_w_file, sheet=sheet_name)
    } else {
        # Reading in the CSV
        df <- read.csv(full_path_w_file, as.is = T, stringsAsFactors = F, fileEncoding="UTF-8")
    }
    return(df)
}


# Function to write specific CSV file from a given directory
write_data <- function(file_path_list, file_name, df){
    # Creating the entire file path name
    full_path = paste(file_path_list, collapse='/' )
    # Checking if path exists and if not, creating it
    if (!file.exists(full_path)){
        dir.create(file.path(full_path))
    }
    # Writing out the CSV
    write.csv(df, file = cat(full_path, file_name), row.names = F)
}