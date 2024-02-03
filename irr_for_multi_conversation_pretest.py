import gspread
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.inter_rater import fleiss_kappa, aggregate_raters
import numpy as np
import pprint
import time
import json

# Authenticate with Google Sheets
gc = gspread.service_account(filename='./tpm-data-annotation-aae74b403ab4.json')

# NOTE: email is: tpm-data-annotation@tpm-data-annotation.iam.gserviceaccount.com
# Everything needs to be shared with this email address!

"""
function: get_ratings_for_range()

@param cell_range: The range of cells for which we want to get the
ratings across all the spreadsheets
"""
def get_ratings_for_range(cell_ranges, sheet_indices, list_of_spreadsheet_links):
	# There should be 1 cell range specified per sheet!
	assert(len(cell_ranges) == len(sheet_indices))

	ratings = []
	
	for spreadsheet in list_of_spreadsheet_links:

		# These are the different conversations; each one has a sheet index
		conversations = []
		for index in sheet_indices:
			conversations.append(gc.open_by_url(spreadsheet).get_worksheet(index))

		values = []
		
		for i in range(len(conversations)): # 1 sheet for each conversation
			# Get value for all conversations
			values.append(conversations[i].range(cell_ranges[i]))

		# Unnest the lists --- each sheet's value is its own sublist
		values = [item for sublist in values for item in sublist]
		ratings.append([value.value for value in values])
		
	return(ratings)

"""
function: convert_ratings_to_int
Convert the ratings (Agree/Neutral/Disagree) to ints.

@param ratings: the ratings to convert
"""
def convert_ratings_to_int(ratings):
    conversion_dict = {'Agree': 0, 'Neutral': 1, 'Disagree': 2, '': 1}
    # Note: we are going to treat blank labels as 'Neutral'
    converted_ratings = [[conversion_dict[item] for item in sublist] for sublist in ratings]

    return converted_ratings

"""
function: convert_ratings_to_fleiss_category_counts

Take the ratings and convert them in a format for applying fleiss' kappa
(category counts).

@param ratings: a list of lists of ratings.
"""
def convert_ratings_to_fleiss_category_counts(ratings):
	directness_ratings_transposed = np.array(ratings).T.tolist()
	directness_ratings_converted = convert_ratings_to_int(directness_ratings_transposed)
	directness_ratings_catcounts = aggregate_raters(directness_ratings_converted, n_cat=3)[0]

	return directness_ratings_catcounts

if __name__ == "__main__":

	# Specify rating cells for the difference conversations
	conv_1 = {
		"directness" : "B3:B10",
		"OI" : "C3:C10"
	}
	conv_2 = {
		"directness" : "B3:B7",
		"OI" : "C3:C7"
	}
	conv_3 = {
		"directness" : "B3:B7",
		"OI" : "C3:C7"
	}

	# Get data from sheets
	EMILY_PRIYA_DICT = {
		"emily": "https://docs.google.com/spreadsheets/d/1-Q6i75z86t7zFAGM_YCJxlMNLgQ9rU1dqPV7IM3gQHQ/edit#gid=2046213595",
		"priya": "https://docs.google.com/spreadsheets/d/13Gcg-HCyptuEp0uNIfxPb61MoE62MNBRE9UmfLbV3tU/edit#gid=0"
	}
	
	SUBMISSION_DICT = {
	"helena": "https://docs.google.com/spreadsheets/d/1VFZWHfCTMVzKBv8IjUAbTbaZ32udjCgdRTmVXIiH5lI/edit#gid=2046213595",
	"amy": "https://docs.google.com/spreadsheets/d/1DoUBDuAyuaGuZ35OoJK6gD_TFv7ZhFF-D1z4he3MYTE/edit#gid=0",
	}

	RESULTS_DICT = {
	"helena": {},
	"amy": {},
	}

	# first get the baseline; agreement between emily and priya
	emily_priya_directness = get_ratings_for_range([conv_1["directness"], conv_2["directness"], conv_3["directness"]], [0, 1, 2], EMILY_PRIYA_DICT.values())
	emily_priya_directness_fk = fleiss_kappa(convert_ratings_to_fleiss_category_counts(emily_priya_directness))

	emily_priya_OI = get_ratings_for_range([conv_1["OI"], conv_2["OI"], conv_3["OI"]], [0, 1, 2], EMILY_PRIYA_DICT.values())
	emily_priya_OI_fk = fleiss_kappa(convert_ratings_to_fleiss_category_counts(emily_priya_OI))

	# Get IRR for ratings (Fleiss' Kappa)
	print("Emily and Priya's Agreement: Fleiss' Kappa for Directness")
	print(emily_priya_directness_fk)
	print("Emily and Priya's Agreement; Fleiss' Kappa for Oppositional Intensity")
	print(emily_priya_OI_fk)


	# for each candidate...
	for student in SUBMISSION_DICT.keys():
		student_sheet = SUBMISSION_DICT[student]

		# compare to Emily
		student_and_emily = [student_sheet, EMILY_PRIYA_DICT["emily"]]
		emily_student_directness = get_ratings_for_range([conv_1["directness"], conv_2["directness"], conv_3["directness"]], [0, 1, 2], student_and_emily)
		emily_student_directness_fk = fleiss_kappa(convert_ratings_to_fleiss_category_counts(emily_student_directness))

		emily_student_OI = get_ratings_for_range([conv_1["OI"], conv_2["OI"], conv_3["OI"]], [0, 1, 2], student_and_emily)
		emily_student_OI_fk = fleiss_kappa( convert_ratings_to_fleiss_category_counts(emily_student_OI))

		# compare to Priya
		student_and_priya = [student_sheet, EMILY_PRIYA_DICT["emily"]]

		student_priya_directness = get_ratings_for_range([conv_1["directness"], conv_2["directness"], conv_3["directness"]], [0, 1, 2], student_and_priya)
		student_priya_directness_fk = fleiss_kappa(convert_ratings_to_fleiss_category_counts(student_priya_directness))

		student_priya_OI = get_ratings_for_range([conv_1["OI"], conv_2["OI"], conv_3["OI"]], [0, 1, 2], student_and_priya)
		student_priya_OI_fk = fleiss_kappa( convert_ratings_to_fleiss_category_counts(student_priya_OI))

		# take the max
		directness_fk = max(emily_student_directness_fk, student_priya_directness_fk)
		OI_fk = max(emily_student_OI_fk, student_priya_OI_fk)

		RESULTS_DICT[student]["Directness"] = directness_fk
		RESULTS_DICT[student]["OI"] = OI_fk

		print("Results for student: " + student)
		print("Directness:")
		print(directness_fk)
		print("Oppositional Intensity:")
		print(OI_fk)
		time.sleep(5)

	print("Results for Students...")
	pprint.pprint(RESULTS_DICT)