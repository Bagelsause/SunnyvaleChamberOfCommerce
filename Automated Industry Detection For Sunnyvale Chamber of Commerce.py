#!/usr/bin/env python
# coding: utf-8

# # Automated Industry Detection For Sunnyvale Chamber of Commerce
# *Created by Robert Beliveau created during July 2022.*

# **Important note: If you want to run this, it requires at minimum 10 Gigabytes of RAM. There is no limitation on CPU information.**
# 
# ## Basic information about the program
# - It works off of the Bing Maps API, which, up to **125,000** requests each year, is completely free.
# - Instead of looking through the entire list of businesses from the City of Sunnyvale business licenses, it's looking through a rectangle on a big outside boundary box of Sunnyvale, then asking for any business types within those miniature rectangles (fig. 1)
# <figure>
#     <img src="https://i.imgur.com/noVF07i.png" height="400px" width="250px">
#     <center><figcaption>Figure 1. Red represents the outer bounding box and orange is the inner boxes.</figcaption></center>
# </figure>
# 
# - All of the types are manually inputted, but if there are any changes to the types being analyzed, it could be automatically created from Cody's module.
# - Instead of sending a request and waiting for the response, we send out a batch of four requests every half second, and we then analyze it after all of it is received.
# - The average runtime is **6 minutes** for the entire Bing Maps program. While the google runtime is around **90 minutes**.
# 
# ## Function/module explanations
# ### boxCreation
# What box creation does is it takes the meta bounding box, with the coordinates at the Southwest and Northeast corners, and separates the box into a bunch of smaller boxes, creating a grid within the meta bounding box. ``LAT_divisor`` is the amount of rows the grid will have, while ``LNG_divisor`` is the amount of columns. It generates the grid positions per call of the function, thus being an automatic generator.
# 
# ### download_link and download_all
# Both of these functions allow for the requests to be sent out in batches of 4, and once it is received, the raw text returned goes directly into a text file. It also does some basic preprocessing as it adds in the business type along with every JSON result.
# 
# ### validate_types, construct_request, validate_request_parameters, parse_locations, search_grid.
# All of these functions are Cody's module, which allow the user to create requests easily along with the validation of the types that would be sent out. In my program, the main function that I use in this module is ``parse_locations``, as it reads from each line of the JSON-text file and parses the individual locations. It then reads that information, transforms it into the CSV, and saves it.

# In[1]:


import requests
import csv
import time

#All possible types from the Bing Maps API, separated into 7 big categories, EatDrink, SeeDo, Shop, BanksAndCreditUnions, Hospitals, HotelsAndMotels, and Parking

eatDrinkTypes = ["Bars", "BarsGrillsAndPubs", "BelgianRestaurants", "BreweriesAndBrewPubs", "BritishRestaurants", "BuffetRestaurants", "CafeRestaurants", "CaribbeanRestaurants", "ChineseRestaurants", "CocktailLounges", "CoffeeAndTea", "Delicatessens", "DeliveryService", "Diners", "DiscountStores", "Donuts", "FastFood", "FrenchRestaurants", "FrozenYogurt", "GermanRestaurants", "GreekRestaurants", "Grocers", "Grocery", "HawaiianRestaurants", "HungarianRestaurants", "IceCreamAndFrozenDesserts", "IndianRestaurants", "ItalianRestaurants", "JapaneseRestaurants", "Juices", "KoreanRestaurants", "LiquorStores", "MexicanRestaurants", "MiddleEasternRestaurants", "Pizza", "PolishRestaurants", "PortugueseRestaurants", "Pretzels", "Restaurants", "RussianAndUkrainianRestaurants", "Sandwiches", "SeafoodRestaurants", "SpanishRestaurants", "SportsBars", "SteakHouseRestaurants", "Supermarkets", "SushiRestaurants", "TakeAway", "Taverns", "ThaiRestaurants", "TurkishRestaurants", "VegetarianAndVeganRestaurants", "VietnameseRestaurants"]
seeDoTypes = ["AmusementParks", "Attractions", "Carnivals", "Casinos", "LandmarksAndHistoricalSites", "MiniatureGolfCourses", "MovieTheaters", "Museums", "Parks", "SightseeingTours", "TouristInformation", "Zoos"]
shopTypes = ["AntiqueStores", "Bookstores", "CDAndRecordStores", "ChildrensClothingStores", "CigarAndTobaccoShops", "ComicBookStores", "DepartmentStores", "DiscountStores", "FleaMarketsAndBazaars", "FurnitureStores", "HomeImprovementStores", "JewelryAndWatchesStores", "KitchenwareStores", "LiquorStores", "MallsAndShoppingCenters", "MensClothingStores", "MusicStores", "OutletStores", "PetShops", "PetSupplyStores", "SchoolAndOfficeSupplyStores", "ShoeStores", "SportingGoodsStores", "ToyyAndGameStores", "VitaminAndSupplementStores", "WomensClothingStores"]

