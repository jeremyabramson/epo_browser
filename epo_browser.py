import json
from typing import Union
from typing import Literal
from pathlib import Path


import numpy as np
import pgeocode
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

st.set_page_config(layout="wide")

url = 'https://hconlinex.healthcomp.com/FindAProvider/ProviderSearch.aspx/GetProviders'

headers = {
    'Content-type': 'application/json; charset=utf-8',
    'Host': 'hconlinex.healthcomp.com',
    'Content-Type': 'application/json',
    'Host': 'hconlinex.healthcomp.com',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Origin': 'https://hconlinex.healthcomp.com',
    'Referer': 'https://hconlinex.healthcomp.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
    'X-Requested-With': 'XMLHttpRequest',
}

params = {
    # 'EPO' or 'PPO', from sidebar
    'healthPlan': 'EPO',
    # Read in from categories_specialties.json
    'category': 'BEHAVIORAL HEALTH',
    # Set depending on category; options are from categories_specialties
    'specialty': 'PSYCHOLOGISTS',
    # Default to 90254 (Hermosa Beach
    'city': '90254',
    # Default to 5 miles, set 
    'radius': '5',
    # Set these two based on city and output from pgeocode library
    'initLatitude': '33.8600693',
    'initLongitude': '-118.3987842',

    # These ones might b
    'pcp': 'False', 
    'onlyNewPatients': 'false',
    'language': '',

    # Boilerplate
    'state': '',
    'keyWords': '',
    'providerBreakdown': '',
    'getFullDetails': 'true',
    'page': '1',
    'pageSize': '200',
    'ppoTier': 'undefined',
    'sortBy': 'Distance',
}

cols = [
    'DisplayName', 
#    'AssociativeValue',
    'Categories',
    'Specialties',
    'BusinessName',
    'FirstName',
    #'MiddleName',
    'LastName', 
    'Title',
    'Languages',
    'Address',
    'City',
    'State',
    'Zip',
    'Phone',
    'AcceptingPatients',
    'IsPCP',
#    'TableId',
#    'HashId',
    'Latitude',
    'Longitude',
    'Distance',
]

column_config={    
    'BusinessName': st.column_config.TextColumn("Business Name"),
    'FirstName': st.column_config.TextColumn("First Name"),
    'LastName': st.column_config.TextColumn("Last Name"),
    'Title': st.column_config.TextColumn("Title/Degree"),
    'Specialties': st.column_config.ListColumn(
        "Specialties",
        help="Medical specialties of the provider",
    ),
    'Distance': st.column_config.NumberColumn("Distance (mi)"),
    'Address': st.column_config.TextColumn("Address"),
    'City': st.column_config.TextColumn("City"),
    'State': st.column_config.TextColumn("State"),
    'Zip': st.column_config.TextColumn("Zip"),
    'Phone': st.column_config.TextColumn("Phone"),
    'AcceptingPatients': st.column_config.CheckboxColumn("Accepting Patients"),
    'IsPCP': st.column_config.CheckboxColumn("Is PCP"),

    'Languages': st.column_config.ListColumn(
        "Languages"),


    "url": st.column_config.LinkColumn("Search Link"),
    'DisplayName': None,
    'TableId': None,
    'Latitude': None,
    'Longitude': None,
}

column_order = [
    'FirstName',
    'LastName',
    'Title',
    'BusinessName',
    'Specialties',
    'Distance',
    'Address',
    'City',
    'State',
    'Zip',
    'Phone',
    'AcceptingPatients',
    'IsPCP',
    'Languages',
    "url"
]  

@st.cache_data
def get_categories_specialties(filepath: Path = Path('categories_specialties.json')) -> dict:
    with open(filepath, 'r') as f:
        return json.load(f)

@st.cache_data
def get_data(params: dict, headers: dict) -> pd.DataFrame:
    resp = requests.post(url, headers = headers, json=params)
    res = json.loads(resp.json()['d'])['filteredResults']
    df = pd.json_normalize(res)

    if df.empty:
        return df        
 
    df = df[cols].drop_duplicates(subset=['FirstName', 'LastName']).reset_index(drop=True).sort_values('Distance')
    df["name"] = df.apply(lambda row: f"{row['FirstName']} {row['LastName']}, {row['Title']}", axis=1)
    df['url'] = df.apply(lambda row: f"https://www.google.com/search?q={row['FirstName']}%20{row['LastName']}%20{row['City']}%20doctor", axis=1)

    # Define the jitter amount so all of our dots aren't on top of each other
    jitter_amount = .001

    # Identify rows where both latitude and longitude values are the same
    same_values_mask = (df.duplicated(subset=["Latitude", "Longitude"], keep=False))

    # Add random noise to "latitude" and "longitude" columns for rows with same values
    df.loc[same_values_mask, "Latitude"] += np.random.uniform(-jitter_amount, jitter_amount, size=same_values_mask.sum())
    df.loc[same_values_mask, "Longitude"] += np.random.uniform(-jitter_amount, jitter_amount, size=same_values_mask.sum())


    return df

