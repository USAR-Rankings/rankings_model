
OPEN_P= {
# Filepath to where the data is
"BASE_PATH": "",
# "DATA_PATH" : "data/open_full_tournaments.csv",
"DATA_PATH": "data/open_full_tournaments.csv",

# Set number of events to use to use intial sperateion for (25 is what was used for final model)
"NUMB_INITAL" : 25,

# Set up Model parameters
"K_ARRAY":[50,125,11],


"DC":625,
"DE":350,
"SEP":2000,
"DECAY":True,
"DECAY_ARRAY":[0,0,20,35],
"REMOVE": True,
"START_PER": 30,

# Export results filename
"EXPORT_FILENAME" : "open"}

WOMENS_P= {
# Filepath to where the data is
"BASE_PATH": "",
# "DATA_PATH" : "data/women_full_tournaments.csv",
"DATA_PATH" : "data/women_full_tournaments.csv",

# Set number of events to use to use intial sperateion for (25 is what was used for final model)
"NUMB_INITAL" : 14,

# Set up Model parameters
"K_ARRAY":[115,225,11],
"DC":700,
"DE":425,
"SEP":2000,
"DECAY":True,
"DECAY_ARRAY":[0,0,0,0],
"REMOVE": True,
"START_PER": 30,


# Export results filename
"EXPORT_FILENAME" : "womens"}