totalTypes = []
for val in eatDrinkTypes:
    totalTypes.append(val)
for val in seeDoTypes:
    totalTypes.append(val)
for val in shopTypes:
    totalTypes.append(val)
totalTypes.append("BanksAndCreditUnions")
totalTypes.append("Hospitals")
totalTypes.append("HotelsAndMotels")
totalTypes.append("Parking")
print(totalTypes)

#Location of the box is a comma separated list of the latitudes and longitudes of two corners of the rectangle, in the following order:
    #- Latitude of the Southwest corner
    #- Longitude of the Southwest corner
    #- Latitude of the Northeast corner
    #- Longitude of the Northeast corner
    #Example: 29.8171041,-122.981995,48.604311,-95.5413725

from numpy import arange
def boxCreation(SW, NE, LAT_divisor, LNG_divisor):
    distLAT = NE[0] - SW[0]
    distLNG = NE[1] - SW[1]
    LATmult = distLAT / LAT_divisor
    LNGmult = distLNG / LNG_divisor
    
    for lat in arange(SW[0], NE[0], LATmult):
        for lng in arange(SW[1], NE[1], LNGmult):
            yield ((lat, lng), (lat + LATmult, lng + LNGmult))
            
            
import asyncio
import time 
import aiohttp
from aiohttp.client import ClientSession

overallType = ""
bizType = ""

newFile = open('ResultsList.txt', "w")

async def download_link(url:str,session:ClientSession):
    async with session.get(url) as response:
        print(url)
        result = await response.text()
        print(result)
        
        bizType = url.split("?type=")[1].split("&")[0]
        
        newFile.write(result + "|" + bizType + "\n")

async def download_all(urls:list):
    my_conn = aiohttp.TCPConnector(limit=4)#could change to 20 apparently and not get banned, but 5 is the max for bing API
    async with aiohttp.ClientSession(connector=my_conn) as session:
        tasks = []
        for url in urls:
            task = asyncio.ensure_future(download_link(url=url,session=session))
            tasks.append(task)
        await asyncio.gather(*tasks,return_exceptions=True)
          
urlList = []
            
for index, bizType in enumerate(totalTypes):
    metaBoundingBoxSW = [37.33190189447495, -122.072770090548]
    metaBoundingBoxNE = [37.448793480573976, -121.97427447581298]
    #Change if you want to edit the grid of objects, no default: Latitude, Longitude.
    #5 columns by 8 rows is the default, but those were just arbitrarity chosen numbers.
    #As long as the proportions are correct (around 5x8), that is all that matters.
    for SW, NE in boxCreation(metaBoundingBoxSW, metaBoundingBoxNE, 8, 5):
        stringifiedQuery = str(SW[0])+","+str(SW[1])+","+str(NE[0])+","+str(NE[1])
        URL = "https://dev.virtualearth.net/REST/v1/LocalSearch/?type="+bizType+"&maxresults=25&userMapView="+stringifiedQuery+"&key=AnGrJg9HJRSEcDeyPbI2cBJ1X2CZLmJLKY6I026rbIFlo4hxas9bTDwKwt9rCV5A"
        
        urlList.append(URL)
        
await download_all(urlList)
newFile.close()


# In[2]:


#Module created by Cody He. Last edit on 7/27.
#The full module page, along with examples, is here: https://replit.com/@codyh587/businessFinder#localSearch.py

from numpy import arange


type_identifiers = {
    'EatDrink': {
        'Bars', 'BarsGrillsAndPubs', 'BelgianRestaurants',
        'BreweriesAndBrewPubs', 'BritishRestaurants', 'BuffetRestaurants',
        'CafeRestaurants', 'CaribbeanRestaurants', 'ChineseRestaurants',
        'CocktailLounges', 'CoffeeAndTea', 'Delicatessens', 'DeliveryService',
        'Diners', 'DiscountStores', 'Donuts', 'FastFood', 'FrenchRestaurants',
        'FrozenYogurt', 'GermanRestaurants', 'GreekRestaurants', 'Grocers',
        'Grocery', 'HawaiianRestaurants', 'HungarianRestaurants',
        'IceCreamAndFrozenDesserts', 'IndianRestaurants', 'ItalianRestaurants',
        'JapaneseRestaurants', 'Juices', 'KoreanRestaurants', 'LiquorStores',
        'MexicanRestaurants', 'MiddleEasternRestaurants', 'Pizza',
        'PolishRestaurants', 'PortugueseRestaurants', 'Pretzels',
        'Restaurants', 'RussianAndUkrainianRestaurants', 'Sandwiches',
        'SeafoodRestaurants', 'SpanishRestaurants', 'SportsBars',
        'SteakHouseRestaurants', 'Supermarkets', 'SushiRestaurants',
        'TakeAway', 'Taverns', 'ThaiRestaurants', 'TurkishRestaurants',
        'VegetarianAndVeganRestaurants', 'VietnameseRestaurants'
    },
    'SeeDo': {
        'AmusementParks', 'Attractions', 'Carnivals', 'Casinos',
        'LandmarksAndHistoricalSites', 'MiniatureGolfCourses', 'MovieTheaters',
        'Museums', 'Parks', 'SightseeingTours', 'TouristInformation', 'Zoos'
    },
    'Shop': {
        'AntiqueStores', 'Bookstores', 'CDAndRecordStores',
        'ChildrensClothingStores', 'CigarAndTobaccoShops', 'ComicBookStores',
        'DepartmentStores', 'DiscountStores', 'FleaMarketsAndBazaars',
        'FurnitureStores', 'HomeImprovementStores', 'JewelryAndWatchesStores',
        'KitchenwareStores', 'LiquorStores', 'MallsAndShoppingCenters',
        'MensClothingStores', 'MusicStores', 'OutletStores', 'PetShops',
        'PetSupplyStores', 'SchoolAndOfficeSupplyStores', 'ShoeStores',
        'SportingGoodsStores', 'ToyAndGameStores',
        'VitaminAndSupplementStores', 'WomensClothingStores'
    },
    'BanksAndCreditUnions': set(),
    'Hospitals': set(),
    'HotelsAndMotels': set(),
    'Parking': set()
}