def get_latlong_from_zip(zipcode: Union[str, int]) -> dict:
    nomi = pgeocode.Nominatim('us')
    query = nomi.query_postal_code(zipcode)
    ret = {
        "latitude": query["latitude"],
        "longitude": query["longitude"]
    }

    return ret

categories_and_specialties = get_categories_specialties()

sidebar = st.sidebar

heath_plan = sidebar.radio(label='Select health plan', options=['EPO', 'PPO'], index=0)
category = sidebar.selectbox(label='MedicalCategory', options=list(categories_and_specialties.keys()), index=2)

# This is a ridiculous way of getting at both the value (for the drop down) and the description (for the info box)
# We should really just pivot the dict
specialty_and_descriptions = [(specialty['Name'], specialty['Description']) for specialty in categories_and_specialties[category]]
specialty = sidebar.selectbox(label='Sub-Specialty', options=[specialty[0] for specialty in specialty_and_descriptions])
specialty_index = [specialty[0] for specialty in specialty_and_descriptions].index(specialty)

# Finally, print an info box with the description
sidebar.info(specialty_and_descriptions[specialty_index][1])


city = sidebar.text_input(label='Zip code', max_chars=5, value='90254')

if len(city) != 5:
    st.warning('Please enter a valid 5 digit zip code')
    st.stop()

try:
    city = int(city)
except ValueError:
    st.warning('Please enter a valid 5 digit zip code')
    st.stop()


radius = sidebar.slider(label='Radius', min_value=1, max_value=50, value=5)

params['healthPlan'] = heath_plan
params['category'] = category
params['specialty'] = specialty
params['city'] = city
params['radius'] = radius
latlong = get_latlong_from_zip(city)
params['initLatitude'] = latlong['latitude']
params['initLongitude'] = latlong['longitude']

df = get_data(params, headers)

if df.empty:
    st.warning('No providers found')
    st.stop()

providers = sidebar.multiselect('Provider Search/Focus', options=df['name'].unique(), help='Search and select a subset of providers to focus the map view')

if providers:
    filtered = df[df['name'].isin(providers)]
else:
    filtered = df


selections = st.dataframe(
    filtered,
    column_config=column_config,
    on_select="rerun",
    selection_mode="multi-row",
    hide_index=True,  
    column_order=column_order, 
)

if len(selections.selection.rows) > 0:
    filtered = filtered.iloc[selections.selection.rows]
    st.subheader('Selected Providers')
    st.dataframe(
        filtered,
        column_config=column_config,
        hide_index=True,  
        column_order=column_order, 
)


layer = pdk.Layer(
    "ScatterplotLayer",
    filtered,
    get_position=["Longitude", "Latitude"],
    get_radius=90,
    get_fill_color=[255, 0, 0],
    pickable=True,
    auto_highlight=True,
    opacity=0.1  # Set opacity to 0.5 (adjust as needed)

)

tooltip = {
    "html": "<b>{FirstName} {LastName}, {Title}</b><br>{Address}</b><br>{Phone}</br>",
    "style": {
        "backgroundColor": "steelblue",
        "color": "white"
    }
}

# Calculate bounding box of the data
min_lat, max_lat = min(filtered['Latitude']), max(filtered['Latitude'])
min_lon, max_lon = min(filtered['Longitude']), max(filtered['Longitude'])

# Calculate center of the bounding box
center_lat = (min_lat + max_lat) / 2
center_lon = (min_lon + max_lon) / 2

# Calculate zoom level to fit all points within the view
#zoom_level = 11  # Adjust as needed based on your preference

#view_state = pdk.ViewState(latitude=df["Latitude"].mean(), longitude=df["Longitude"].mean())
view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon)

map_ = pdk.Deck(
    map_style="mapbox://styles/mapbox/dark-v9",
    initial_view_state=view_state,
    layers=[layer],
    tooltip=tooltip)

# Render the map in Streamlit
st.pydeck_chart(map_)
