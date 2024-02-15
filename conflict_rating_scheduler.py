import pandas as pd
import numpy as np
import gspread
import random
import os
import argparse
import time
from gspread_formatting import *
from rating_dictionary import RATING_DICTIONARY

# Authenticating with Google Sheeets
# Service Email: tpm-data-annotation@tpm-data-annotation.iam.gserviceaccount.com
gc = gspread.service_account(filename='./tpm-data-annotation-aae74b403ab4.json')

# Read in the conversations
AWRY = pd.read_csv('./conflict_reddit_data/full_data/conversations_gone_awry.csv', dtype={'timestamp': 'Int64', 'meta.score': 'Int64'})
WINNNING = pd.read_csv('./conflict_reddit_data/full_data/winning_conversations.csv', dtype={'timestamp': 'Int64', 'meta.score': 'Int64'})
CONVERSATIONS = pd.concat([AWRY, WINNNING], axis=0)

"""
Check for the conversation labeling log and create one if it doesn't exist
The conversation labeling log stores all of the samples that we have allocated to users, 
as well as the latest ratings.

Here's what each column in the conversation log should contain:
- CONV_ID: the id associated with the conversation
- id: the id associated with each message/chat
- rating_directness_content: the rating for directness assigned by the rater (content)
- rating_directness_expression: the rating for directness assigned by the rater (expression)
- rating_OI_content: the rating for directness assigned by the rater (content)
- rating_OI_expression: the rating for directness assigned by the rater (expression)
- rater_id: the userid of the rater
- status: {allocated, done}
- last_updated_time: time associated with the last update / check to this log item
""" 
CONVERSATION_LABELING_LOG_PATH = './CONFLICT_CONVO_LABELING_LOG.csv'
if(not os.path.isfile(CONVERSATION_LABELING_LOG_PATH)):
	# define a simple CSV with just the headers
	log_setup = pd.DataFrame(columns = ["CONV_ID", "id", "rating_directness_content", "rating_directness_expression", "rating_OI_content", "rating_OI_expression", "rater_id", "status", "last_updated_time"])
	log_setup.to_csv(CONVERSATION_LABELING_LOG_PATH, index=False)

LABEL_LOG = pd.read_csv(CONVERSATION_LABELING_LOG_PATH)

# Constants for where directness and oppositional intensity are rated
DIRECTNESS_CONTENT_COL = "E"
DIRECTNESS_EXPRESSION_COL = "F"
OI_CONTENT_COL = "G"
OI_EXPRESSION_COL = "H"

# Define a constant, but random, ordering for the conversations
random.seed(19104)
CONVERSATION_IDS = list(set(CONVERSATIONS["CONV_ID"]))
CONVERSATION_IDS.sort()
random.shuffle(CONVERSATION_IDS)

"""
function: update_log_allocated

Update the rating log to indicate that a new conversation has been allocated.
"""
def update_log_allocated(sample_to_label, rater_id):
	static_data = {
		"rating_directness_content": pd.Series(['-']).repeat(len(sample_to_label)),
		"rating_directness_expression": pd.Series(['-']).repeat(len(sample_to_label)),
		"rating_OI_content": pd.Series(['-']).repeat(len(sample_to_label)),
		"rating_OI_expression": pd.Series(['-']).repeat(len(sample_to_label)),
		"rater_id": pd.Series([rater_id]).repeat(len(sample_to_label)),
		"status": pd.Series(['allocated']).repeat(len(sample_to_label)),
		"last_updated_time": pd.Series([pd.Timestamp.now()]).repeat(len(sample_to_label))
	}
	sample_to_label_reset = sample_to_label[["CONV_ID", "id"]].reset_index(drop=True)
	static_data_reset = pd.DataFrame(static_data).reset_index(drop=True)
	new_data = pd.concat([sample_to_label_reset, static_data_reset], axis=1)
	# Append the new data to the existing DataFrame
	log_setup = pd.read_csv(CONVERSATION_LABELING_LOG_PATH)
	updated_data = new_data.copy() if log_setup.empty else pd.concat([log_setup, new_data], ignore_index=True)
	updated_data.to_csv(CONVERSATION_LABELING_LOG_PATH, index=False)

	# also update LABEL_LOG
	LABEL_LOG = updated_data