def validate_types(types):
    """
    Verifies that a list of type IDs contains valid strings for the Local
    Search API type parameter.

    Args:
        types: a list, tuple, or set of strings containing type IDs. Space
        separated string also supported.

    Returns:
        True if every element in types is present in type_identifiers and False
        if not.
    """
    for type_id in types:
        found = False
        for category in type_identifiers:
            if type_id == category or type_id in type_identifiers[category]:
                found = True
                break

        if not found: return False
    return True


def construct_request(query=None,
                      types=None,
                      maxResults=None,
                      userCircularMapView=None,
                      userLocation=None,
                      userMapView=None,
                      key=None,
                      validate=False):
    """
    Constructs the URL for a Local Search API request given API parameters.

    Args:
        query: string representing a search query. Either query or types must
            be provided.

        types: a list, tuple, or set of strings containing type IDs. Either
            query or types must be provided. Space separated string also
            supported.
        maxResults: integer indicating the maximum amount of  results to
            retrieve (between 1-25).
        userCircularMapView: a list or tuple of 3 floats specifying the
            center location (latitude, longitude) and radius (m) of a circular
            region to search from. Cannot be used with userMapView.
        userLocation: a list or tuple of 2-3 floats specifying the target
            location (latitude, longitude) and radius (m, optional)
            representing the confidence in the accuracy of the location. Does
            nothing if userCircularMapView or userMapView are provided.
        userMapView: a list or tuple of 4 floats specifying two corners of a
            rectangular search region, in order of:
                - Latitude of the Southwest corner
                - Longitude of the Southwest corner
                - Latitude of the Northeast corner
                - Longitude of the Northeast corner
            Cannot be used with userCircularMapView.
        key: string representing the API key. Must be provided.
        validate: boolean toggling optional parameter validation.

    Returns:
        A string representing the URL for the desired API request.
    
    Raises:
        Applies when validate is set to True.

        ValueError: if type IDs are invalid.
        ValueError: if maxResults is not between 1-25.
        ValueError: if neither query nor type are provided.
        ValueError: if both userCircularMapView and userMapView are provided.
        ValueError: if userMapView coordinates do not form a rectangle.
        ValueError: if key is not provided.
    """
    if type(types) is str: types = types.split()
    if validate:
        validate_request_parameters(query, types, maxResults,
                                    userCircularMapView, userLocation,
                                    userMapView, key)

    url = f"https://dev.virtualearth.net/REST/v1/LocalSearch/?key={key}"
    if query: url += f"&query={query.replace(' ', '%20')}"
    if types: url += f"&type={','.join(types)}"
    if maxResults: url += f"&maxResults={int(maxResults)}"
    if userCircularMapView:
        url += (
            f"&userCircularMapView={','.join(map(str, userCircularMapView))}")
    if userLocation: url += f"&userLocation={','.join(map(str, userLocation))}"
    if userMapView: url += f"&userMapView={','.join(map(str, userMapView))}"

    return url


def validate_request_parameters(query, types, maxResults, userCircularMapView,
                                userLocation, userMapView, key):
    """
    Helper method to perform optional construct_request() parameter validation.
    Does not validate specfied data types.
    """
    if not query and not types:
        raise ValueError("Either query or types must be provided")
    if types and not validate_types(types):
        raise ValueError("types contains invalid type IDs")
    if maxResults and not (1 <= maxResults <= 25):
        raise ValueError("maxResults must be between 1-25")
    if userCircularMapView and userMapView:
        raise ValueError("userCircularMapView and userMapView cannot both be" +
                         "provided")
    if userMapView:
        sw_lat, sw_long, ne_lat, ne_long = userMapView
        if sw_lat > ne_lat or sw_long > ne_long:
            raise ValueError("userCircularMapView coordinates must form a" +
                             "rectangle (sw_lat < ne_lat, sw_long < ne_long)")
    if not key:
        raise ValueError("key must be provided")


