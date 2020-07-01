import pandas as pd
import math
from geopy import distance
import networkx as nx
import itertools
import time

# NO LOOPS!!! CODE BREAKS IF THERE ARE LOOPS!!

ROOT_DIR = '' # don't change this unless you want to put stuff elsewhere
# pd.options.display.max_rows = 999

t0 = time.time()
with open(ROOT_DIR + 'constants.txt', 'r') as f:
    constants = [float(a.strip().split(' ')[2]) for a in f.readlines()]

MAX_SPEED_KMH, ACCELERATION, TIME_AT_STATION_M, TRANSFER_TIME_1_M, EXPRESS_POP_CUTOFF = constants
TRANSFER_TIME_2_M = 240 # minutes

MAX_SPEED = MAX_SPEED_KMH/3.6 # m/s2
ACC_TIME = MAX_SPEED/ACCELERATION # s
ACC_DISTANCE = ACC_TIME * MAX_SPEED / 2 # d = 1/2 at^2
TIME_AT_STATION = TIME_AT_STATION_M * 60 # s
TRANSFER_TIME_1 = TRANSFER_TIME_1_M * 60 # s
TRANSFER_TIME_2 = TRANSFER_TIME_2_M * 60 # s

with open(ROOT_DIR + 'metro_data.txt', 'r') as f:
    lines_raw = [a.strip().replace(':', '') for a in f.readlines()]
    
line_dict = {}
station_set = set()
next_is_stations_mainline = False
next_is_stations_branch = False
current_line_name = ''
current_branch_name = ''

# add to line_dict and station_set
for text_line in lines_raw:
    if text_line.split(' ')[-1] == 'LINE':
        current_line_name = text_line.split(' ')[0]
        line_dict[current_line_name] = None
        next_is_stations_mainline = True
    elif next_is_stations_mainline == True:
        line_dict[current_line_name] = text_line.split(',')
        next_is_stations_mainline = False
        station_set = station_set.union(set(text_line.split(',')))
    elif text_line.split(' ')[0] == 'BRANCH':
        current_branch_name = ' '.join(text_line.split(' ')[3:]) + '_' + current_line_name + '_' + text_line.split(' ')[1]
        line_dict[current_branch_name] = None
        next_is_stations_branch = True
    elif next_is_stations_branch == True:
        line_dict[current_branch_name] = text_line.split(',')
        next_is_stations_branch = False
        station_set = station_set.union(set(text_line.split(',')))

line_totals = {}
for line in line_dict:
    if '_' not in line: # main line
        line_totals[line] = line_totals[line] + len(line_dict[line]) if line in line_totals else len(line_dict[line])
    else:
        actual_line = line.split('_')[1]
        line_totals[actual_line] = line_totals[actual_line] + len(line_dict[line]) if actual_line in line_totals else len(line_dict[line])

station_df = pd.DataFrame(sorted(list(station_set)), columns=['station'])

country_map = pd.read_csv(ROOT_DIR + 'iso_3166_country_mapping.csv')[['alpha-3', 'name', 'region', 'sub-region']]
city_map = pd.read_csv(ROOT_DIR + 'worldcities.csv')[['city_ascii', 'lat', 'lng', 'iso3', 'population']]
# station_df

# too many duplicates otherwise
city_map_small = city_map[(city_map['population'] > 60000) | (city_map['city_ascii'].isin(['Basse-Terre', 'Banjul', 'Monaco', 'Santa Cruz de la Sierra']))]

station_df = station_df.merge(city_map_small, left_on='station', right_on='city_ascii', how='left').drop(columns=['city_ascii'])
station_df = station_df.merge(country_map, left_on='iso3', right_on='alpha-3', how='left').drop(columns=['alpha-3'])

station_df = station_df.rename(columns={'iso3': 'country_code', 'name': 'country_territory', 'lng': 'long', 'sub-region': 'sub_region'})

