# MetroWorld Directions

Welcome to directions for MetroWorld! If you're reading this, you probably already know of my post on NUMTOTS and/or Reddit earlier of a "world metro" concept map I designed (https://www.reddit.com/r/MapPorn/comments/hf7w8q/new_take_on_the_concept_of_a_world_metro/) I know people (including myself) were wondering how good this system was in terms of efficiency and speed, so I decided that I wanted to take some time to make an algorithm, much like Google Maps, to figure out the best route and best time to get from one city to another. My idea is to have each station be designated "local" or "express," much like in the NYC subway, so that less populated cities will get less service and more populated cities get more direct routes with less stops. So I've made this Python script to do just that! I didn't want to put in enough time to make a GUI website, so if any of you want to do that with this code, feel free to do so (but let me know)! After downloading/cloning this repo, follow the instructions below.

## Step 1: Download dependencies

You'll need Python 3 to run this, in addition to Python 3 modules `pandas`, `geopy`, and `networkx`. You can install them with `pip`.

## Step 1: Change constants

Because this is very hypothetical, especially regarding the train's speed, there are some constants that you can adjust yourself. Open the constants.txt file and change any of the constants. They are:

- Max speed: Maximum speed of the train in km/h. Default is 1200kmh, because from my very cursory research that's how fast Hyperloops are supposed to be able to travel in the future.
- Acceleration: A number in meters per second squared that represents the CONSTANT acceleration AND de-acceleartion of the train. 9.8m/s^2 is 1G. The default is 3, which goes from 0 to 100km/h in about 9 seconds, and accelerates to 1200km/h in just under 2 minutes.
- Time at station: The number of minutes the train stops at a station before continuing on.
- Transfer time: The number of minutes total it takes from getting off of one train to getting on another train at the same station, including walking time through the station and waiting for the next train.
- Population cutoff for an express station. An express station is meant to only serve the biggest cities, so all cities below this threshold and are not a transfer station will be local. All cities with a population above this threshold AND transfer stations will be express.

## Step 2: Build the network

The MetroWorld network is represented by a graph (set of vertices and edges), so running the below will create that network. It will also join each station to its respective city, its population, and the country. The metro station information is in `metro_data.txt`, and city and country mapping information is in `worldcities.csv` and `iso_3166_country_mapping.csv`.

- Run `python3 build_network.py`. It should take a few seconds, and output some information about the stations.

## Step 3: Enter your route!

Now you're ready to enter your route(s)! You can do this as many times with just building the network once. Run the below:

- Run `python3 find_route.py "City 1" "City 2"`. The two cities do not need to be in quotes if they do not contain spaces. They also need to be spelled correctly. At this point, you should have a `station_df.csv` file, which has a list of all the stations, so reference that if you're getting errors because of spelling. This script will run Dijkstra's shortest path algorithm to find and return your shortest path and some additional stats. Specifically, you'll see the best path optimized by speed, and a best path optimized by number of transfers, since some people would prioritize less transfers than others.


If you find errors, FB message me or email me at alexanderguo99@gmail.com. I wrote this pretty hastily so I have no idea if things actually always work properly. 