def parse_locations(response, items=None):
    """
    Generator that retrieves location data from a JSON response given by the
    Local Search API. Can retrieve specifed attributes from each search result.

    Args:
        response: dictionary created from a Local Search API JSON
            response. Dictionary must contain entire JSON document.
        items: a list or tuple containing strings specifying the desired yield
            attributes.

            Attribute Hierarchy:
                > '__type'
                > 'name'
                v 'point'
                    > 'type'
                    v 'coordinates'
                        > list (size 2)
                v 'Address'
                    > 'addressLine'
                    > 'adminDistrict'
                    > 'countryRegion'
                    > 'formattedAddress'
                    > 'locality'
                    > 'postalCode'
                > 'PhoneNumber'
                > 'Website'
                > 'entityType'
                v 'geocodePoints'
                    v list (size 1)
                        > 'type'
                        v 'coordinates'
                            > list (size 2)
                        > 'calculationMethod'
                        v 'usageTypes'
                            > list (size 1)
            
            To retrieve a specific attribute from a location, indicate the
            hierarchy separated by dots. To retrieve an element from a list,
            type the index number.

            Ex: to retrieve name and calculationMethod, set
            items=["name", "geocodePoints.0.calculationMethod"].

    Yields:
        A list of string values corresponding to attributes specified in items
        for each search result, in identical order. Returns None if attribute
        does not exist. Returns dictionary of
        entire search result if items is not specified.

    Raises:
        KeyError: if specified attributes do not exist.
        TypeError: if specified attributes do not exist.
        KeyError: if JSON dictionary is invalid.
    """
    if items: items_split = tuple(tuple(item.split(".")) for item in items)
    for location_dict in response['resourceSets'][0]['resources']:
        if not items:
            yield location_dict
        else:
            location_data = []
            for item_levels in items_split:
                try:
                    data_entry = location_dict[item_levels[0]]
                    for item_level in item_levels[1:]:
                        if item_level.isdigit(): item_level = int(item_level)
                        data_entry = data_entry[item_level]
                except KeyError: data_entry = None
                location_data.append(data_entry)

            yield location_data


def search_grid(coordinates, lat_partition, long_partition, set_size=False):
    """
    Generator that splits a rectangular search region into evenly distributed
    search grids.

    Args:
        coordinates: a list or tuple of 4 floats specifying two corners of a
            rectangular search region, in order of:
                - Latitude of the Southwest corner
                - Longitude of the Southwest corner
                - Latitude of the Northeast corner
                - Longitude of the Northeast corner
        lat_partition: integer or float representing the divisor used to
            separate the search region by latitude. Must be positive.

            Ex: Set lat_partition=2 to split the search region into halves
            latitudinally.
        long_partition: integer or float representing the divisor used to
            separate the search region by longitude. Must be positive.

            Ex: Set long_partition=2 to split the search region into halves
            longitudinally.
        set_size: boolean toggling set_size mode. set_size mode will use
            lat_partition and long_partition as the size of each grid instead
            of its divisor.

            Ex: Set lat_partition=2, long_partition=2, and set_size=True to
            split a rectangular search region into 2x2 degree grids rather than
            into quarters.

    Yields:
        A tuple of 4 floats specifying the southwest corner (latitude,
        longitude) and northeast corner (latitude, longitude) of each separate
        grid in the search region.
    
    Raises:
        ValueError: if coordinates do not form a rectangle.
        ValueError: if lat_partition or long_partition are not positive. 
    """
    sw_lat, sw_long, ne_lat, ne_long = coordinates

    if sw_lat > ne_lat or sw_long > ne_long:
        raise ValueError("Coordinates must form a rectangle (sw_lat < " +
                         "ne_lat, sw_long < ne_long)")
    if lat_partition <= 0 or long_partition <= 0:
        raise ValueError("lat_partition and long_partition must be positive")

    if not set_size:
        lat_step = (ne_lat - sw_lat) / lat_partition
        long_step = (ne_long - sw_long) / long_partition
    else:
        lat_step = lat_partition
        long_step = long_partition

    for grid_lat in arange(sw_lat, ne_lat, lat_step):
        for grid_long in arange(sw_long, ne_long, long_step):
            yield (grid_lat, grid_long, min(grid_lat + lat_step, ne_lat),
                   min(grid_long + long_step, ne_long))


# In[3]:


import json
import csv

csvfile = open('BusinessList.csv', "w", newline='')
writer = csv.writer(csvfile, delimiter=",")
writer.writerow(["Overall Type", "Type", "Name", "Address", "Phone Number", "Website", "Latitude", "Longitude"])

