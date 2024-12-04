# TODO: Up row limit on results = && change the naming for application_in?
# TODO: generate requirements.txt

import pandas as pd
from sodapy import Socrata

# Unauthenticated client only works with public data sets. Note 'None'
# in place of application token, and no username or password:
client = Socrata("data.pa.gov", None)

# First 1000 results, returned as JSON from API / converted to Python list of
# dictionaries by sodapy.
results = client.get("mcba-yywm", limit=1000)

# Convert to pandas DataFrame
application_in = pd.DataFrame.from_records(results)

# Force invalid timestamps to null values - Only had problems with appissuedate, doing the others to be safe
application_in['appissuedate'] = pd.to_datetime(application_in['appissuedate'], errors = 'coerce')
application_in['appreturndate'] = pd.to_datetime(application_in['appreturndate'], errors = 'coerce')
application_in['ballotsentdate'] = pd.to_datetime(application_in['ballotsentdate'], errors = 'coerce')
application_in['ballotreturneddate'] = pd.to_datetime(application_in['ballotreturneddate'], errors = 'coerce')
application_in['dateofbirth'] = pd.to_datetime(application_in['dateofbirth'], errors = 'coerce')


# Grab rows with any null data & store, then drop rows from application_in
invalid_data = application_in[application_in.isna().any(axis=1)]
application_in.dropna(inplace=True)

# Convert senate data to snake case
application_in['senate'] = application_in['senate'].str.lower().str.replace(' ', '_')

# Insert new column yr_born, getting birth year from dateofbirth
application_in.insert(
    loc=application_in.columns.get_loc('dateofbirth') + 1,  # Positions column to the right of 'dateofbirth'
    column='yr_born',
    value=pd.to_datetime(application_in['dateofbirth']).dt.year
)

# Question 1
print('How does applicant age (in years) and party designation relate to overall vote by mail requests?')
current_year = pd.Timestamp.now().year
application_in['age'] = current_year - application_in['yr_born']

# Assign age ranges
bins = [18, 25, 35, 45, 55, 65, 75, 100]
labels = ['18-25', '25-35', '35-45', '45-55', '55-65', '65-75', '75+']
application_in['age_range'] = pd.cut(application_in['age'], bins=bins, labels=labels, right=False)

age_and_party = application_in.groupby(['age_range', 'party']).size().reset_index(name='requests')
age_and_party = age_and_party[age_and_party['party'].isin(['D', 'R'])]

print(age_and_party)

# Question 2
print('\nWhat was the median latency from when each legislative district issued their application and when the ballot was returned?')
latency_df = application_in[['legislative', 'appissuedate', 'ballotreturneddate']].copy()
latency_df['appissuedate'] = pd.to_datetime(latency_df['appissuedate'])
latency_df['ballotreturneddate'] = pd.to_datetime(latency_df['ballotreturneddate'])
latency_df['latency'] = (latency_df['ballotreturneddate'] - latency_df['appissuedate']).dt.days

latency_by_district = latency_df.groupby('legislative')['latency'].mean().reset_index()

median_latency = latency_by_district['latency'].median()
print(f'The median_latency, by legislative district, was {median_latency} days')

# Question 3
print('\nWhat is the congressional district that has the highest frequency of ballot requests?')
highest_request_district = application_in.groupby(['congressional']).size().nlargest(1).reset_index(name='requests')
print(f"The congressional district with the highest frequency of ballot requests is the {highest_request_district['congressional'][0]}, with {highest_request_district['requests'][0]} requests.")

# Question 4
print('\nCreate a visualization demonstrating the republican and democratic application counts in each county.')
two_party_system = application_in[application_in['party'].isin(['D', 'R'])]
two_party_system = two_party_system.groupby(['countyname', 'party']).size().reset_index(name='count')

# Pivot the data for plotting
plot_df = two_party_system.pivot(index='countyname', columns='party', values='count')

# Plot the data using pandas
plot = plot_df.plot(
    kind='bar',
    color={'D': 'blue', 'R': 'red'},
    figsize=(20, 10),
    title='Mail-In Ballot Requests By County & Party'
)
plot.set_xlabel('County')
plot.set_ylabel('Count')