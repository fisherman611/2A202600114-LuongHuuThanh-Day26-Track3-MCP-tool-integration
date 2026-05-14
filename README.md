# SQLite Lab MCP Server (FastMCP + SQLite)

Du an nay da duoc implementation day du theo rubric:

- 3 tools: `search`, `insert`, `aggregate`
- 2 resources:
  - `schema://database`
  - `schema://table/{table_name}`
- Validation an toan cho table/column/operator/aggregate/insert
- SQLite seed data co the tai tao (reproducible)
- Script verify + unit tests
- Huong dan tich hop client (Codex, Claude Code, Gemini CLI)

## 1. Cau truc thu muc

```text
implementation/
  db.py
  init_db.py
  mcp_server.py
  verify_server.py
  requirements.txt
  start_inspector.sh
  start_inspector.ps1
  tests/
    test_db.py
pseudocode/
README.md
Rubric.md
Tips.md
```

## 2. Yeu cau moi truong

- Python 3.10+
- pip
- (Tuy chon) Node.js + npx de chay MCP Inspector

## 3. Cai dat

Tu thu muc goc project:

```bash
cd implementation
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Cai dependency:

```bash
pip install -r requirements.txt
```

## 4. Khoi tao database

Khoi tao moi (reset + seed):

```bash
python init_db.py
```

Mac dinh DB nam tai: `implementation/lab.db`

Neu muon doi duong dan DB, set env var:

Windows PowerShell:

```powershell
$env:SQLITE_LAB_DB_PATH = "D:\path\to\your.db"
```

macOS/Linux:

```bash
export SQLITE_LAB_DB_PATH="/absolute/path/your.db"
```

## 5. Chay MCP server

### STDIO (khuyen nghi cho MCP clients)

```bash
python mcp_server.py
```

### HTTP/SSE (bonus/demo)

```bash
python mcp_server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

```bash
python mcp_server.py --transport sse --host 127.0.0.1 --port 8000 --path /mcp
```

## 6. Tool contract

### `search`

Input chinh:

- `table` (string)
- `filters` (list), moi filter:
  - `column`
  - `operator`: `=`, `!=`, `<`, `>`, `<=`, `>=`, `like`, `in`
  - `value`
- `columns` (list string)
- `order_by` (string hoac list string)
- `descending` (bool)
- `limit` (1..1000)
- `offset` (>=0)

### `insert`

Input chinh:

- `table` (string)
- `values` (object, khong duoc rong)

### `aggregate`

Input chinh:

- `table` (string)
- `metric`: `count`, `avg`, `sum`, `min`, `max`
- `column` (bat buoc voi metric khac `count`)
- `filters` (tuong tu `search`)
- `group_by` (string hoac list string)

## 7. Resource contract

- `schema://database`: tra ve schema tat ca bang
- `schema://table/{table_name}`: tra ve schema 1 bang

## 8. Validation/Error handling

Server se reject ro rang cac truong hop:

- unknown table
- unknown column
- unsupported operator
- invalid aggregate metric
- aggregate thieu column khi can
- empty insert
- limit/offset khong hop le

SQL duoc xay dung theo huong parameterized, khong noi chuoi input tho.

## 9. Verify nhanh (tu dong)

Chay script verify:

```bash
python verify_server.py
```

Script verify se check:

1. Ket noi server bang FastMCP Client
2. Discover du 3 tools
3. Discover du resource + resource template
4. Goi tool hop le thanh cong
5. Goi tool sai co loi ro rang

## 10. Chay unit tests

```bash
pytest -q
```

## 11. Chay MCP Inspector

Windows PowerShell:

```powershell
.\start_inspector.ps1
```

macOS/Linux:

```bash
chmod +x start_inspector.sh
./start_inspector.sh
```

Checklist Inspector:

- Tools hien: `search`, `insert`, `aggregate`
- Resources hien: `schema://database` va template `schema://table/{table_name}`
- Goi duoc ca case dung va case sai

## 12. Client configuration examples

### Codex (`~/.codex/config.toml`)

```toml
[mcp_servers.sqlite_lab]
command = "python"
args = ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"]
```

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "python",
      "args": ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"],
      "env": {}
    }
  }
}
```

### Gemini CLI

```bash
gemini mcp add sqlite-lab /ABSOLUTE/PATH/TO/python /ABSOLUTE/PATH/TO/implementation/mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
```

## 13. Demo script goi y (2 phut)

1. Start server
2. Mo Inspector, show tool/resource discovery
3. Goi `search` cohort `A1`
4. Goi `insert` them 1 student
5. Goi `aggregate` avg score theo cohort
6. Doc `schema://database` va `schema://table/students`
7. Goi 1 request sai de show error handling

## 14. Luu y nop bai

- Commit ca source code + README
- Kem screenshot Inspector (khuyen nghi)
- Kem 1 video demo ngan theo flow tren