newFile = open('ResultsList.txt', "r")
for line in newFile:
    #Structure of the line:
    #{JSON_RESULT}|BusinessType
    
    print(line)
    bizType = line.rsplit("|")[-1]
    print(bizType)
    
    bizLen = len(bizType) + 1
    line = line[:-(bizLen)]
    print(line)
    
    data = json.loads(line)
    
    bizType = bizType.strip() #We run this strip() function to remove the newlines, as that's included into the substring.
    
    overallType = ""
    if bizType in eatDrinkTypes:
        overallType = "EatDrink"
    elif bizType in seeDoTypes:
        overallType = "SeeDo"
    elif bizType in shopTypes:
        overallType = "Shop"
    else:
        overallType = bizType
        
    for name, address, phone, website, location in parse_locations(data,items=("name", "Address.formattedAddress", "PhoneNumber", "Website", "point.coordinates")):
        try:
            if location is not None: #If the location is able to be mapped as a point, keep the location as a point.
                writer.writerow([overallType, bizType, name, address, phone, website, location[0], location[1]])
            else: #Otherwise, put the latitude and longitude as 0.
                writer.writerow([overallType, bizType, name, address, phone, website, 0, 0])
        except EncodingError:
            #This error most likely occurs when a business name has an accented character (e.g accent et gu e/é)
            #If it still returns an error after this exception, the website is most likely the next culprit.
            writer.writerow([overallType, bizType, "ENCODING ERROR", address, phone, website, location[0], location[1]])
            
newFile.close()
csvfile.close()


# In[4]:


import pandas as pd
from pathlib import Path
#Reading each line with accents, assuming there are only Latin and accented characters.
df = pd.read_csv('BusinessList.csv', encoding="latin1")
#As none of the results are ordered, we just order now
df.sort_values(by=['Overall Type', 'Type'])
#If the same business appears multiple times, combine all of the types together.
df = df.groupby(['Overall Type','Name','Address', 'Phone Number', 'Website', 'Latitude', 'Longitude'])['Type'].apply(', '.join).reset_index()
#Reordering the columns as "Type" would be at the end.
df = df[['Overall Type', 'Type', 'Name', 'Address', 'Phone Number', 'Website', 'Latitude', 'Longitude']]
#If the Type associated with a business is repeated, remove one but keep the other.
df['Type'] = df['Type'].str.split(', ').apply(set).str.join(', ')

#Putting the dataframe into a file
filepath = Path('CleanedBusinessList.csv')
df.to_csv(filepath,index=False)


# ## Visualizations/Conclusions
# ### What are the most common types of businesses in Sunnyvale?

# In[5]:


import pandas as pd
#Reading each line with accents, assuming there are only Latin and accented characters.
df = pd.read_csv('CleanedBusinessList.csv', encoding="latin1")
typesColumns = df[['Overall Type', 'Type']]
typesColumns.head(10)
overallTypeCount = {
    'BanksAndCreditUnions': 0,
    'EatDrink': 0,
    'Hospitals': 0,
    'HotelsAndMotels': 0,
    'Parking': 0,
    'SeeDo': 0,
    'Shop': 0
}

for index, row in df.iterrows():
    if index == 0:
        continue
    overallTypeCount[str(row[0])] += 1

import matplotlib.pyplot as plt

hosHotParkBank = overallTypeCount['Hospitals'] + overallTypeCount['HotelsAndMotels'] + overallTypeCount['Parking'] + overallTypeCount['BanksAndCreditUnions']

labels = 'Retail', 'Restauraunts/Bars', 'Activities', 'Misc'
sizes = overallTypeCount['Shop'], overallTypeCount['EatDrink'], overallTypeCount['SeeDo'], hosHotParkBank
explode = (0.1, 0.1, 0, 0)

fig1, ax1 = plt.subplots()
ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax1.axis('equal')

plt.show()


# In[6]:


eatDrinkTypes = ["Bars", "BarsGrillsAndPubs", "BelgianRestaurants", "BreweriesAndBrewPubs", "BritishRestaurants", "BuffetRestaurants", "CafeRestaurants", "CaribbeanRestaurants", "ChineseRestaurants", "CocktailLounges", "CoffeeAndTea", "Delicatessens", "DeliveryService", "Diners", "DiscountStores", "Donuts", "FastFood", "FrenchRestaurants", "FrozenYogurt", "GermanRestaurants", "GreekRestaurants", "Grocers", "Grocery", "HawaiianRestaurants", "HungarianRestaurants", "IceCreamAndFrozenDesserts", "IndianRestaurants", "ItalianRestaurants", "JapaneseRestaurants", "Juices", "KoreanRestaurants", "LiquorStores", "MexicanRestaurants", "MiddleEasternRestaurants", "Pizza", "PolishRestaurants", "PortugueseRestaurants", "Pretzels", "Restaurants", "RussianAndUkrainianRestaurants", "Sandwiches", "SeafoodRestaurants", "SpanishRestaurants", "SportsBars", "SteakHouseRestaurants", "Supermarkets", "SushiRestaurants", "TakeAway", "Taverns", "ThaiRestaurants", "TurkishRestaurants", "VegetarianAndVeganRestaurants", "VietnameseRestaurants"]
seeDoTypes = ["AmusementParks", "Attractions", "Carnivals", "Casinos", "LandmarksAndHistoricalSites", "MiniatureGolfCourses", "MovieTheaters", "Museums", "Parks", "SightseeingTours", "TouristInformation", "Zoos"]
shopTypes = ["AntiqueStores", "Bookstores", "CDAndRecordStores", "ChildrensClothingStores", "CigarAndTobaccoShops", "ComicBookStores", "DepartmentStores", "DiscountStores", "FleaMarketsAndBazaars", "FurnitureStores", "HomeImprovementStores", "JewelryAndWatchesStores", "KitchenwareStores", "LiquorStores", "MallsAndShoppingCenters", "MensClothingStores", "MusicStores", "OutletStores", "PetShops", "PetSupplyStores", "SchoolAndOfficeSupplyStores", "ShoeStores", "SportingGoodsStores", "ToyyAndGameStores", "VitaminAndSupplementStores", "WomensClothingStores"]

