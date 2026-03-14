
OPEN_P= {
# Filepath to where the data is
"BASE_PATH": "",
"DATA_PATH": "data/open_full_tournaments.csv",

# Set number of events to use to use intial sperateion for (25 is what was used for final model)
"NUMB_INITAL" : 25,

# Set up Model parameters

"remove":True,
"team_method":"inv_var",
"avg_mu":False,

            # RD bounds
"RD_MIN":80,      # ~80.36


            # team uncertainty (inv-var)
"team_var_alpha":1.32,   # ~1.317
"inv_var_gamma":0.60,

            # RD shrink cap
"cap_redux":True,
"max_reduction_frac":0.67,  # ~0.6699

            # volatility learning
"tau":0.50,  # ~0.491

            # inactivity RD inflation curve (your chosen saturating form)
"rd_inflation_mode":"saturating",
"time_constant":0.90,         # time_constant_phi
"buffer_days":25,
"decay_tau_days":365 * 1.5,   # 547.5
"sat_power":0.95,

 # kept for compatibility (ignored in saturating mode)
"convexity":0.70,
"DE":450,
"DC":625,


# Export results filename
"EXPORT_FILENAME" : "open"}

WOMENS_P= {
# Filepath to where the data is
"BASE_PATH": "",
"DATA_PATH" : "data/women_full_tournaments.csv",

# Set number of events to use to use intial sperateion for (25 is what was used for final model)
"remove":True,
"team_method":"inv_var",
"avg_mu":False,

            # RD bounds
"RD_MIN":60,      # ~80.36


            # team uncertainty (inv-var)
"team_var_alpha":1.32,   # ~1.317
"inv_var_gamma":0.60,

            # RD shrink cap
"cap_redux":True,
"max_reduction_frac":0.67,  # ~0.6699

            # volatility learning
"tau":0.60,  # ~0.491

            # inactivity RD inflation curve (your chosen saturating form)
"rd_inflation_mode":"saturating",
"time_constant":0.90,         # time_constant_phi
"buffer_days":25,
"decay_tau_days":365 * 1.5,   # 547.5
"sat_power":1.7,

 # kept for compatibility (ignored in saturating mode)
"convexity":0.70,
"DE":575,
"DC":625,


# Export results filename
"EXPORT_FILENAME" : "womens"}
