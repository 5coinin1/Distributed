import socket, json

def send(port, msg):
    s = socket.socket()
    s.connect(("127.0.0.1", port))
    s.send(json.dumps(msg).encode())
    print(s.recv(4096).decode())
    s.close()
for i in range(10):
    send(5000, {"type":"PUT","key":f"user{i}","value":str(i)})

send(5000, {"type":"GET","key":"user3"})

send(5000, {"type":"DELETE","key":"user3"})

send(5000, {"type":"GET","key":"user3"})