for index, biztype in enumerate(eatDrinkTypes):
    eatDrinkTypes[index] = [biztype, 0]
for index, biztype in enumerate(seeDoTypes):
    seeDoTypes[index] = [biztype, 0]
for index, biztype in enumerate(shopTypes):
    shopTypes[index] = [biztype, 0]
typesColumns = df[['Overall Type', 'Type']] 
eatdf = df[df['Overall Type'].str.contains('EatDrink')]
seedf = df[df['Overall Type'].str.contains('SeeDo')]
shopdf = df[df['Overall Type'].str.contains('Shop')]

import pandas as pd
from pathlib import Path
#Reading each line with accents, assuming there are only Latin and accented characters.
df = pd.read_csv('CleanedBusinessList.csv', encoding="latin1")
typesColumns = df[['Overall Type', 'Type']]
typesColumns.head(10)
eatdrinkCount = {
    "Bars" : 0,
    "BarsGrillsAndPubs" : 0,
    "BelgianRestaurants" : 0,
    "BreweriesAndBrewPubs" : 0,
    "BritishRestaurants" : 0,
    "BuffetRestaurants" : 0,
    "CafeRestaurants" : 0,
    "CaribbeanRestaurants" : 0,
    "ChineseRestaurants" : 0,
    "CocktailLounges" : 0,
    "CoffeeAndTea" : 0,
    "Delicatessens" : 0,
    "DeliveryService" : 0,
    "Diners" : 0,
    "DiscountStores" : 0,
    "Donuts" : 0,
    "FastFood" : 0,
    "FrenchRestaurants" : 0,
    "FrozenYogurt" : 0,
    "GermanRestaurants" : 0,
    "GreekRestaurants" : 0,
    "Grocers" : 0,
    "Grocery" : 0,
    "HawaiianRestaurants" : 0,
    "HungarianRestaurants" : 0,
    "IceCreamAndFrozenDesserts" : 0,
    "IndianRestaurants" : 0,
    "ItalianRestaurants" : 0,
    "JapaneseRestaurants" : 0,
    "Juices" : 0,
    "KoreanRestaurants" : 0,
    "LiquorStores" : 0,
    "MexicanRestaurants" : 0,
    "MiddleEasternRestaurants" : 0,
    "Pizza" : 0,
    "PolishRestaurants" : 0,
    "PortugueseRestaurants" : 0,
    "Pretzels" : 0,
    "Restaurants" : 0,
    "RussianAndUkrainianRestaurants" : 0,
    "Sandwiches" : 0,
    "SeafoodRestaurants" : 0,
    "SpanishRestaurants" : 0,
    "SportsBars" : 0,
    "SteakHouseRestaurants" : 0,
    "Supermarkets" : 0,
    "SushiRestaurants" : 0,
    "TakeAway" : 0,
    "Taverns" : 0,
    "ThaiRestaurants" : 0,
    "TurkishRestaurants" : 0,
    "VegetarianAndVeganRestaurants" : 0,
    "VietnameseRestaurants" : 0
}

seedoCount = {
    "AmusementParks" : 0,
    "Attractions" : 0,
    "Carnivals" : 0,
    "Casinos" : 0,
    "LandmarksAndHistoricalSites" : 0,
    "MiniatureGolfCourses" : 0,
    "MovieTheaters" : 0,
    "Museums" : 0,
    "Parks" : 0,
    "SightseeingTours" : 0,
    "TouristInformation" : 0,
    "Zoos" : 0
}

shopCount = {
    "AntiqueStores" : 0,
    "Bookstores" : 0,
    "CDAndRecordStores" : 0,
    "ChildrensClothingStores" : 0,
    "CigarAndTobaccoShops" : 0,
    "ComicBookStores" : 0,
    "DepartmentStores" : 0,
    "DiscountStores" : 0,
    "FleaMarketsAndBazaars" : 0,
    "FurnitureStores" : 0,
    "HomeImprovementStores" : 0,
    "JewelryAndWatchesStores" : 0,
    "KitchenwareStores" : 0,
    "LiquorStores" : 0,
    "MallsAndShoppingCenters" : 0,
    "MensClothingStores" : 0,
    "MusicStores" : 0,
    "OutletStores" : 0,
    "PetShops" : 0,
    "PetSupplyStores" : 0,
    "SchoolAndOfficeSupplyStores" : 0,
    "ShoeStores" : 0,
    "SportingGoodsStores" : 0,
    "ToyyAndGameStores" : 0,
    "VitaminAndSupplementStores" : 0,
    "WomensClothingStores" : 0
}

