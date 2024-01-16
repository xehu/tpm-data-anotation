import gspread
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.inter_rater import fleiss_kappa, aggregate_raters
import numpy as np

# Authenticate with Google Sheets
# Note that authentication is saved locally, at ~/.config/gspread/credentials.json
gc = gspread.oauth()

"""
function: get_ratings_for_range()

@param cell_range: The range of cells for which we want to get the
ratings across all the spreadsheets
"""
def get_ratings_for_range(cell_ranges, sheet_indices):
	# There should be 1 cell range specified per sheet!
	assert(len(cell_ranges) == len(sheet_indices))

	ratings = []
	
	for spreadsheet in list_of_spreadsheets:

		# These are the different conversations; each one has a sheet index
		conversations = []
		for index in sheet_indices:
			conversations.append(gc.open(spreadsheet).get_worksheet(index))

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
    conversion_dict = {'Agree': 0, 'Neutral': 1, 'Disagree': 2}
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
	list_of_spreadsheets = ["Emily's copy of Data Labeling Task January 2024", "Copy of Emily's copy of Data Labeling Task January 2024"]

	# get directness and OI ratings
	directness_ratings = get_ratings_for_range([conv_1["directness"], conv_2["directness"], conv_3["directness"]], [0, 1, 2])
	directness_fleiss_cc = convert_ratings_to_fleiss_category_counts(directness_ratings)

	OI_ratings = get_ratings_for_range([conv_1["OI"], conv_2["OI"], conv_3["OI"]], [0, 1, 2])
	OI_ratings_fleiss_cc = convert_ratings_to_fleiss_category_counts(OI_ratings)

	# Get IRR for ratings (Fleiss' Kappa)
	print("Fleiss' Kappa for Directness")
	print(fleiss_kappa(directness_fleiss_cc))
	print("Fleiss' Kappa for Oppositional Intensity")
	print(fleiss_kappa(OI_ratings_fleiss_cc))