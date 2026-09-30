import json
import math

# Load existing locations to ensure coverage
with open('data/units.json') as f:
    units = json.load(f)
with open('data/incidents.json') as f:
    incidents = json.load(f)

# Collect all unit and incident locations
locations = []
for u in units:
    locations.append((u['id'], u['latitude'], u['longitude']))
for i in incidents:
    locations.append((i['id'], i['latitude'], i['longitude']))

# Create a grid of nodes covering the bounding box
# Lat range: 21.150 to 21.200 (approx)
# Lon range: 72.810 to 72.850 (approx)

lats = [21.155, 21.175, 21.195]
lons = [72.815, 72.830, 72.845]

nodes = {}
node_idx = 1
for lat in lats:
    for lon in lons:
        nid = f"NODE-{node_idx:02d}"
        nodes[nid] = (lat, lon)
        node_idx += 1

def haversine_km(lat1, lon1, lat2, lon2):
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

roads = []
road_idx = 1

def add_road(nid1, nid2, speed=40):
    global road_idx
    dist = haversine_km(nodes[nid1][0], nodes[nid1][1], nodes[nid2][0], nodes[nid2][1])
    roads.append({
        "id": f"ROAD-{road_idx:03d}",
        "name": f"Segment {nid1}-{nid2}",
        "from_node": nid1,
        "to_node": nid2,
        "from_lat": nodes[nid1][0],
        "from_lon": nodes[nid1][1],
        "to_lat": nodes[nid2][0],
        "to_lon": nodes[nid2][1],
        "distance_km": round(dist, 3),
        "speed_kmh": speed,
        "blocked": False,
        "delay_minutes": 0.0
    })
    road_idx += 1
    # Bi-directional?
    roads.append({
        "id": f"ROAD-{road_idx:03d}",
        "name": f"Segment {nid2}-{nid1}",
        "from_node": nid2,
        "to_node": nid1,
        "from_lat": nodes[nid2][0],
        "from_lon": nodes[nid2][1],
        "to_lat": nodes[nid1][0],
        "to_lon": nodes[nid1][1],
        "distance_km": round(dist, 3),
        "speed_kmh": speed,
        "blocked": False,
        "delay_minutes": 0.0
    })
    road_idx += 1

# Connect grid horizontally and vertically
# Grid is 3x3
grid_nodes = list(nodes.keys())
for i in range(3):
    for j in range(3):
        idx = i*3 + j
        # Horizontal to the right
        if j < 2:
            add_road(grid_nodes[idx], grid_nodes[idx+1])
        # Vertical down
        if i < 2:
            add_road(grid_nodes[idx], grid_nodes[idx+3])

# Add a diagonal road to provide an alternative route across the center
add_road(grid_nodes[0], grid_nodes[4]) # 0,0 to 1,1
add_road(grid_nodes[4], grid_nodes[8]) # 1,1 to 2,2
add_road(grid_nodes[2], grid_nodes[4]) # 0,2 to 1,1
add_road(grid_nodes[4], grid_nodes[6]) # 1,1 to 2,0

# Write out the roads.json
with open('data/roads.json', 'w') as f:
    json.dump(roads, f, indent=2)

print(f"Generated {len(nodes)} nodes and {len(roads)} road segments.")