def next_available_row(worksheet):
	# Modified from: https://stackoverflow.com/questions/40781295/how-to-find-the-first-empty-row-of-a-google-spread-sheet-using-python-gspread
	str_list = list(filter(None, worksheet.col_values(1)))
	return len(str_list)+2

"""
function: write_sample_to_sheet

Given a sample to label, write it to the Google Sheet specific to the user in question.
"""
def write_sample_to_sheet(sample_to_label, rater_id):
	rater_sheet = RATING_DICTIONARY[rater_id]
	sh = gc.open_by_url(rater_sheet).sheet1

	available_row = next_available_row(sh) # Figure out the next open line
	update_range_CONV_ID = sh.range("A{}:A{}".format(available_row, available_row + len(sample_to_label)))
	update_range_id = sh.range("B{}:B{}".format(available_row, available_row + len(sample_to_label)))
	update_range_speaker = sh.range("C{}:C{}".format(available_row, available_row + len(sample_to_label)))
	update_range_text = sh.range("D{}:D{}".format(available_row, available_row + len(sample_to_label)))
	
	# Convert values to strings if needed
	CONV_IDS_to_udpate = [str(value) for value in list(sample_to_label["CONV_ID"])]
	ids_to_udpate = [str(value) for value in list(sample_to_label["id"])]
	speakers_to_udpate = [str(value) for value in list(sample_to_label["speaker"])]
	text_values_to_update = [str(value) for value in list(sample_to_label["text"])]

	# Update the values in the range
	for i in range(len(sample_to_label)):
		update_range_CONV_ID[i].value = CONV_IDS_to_udpate[i]
		update_range_id[i].value = ids_to_udpate[i]
		update_range_speaker[i].value = speakers_to_udpate[i]
		update_range_text[i].value = text_values_to_update[i]

	# Batch update the range
	sh.update_cells(update_range_CONV_ID)
	sh.update_cells(update_range_id)
	sh.update_cells(update_range_speaker)
	sh.update_cells(update_range_text)
	
	# Update the formatting for the next columns
	validation_rule_directness_content = DataValidationRule(
	BooleanCondition('ONE_OF_LIST', ["Yes - Direct Content", "Neutral - Content contains no opinion", "No - Indirect Content"]),
		showCustomUi=True
	)
	set_data_validation_for_cell_range(sh, DIRECTNESS_CONTENT_COL + str(available_row) + ":" + DIRECTNESS_CONTENT_COL + str(available_row + len(sample_to_label)), validation_rule_directness_content)

	validation_rule_directness_expression = DataValidationRule(
	BooleanCondition('ONE_OF_LIST', ["Yes - Direct Expression", "No - Indirect Expression"]),
		showCustomUi=True
	)
	set_data_validation_for_cell_range(sh, DIRECTNESS_EXPRESSION_COL + str(available_row) + ":" + DIRECTNESS_EXPRESSION_COL + str(available_row + len(sample_to_label)), validation_rule_directness_expression)

	validation_rule_OI_content = DataValidationRule(
	BooleanCondition('ONE_OF_LIST', ["Yes - Content opposes someone else", "No - Content does not oppose anyone"]),
		showCustomUi=True
	)
	set_data_validation_for_cell_range(sh, OI_CONTENT_COL + str(available_row) + ":" + OI_CONTENT_COL + str(available_row + len(sample_to_label)), validation_rule_OI_content)

	validation_rule_OI_expression = DataValidationRule(
	BooleanCondition('ONE_OF_LIST', ["Yes - Expression is emotional/forceful", "No - Expression is not emotional/forceful"]),
		showCustomUi=True
	)
	set_data_validation_for_cell_range(sh, OI_EXPRESSION_COL + str(available_row) + ":" + OI_EXPRESSION_COL + str(available_row + len(sample_to_label)), validation_rule_OI_expression)



def get_n_convos_to_rate(conversations_for_rater, n_convos, rater_id):
	# Identify conversations that have already been labeled
	already_labeled_ids = set(conversations_for_rater["CONV_ID"])
	df_to_label = [conversation_id for conversation_id in CONVERSATION_IDS if conversation_id not in already_labeled_ids]
	n_convo_ids = df_to_label[:n_convos]
	sample_to_label = CONVERSATIONS[CONVERSATIONS["CONV_ID"].isin(n_convo_ids)]

	return(sample_to_label)

