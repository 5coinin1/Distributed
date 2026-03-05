# Distributed Key-Value Store

Đây là một project mô phỏng hệ thống lưu trữ khóa-giá trị (key-value store) phân tán đơn giản, được xây dựng bằng Python. Project này nhằm mục đích minh họa các khái niệm cốt lõi trong các hệ thống phân tán.

## Các tính năng chính

Hệ thống triển khai 6 chức năng cơ bản của một hệ thống phân tán có khả năng chịu lỗi:

1.  **Phân tán dữ liệu (Data Partitioning):** Dữ liệu được phân chia trên các node khác nhau sử dụng thuật toán hash-partitioning.
2.  **Sao lưu dữ liệu (Data Replication):** Mỗi mẩu dữ liệu được lưu trữ trên ít nhất hai node (một node chính và các node bản sao) để đảm bảo tính sẵn sàng.
3.  **Định tuyến yêu cầu (Request Routing):** Bất kỳ node nào cũng có thể nhận yêu cầu từ client và chuyển tiếp (forward) nó đến node sở hữu dữ liệu.
4.  **Phát hiện lỗi (Failure Detection):** Các node liên tục gửi tin nhắn "heartbeat" cho nhau để phát hiện khi một node nào đó không còn hoạt động.
5.  **Chịu lỗi (Fault Tolerance):** Khi node chính chứa dữ liệu gặp sự cố, hệ thống có thể tự động đọc dữ liệu từ node bản sao.
6.  **Khôi phục node (Node Recovery):** Khi một node khởi động lại sau sự cố, nó có thể tự động khôi phục lại đúng trạng thái dữ liệu mà nó chịu trách nhiệm.

---

## Kiến trúc và Giải thích Thiết kế

### 1. Giao thức và Định dạng Dữ liệu

*   **Giao thức truyền thông:** Hệ thống sử dụng **TCP** để đảm bảo việc giao tiếp giữa các node và giữa client-node được thực hiện một cách đáng tin cậy.
*   **Định dạng tuần tự hóa dữ liệu:** Tất cả các thông điệp (requests, responses) đều được tuần tự hóa (serialize) dưới định dạng **JSON**. Đây là định dạng văn bản đơn giản, dễ đọc và dễ debug.

### 2. Phân tán và Sao lưu Dữ liệu

*   **Phân tán (Partitioning):** Để xác định node nào sở hữu một `key`, hệ thống sử dụng thuật toán **hash partitioning**. `key` được hash bằng SHA-256, sau đó lấy modulo cho số lượng node để tìm ra `node_id` sở hữu (owner).
*   **Lan truyền và Sao lưu (Replication):** Khi một node sở hữu nhận được yêu cầu `PUT`, quy trình sau sẽ diễn ra:
    1.  Node sở hữu ghi cặp key-value vào bộ lưu trữ cục bộ của mình.
    2.  Ngay sau đó, nó gửi các yêu cầu `REPLICA_PUT` (một cách bất đồng bộ) đến các node bản sao (replica nodes) được xác định trước (ví dụ: `owner + 1`, `owner + 2`).
*   **Tính nhất quán (Consistency):** Do việc gửi yêu cầu đến các bản sao là bất đồng bộ và không chờ xác nhận, hệ thống đảm bảo **tính nhất quán sau cùng (eventual consistency)**. Điều này có nghĩa là sẽ có một độ trễ nhỏ để dữ liệu trên các bản sao được cập nhật giống với bản gốc.

### 3. Chịu lỗi và Khôi phục

*   **Phát hiện lỗi:** Mỗi node gửi một tin nhắn `PING` (heartbeat) đến tất cả các node khác trong cụm theo chu kỳ. Nếu một node không nhận được phản hồi (`PONG`) từ một node khác trong một khoảng thời gian nhất định (timeout), nó sẽ đánh dấu node đó là `dead`.
*   **Xử lý lỗi (Fault Tolerance):**
    *   Khi client gửi yêu cầu `GET` một `key` mà node sở hữu đã chết, node nhận yêu cầu sẽ thử liên hệ node sở hữu, và khi thất bại, nó sẽ tự động chuyển hướng yêu cầu đến các node bản sao để lấy dữ liệu. Điều này giúp hệ thống duy trì **tính sẵn sàng (availability)**.
    *   Khi một yêu cầu `PUT` được thực hiện và một trong các node bản sao đã chết, node sở hữu vẫn ghi dữ liệu và gửi yêu cầu sao lưu đến các node còn lại. Dữ liệu vẫn được lưu thành công.
