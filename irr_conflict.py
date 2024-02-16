import gspread
from sklearn.metrics import cohen_kappa_score
from agreement.metrics import cohens_kappa, krippendorffs_alpha, observed_agreement
# see documentation @: https://github.com/heolin/agreement/blob/master/src/agreement/metrics.py
from agreement.utils.transform import pivot_table_frequency
import pandas as pd
import numpy as np
import pprint
import time
import json
from rating_dictionary import RATING_DICTIONARY
import argparse
# remove emily's test instance from the dictioary
RATING_DICTIONARY.pop("xehu")

# Authenticate with Google Sheets
gc = gspread.service_account(filename='./tpm-data-annotation-aae74b403ab4.json')

# NOTE: email is: tpm-data-annotation@tpm-data-annotation.iam.gserviceaccount.com
# Everything needs to be shared with this email address!

"""
function: get_ratings_for_range()

@param cell_range: The range of cells for which we want to get the
ratings across all the spreadsheets
"""
def get_ratings_for_range(cell_range, list_of_spreadsheet_links):
	ratings = []
	
	for spreadsheet in list_of_spreadsheet_links:
		values = gc.open_by_url(spreadsheet).sheet1.range(cell_range)
		values = [value.value for value in values]
		ratings.append(values)	

	return(ratings)

"""
function: convert_ratings_to_int
Convert the ratings (Agree/Neutral/Disagree) to ints.

@param ratings: the ratings to convert
@param conversion_dict: the dictionary for converting answers
"""
def convert_ratings_to_int(ratings, conversion_dict):
	# Note: we are going to treat blank labels as 'Neutral'
	return [[conversion_dict[item] for item in sublist] for sublist in ratings]

"""
function: convert_ratings_to_question_rater_answer

Converts the ratings to a matrix of [question, rater, answer
"""
def convert_ratings_to_question_rater_answer(ratings, conversion_dict):
	ratings = convert_ratings_to_int(ratings, conversion_dict)
	num_questions = len(ratings[0])
	transformed_data = []
	for question_id in range(1, num_questions + 1):
		for rater_id, response in enumerate(ratings):
			transformed_data.append([question_id, rater_id + 1, response[question_id - 1]])
	dataset = np.array(transformed_data)
	return dataset


def next_available_row(worksheet, colnum=8):
	# Modified from: https://stackoverflow.com/questions/40781295/how-to-find-the-first-empty-row-of-a-google-spread-sheet-using-python-gspread
	str_list = list(filter(None, worksheet.col_values(colnum)))
	return len(str_list)+2


def get_disagreed_messages(questions_answers_table):
	disagreed_indices = np.where(np.all(questions_answers_table != 3, axis=1))[0]

	print(disagreed_indices)

	disagreed_messages = {} # Format -- {id: text}
	for index in disagreed_indices:
		sh = gc.open_by_url(list(RATING_DICTIONARY.values())[0]).sheet1 # open just the first sheet
		ID_COL = "B"
		TEXT_COL = "D"

		disag_id = sh.acell(ID_COL + str(index + 2)).value  # + 2 because there are 2 header rows
		disag_text = sh.acell(TEXT_COL + str(index + 2)).value

		disagreed_messages[disag_id] = disag_text
	
	disagreed_messages_df = pd.DataFrame(list(disagreed_messages.items()), columns=['id', 'text'])
	return(disagreed_messages_df)

