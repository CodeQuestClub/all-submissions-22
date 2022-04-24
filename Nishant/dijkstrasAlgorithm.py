from turtle import distance


def dijkstrasAlgorithm(map_data, start_point):
    # Step 1: Generate edges - for this we will just use orthogonally connected cells.
    adj = {}
    idx = {}
    distance = {}
    points = []
    counter = 0
    h, w = len(map_data), len(map_data[0])
    
    for y in range(h):
        for x in range(w):
            adj[(x, y)] = []
            
            if map_data[y][x] == "W": continue
            
            points.append((x, y))
            idx[(x, y)] = counter
            counter += 1
    
    for x, y in points:
        for a, b in [(y+1, x), (y-1, x), (y, x+1), (y, x-1)]:
            if 0 <= a < h and 0 <= b < w and map_data[a][b] != "W":
                adj[(x, y)].append((b, a, 1))
                
    # Step 2: Run Dijkstra's         
    import heapq
    expanded = [False]*len(points)
    queue = []
    heapq.heappush(queue, (0, start_point))
    while queue:
        d, (a, b) = heapq.heappop(queue)
        
        if expanded[idx[(a, b)]]: continue
        
        expanded[idx[(a, b)]] = True
        distance[(a, b)] = d
        for j, k, d2 in adj[(a, b)]:
            if not expanded[idx[(j, k)]]:
                heapq.heappush(queue, (
                    d + d2,
                    (j, k)
                ))
    
    return distance