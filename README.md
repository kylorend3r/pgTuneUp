# PostgreSQL Configuration Assessment Tool

A comprehensive tool for analyzing and optimizing PostgreSQL database configurations.

## Overview

This tool connects to a PostgreSQL database and performs a series of configuration assessments to identify potential issues and optimization opportunities. It evaluates various parameters against best practices and provides recommendations based on your specific environment.

## Features

- **Comprehensive Parameter Checks**: Analyzes over 10 critical PostgreSQL configuration parameters
- **Smart Recommendations**: Provides context-aware suggestions based on your hardware and workload
- **Customizable Output**: Filter results by priority, status, or specific parameters
- **Multiple Output Formats**: View results as tables or export to CSV
- **Storage-Aware Optimization**: Provides different recommendations for SSD vs HDD storage
- **Recovery Time Objective (RTO) Analysis**: Ensures your configuration meets your recovery goals

## Installation

### Prerequisites

- Python 3.6+
- PostgreSQL database (9.6+)
- Required Python packages:
  - psycopg2
  - pandas
  - tabulate
  - psutil

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/postgresql-configuration-assessment.git
   cd postgresql-configuration-assessment
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables for database connection:
   ```bash
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_DB=your_database
   export POSTGRES_USER=your_username
   export POSTGRES_PASSWORD=your_password
   ```

   Alternatively, you can use a `.pgpass` file:
   ```bash
   export PGPASSFILE=/path/to/.pgpass
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_DB=your_database
   ```

## Usage

### Basic Usage

```bash
python check-configurations.py
```

### Advanced Options

```bash
python check-configurations.py --cpu-count 8 --memory-gb 32 --storage-type ssd --desired-rto 15 --deployment-type onprem
```

### Command Line Arguments

- `--cpu-count`: Number of CPUs to use (defaults to system CPU count)
- `--memory-gb`: Memory in GB (defaults to system available memory)
- `--storage-type`: Storage backend type (`ssd` or `hdd`, defaults to `ssd`)
- `--desired-rto`: Desired Recovery Time Objective in minutes
- `--deployment-type`: Deployment type (`onprem` or `rds`, defaults to `onprem`)


## Assessment Categories

The tool performs checks in the following categories:

1. **Memory Configuration**
   - shared_buffers
   - work_mem
   - maintenance_work_mem
   - max_connections memory usage

2. **I/O Optimization**
   - random_page_cost/seq_page_cost
   - checkpoint_timeout
   - max_wal_size
   - bgwriter_lru_maxpages

3. **Parallelism & Workers**
   - autovacuum_max_workers
   - max_parallel_maintenance_workers

4. **Timeout Settings**
   - idle_in_transaction_session_timeout
   - idle_session_timeout
   - statement_timeout

## Example Output

| Parameter                           | Check Result   | Priority  | Notes                                                                                                                                                          |
|-------------------------------------|---------------|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| shared_buffers                      | PASSED        | HIGH      | Within acceptable range                                                                                                                                        |
| max_connections                     | PASSED        | HIGH      | Memory configuration within safe limits                                                                                                                        |
| work_mem                            | PASSED        | HIGH      | Within reasonable limits                                                                                                                                       |
| random_page_cost/seq_page_cost      | FAILED        | MEDIUM    | For SSD: reduce random_page_cost to within 0.1-0.3 of seq_page_cost                                                                                            |
| max_parallel_maintenance_workers    | FAILED        | MEDIUM    | Current: 2, Recommended: 4 for 32 CPUs                                                                                                                         |
| autovacuum_max_workers              | FAILED        | MEDIUM    | Current: 3, Recommended: 6 for 32 CPUs                                                                                                                         |
| maintenance_work_mem                | PASSED        | MEDIUM    | Within recommended limits                                                                                                                                      |
| checkpoint_timeout                  | FAILED        | MEDIUM    | Exceeds RTO (5.0min > 1min). Reduce to meet recovery objectives.                                                                                               |
| bgwriter_lru_maxpages               | PASSED        | LOW       | bgwriter_lru_maxpages is properly configured.                                                                                                                  |
| max_wal_size                        | PASSED        | LOW       | max_wal_size is properly configured.                                                                                                                           |
| idle_session_timeout                | FAILED        | LOW       | No timeout set. Add timeout to terminate inactive sessions.                                                                                                    |
| track_io_timing                     | FAILED        | LOW       | track_io_timing is disabled. Enabling this setting allows for measuring I/O timings which is useful for performance diagnostics.                               |
| track_wal_io_timing                 | FAILED        | LOW       | track_wal_io_timing is disabled. Enabling this setting allows for measuring WAL I/O timings which can help diagnose WAL-related performance issues.            |
| track_commit_timestamp              | FAILED        | LOW       | track_commit_timestamp is disabled. Enabling this setting allows tracking transaction commit timestamps, which is useful for replication and temporal queries. |
| log_lock_waits                      | FAILED        | LOW       | log_lock_waits is disabled. Enabling this setting allows logging of lock wait events, which can help diagnose lock contention issues.                          |
| log_temp_files                      | PASSED        | LOW       | log_temp_files is set to 100KB, which logs usage of temporary files larger than this threshold to help identify inefficient queries.                           |
| idle_in_transaction_session_timeout | FAILED        | LOW       | No timeout set. Add timeout to prevent resource locks.                                                                                                         |
| statement_timeout                   | FAILED        | LOW       | No timeout set. Add timeout to prevent long-running queries.                                                                                                   |


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
EOF