if __name__ == "__main__":

	# Constants for where directness and oppositional intensity are rated
	DIRECTNESS_CONTENT_COL = "E"
	DIRECTNESS_EXPRESSION_COL = "F"
	OI_CONTENT_COL = "G"
	OI_EXPRESSION_COL = "H"

	# Conversion dicts for different questions
	conversion_directness_content = {'Yes - Direct Content': 2, 'Neutral - Content contains no opinion': 0, 'No - Indirect Content': 1, '': 0}
	conversion_directness_expression = {'Yes - Direct Expression': 2, 'No - Indirect Expression': 1, '': 0}
	conversion_OI_content = {'Yes - Content opposes someone else': 2, 'No - Content does not oppose anyone': 1, '': 0}
	conversion_OI_expression = {'Yes - Expression is emotional/forceful': 2, 'No - Expression is not emotional/forceful': 1, '': 0}


	parser = argparse.ArgumentParser(description='This script checks inter-rater reliability for the conflict portion of the Team Process Mapping project.')
	parser.add_argument('--check', nargs=1, help='Check the specific IRR for a single one of the metrics. You need to pass in 1 argument for which of the 4: directness_content, directness_expression, OI_content, or OI_expression.')
	args = parser.parse_args()

	# Get the end of where we should be checking for IRR
	avail_rows = []

	for rater_sheet in RATING_DICTIONARY.values():
		sh = gc.open_by_url(rater_sheet).sheet1
		# get where the labels end
		next_row = next_available_row(sh) # Figure out the next open line
		avail_rows.append(next_row)

	# This is the end of where we should be checking for IRR
	last_rated_row = min(avail_rows)-1

	if(last_rated_row) < 3:
		print("Not enough ratings!")

	else:
		if args.check:
			metric_to_check = args.check[0]

			if metric_to_check == "directness_content":
				COL = DIRECTNESS_CONTENT_COL
				conversion_dict = conversion_directness_content
			elif metric_to_check == "directness_expression":
				COL = DIRECTNESS_EXPRESSION_COL
				conversion_dict = conversion_directness_expression
			elif metric_to_check == "OI_content":
				COL = OI_CONTENT_COL
				conversion_dict = conversion_OI_content
			elif metric_to_check == "OI_expression":
				COL = OI_EXPRESSION_COL
				conversion_dict = conversion_OI_expression
			else:
				raise ValueError('Please provide one of the following 4 metric names: directness_content, directness_expression, OI_content, or OI_expression.')

			# get the range for which we are checking irr
			content = COL+"3:" + COL+str(last_rated_row)
			content_ratings = get_ratings_for_range(content, RATING_DICTIONARY.values())
			datatable = convert_ratings_to_question_rater_answer(content_ratings, conversion_dict)
		
			questions_answers_table = pivot_table_frequency(datatable[:, 0], datatable[:, 2])

			print("Agreement for " + metric_to_check + ": " + str(observed_agreement(questions_answers_table)))
			get_disagreed_messages(questions_answers_table).to_csv('./disagreed_messages/' + metric_to_check + '.csv')

		else: # Default IRR check	
			# Agreement
			AGREEMENT = {}

			# Specify where we should be checking IRR
			directness_content = DIRECTNESS_CONTENT_COL+"3:" + DIRECTNESS_CONTENT_COL+str(last_rated_row)
			directness_expression = DIRECTNESS_EXPRESSION_COL+"3:" + DIRECTNESS_EXPRESSION_COL+ str(last_rated_row)
			OI_content = OI_CONTENT_COL+"3:" + OI_CONTENT_COL+str(last_rated_row)
			OI_expression = OI_EXPRESSION_COL+"3:" + OI_EXPRESSION_COL+str(last_rated_row)

			# Directness
			directness_content_ratings = get_ratings_for_range(directness_content, RATING_DICTIONARY.values())
			dc_datatable = convert_ratings_to_question_rater_answer(directness_content_ratings, conversion_directness_content)
			dc_questions_answers_table = pivot_table_frequency(dc_datatable[:, 0], dc_datatable[:, 2])
			AGREEMENT["Directness_content"] = observed_agreement(dc_questions_answers_table)
			
			directness_expression_ratings = get_ratings_for_range(directness_expression, RATING_DICTIONARY.values())
			de_datatable = convert_ratings_to_question_rater_answer(directness_expression_ratings, conversion_directness_expression)
			de_questions_answers_table = pivot_table_frequency(de_datatable[:, 0], de_datatable[:, 2])
			AGREEMENT["Directness_expression"] = observed_agreement(de_questions_answers_table)

			# Oppositional Intensity
			OI_content_ratings = get_ratings_for_range(OI_content, RATING_DICTIONARY.values())
			OIc_datatable = convert_ratings_to_question_rater_answer(OI_content_ratings, conversion_OI_content)
			OIc_questions_answers_table = pivot_table_frequency(OIc_datatable[:, 0], OIc_datatable[:, 2])
			AGREEMENT["OI_content"] = observed_agreement(OIc_questions_answers_table)
			
			OI_expression_ratings = get_ratings_for_range(OI_expression, RATING_DICTIONARY.values())
			OIe_datatable = convert_ratings_to_question_rater_answer(OI_expression_ratings, conversion_OI_expression)
			OIe_questions_answers_table = pivot_table_frequency(OIe_datatable[:, 0], OIe_datatable[:, 2])
			AGREEMENT["OI_expression"] = observed_agreement(OIe_questions_answers_table)

			print(AGREEMENT)