"""
function: schedule

Allocates n_convos to the spreadsheet of rater_id.
"""
def schedule(rater_id, n_convos):
	# check whether user has any allocated but incomplete conversations
	conversations_for_rater = LABEL_LOG[LABEL_LOG["rater_id"]==rater_id]
	if(conversations_for_rater[conversations_for_rater["status"]=="allocated"].empty):
		new_conversations = get_n_convos_to_rate(conversations_for_rater, n_convos, rater_id)
		write_sample_to_sheet(new_conversations, rater_id)
		update_log_allocated(new_conversations, rater_id)
		print("Updated rating sheet for " + str(rater_id) + " with " + str(n_convos) + " new conversations!")
	else:
		print("Rating sheet for " + str(rater_id) + " contains unlabeled conversations. Please either complete ratings or update the log.")		


"""
function: update

Checks the cells pertaining to a user (rater_id) for their updated status and push changes to the log.
"""
def update(rater_id):

	# filter for id's that were allocated to the user
	conversations_for_rater = LABEL_LOG[LABEL_LOG["rater_id"]==rater_id]

	# additional filter for ONLY searching conversations that were previously not marked 'done'
	# this can help speed things up a bit in terms of not searching through the entire history
	# conversations_for_rater = LABEL_LOG[LABEL_LOG["status"]!="done"]

	message_ids = list(conversations_for_rater["id"])

	# check for id's in the spreadsheet
	rater_sheet = RATING_DICTIONARY[rater_id]
	sh = gc.open_by_url(rater_sheet).sheet1

	for i, id_num in enumerate(message_ids):
		cell = sh.find(id_num)
		directness_content_cell = DIRECTNESS_CONTENT_COL + str(cell.row)
		directness_expression_cell = DIRECTNESS_EXPRESSION_COL + str(cell.row)
		oi_content_cell = OI_CONTENT_COL + str(cell.row)
		oi_expression_cell = OI_EXPRESSION_COL + str(cell.row)

		rating_directness_content = sh.acell(directness_content_cell).value
		rating_directness_expression = sh.acell(directness_expression_cell).value
		rating_OI_content = sh.acell(oi_content_cell).value
		rating_OI_expression = sh.acell(oi_expression_cell).value
		# check whether they were rated or not
		if(rating_directness_content is not None):
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'rating_directness_content'] = rating_directness_content
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'last_updated_time'] = pd.Timestamp.now()
		if(rating_directness_expression is not None):
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'rating_directness_expression'] = rating_directness_expression
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'last_updated_time'] = pd.Timestamp.now()
		if(rating_OI_content is not None):
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'rating_OI_content'] = rating_OI_content
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'last_updated_time'] = pd.Timestamp.now()
		if (rating_OI_expression is not None):
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'rating_OI_expression'] = rating_OI_expression
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'last_updated_time'] = pd.Timestamp.now()
		# if ratings are complete, mark status as "done"
		if(rating_directness_content is not None and rating_directness_expression is not None and rating_OI_content is not None and rating_OI_expression is not None):
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'status'] = "done"
			LABEL_LOG.loc[LABEL_LOG['id'] == id_num, 'last_updated_time'] = pd.Timestamp.now()

		if(i > 0 and i % 10 == 0):
			print(str(i) + " requests completed...")
			if(i%20 == 0):
				time.sleep(10) # sleeping due to API quota limits (for now)

	# update LABEL_LOG
	LABEL_LOG.to_csv(CONVERSATION_LABELING_LOG_PATH, index=False)

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='This is the scheduler that manages the data annotation system for the conflict portion of the Team Process Mapping project.')
	
	# Using nargs to indicate that --schedule should take two arguments
	parser.add_argument('--schedule', nargs=2, help='Add n_convos for rating to the spreadsheet belonging to rater_id. You need to pass in 2 arguments, rater_id and n_convos (in that order).')
	parser.add_argument('--update', nargs=1, help='Update the spreadsheet belonging to rater_id. You need to pass in 1 arguments, rater_id.')
	
	args = parser.parse_args()

	# Check if --schedule is provided
	if args.schedule:
		rater_id, n_convos = args.schedule
		schedule(rater_id, int(n_convos))
	elif args.update:
		rater_id = args.update[0]
		update(rater_id)
	else:
		print("No arguments provided. Usage: --schedule rater_id n_convos OR --update rater_id")
