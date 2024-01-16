import pandas as pd
import numpy as np
import gspread
import random
import os

# Authenticating with Google Sheeets
# Note that authentication is saved locally, at ~/.config/gspread/credentials.json
gc = gspread.oauth()

# Read in the conversation samples
AWRY_SAMPLES = pd.read_csv('./conflict_reddit_data/samples/awry_samples.csv')
WINNNING_SAMPLES = pd.read_csv('./conflict_reddit_data/samples/winning_samples.csv')
CONVERSATIONS = pd.concat([AWRY_SAMPLES, WINNNING_SAMPLES], axis=0)

# Check for the conversation labeling log and create one if it doesn't exist
CONVERSATION_LABELING_LOG_PATH = './CONFLICT_CONVO_LABELING_LOG'
if(!os.path.isfile(CONVERSATION_LABELING_LOG_PATH)):
	# define a simple CSV
	log_setup = pd.DataFrame(columns = ["CONV_ID", "RATER", "LAST_UPDATED"])
	log_setup.to_csv(CONVERSATION_LABELING_LOG)

LABEL_LOG = pd.read_csv(CONVERSATION_LABELING_LOG_PATH)


"""
function: get_n_new_convos_to_rate
"""
def get_n_new_convos_to_rate(n_convos):
	# Identify conversations that have already been labeled
	already_labeled_ids = list(LABEL_LOG["CONV_ID"])
	df_to_label = CONVERATIONS[!CONVERSATIONS["CONV_ID"].isin(already_labeled_ids)]

	# get the first n conversation id's to label
	n_convo_ids = list(set{df_to_label["CONV_ID"]})[:n_convos]
	sample_to_label = df_to_label[df_to_label["CONV_ID"].isin(n_convo_ids)]

	return(sample_to_label)


