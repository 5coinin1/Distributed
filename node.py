import socket
import threading
import json
import time
import sys
import hashlib

NODES = [
    ("127.0.0.1", 5000),
    ("127.0.0.1", 5001),
    ("127.0.0.1", 5002),
]

HEARTBEAT_INTERVAL = 2
TIMEOUT = 5


class Node:
    def __init__(self, node_id):
        self.node_id = node_id
        self.addr = NODES[node_id]
        self.data = {}
        self.alive = [True] * len(NODES)
        self.last_seen = [time.time()] * len(NODES)

        print(f"[Node {node_id}] Started at {self.addr}")

    # ------------------ Hash partition ------------------
    def key_owner(self, key):
        h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
        return h % len(NODES)

    def replica_owner(self, primary):
        return (primary + 1) % len(NODES)

    # ------------------ Networking ------------------
    def start(self):
        threading.Thread(target=self.server_loop, daemon=True).start()
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        threading.Thread(target=self.failure_detector, daemon=True).start()
        self.recover()
        while True:
            time.sleep(1)

    def server_loop(self):
        s = socket.socket()
        s.bind(self.addr)
        s.listen()

        while True:
            conn, _ = s.accept()
            threading.Thread(target=self.handle_conn, args=(conn,), daemon=True).start()

    def handle_conn(self, conn):
        try:
            data = conn.recv(4096).decode()
            if not data:
                return
            req = json.loads(data)
            res = self.handle_request(req)
            conn.send(json.dumps(res).encode())
        except Exception as e:
            print("Error:", e)
        finally:
            conn.close()

    def send(self, node_id, msg):
        s = socket.socket()
        s.settimeout(2)

        try:
            s.connect(NODES[node_id])
            s.sendall(json.dumps(msg).encode())
            data = s.recv(4096)
            return json.loads(data.decode())

        except Exception as e:
            raise e

        finally:
            s.close()


    # ------------------ Core logic ------------------
    def handle_request(self, req):
        t = req["type"]

        if t == "PUT":
            return self.put(req["key"], req["value"])
        if t == "GET":
            return self.get(req["key"])
        if t == "DELETE":
            return self.delete(req["key"])
        if t == "REPLICA_PUT":
            self.data[req["key"]] = req["value"]
            print(self.data)

            return {"status": "ok"}
        if t == "PING":
            return {"type": "PONG"}
        if t == "SNAPSHOT":
            return {"data": self.data}

    def put(self, key, value):
        p = self.key_owner(key)
        print(f"Key {key} owned by node {p}")

        r = self.replica_owner(p)

        if p != self.node_id:
            return self.send(p, {"type": "PUT", "key": key, "value": value})

        self.data[key] = value
        if self.alive[r]:
            self.send(r, {"type": "REPLICA_PUT", "key": key, "value": value})

        return {"status": "ok"}

    def get(self, key):
        p = self.key_owner(key)
        r = self.replica_owner(p)

        if p == self.node_id and key in self.data:
            return {"status": "ok", "value": self.data[key]}

        if self.alive[p]:
            return self.send(p, {"type": "GET", "key": key})
        elif self.alive[r]:
            return self.send(r, {"type": "GET", "key": key})
        else:
            return {"status": "error", "msg": "no replicas alive"}

    def delete(self, key):
        p = self.key_owner(key)
        r = self.replica_owner(p)

        if p != self.node_id:
            return self.send(p, {"type": "DELETE", "key": key})

        self.data.pop(key, None)
        if self.alive[r]:
            self.send(r, {"type": "REPLICA_PUT", "key": key, "value": None})

        return {"status": "ok"}

    # ------------------ Fault tolerance ------------------
    def heartbeat_loop(self):
        while True:
            for i in range(len(NODES)):
                if i == self.node_id:
                    continue
                try:
                    resp = self.send(i, {"type": "PING"})

                    if resp.get("type") == "PONG":
                        if not self.alive[i]:
                            print(f"[FD] Node {i} is back online")

                        self.last_seen[i] = time.time()
                        self.alive[i] = True
                except:
                    pass

            time.sleep(HEARTBEAT_INTERVAL)

    def failure_detector(self):
        while True:
            now = time.time()
            for i in range(len(NODES)):
                if i == self.node_id:
                    continue

                if now - self.last_seen[i] > TIMEOUT:
                    if self.alive[i]:   # chỉ in khi vừa mới chết
                        print(f"[FD] Node {i} is dead")
                    self.alive[i] = False
            time.sleep(1)


    # ------------------ Recovery ------------------
    def recover(self):
        time.sleep(2)
        for i in range(len(NODES)):
            if i != self.node_id and self.alive[i]:
                res = self.send(i, {"type": "SNAPSHOT"})
                if "data" in res:
                    recovered = {}
                    for k, v in res["data"].items():
                        p = self.key_owner(k)
                        r = self.replica_owner(p)
                        if p == self.node_id or r == self.node_id:
                            recovered[k] = v

                    self.data = recovered
                    print(f"[Node {self.node_id}] Recovered {len(self.data)} keys from node {i}")
                    print(self.data)
                    return



if __name__ == "__main__":
    nid = int(sys.argv[1])
    Node(nid).start()