*   **Khôi phục Node:** Khi một node khởi động lại, nó sẽ thực hiện quy trình khôi phục:
    1.  Node gửi yêu cầu `SNAPSHOT` đến một node khác còn sống trong cụm.
    2.  Nó nhận về một bản chụp toàn bộ dữ liệu của node đó.
    3.  Node đang khôi phục sẽ duyệt qua bản chụp và chỉ lấy lại những cặp key-value mà nó chịu trách nhiệm (với tư cách là node sở hữu hoặc node bản sao).
    Điều này đảm bảo node sau khi khởi động lại sẽ có đúng phần dữ liệu của mình và sẵn sàng tham gia lại vào cụm.

---

## Hướng dẫn Demo và Kiểm tra

Thực hiện theo đúng quy trình dưới đây để kiểm tra và trình bày từng chức năng của hệ thống.

### 1. Chuẩn bị môi trường

Mở 4 cửa sổ terminal riêng biệt.

*   **Terminal 1, 2, 3:** Dùng để chạy 3 node của hệ thống.
*   **Terminal 4:** Dùng để chạy client để gửi yêu cầu.

**Khởi động các node:**

Ở mỗi Terminal 1, 2, và 3, lần lượt chạy các lệnh sau:

```bash
# Terminal 1
python node.py 0

# Terminal 2
python node.py 1

# Terminal 3
python node.py 2
```

Bạn sẽ thấy output tương tự như sau trên các terminal:

```
[Node 0] Started at ('127.0.0.1', 5000)
[Node 1] Started at ('127.0.0.1', 5001)
[Node 2] Started at ('127.0.0.1', 5002)
```

Đợi vài giây để cơ chế "heartbeat" đi vào ổn định.

**Chuẩn bị client:**

Ở Terminal 4, bạn sẽ sử dụng file `client.py` để gửi yêu cầu.

### 2. Test Chức năng PUT (Định tuyến & Phân tán)

Trong Terminal 4 (client), chạy lệnh `python` để vào môi trường interactive và gửi một yêu cầu `PUT`.

```python
#thay vào sau đây để chạy thử
send(5000, {"type": "PUT", "key": "user1", "value": "alice"})
```

Quan sát các cửa sổ terminal của các node. Bạn sẽ thấy một trong các node in ra log:

```
Key user1 owned by node X
```

Dù bạn gửi yêu cầu đến `node 0` (port 5000), `node 0` đã tính toán và chuyển tiếp yêu cầu đến đúng `node X` sở hữu khóa `user1`.

> ✅ **Chứng minh:** **Request Routing** và **Data Partitioning** hoạt động.

### 3. Test Phân tán Dữ liệu

Dùng client để ghi 10 cặp key-value vào hệ thống:

```python
for i in range(10):
    send(5000, {"type": "PUT", "key": f"user{i}", "value": str(i)})
```

Quan sát log `print(self.data)` trên cả 3 node. Bạn sẽ thấy dữ liệu được phân bố không đồng đều, ví dụ:

*   **Node 0 data:** `{'user8': '8', 'user3': '3', ...}`
*   **Node 1 data:** `{'user1': '1', 'user6': '6', ...}`
*   **Node 2 data:** `{'user0': '0', 'user4': '4', ...}`

> ✅ **Chứng minh:** **Hash Partitioning** hoạt động, các key khác nhau được gán cho các node khác nhau.

### 4. Test Sao lưu Dữ liệu (Replication)

Tiếp tục quan sát `self.data` trên các node. Bạn sẽ thấy dữ liệu của một node cũng xuất hiện ở node khác. Ví dụ, nếu `user0` thuộc về `node 2`:

*   **Node 2 (Primary):** `{'user0': '0', ...}`
*   **Node 0 (Replica):** `{'user0': '0', ...}` (nếu dùng 1 replica)
*   **Node 1 (Replica):** `{'user0': '0', ...}` (nếu dùng 2 replica)

