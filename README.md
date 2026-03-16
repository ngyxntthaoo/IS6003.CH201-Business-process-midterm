
# Process Graph Analyzer – Accounting / Finance Workflows
This project is a process analysis toolkit for Business Process Modeling.
It loads process definitions from node / edge tables, builds a directed graph, detects cycles, analyzes paths, calculates cost/resources, and exports BPMN.

The project is designed for experiments with Accounting / Finance workflows (10 processes).

### Data Format
#### Node table
- Each row = one node
- Columns:

     | column     | meaning                      |
     | ---------- | ---------------------------- |
     | id         | node id                      |
     | label      | node name                    |
     | type       | 1 event / 2 task / 3 gateway |
     | graph      | process name                 |
     | pool       | pool                         |
     | lane       | lane                         |
     | assignee   | person                       |
     | department | department                   |
     | headcount  | number of people             |
     | node_cost  | cost                         |
     | equipment  | tools                        |
     | type_name  | Event / Task / Gateway       |
#### Edge table

- Each row = connection Used to build directed graph.

     | source | target | label |

### Use cases
- BPMN experiment
- cycle time calculation
- process mining demo
- workflow simulation
- cost analysis
- workflow modeling

### Sub-processes
| # |Quy trình | Gateway|
|---|----------|--------|
| 1 | Lập ngân sách (Budgeting) | XOR |
| 2 | Phê duyệt chi phí (Expense Approval) | XOR + cycle | 
| 3 | Thanh toán nhà cung cấp (AP) | XOR
| 4 |Thu tiền khách hàng (AR) | OR|
| 5 | Xử lý lương (Payroll) | XOR | 
| 6 | Đối soát ngân hàng (Bank Reconciliation)| XOR + cycle| 
| 7 | Kiểm toán nội bộ (Internal Audit) | OR |
| 8 | Báo cáo tài chính (Financial Report)| XOR|
| 9 | Quản lý tài sản (Asset Management) | XOR |
| 10 | Xử lý hoàn thuế (Tax Refund) |XOR + cycle |

### Structure

```
my_project/
├── app.py               ← orchestrator
├── graph_view.py        ← pyvis + hover panel + cycle highlight
├── stats.py             ← thống kê + bar/pie chart
├── cycle.py             ← DFS cycle detection
├── path_analysis.py     ← path cost + nhân sự + thiết bị
├── bpmn_export.py       ← graph → BPMN XML + SVG  ← mới
├── report.py            ← Excel 6 sheet đẹp
└── data/
    ├── nodes.csv / edges.csv
    └── templates/
        └── accounting_nodes/edges.csv  ← 10 quy trình Accounting/Finance
```


### Requirements
Install dependencies:

`pip install -r requirements.txt`

### Run application
`streamlit run app.py`

Open browser: http://localhost:8501