print('Total stations:', station_df.shape[0])
print('Stations in urban areas with pop >5m:', station_df[station_df['population'] > 5000000].shape[0])
print('Stations in urban areas with pop >2m:', station_df[station_df['population'] > 2000000].shape[0])
print('Stations in urban areas with pop >1m:', station_df[station_df['population'] > 1000000].shape[0])
print('Stations in urban areas with pop >500k:', station_df[station_df['population'] > 500000].shape[0])
print('Stations in urban areas with pop >100k:', station_df[station_df['population'] > 100000].shape[0])
print('Total population in urban area of stations:', station_df['population'].sum())
print()



def get_next_stations_from_line_dict(line_dict, station_dict, field):
    for line in line_dict:
        for i, station in enumerate(line_dict[line]):
            if '_' not in line: # main line
                station_dict[station][field] += [line_dict[line][i-1] + '_' + line] if i > 0 else [] # station before
                station_dict[station][field] += [line_dict[line][i+1] + '_' + line] if i < len(line_dict[line])-1 else [] # station after
            else: # branch line
                split_station, main_line, direction = line.split('_')
                station_dict[station]['lines'].add(main_line)
                if i == 0:
#                     print(line_dict[line])

#                     ml_station = line_dict[main_line]
#                     ml_split_index = ml_station.index(split_station)
                    
#                     previous_station = ml_station[ml_split_index-1] if direction == 'R' else ml_station[ml_split_index+1]
#                     print(previous_station, split_station)
#                     station_dict[previous_station][field] += [split_station + '_' + main_line]
#                     station_dict[split_station][field] += [previous_station + '_' + main_line]
                    station_dict[station][field] += [split_station + '_' + main_line]
                    station_dict[split_station][field] += [station + '_' + main_line]
                station_dict[station][field] += [line_dict[line][i-1] + '_' + main_line] if i > 0 else [] # station before
                station_dict[station][field] += [line_dict[line][i+1] + '_' + main_line] if i < len(line_dict[line])-1 else [] # station after
    return station_dict

def dict_to_df(row):
    row['lines'] = ','.join(station_dict[row['station']]['lines'])
    row['line_num'] = len(station_dict[row['station']]['lines'])
    row['transfer'] = True if row['line_num'] > 1 else False
    row['type'] = 'EXPRESS' if row['transfer'] or row['population'] > EXPRESS_POP_CUTOFF else 'LOCAL'
    return row


def dict_to_df_station_list(row):
    row['next_local_stations'] = ','.join(station_dict[row['station']]['next_local_stations'])
    row['next_express_stations'] = ','.join(station_dict[row['station']]['next_express_stations']) if station_dict[row['station']]['next_express_stations'] != [] else '' 
    return row



station_dict = {station: {'lines': set(), 'next_local_stations': [], 'next_express_stations': []} for station in station_set}


# add lines to station dict
for line in line_dict:
    for i, station in enumerate(line_dict[line]):
        if '_' not in line: # main line
            station_dict[station]['lines'].add(line)
        else: # branch line
            split_station, main_line, direction = line.split('_')
            station_dict[station]['lines'].add(main_line)

            
            
            
# add lines, line_num, transfer, and type (express/local) to dataframe
station_df = station_df.apply(dict_to_df, axis=1)



# generate a dict of express stations to get express stations
express_line_dict = {}
express_inters = {}
for line in line_dict:
    new_line_list = []
    temp_inters = []
    
    if '_' not in line: # main line
        previous_express = None
        for station in line_dict[line]:
            if station_df.set_index('station').at[station, 'type'] == 'EXPRESS':
                new_line_list.append(station)
                
                # intermediate stations
                if previous_express is not None: # end and start
                    temp_inters.append(station+'_'+line)
                    express_inters[(previous_express+'_'+line, station+'_'+line)] = temp_inters
                temp_inters = [station+'_'+line] # start
                previous_express = station
            else:
                temp_inters.append(station+'_'+line)

    else: # branch line
        split_station, main_line, direction = line.split('_')
        
        # split station is an express station = normal
        if station_df.set_index('station').at[split_station, 'type'] == 'EXPRESS':
            previous_express = split_station

        # need to backtrack and change name of line to nearest express station
        else: 
            split_station_i = line_dict[main_line].index(split_station)
            earlier_stations = line_dict[main_line][split_station_i:] if direction == 'L' else line_dict[main_line][0:split_station_i][::-1]
            for sstation in earlier_stations:
                if station_df.set_index('station').at[sstation, 'type'] == 'EXPRESS':
                    split_station = sstation
                    break # last express station found
        
        previous_express = split_station
        temp_inters = [previous_express+'_'+main_line]
        for station in line_dict[line]:
            if station_df.set_index('station').at[station, 'type'] == 'EXPRESS':
                new_line_list.append(station)

                # intermediate stations
                temp_inters.append(station+'_'+main_line)
                express_inters[(previous_express+'_'+main_line, station+'_'+main_line)] = temp_inters
                temp_inters = [station+'_'+main_line] # start
                previous_express = station
            else:
                temp_inters.append(station+'_'+main_line)
    
        line = split_station + '_' + main_line + '_' + direction            
    express_line_dict[line] = new_line_list