Logic sao lưu `replica = (primary + 1)` và `replica = (primary + 2)` đảm bảo dữ liệu được nhân bản.

> ✅ **Chứng minh:** **Data Replication** hoạt động.

### 5. Test Chức năng GET

Dùng client để đọc một key bất kỳ:

```python
# Gửi yêu cầu tới một node không phải là chủ sở hữu
send(5002, {"type": "GET", "key": "user1"})
```

Dù `user1` có thể thuộc về `node 1`, yêu cầu gửi đến `node 2` vẫn trả về kết quả đúng:

```json
{"status": "ok", "value": "1"}
```

> ✅ **Chứng minh:** **Request Routing** cho các yêu cầu `GET` hoạt động.

### 6. Test Chức năng DELETE

Dùng client xóa một key, sau đó đọc lại nó:

```python
# Xóa key
send(5000, {"type": "DELETE", "key": "user1"})

# Đọc lại key vừa xóa
send(5000, {"type": "GET", "key": "user1"})
```

Kết quả đọc lại sẽ là lỗi:

```json
{"status": "error"}
```

Quan sát log các node, bạn sẽ thấy cả node sở hữu và node bản sao đều đã xóa key này.

> ✅ **Chứng minh:** Lệnh `DELETE` được lan truyền (propagate) đến các bản sao.

### 7. Test Phát hiện lỗi (Failure Detection)

Trong Terminal 2 (đang chạy `node 1`), nhấn `Ctrl + C` để tắt node.

Đợi khoảng 5-7 giây (lớn hơn `TIMEOUT`).

Quan sát Terminal 1 và 3. Bạn sẽ thấy log:

```
[FD] Node 1 is dead
```

> ✅ **Chứng minh:** **Failure Detector** hoạt động.

### 8. Test Tính chịu lỗi (Fault Tolerance)

Giả sử `user1` thuộc sở hữu của `node 1` (hiện đã chết). Dùng client để đọc `user1`:

```python
# Gửi yêu cầu đến một node còn sống
send(5000, {"type": "GET", "key": "user1"})
```

Hệ thống sẽ thực hiện quy trình sau:
1.  Client gửi yêu cầu đến `node 0`.
2.  `Node 0` xác định `node 1` là chủ sở hữu nhưng phát hiện `node 1` đã chết.
3.  `Node 0` chuyển sang đọc từ node bản sao (`node 2`).
4.  Client vẫn nhận được kết quả đúng.

```json
{"status": "ok", "value": "1"}
```

> ✅ **Chứng minh:** Hệ thống có **Fault Tolerance**, có thể đọc dữ liệu từ bản sao khi node chính gặp sự cố.

### 9. Test Khôi phục Node (Node Recovery)

Trong Terminal 2, khởi động lại `node 1`:

```bash
python node.py 1
```

Quan sát log của Terminal 2. Bạn sẽ thấy:

```
[Node 1] Started at ('127.0.0.1', 5001)
...
[FD] Node 0 is back online
[FD] Node 2 is back online
...
[Node 1] Recovered X keys from node Y
{'user1': '1', 'user6': '6', ...}
```

`Node 1` đã liên hệ với các node còn sống, tải về một bản `snapshot` dữ liệu và chỉ lấy lại những phần dữ liệu mà nó chịu trách nhiệm.

> ✅ **Chứng minh:** **Node Recovery** hoạt động.

---


## Tổng kết các tính năng

| Feature | Phương pháp kiểm tra |
| :--- | :--- |
| **Data Partitioning** | Phân bố key sau khi `PUT` hàng loạt. |
| **Data Replication** | Dữ liệu gốc và bản sao xuất hiện ở các node khác nhau. |
| **Request Routing** | Gửi `GET`/`PUT` tới node không sở hữu vẫn thành công. |
| **Failure Detection** | Log "Node is dead" sau khi một node bị tắt. |
| **Fault Tolerance** | `GET` thành công một key có node chính đã chết. |
| **Node Recovery** | Log "Recovered X keys" sau khi một node khởi động lại. |
