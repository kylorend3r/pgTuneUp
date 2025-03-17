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

| Parameter                           | Check Result   | Priority   | Notes                                                                                  |
|-------------------------------------|---------------|------------|----------------------------------------------------------------------------------------|
| work_mem                            | FAILED        | HIGH       | Potential usage (51200MB) exceeds 25% limit (32736MB). Reduce work_mem or connections. |
| random_page_cost/seq_page_cost      | FAILED        | MEDIUM     | For SSD: reduce random_page_cost to within 0.1-0.3 of seq_page_cost                    |
| maintenance_work_mem                | PASSED        | MEDIUM     | Within recommended limits                                                              |
| bgwriter_lru_maxpages               | FAILED        | MEDIUM     | Consider increasing bgwriter_lru_maxpages to reduce checkpoint I/O spikes.             |
| autovacuum_max_workers              | FAILED        | MEDIUM     | Current: 3, Recommended: 6 for 32 CPUs                                                 |
| max_parallel_maintenance_workers    | FAILED        | MEDIUM     | Current: 2, Recommended: 4 for 32 CPUs                                                 |
| shared_buffers                      | PASSED        | LOW        | Within acceptable range                                                                |
| checkpoint_timeout                  | PASSED        | LOW        | Within acceptable range for RTO                                                        |
| max_connections                     | PASSED        | LOW        | Memory configuration within safe limits                                                |
| idle_in_transaction_session_timeout | FAILED        | LOW        | No timeout set. Add timeout to prevent resource locks.                                 |
| idle_session_timeout                | FAILED        | LOW        | No timeout set. Add timeout to terminate inactive sessions.                            |
| statement_timeout                   | FAILED        | LOW        | No timeout set. Add timeout to prevent long-running queries.                           |
| max_wal_size                        | PASSED        | LOW        | max_wal_size is properly configured.                                                   |


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
EOF