# get next local stations
get_next_stations_from_line_dict(line_dict, station_dict, 'next_local_stations')
get_next_stations_from_line_dict(express_line_dict, station_dict, 'next_express_stations')


station_df = station_df.apply(dict_to_df_station_list, axis=1)

print('Total transfer stations:', station_df[station_df['transfer']].shape[0])
print('Hub stations (3 lines):', station_df[station_df['line_num'] == 3].shape[0])
print('Superhub stations (4+ lines):', station_df[station_df['line_num'] >= 4].shape[0])
print('Express stations:', station_df[station_df['type'] == 'EXPRESS'].shape[0], 'out of', station_df.shape[0])
print()

station_df.to_csv('station_df.csv')


# get distances + times between each pair of adjacent stations - edges of the graph!

def get_time_from_dist(dist_km): # in km
    '''
    Returns tuple (dist, time, max_speed, avg_speed) for time in seconds,
    max speed reached in km/h, and average speed for trip im km/h
    '''
    dist = dist_km*1000
    if dist > 2 * ACC_DISTANCE: # can fully accelerate to maximum speed
        max_speed_dist = dist - 2*ACC_DISTANCE
        time = 2*ACC_TIME + max_speed_dist/MAX_SPEED
        return int(dist_km), int(time), int(MAX_SPEED_KMH), int(dist_km/(time/3600))
    else: # distance too short, cannot accelerate fully
        acc_dist = dist/2
        acc_time = math.sqrt(2 * acc_dist/ACCELERATION) # from d = 1/2 at^2
        time = acc_time * 2
        return int(dist_km), int(time), int(acc_time * ACCELERATION * 3.6), int(dist_km/(time/3600))
    
    
station_durs = []

for i, row in station_df.iterrows():
    station_df_set = station_df.set_index('station')
    station_strip = row['station']
    all_station_lines = [station_strip + '_' + line for line in station_df_set.at[station_strip, 'lines'].split(',')]
    station_coord = (station_df_set.at[station_strip, 'lat'], station_df_set.at[station_strip, 'long'])
    next_local = row['next_local_stations'].split(',')
    next_express = row['next_express_stations'].split(',')
    for next_st in next_local:
        next_st_strip, next_line = next_st.split('_')
        next_coord = (station_df_set.at[next_st_strip, 'lat'], station_df_set.at[next_st_strip, 'long'])
        for station in all_station_lines:
            station_line = station.split('_')[1]
            if station_line == next_line: 
                station_durs.append((station+'_'+'LOCAL', next_st+'_'+'LOCAL', get_time_from_dist(distance.distance(station_coord, next_coord).km)))
    if next_express == ['']:
        continue
    for next_st in next_express:
        next_st_strip, next_line = next_st.split('_')
        for station in all_station_lines:
            station_line = station.split('_')[1]
            if station_line == next_line:
                next_inters = express_inters[(station, next_st)] if (station, next_st) in express_inters else express_inters[(next_st, station)]
                total_exp_dist = 0
                for j in range(len(next_inters)-1): # add up distances through intermediate stations
                    station1, station2 = next_inters[j], next_inters[j+1]
                    station1_strip, station1_line = station1.split('_')
                    station2_strip, station2_line = station2.split('_')
                    station1_coord = (station_df_set.at[station1_strip, 'lat'], station_df_set.at[station1_strip, 'long'])
                    station2_coord = (station_df_set.at[station2_strip, 'lat'], station_df_set.at[station2_strip, 'long'])
                    total_exp_dist += distance.distance(station1_coord, station2_coord).km
                station_durs.append((station+'_'+'EXPRESS', next_st+'_'+'EXPRESS', get_time_from_dist(total_exp_dist)))