for index, row in eatdf.iterrows():
    if index == 0:
        continue
    if "," in row[1]:
        for value in row[1].split(','):
            value = value.strip()
            eatdrinkCount[str(value)] += 1
            
arrayOfValues = []
            
for key, value in eatdrinkCount.items():
    if int(value) > 50:
        arrayOfValues.append([key, value])

for index, value in enumerate(arrayOfValues):
    if value[0] == "Restaurants" or value[0] == "Grocers" or value[0] == "Grocery" or value[0] == "Supermarkets" or value[0] == "SportsBars" or value[0] == "BarsGrillsAndPubs" or value[0] == "BreweriesAndBrewPubs":
        del arrayOfValues[index]

del arrayOfValues[1]
del arrayOfValues[2]
del arrayOfValues[3]
del arrayOfValues[7]
del arrayOfValues[7]
arrayOfValues[1][0] = "Cafe"
arrayOfValues[2][0] = "Fast Food"
arrayOfValues[3][0] = "Japanese"
arrayOfValues[4][0] = "Mexican"
#del arrayOfValues["Grocery"]
#del arrayOfValues["Supermarkets"]
#del arrayOfValues["Taverns"]

#print(arrayOfValues)

keys = []
values = []

for value in arrayOfValues:
    keys.append(value[0])
    values.append(value[1])

plt.bar(keys, values,width = 0.4)
 

plt.xlabel("Restaurant Styles")
plt.ylabel("No. in Sunnyvale")
plt.title("Most popular Restaurant Styles in Sunnyvale")
plt.show()
            
#Then, do the same with seedo and shop types
#print(eatdrinkCount)


# In[7]:


for index, row in seedf.iterrows():
    if index == 0:
        continue
    if "," in row[1]:
        for value in row[1].split(','):
            value = value.strip()
            seedoCount[str(value)] += 1
            
arrayOfValues = []
            
for key, value in seedoCount.items():
    if int(value) > 10:
        arrayOfValues.append([key, value])

arrayOfValues[0][0] = "Amusement Parks"
del arrayOfValues[1]
        
print(arrayOfValues)

keys = []
values = []

for value in arrayOfValues:
    keys.append(value[0])
    values.append(value[1])

plt.bar(keys, values,width = 0.4)
 

plt.xlabel("Things To Do In Sunnyvale")
plt.ylabel("No. in Sunnyvale")
plt.title("Activity")
plt.show()


# In[8]:


for index, row in shopdf.iterrows():
    if index == 0:
        continue
    if "," in row[1]:
        for value in row[1].split(','):
            value = value.strip()
            shopCount[str(value)] += 1
            
arrayOfValues = []
            
for key, value in shopCount.items():
    if int(value) > 20:
        arrayOfValues.append([key, value])

# arrayOfValues[0][0] = "Amusement Parks"
# del arrayOfValues[1]

del arrayOfValues[2]
print(arrayOfValues)

keys = []
values = []

for value in arrayOfValues:
    keys.append(value[0])
    values.append(value[1])

plt.bar(keys, values,width = 0.4)
 

plt.xlabel("Most Popular Shops In Sunnyvale")
plt.ylabel("No. in Sunnyvale")
plt.title("Shop Type")
plt.show()


# ## Alternate program, utilizing the spreadsheet and google's maps API.
# The only prerequisite is to have a Google Places API Key, which has an average of $300 credit for the free trial. After a few runs, the free trial will have ran out and you would need to create another free trial. The API Key should be stored in a text file titled ``api_key.txt``.
# 
# As we only have three key pieces of information, the address, name of business, and phone number, it's unreliable and most of the time incorrect. Since we are using the name of the business as another factor, it could autocomplete an incorrect address or business. The address could also not be associated with any specific business, which it would come with just ``subpremise`` as the result.

# In[ ]:


