import pandas as pd
import math
from geopy import distance
import networkx as nx
import itertools
import time
import sys

ROOT_DIR = '' # don't change this unless you want to put stuff elsewhere

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
station_df = pd.read_csv('station_df.csv')
station_durs = [(a[1], a[2], a[3][1:-1].replace(' ', '').split(',')) for a in pd.read_csv('station_durs_df.csv').values.tolist()]
G_speed = nx.read_gml('graph_speed_priority.txt')
G_transfer = nx.read_gml('graph_transfer_priority.txt')

def s_to_hm(s):
    return str(int(s//3600)) + 'h ' + str(int((s-3600*(s//3600))//60)) + 'm' if s//3600 > 0 else str(s//60) + 'min'



def run_analysis(G, station_durs, origin_st, dest_st, transfer_time):
    station_durs_dict = {(station1+'_DEP', station2+'_ARR'): {'distance': int(stats[0]), 'duration': int(stats[1]), 'avg_speed': int(stats[3])} for station1, station2, stats in station_durs}
    detail_station_set = set([b for a in [(station1, station2) for station1, station2, stats in station_durs] for b in a])

    detailed_st_per_st = {}
    for detailed_st in detail_station_set:
        station, line, exploc = detailed_st.split('_')
        detailed_st_per_st[station] = detailed_st_per_st[station] + [detailed_st] if station in detailed_st_per_st else [detailed_st]

    origin_set = set([st + '_DEP' for st in detailed_st_per_st[origin_st]])
    dest_set = set([st + '_ARR' for st in detailed_st_per_st[dest_st]])

    best_segments = None
    best_dur = float('inf')
    best_transfers = None

    for dest_st in dest_set:
        dur, path = nx.multi_source_dijkstra(G, origin_set, dest_st)
        if dur < best_dur:
            segments, line_list, transfers = {}, [path[0].split('_')[1]], []
            beg_station = origin_st
            cum_duration = 0
            cum_distance = 0
            stops = []
            for i in range(len(path)-1):
                station1, line1, type1, deparr1 = path[i].split('_')
                station2, line2, type2, deparr2 = path[i+1].split('_')
                if deparr1 == 'DEP' and deparr2 == 'ARR': # travel dist
                    cum_duration += station_durs_dict[(path[i], path[i+1])]['duration']
                    cum_distance += station_durs_dict[(path[i], path[i+1])]['distance']
                    stops.append((station2, station_durs_dict[(path[i], path[i+1])]['duration'], station_durs_dict[(path[i], path[i+1])]['distance']))
                elif deparr1 == 'ARR' and deparr2 == 'DEP':
                    if line1 != line2 or type1 != type2:
                        end_station = station1
                        segments[(beg_station, end_station)] = {'type': 'travel', 'stops': stops, 'line': line1 + ' ' + type1, 'distance': cum_distance, 'duration': cum_duration}
                        beg_station = end_station
                        cum_distance, cum_duration, stops = 0, 0, []
                        transfers.append(station1)
                        if line1 != line2: # transfer between two lines
                            line_list.append(line2)
                            segments[(station1, station2)] = {'type': 'reg_transfer', 'lines': (line1 + ' ' + type1, line2 + ' ' + type2), 'distance': 0, 'duration': transfer_time}
                        elif type1 != type2: # local-exp transfer
                            segments[(station1, station2)] = {'type': 'le_transfer', 'lines': (line1 + ' ' + type1, line2 + ' ' + type2), 'distance': 0, 'duration': transfer_time}
                    else:
                        cum_duration += TIME_AT_STATION
                else:
                    print('whats going on')

            # add the last leg
            end_station = station2
            segments[(beg_station, end_station)] = {'type': 'travel', 'stops': stops, 'line': line1 + ' ' + type1, 'distance': cum_distance, 'duration': cum_duration}

            best_segments = segments
            best_dur = dur
            best_transfers = transfers


    counter = 0
    for segment in best_segments:
        station1, station2 = segment
        counter += 1
        if best_segments[segment]['type'] == 'travel':
            stops = best_segments[segment]['stops']
            print(str(counter), 'Take the', best_segments[segment]['line'], 'line from', station1, 'to', station2, '(' + str(best_segments[segment]['distance']) + 'km' + ' '  + s_to_hm(best_segments[segment]['duration']) + ')')
            for stop, dur, dist in stops:
                print('    ', stop, str(dist)+'km', s_to_hm(dur))
        else:
            print(str(counter), 'Transfer at', station1, 'from the', best_segments[segment]['lines'][0], 'line to the', best_segments[segment]['lines'][1], 'line')
    print()  
    print('Transfers:', len(transfers))
    print('Total time:', s_to_hm(best_dur - (transfer_time - TRANSFER_TIME_1)*len(transfers)))




origin_st = sys.argv[1]
dest_st = sys.argv[2]

origin_coords = (station_df.set_index('station').at[origin_st, 'lat'], station_df.set_index('station').at[origin_st, 'long'])
dest_coords = (station_df.set_index('station').at[dest_st, 'lat'], station_df.set_index('station').at[dest_st, 'long'])

print(origin_st, 'to', dest_st)
print('Straight line distance:', int(distance.distance(origin_coords, dest_coords).km), 'km')
print('By plane at 800kmh:', s_to_hm(int(3600*distance.distance(origin_coords, dest_coords).km/800)))
print()
print('Transfer time:', TRANSFER_TIME_1_M, 'minutes')
print('Time at station:', TIME_AT_STATION_M, 'minutes')
print('Train speed:', MAX_SPEED_KMH, 'kmh')

print('\n\n')
print('Prioritize speed')
run_analysis(G_speed, station_durs, origin_st, dest_st, TRANSFER_TIME_1)

print('\n\n')
print('Prioritize less transfers')
run_analysis(G_transfer, station_durs, origin_st, dest_st, TRANSFER_TIME_2)


