"""Step 3: for a water level h -> cut roads, evacuation routes, shelter loads.

Pure pandas + networkx, so the same file runs in Colab AND in the backend.
"""
import json
import numpy as np
import pandas as pd
import networkx as nx

MAX_TRAVEL_S = 45 * 60     # ignore shelters more than 45 minutes away
MIN_FLOODED_SHARE = 0.02   # a cell is 'at risk' if >= 2% of it is under water
OVERFLOW_COST = 10_000     # cost of leaving people unassigned (very high)

class Engine:
    def __init__(self, data_dir):
        self.nodes = pd.read_csv(f"{data_dir}/nodes.csv").set_index("id")
        self.edges = pd.read_csv(f"{data_dir}/edges.csv")
        self.shelters = pd.read_csv(f"{data_dir}/shelters.csv")
        self.origins = json.load(open(f"{data_dir}/origins.json"))
        self.meta = json.load(open(f"{data_dir}/meta.json"))
        
        self.G = nx.Graph()
        self.G.add_weighted_edges_from(
            self.edges[["u", "v", "travel_time"]].itertuples(index=False), weight="w")
            
        self.coord = {i: (round(r.lon, 5), round(r.lat, 5)) for i, r in self.nodes.iterrows()}

    # ------------------------------------------------------------------ helpers

    def _surviving_graph(self, h):
        flooded = set(self.nodes.index[self.nodes.hand <= h])
        Gh = self.G.copy()
        Gh.remove_nodes_from(flooded)
        cut = self.edges[self.edges.u.isin(flooded) | self.edges.v.isin(flooded)]
        return Gh, cut

    @staticmethod
    def _path(pred, target):
        path = [target]
        while pred.get(path[-1]):
            path.append(pred[path[-1]][0])
        return path[::-1]

    # ------------------------------------------------------------------ main

    def run(self, h):
        h = float(h)
        Gh, cut = self._surviving_graph(h)
        
        sh = self.shelters.copy()
        sh["usable"] = (sh.hand > h) & sh.node.isin(list(Gh.nodes))
        usable = sh[sh.usable]
        
        shelter_at_node = {}
        for r in usable.itertuples():
            shelter_at_node.setdefault(r.node, []).append(r.id)
            
        origins_out, reach, isolated = [], {}, 0
        for o in self.origins:
            share = float(np.mean(np.asarray(o["hand_pct"]) <= h))
            people = int(round(o["population"] * share))
            
            if share < MIN_FLOODED_SHARE or people == 0:
                continue
                
            start = next((c for c in o["candidates"] if c in Gh), None)
            if start is None:
                origins_out.append({**_o(o), "people": people, "status": "isolated"})
                isolated += people
                continue
                
            pred, dist = nx.dijkstra_predecessor_and_distance(
                Gh, start, cutoff=MAX_TRAVEL_S, weight="w")
                
            options = [(dist[n], sid, n) for n, sids in shelter_at_node.items()
                       if n in dist for sid in sids]
            
            if not options:
                origins_out.append({**_o(o), "people": people, "status": "isolated"})
                isolated += people
                continue
                
            reach[o["id"]] = (people, pred, sorted(options)[:8])
            origins_out.append({**_o(o), "people": people, "status": "ok"})
            
        cap = dict(zip(usable.id, usable.capacity))
        naive = {sid: 0 for sid in cap}
        for people, _, opts in reach.values():
            naive[opts[0][1]] += people   # everyone to the nearest shelter
            
        flows = self._min_cost_flow(reach, cap)
        load = {sid: 0 for sid in cap}
        routes, unassigned = [], 0
        
        for oid, (people, pred, opts) in reach.items():
            node_of = {sid: (t, n) for t, sid, n in opts}
            for sid, f in flows.get(oid, {}).items():
                if f <= 0:
                    continue
                if sid == "OVERFLOW":
                    unassigned += f
                    continue
                load[sid] += f
                t, n = node_of[sid]
                routes.append({"origin": oid, "shelter": sid, "people": int(f),
                               "minutes": round(t / 60, 1),
                               "path": [self.coord[p] for p in self._path(pred, n)]})
                               
        for oo in origins_out:
            if oo["status"] == "ok" and flows.get(oo["id"], {}).get("OVERFLOW", 0) > 0:
                oo["status"] = "partly_unassigned"
                
        shelters_out = []
        for r in sh.itertuples():
            c = int(r.capacity)
            shelters_out.append({
                "id": r.id, "name": r.name, "kind": r.kind,
                "lon": round(r.lon, 5), "lat": round(r.lat, 5), "capacity": c,
                "usable": bool(r.usable),
                "load_naive": int(naive.get(r.id, 0)), "load_opt": int(load.get(r.id, 0)),
                "pct_naive": round(100 * naive.get(r.id, 0) / c), "pct_opt": round(100 * load.get(r.id, 0) / c)})
                
        return {
            "level": h,
            "cut_roads": [[self.coord[u], self.coord[v]] for u, v in zip(cut.u, cut.v)],
            "shelters": shelters_out, "routes": routes, "origins": origins_out,
            "totals": {"people_at_risk": int(sum(o["people"] for o in origins_out)),
                       "assigned": int(sum(load.values())), "unassigned": int(unassigned),
                       "isolated": int(isolated), "roads_cut": int(len(cut)),
                       "shelters_usable": int(len(usable)),
                       "shelters_over_capacity_naive": int(sum(
                           1 for s in shelters_out if s["usable"] and s["pct_naive"] > 100))}}

    @staticmethod
    def _min_cost_flow(reach, cap):
        """Assign people to shelters: minimum total travel time, capacities respected."""
        if not reach:
            return {}
        D = nx.DiGraph()
        total = 0
        for oid, (people, _, opts) in reach.items():
            D.add_node(oid, demand=-people)
            total += people
            for t, sid, _ in opts:
                D.add_edge(oid, sid, capacity=people, weight=int(t // 60) + 1)
            D.add_edge(oid, "OVERFLOW", capacity=people, weight=OVERFLOW_COST)
            
        for sid, c in cap.items():
            if D.has_node(sid):
                D.add_edge(sid, "SINK", capacity=int(c), weight=0)
                
        D.add_edge("OVERFLOW", "SINK", capacity=total, weight=0)
        D.add_node("SINK", demand=total)
        
        flow = nx.min_cost_flow(D)
        return {oid: flow[oid] for oid in reach}

def _o(o):
    return {"id": o["id"], "lon": o["lon"], "lat": o["lat"]}
