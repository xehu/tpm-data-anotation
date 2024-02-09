# tpm-data-anotation
This is a repository that uses gspread (https://docs.gspread.org/en/latest/) to manage the Google Sheets-based data annotation for the Team Process Mapping project.

### Setting up authentication for `gspread` using a service account
A service account is a special type of Google account intended to represent a non-human user that needs to authenticate and be authorized to access data in Google APIs [sic].

Since it’s a separate account, by default it does not have access to any spreadsheet until you share it with this account. Just like any other Google account.

Here’s how to get one:

Enable API Access for a Project if you haven’t done it yet.
Go to “APIs & Services > Credentials” and choose “Create credentials > Service account key”.
Fill out the form
Click “Create” and “Done”.
Press “Manage service accounts” above Service Accounts.
Press on ⋮ near recently created service account and select “Manage keys” and then click on “ADD KEY > Create new key”.
Select JSON key type and press “Create”.
You will automatically download a JSON file with credentials. It may look like this:

```
{
    "type": "service_account",
    "project_id": "api-project-XXX",
    "private_key_id": "2cd … ba4",
    "private_key": "-----BEGIN PRIVATE KEY-----\nNrDyLw … jINQh/9\n-----END PRIVATE KEY-----\n",
    "client_email": "473000000000-yoursisdifferent@developer.gserviceaccount.com",
    "client_id": "473 … hd.apps.googleusercontent.com",
    ...
}
```

Remember the path to the downloaded credentials file. (NOTE: in the case of TPM, we gitignore it, so it's not pushed to git! Contact Emily for details on this key). Also, in the next step you’ll need the value of client_email from this file.

## The Conflict Rating Scheduler
One tool implemented in this repository is an automated process for allocating conversations to be rated for directness and oppositional intensity (as part of the conflict project). The process for rating the conflict conversations works as follows:

### Step 1: Random Selection of Conversations 
[The ConvoKit Data Downloader Notebook](https://github.com/xehu/tpm-data-anotation/blob/main/conflict_reddit_data/convokit_data_downloader.ipynb) downloads a random sample of 100 conversations into the [samples](https://github.com/xehu/tpm-data-anotation/tree/main/conflict_reddit_data/samples) folder.

### Step 2: Using the Scheduler
The role of the scheduler is to manage the process by which the sample of conversations is distributed to RA's for rating. It assigns raters samples of conversations and pushes them to a personal spreadsheet link. Once raters do their ratings (in their own spreadsheet links), it checks each link for the ratings and updates a central log, which tracks the progress of ratings.
- Within the scheduler, each rater/user is associated with a rater ID and a spreadsheet link. This spreadsheet will be the location to which the scheduler pushes updates / new conversations for rating.
- Upon calling the `schedule()` function, the scheduler checks whether a rater has any incomplete assignments. If the rater has previously been allocated work and has not finished it, it does not assign any new conversations to rate. If all previous assignments have been completed, the scheduler assigns the rater the first `n` conversations that they have not yet seen (`n` is specified by the person calling the function).
- By calling the `update` function for a specific user, the scheduler checks the spreadsheet for a particular rater and updates the central log.

#### The Central Rating Log
The conversation labeling log is a file called `CONFLICT_CONVO_LABELING_LOG.csv`. It stores all of the samples that we have allocated to users, as well as the latest ratings.

Here's what each column in the conversation log should contain:
- `CONV_ID`: the id associated with the conversation
- `id`: the id associated with each message/chat
- `rating_directness`: the rating for directness assigned by the rater
- `rating_OI`: the rating for directness assigned by the rater
- `rater_id`: the userid of the rater
- `status`: {allocated, done}
- `last_updated_time`: time associated with the last update / check to this log item

If it does not yet exist, upon the first run of the program, a blank version of the rating log will be created.

#### Dictionary for Storing Personal Spreadsheets
Each user ID needs to be associated with a specific Google Sheets link, where new conversations will be posted for them to rate. This is done here:

```
RATING_DICTIONARY = {
	"xehu": "https://docs.google.com/spreadsheets/d/1W4zLWTRaT6UIgb1WvTa8_Ca92O1Nqzqgl80it6l5miU/edit#gid=2046213595"
}
```
#### Scheduling
The syntax for scheduling a number of conversations for a rater is as follows:
```
python3 conflict_rating_scheduler.py --schedule [rater_id] [num_convs]
```
When this is called, `[num_convs]` new conversations will be added to the next available lines in the user's personal spreadsheet, alongside drop-downs for rating:

<img width="1192" alt="Screenshot 2024-01-16 at 10 53 07 PM" src="https://github.com/xehu/tpm-data-anotation/assets/28793641/8e257e1a-3167-424b-a759-0de92d012b7d">

Additionally, the relevant ID's will be added to the log, which tracks when and to whom the messages were assigned.

<img width="604" alt="Screenshot 2024-01-16 at 10 54 21 PM" src="https://github.com/xehu/tpm-data-anotation/assets/28793641/eb980206-fad6-4607-8fd3-776c2510ee64">

If the user tries to call the scheduler multiple times without finishing their existing allocation, they get an error message:
```
Rating sheet for xehu contains unlabeled conversations. Please either complete ratings or update the log.
```

#### Updating the Log / Checking Ratings
The syntax for updating the log and checking a rater's rating spreadsheet is as follows:
```
python3 conflict_rating_scheduler.py --update [rater_id]
```
This will check each message ID for whether it is rated or not, and update the central log accordingly:

<img width="620" alt="Screenshot 2024-01-16 at 10 57 18 PM" src="https://github.com/xehu/tpm-data-anotation/assets/28793641/b94b56c7-035c-4714-b604-bf1cc00e8bc5">

Note that, since each message ID is rated one by one, it needs to be checked one by one. Due to API usage limits, this process is a bit slow for now.

## An automated process for inter-rater reliability
Another tool built into this repository is the ability to calculate inter-rater reliability across multiple duplicate copies of a spreadsheet. That is, if rater are using spreadsheets with identical set-ups, the tool can check whether raters have put the same rating in the same corresponding cell --- and quantify their level of agreement.

### IRR / Agreement for Live Ratings
The file [`irr_conflict.py`](https://github.com/xehu/tpm-data-anotation/blob/main/irr_conflict.py) is designed to read from the individual spreadsheets of each rater and help track inter-rater reliability

The default behavior occurs when you run the script with no arguments:
```
python3 irr_conflict.py
```
This will print the proportion of agreement across all of the rating metrics:
```
{'Directness_content': 0.9555555555555556, 'Directness_expression': 0.9111111111111112, 'OI_content': 0.8666666666666668, 'OI_expression': 0.8666666666666667}
```
By running the script with the `--check` argument, you can specifically check for IRR on one of the 4 metrics:
```
python3 irr_conflict.py --check [ARGUMENT]
```
You need to pass in one of `directness_content`, `directness_expression`, `OI_content`, or `OI_expression` as the ARGUMENT.

This will print out the specific IRR for that metric, and also save a CSV under the `disagreed_messages/` folder that identifies which messages people disagreed on. This will make it easier to streamline discussions and surface misunderstandings.

### IRR for the Conversation Pre-Test
[The `irr_for_multi_conversation_pretest` script](https://github.com/xehu/tpm-data-anotation/blob/main/irr_for_multi_conversation_pretest.py) is designed to calculate the Fleiss's Kappa inter-rater reliability metric for RA candidates completing the three-conversation rating task. The logic/code from this file can be easily adapted to other rating contexts, assuming that each rater has a duplicate of the same spreadsheet (that is, the scheduler assigns spreadsheets consistently to all raters).
