import json
import math

def haversine_km(lat1, lon1, lat2, lon2):
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

with open('data/roads.json') as f:
    roads = json.load(f)
with open('data/units.json') as f:
    units = json.load(f)
with open('data/incidents.json') as f:
    incidents = json.load(f)

# Collect all distinct nodes (by coordinate)
nodes = set()
for r in roads:
    nodes.add((r['from_lat'], r['from_lon']))
    nodes.add((r['to_lat'], r['to_lon']))

print("Nodes in road graph:", len(nodes))
print("Total road segments (edges):", len(roads))

# Check how many units are actually ON a road node, or can connect to one
for u in units:
    closest_dist = min([haversine_km(u['latitude'], u['longitude'], n[0], n[1]) for n in nodes])
    print(f"Unit {u['id']} closest road node is {closest_dist:.2f} km away.")

for i in incidents:
    closest_dist = min([haversine_km(i['latitude'], i['longitude'], n[0], n[1]) for n in nodes])
    print(f"Incident {i['id']} closest road node is {closest_dist:.2f} km away.")
