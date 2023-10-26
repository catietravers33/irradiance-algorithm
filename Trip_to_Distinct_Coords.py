import pandas as pd 
import os
import numpy as np 
import geemap
import matplotlib.pyplot as plt
import json
import openrouteservice
from openrouteservice import convert
from geojson import MultiLineString
from geojson import LineString
import geopandas as gpd
import geopy
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import ArcGIS
import folium
from folium.plugins import FastMarkerCluster

client = openrouteservice.Client(key = '5b3ce3597851110001cf6248d5cc6329856d4104b16de2d55d56f603')

def concat_address(df):
    '''
    Converts a dataframe with fragmented address data to a full address. 
    Input dataframe should be either Woolworths Distribution Centres or Woolworths Stores
    
    :params df: dataframe containing Street Name, Town, State and Post Code columns for Australia
    
    :returns: dataframe with added full address column
    '''
    df['Address'] = df['Street Name']+', ' + df['Town'] +', ' + df['State'] + ' ' + df['Post Code'] + ' Australia'

def geocode_df(df):
    '''
    Returns latitude, longitude and elevation from full address
    
    :params df: input dataframe containing a column 'Address'
    
    :returns: dataframe with 'Point' column that contains latitude, longitude, and elevation values

    '''
    df['Location'] = df['Address'].apply(geocode)
    df['Point'] = df['Location'].apply(lambda loc: tuple(loc.point) if loc else None)
    print(df['Point'])

def lat_long_altitude(df):
    '''
    Convert geocoded point to latitude and longitude columns
    
    :params df: dataframe with geocoded "point" column
    
    :returns: dataframe with additional latitiude and longitude columns
    '''
    #point_data = pd.DataFrame(df['Point'].tolist(), index = df.index)
    df['latitude'] = [float(((df['Point'][i].split('('))[1].split(','))[0]) for i  in  range(0,len(df['Point']))]
    df['longitude'] = [float(((df['Point'][i].split('('))[1].split(','))[1]) for i  in  range(0,len(df['Point']))]
    df.head()

def sites_coords(start,end,storesdf,dcdf):
    '''
    :params start: string with name of Woolworths site MUST match stores or dcs csv
    :params end: string with name of Woolworths site MUST match stores or dcs csv
    :params storesdf: Woolworths supplied stores csv file in frame format after latitude and longitude columns added
    :params dcdf: Woolworths supplied dcs csv file in frame format after latitude and longitude columns added
    
    :returns: start and end coordinates of the trip
    '''
    if start in storesdf['Site Name'].unique():
        idx = (storesdf.index[storesdf['Site Name'] == start])[0]
        start_lat = storesdf['latitude'][idx]
        start_long = storesdf['longitude'][idx]
    elif start in dcdf['Site Name'].unique():
        idx = (dcdf.index[dcdf['Site Name'] == start])[0]
        start_lat = dcdf['latitude'][idx]
        start_long = dcdf['longitude'][idx]
    start_coord = '(' + str(start_lat) + ',' + str(start_long) + ')'
     
    if end in storesdf['Site Name'].unique():
        idx = (storesdf.index[storesdf['Site Name'] == end])[0]
        end_lat = storesdf['latitude'][idx]
        end_long = storesdf['longitude'][idx]
    elif end in dcdf['Site Name'].unique():
        idx = (dcdf.index[dcdf['Site Name'] == end])[0]
        end_lat = dcdf['latitude'][idx]
        end_long = dcdf['longitude'][idx]
    end_coord = '(' + str(end_lat) + ',' + str(end_long) + ')'
    
    coords = ((start_long,start_lat),(end_long,end_lat))
    return coords

def route_to_coords(decodedpolyline, directions):
    '''
    :params decodedpolyline: route map between the start and end coordinates given by convert.decode_polyline(client.directions(sites_coords(start,end,storesdf,dcdf))['routes'][0]['geometry'])
    :params directions: calculated by using client.directions function of start and end coordinates outputted from sites_coords function i.e. client.directions(sites_coords(start,end,storesdf,dcdf))
    
    :returns: list of coordinates in 10 minute intervals 
    '''
    index = [0]
    x = 0 
    while x < (len(decodedpolyline['coordinates'])-round(round(len(decodedpolyline['coordinates']))/round((directions['routes'][0]['summary']['duration']/60)/10))):
        x += round(round(len(decodedpolyline['coordinates']))/round((directions['routes'][0]['summary']['duration']/60)/10)) 
        index.append(x)
    list = [decodedpolyline['coordinates'][i] for i in index] 
    listpd = pd.Series(list)
    return listpd