# create the graph!!

def create_graph(transfer_time):
    G = nx.DiGraph()

    travel_edges = [(station1+'_DEP', station2+'_ARR', stats[1]) for station1, station2, stats in station_durs]
    G.add_weighted_edges_from(travel_edges)

    # time at station
    detail_station_set = set([b for a in [(station1, station2) for station1, station2, stats in station_durs] for b in a])
    G.add_weighted_edges_from([(station+'_ARR', station+'_DEP', TIME_AT_STATION) for station in detail_station_set])

    for i, row in station_df.iterrows():
        station = row['station']
        lines = row['lines'].split(',')
        if row['line_num'] > 1:
            all_line_pairs = list(itertools.permutations(lines, 2))
            # transfer between lines
            if row['type'] == 'EXPRESS':
                for line1, line2 in all_line_pairs:
                    G.add_weighted_edges_from([(station+'_'+line1+'_LOCAL_ARR', station+'_'+line2+'_LOCAL_DEP', transfer_time)])
                    G.add_weighted_edges_from([(station+'_'+line1+'_EXPRESS_ARR', station+'_'+line2+'_EXPRESS_DEP', transfer_time)])
                    G.add_weighted_edges_from([(station+'_'+line1+'_LOCAL_ARR', station+'_'+line2+'_EXPRESS_DEP', transfer_time)])
                    G.add_weighted_edges_from([(station+'_'+line1+'_EXPRESS_ARR', station+'_'+line2+'_LOCAL_DEP', transfer_time)])
            else:
                for line1, line2 in all_line_pairs:
                    G.add_weighted_edges_from([(station+'_'+line1+'_LOCAL_ARR', station+'_'+line2+'_LOCAL_DEP', transfer_time)])
        # express-local transfer
        if row['type'] == 'EXPRESS':
            for line in lines:
                G.add_weighted_edges_from([(station+'_'+line+'_LOCAL_ARR', station+'_'+line+'_EXPRESS_DEP', transfer_time)])
                G.add_weighted_edges_from([(station+'_'+line+'_EXPRESS_ARR', station+'_'+line+'_LOCAL_DEP', transfer_time)])

    return G

G_speed = create_graph(TRANSFER_TIME_1)
G_transfer = create_graph(TRANSFER_TIME_2)

# nx.write_multiline_adjlist(G_speed, ROOT_DIR + 'graph_speed_priority.txt')
# nx.write_multiline_adjlist(G_transfer, ROOT_DIR + 'graph_transfer_priority.txt')
nx.write_gml(G_speed, ROOT_DIR + 'graph_speed_priority.txt')
nx.write_gml(G_transfer, ROOT_DIR + 'graph_transfer_priority.txt')

pd.DataFrame(station_durs).to_csv('station_durs_df.csv')


by_region = station_df[['region', 'station']].groupby('region').count().reset_index().sort_values('station', ascending=False)
print('By ISO-3166 Region:')
print(by_region.reset_index().drop(columns=['index']))
print()

by_subregion = station_df[['region', 'sub_region', 'station']].groupby(['region', 'sub_region']).count().reset_index().sort_values('station', ascending=False)
print('By ISO-3166 Subregion:')
print(by_subregion.reset_index().drop(columns=['index']))
print()

by_country = station_df[['country_territory', 'station']].groupby('country_territory').count().reset_index().sort_values('station', ascending=False)
print('Total countries/territories:', by_country.shape[0])
print('By ISO-3166 Country/Territory, countries/territories with more than 2 stations:')
country_1 = by_country[by_country['station'] > 2]
print(country_1.reset_index().drop(columns=['index']))
print()

print('Graphs created in', round(time.time()-t0, 1), 'seconds')
