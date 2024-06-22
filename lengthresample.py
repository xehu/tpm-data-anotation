import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
import os

# Function to read and filter data from CSV
def read_csv(csv_file_path):
    # Read CSV file into DataFrame
    df = pd.read_csv(csv_file_path)

    # Separate data into 'winning' and 'awry' categories based on 'dataset_numeric' column
    winning_data = df[df['dataset_numeric'] == 1]
    awry_data = df[df['dataset_numeric'] == 0]

    return winning_data, awry_data

# Function to resample data to balance counts
def resample_data(winning_data, awry_data):
    # Count occurrences of each unique value in both datasets
    winning_counts = winning_data.value_counts()
    awry_counts = awry_data.value_counts()

    # Identify all unique values across both datasets
    unique_values = set(winning_counts.index).union(set(awry_counts.index))

    # Determine minimum counts to balance datasets
    new_counts = {val: min(winning_counts.get(val, 0), awry_counts.get(val, 0)) for val in unique_values}

    # Resample data based on the determined counts
    new_winning = pd.concat([winning_data[winning_data == key].sample(n=value) for key, value in new_counts.items()])
    new_awry = pd.concat([awry_data[awry_data == key].sample(n=value) for key, value in new_counts.items()])

    # Create 'output' directory if it does not exist
    os.makedirs("./output", exist_ok=True)

    # Save resampled data to CSV
    new_winning.to_csv('./output/Dataset_conversation_length_resampled.csv', index=False)

    return new_winning, new_awry

# Function to describe dataset and save descriptive statistics
def describe_data(df, dataset_type=""):
    # Create a copy of the dataset to avoid modifying the original data
    df_copy = df.copy()

    # Rename columns based on the dataset type
    df_copy.columns = [f"{1 if dataset_type == 'Winning' else 0}_{dataset_type}_{col}" for col in df_copy.columns]

    # Generate descriptive statistics and save to CSV
    describe_df = df_copy.describe().T
    describe_df.to_csv(f'./output/Dataset_{1 if dataset_type == "Winning" else 0}_{dataset_type}_describe.csv', sep=',')

# Function to draw KDE plot for resampled data
def draw_image(new_winning, new_awry, feature="conversation_length"):
    # Describe resampled data and save descriptive statistics
    describe_data(pd.DataFrame({'Dataset_1_Winning': new_winning, 'Dataset_0_Awry': new_awry}), dataset_type="Resampled")

    # Save KDE plot to a PDF
    with PdfPages(f'./output/{feature}.pdf') as pdf:
        sns.kdeplot(new_winning, color='red', shade=True, label='Dataset_1_Winning')
        sns.kdeplot(new_awry, color='black', shade=True, label='Dataset_0_Awry')
        plt.legend()
        pdf.savefig()
        plt.close()

if __name__ == "__main__":
    # Path to the CSV file containing the dataset
    csv_file_path = "tpm_with_xgboost_noreg_reduced_dim.csv"

    # Read and filter dataset into 'winning' and 'awry' subsets
    winning_data, awry_data = read_csv(csv_file_path)

    # Specify the feature for analysis
    feature = "conversation_length"

    # Resample data for the specified feature
    new_winning, new_awry = resample_data(winning_data[feature], awry_data[feature])

    # Draw KDE plot to visualize the resampled data distribution
    draw_image(new_winning, new_awry, feature=feature)
