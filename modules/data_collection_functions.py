import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv(".env")
import requests
from bs4 import BeautifulSoup
import re

# Set up Spotify API credentials
my_id = os.getenv("SPOTIPY_CLIENT_ID")
my_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI")
scope = "user-library-read user-read-recently-played"
# Set up Spotify API object
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=my_id,
        client_secret=my_secret,
        scope=scope,
        #redirect_uri="http://localhost/3000",
    )
)

def get_playlist(playlist, country):
    """
    Takes as input a playlist via its playlist id and a country
    vie its two digit country code (ISO 3166-1 alpha-2).
    Returns a dataframe that represents the playlist with the 
    columns artist, artist_id, playlist_song, country, and 
    artist_uri.
    """
    # Create empty lists to append the API data into
    artist_name = []
    track_name = []
    artist_uri = []
    id = []
    # Add the length [:50] in case some playlists are longer
    for item in playlist['items'][:50]:
        track = item['track']
        artist_name.append(track['artists'][0]['name'])
        track_name.append(track['name'])
        id.append(item["track"]["artists"][0]["id"])
        artist_uri.append(item["track"]["artists"][0]["uri"])
    # Turn the playlist into a data frame
    top_playlist_df = pd.DataFrame({
        "artist": artist_name,
        "artist_id": id,
        "playlist_song": track_name,
        "country": country,
        "artist_uri": artist_uri,
    })
    return top_playlist_df

def get_top_songs(artist_uri, country_id):
    """
    Fetches top 3 songs for a given artist in a specific 
    country.
    Returns a list of song name, song id, release date, 
    release date precision, and popularity.
    """
    top_songs = []
    top_tracks = sp.artist_top_tracks(
        artist_uri, country=country_id
        )["tracks"]    
    for i in range(3):
        song_data = [
            top_tracks[i]["name"], 
            top_tracks[i]["id"],
            top_tracks[i]["album"]["release_date"],
            top_tracks[i]["album"]["release_date_precision"],
            top_tracks[i]["popularity"]
        ]
        top_songs.append(song_data)
    return top_songs

def get_track_info(some_tracks_table):
    """
    Fetches song_id, release date, and popularity of each 
    track in a given dataframe of tracks.
    Returns the given dataframe with the new columns added.
    """
    for _, row in some_tracks_table.iterrows():
        track_info = sp.search(q=row, type="track")["tracks"]["items"][0]
        some_tracks_table["song_id"] = track_info["id"]
        some_tracks_table["release_date"] = track_info["album"]["release_date"]
        some_tracks_table["popularity"] = track_info["popularity"]
    return some_tracks_table

def get_artists(top_country, country):
    """
    Fetches the top artists for a given country.
    Returns a dataframe of the top artists with the columns
    country, artist, artist_id, and artist_uri.
    """
    artists = []
    id = []
    artist_uri = []
    for item in top_country["items"]:
        artists.append(item["track"]["artists"][0]["name"])
        id.append(item["track"]["artists"][0]["id"])
        artist_uri.append(item["track"]["artists"][0]["uri"])
    top_country_artists = pd.DataFrame(
        {"country": country,
         "artist": artists, 
         "artist_id": id,
         "artist_uri": artist_uri
         })
    return top_country_artists

# Smaller function to fetch individual artist info
def fetch_artist_info(artist):
    """
    Fetches the origin and birthplace of a given artist.
    Returns a dictionary of the artist, origin, and birthplace.
    """
    artist_url = []
    alternate_options = ['',"_(band)", "_(rapper)", 
        "_(musician)", "_(singer)", "_(group)",
        "_(South Korean band)", "_(singer-songwriter)", "_(DJ)"
        ]
    info_dict = {}
    pattern = r"(.*?)[)\d]"
    letters_regex = r"[a-zA-Z]+"
    # Setting base variables for born and origin location
    born_location = "N/A"
    origin_location = "N/A"
    for i in range(len(alternate_options)):
        artist_url.append('https://en.wikipedia.org/wiki/' 
            + artist.replace(' ','_') + alternate_options[i])
    # Adding a counter so it's clear how many times code has to 
    # work to find a correct URL
    count = 0
    # Looping through the list of URLs
    for url_option in artist_url:
        response = requests.get(url_option)
        # If the page exists, scrape it for origin and
        # birthplace
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 
                'html.parser')
            infobox_labels = soup.find_all(class_="infobox-label")
            # If the infobox exists, scrape it for origin and
            # birthplace
            if infobox_labels is not None:
                # Loop through the infobox labels to find the
                # "Born" and "Origin" labels
                for label in infobox_labels:
                    if label.text == "Born":
                        born_data = label.find_next_sibling()
                        if born_data:
                            birthplace = born_data.find(
                                class_="birthplace"
                                )
                            if birthplace:
                                born_location = birthplace.get_text(
                                    strip=True
                                    )
                            else:
                                born_location = born_data.get_text(
                                    strip=True
                                    )
                                #Data cleaning born location information
                                clean_location = re.search(pattern, 
                                    born_location[::-1]
                                    )
                                if clean_location:
                                    born_location = clean_location.group(
                                        1)[::-1].strip()

                    if label.text == "Origin": 
                        origin_data = label.find_next_sibling()
                        if origin_data:
                            origin_location = origin_data.get_text(
                                strip=True
                                )
            else:
                born_location == "N/A" and origin_location == "N/A"

        # Filling blank values with "N/A"
        if born_location == '' or born_location == None or born_location == " ":
            born_location == "N/A"
        if origin_location == '' or origin_location == None or origin_location == " ":
            origin_location == "N/A"

        # Setting up a base dictionary for artist with born 
        # origin and location
        info_dict[artist] = [born_location, origin_location]

        # Convert info_dict into a dataframe - no longer using 
        # because of efficiency, dictionary is better
        # solo_df = pd.DataFrame.from_dict(info_dict, 
        #   orient='index', columns=['Born', 'Origin'])
        
        # Adding one to counter to show how many versions of 
        # URL it has to go through 
        count += 1

        for key, value in info_dict.items():
            if value != ["N/A", "N/A"]:
                # print(info_dict)
                return info_dict
            
            elif count < len(alternate_options):
                continue

            else:
                return info_dict
            
