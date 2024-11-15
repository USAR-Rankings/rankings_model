
OPEN_P= {
# Filepath to where the data is
"DATA_PATH" : "data/open_full_tournaments.csv",

# Set number of events to use to use intial sperateion for (25 is what was used for final model)
"NUMB_INITAL" : 25,

# Set up Model parameters
"K1":125,
"K2":50,
"NG":11,
"DC":700,
"DE":425,
"SEP":2000,
"DECAY":True,
"DECAY_ARRAY":[5,8,18,40],


# Export results filename
"EXPORT_FILENAME" : "open"}

WOMENS_P= {
# Filepath to where the data is
"DATA_PATH" : "data/women_full_tournaments.csv",

# Set number of events to use to use intial sperateion for (25 is what was used for final model)
"NUMB_INITAL" : 14,

# Set up Model parameters
"K1":225,
"K2":115,
"NG":11,
"DC":700,
"DE":425,
"SEP":2000,
"DECAY":False,
"DECAY_ARRAY":[0,0,0,0],


# Export results filename
"EXPORT_FILENAME" : "womens"}