def placeReq(extractedAddress, businessName, phoneNumber, searchMethod = "address"):
    if searchMethod == "address":
        #If you are only going off of the address
        url = urllib.parse.quote_plus(extractedAddress)
        api_key = open("api_key.txt", "r").read()

        findPlaceLink = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input="+url+"&inputtype=textquery&fields=business_status,formatted_address,name,place_id,plus_code,type,geometry&key="+api_key
    if searchMethod == "name":
        #HIGHLY NOT RECOMMENDED, AS BUSINESS NAME MIGHT HAVE MORE PRIORITY OVER THE ADDRESS
        #If you are going off of the name and address
        url = urllib.parse.quote_plus(extractedAddress)
        url = url + " " + urllib.parse.quote_plus(businessName)
        api_key = open("api_key.txt", "r").read()
        
        findPlaceLink = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input="+url+"&inputtype=textquery&fields=business_status,formatted_address,name,place_id,plus_code,type,geometry&key="+api_key
    if searchMethod == "phone":
        #If you are only going off of the phone number
        if "+" in phoneNumber:
            newUrl = urllib.parse.quote_plus(phoneNumber)
        else:
            newUrl = urllib.parse.quote_plus("+1 " + phoneNumber)
        api_key = open("api_key.txt", "r").read()
        
        findPlaceLink = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input="+newUrl+"&inputtype=phonenumber&fields=business_status,formatted_address,name,place_id,plus_code,type,geometry&key="+api_key
    payload = {}
    headers = {}
    response = requests.request("GET", findPlaceLink, headers=headers, data=payload)
    
    if "\"status\" : \"OK\"" not in (response.text):
        if "ZERO_RESULTS" in (response.text):
            if searchMethod == "phone":
                combinedValue = placeReq(extractedAddress, businessName, phoneNumber, searchMethod = "name")
            #CONSIDER REMOVING BELOW ELIF, AS NAME IS EXTREMELY INNACURATE ABOUT EXACT BUSINESS:
            #Pros: Uses both businessName and extractedAddress, if name/address are related to field, google searching does help with finding company related to it.
            #Cons: Not guaranteed to have the correct business nor location, only limited to sunnyvale area
            elif searchMethod == "name":
                combinedValue = placeReq(extractedAddress, businessName, phoneNumber, searchMethod = "address")
            else:
                combinedValue = ""
        if "UNKNOWN_ERROR" in (response.text):
            print("unknown error")
            combinedValue = ""
        if "OVER_QUERY_LIMIT" in (response.text):
            print("over query limit")
            combinedValue = ""
        if "INVALID_REQUEST" in (response.text):
            print("malformed request")
            combinedValue = ""
    else:
        place_id = (response.text).split("place_id\" : \"")[1].split("\",")[0]
        business_name = (response.text).split("name\" : \"")[1].split("\",")[0]
        types = "\""+(response.text).split("types\" : [")[1].split("]")[0].strip().replace("\"", "")+"\""
        
        try:
            location = (response.text).split("location\": {")[1].split(",")
            latitude = location[0].split(":")[1].strip()
            longitude = location[1].split(":")[1].split("}")[0].strip()
        except:
            latitude = ""
            longitude = ""
        
        combinedValue = []
        combinedValue.append(place_id)
        combinedValue.append(business_name)
        combinedValue.append(types)
        combinedValue.append(longitude)
        combinedValue.append(latitude)

        return combinedValue
    
    return combinedValue


# In[ ]:


import urllib.parse
import requests
import csv

import time
seconds = time.time()
local_time = time.ctime(seconds)
print("Initialization time: ", local_time)

totalLines = []
with open('SVChamberofCommerce-Non-HomeBasedbusinesses.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        totalLines.append(row)

totalLines[0].append("Google Place ID")
totalLines[0].append("Google Place Name")
totalLines[0].append("Google Business Types")
totalLines[0].append("Longitude")
totalLines[0].append("Latitude")

for index, row in enumerate(totalLines):
    print(str(((index+1)/len(totalLines))*100 ) + "% completed")
    if index == 0:
        continue
    #Get business info
    #row is now an array which should be constant indexing
    address = row[3] + ", " + row[4]
    #GOOGLE DOESNT ACCEPT PO BOX SEARCHES
    if "PO BOX" in address:
        continue
    name = row[1]
    phone = row[6]
    if phone == "":
        businessInfo = placeReq(address, name, phone)
    else:
        businessInfo = placeReq(address, name, phone, searchMethod = "phone")
        
    if businessInfo == "":
        continue
    
    print(businessInfo[1])
    
    for value in businessInfo:
        row.append(value)
    
    #Fully updating the row after all analysis
    totalLines[index] = row

seconds = time.time()
end_time = time.ctime(seconds)
print("Final time time: ", end_time)


# In[ ]:


output = open("SVChamberofCommerce-Non-HomeBasedbusinessesSearched.csv", "w")

for rw in totalLines:
    concatLine = ""
    for index, value in enumerate(rw):
        if index+1 == len(rw):
            value = value.replace("\n", " ")
            if "," in value:
                value = "\"" + value + "\""
                if '""' in value:
                    value = value.replace('""', '"')
            value = value + "\n "
        else:
            value = value.replace("\n", " ")
            if "," in value:
                value = "\"" + value + "\""
                if '""' in value:
                    value = value.replace('""', '"')
            value = value + ","
        print(value)
        try:
            output.write(value)
        except UnicodeEncodeError:
            print("encodingError")
            value = ","
            output.write(value)
        
output.close()


# In[ ]:


print("done with coalescing the data with no errors")