#Function to scrape multiple artists
def multi_artist_scrape(artist_list, country_code, csv_saved):

    """
    artist_list = list of artist names
    country_code = country code for csv file name
    csv_saved = True if you want to save a csv file, False if you don't
    """
    if csv_saved == True and country_code == None:
        raise ValueError(
            "Please enter a country code or set csv_saved to False"
            )   
    # Retrieve individual dictionaries and merge them using 
    # a dictionary comprehension
    artist_origin_birthplace_dict = {}
    for artist in artist_list:
        if artist not in artist_origin_birthplace_dict:
            artist_origin_birthplace_dict[artist] = fetch_artist_info(
                artist)[artist]
        else: 
            artist_origin_birthplace_dict[
                artist + " duplicate"
                ] = fetch_artist_info(
                artist)[artist]

    #Convert dictionary into a dataframe
    artist_origin_birthplace_df = pd.DataFrame.from_dict(
        artist_origin_birthplace_dict, 
        orient='index', 
        columns=['born', 'origin']
        )

    #Adding a column for country code
    artist_origin_birthplace_df["country_code"] = country_code

    #Change index to artist name
    artist_origin_birthplace_df.index.names = ['artist_name']

    #Resetting index to include
    artist_origin_birthplace_df.reset_index(inplace=True)

    print(f"{country_code} artists info completed")

    #Saving the dataframe as a csv file
    if csv_saved == True:
        artist_origin_birthplace_df.to_csv(
            f"{country_code}_artists_places.csv"
            )
  
    return artist_origin_birthplace_df


def split_dataframe(df):
    """
    Split a dataframe into six smaller dataframes of equal size.

    Parameters:
     - df (pandas.DataFrame): The dataframe to be split.
     - chunk_size (int): The number of rows in each smaller dataframe.

    Returns:
     - list: A list of smaller dataframes.
    """

    df1 = df.iloc[:50, :]
    df2 = df.iloc[50:100, :]
    df3 = df.iloc[100:150, :]
    df4 = df.iloc[150:200, :]
    df5 = df.iloc[200:250, :]
    df6 = df.iloc[250:300, :]
     
    return [df1, df2, df3, df4, df5, df6]

def get_genre(df):
    """
    Fetches the genre of a given artist ids from dataframes.
    Returns a dataframe of genres.
    """
    # Create a list of artist IDs
    artist_ids = df["artist_id"].tolist()
    artists_info = sp.artists(artist_ids)

    # Get artist id and genres from the artist_info object
    artist_genres = {}
    for artist in artists_info["artists"]:
        artist_genres[artist["id"]] = artist["genres"]

    # Create a dataframe from the artist_genres dictionary
    genre_df = pd.DataFrame.from_dict(artist_genres, orient="index")
    genre_df.reset_index(inplace=True)
    genre_df = genre_df.rename(
        columns={
            "index": "artist_id",
            0: "artist_genre1",
            1: "artist_genre2",
            2: "artist_genre3",
            3: "artist_genre4",
            4: "artist_genre5",
            5: "artist_genre6",
            6: "artist_genre7",
            7: "artist_genre8",
        }
    )

    # Print the head of the dataframe
    return genre_df

#Cleaning missing information for origin/birthplace:
def missing_info(df):
    """
    This function takes a DataFrame and returns a list of artists 
    with missing information.
    
    Parameters:
    df (DataFrame): The input DataFrame containing artist information.
    
    Returns:
    list: A list of artists with missing information.
    """
    none_info = df[df['born'].isnull() & df['origin'].isnull()]
    wrong = df[df['born'].str.contains(']') | df['origin'].str.contains(']')]
    missing_info_artists = [wrong['artist_name'].tolist(), none_info['artist_name'].tolist()]
    return missing_info_artists


# This function merges two dataframes by finding matching artist names 
# and adding the genre information to the main dataframe
def genre_merge(maindf, seconddf):
    for index, row in seconddf.iterrows():
        # Find the corresponding row in artist_spreadsheet_df based on artist_name
        matching_row = maindf.loc[maindf['artist_name'] == row['artist_name']]
        
        # Assign values from uk_info to artist_spreadsheet_df columns
        maindf.loc[matching_row.index, 'artist_genre1'] = row['artist_genre1']
        maindf.loc[matching_row.index, 'artist_genre2'] = row['artist_genre2']

    return maindf

# Defining a function to break the dictionary of dictionaries into a dictionary of lists
# def break_into_dicts(song_features_dict):
    song_features_dict2 = {}
    for song in song_features_dict:
        song_features_dict2[song] = song_features_dict[song][0][0]
    return song_features_dict2