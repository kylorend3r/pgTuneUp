import os
import sys
import psycopg2
import psutil
import argparse
import pandas as pd
from tabulate import tabulate
from pathlib import Path
from enums.storage_type import StorageType
from enums.deployment_type import DeploymentType
from assessments import CheckpointAssessment, WorkerAssessment
from assessments.timeouts import TimeoutsAssessment
from assessments.observability import ObservabilityAssessment

class PostgresqlConnection:
    """
    A class to manage PostgreSQL database connections with environment variables
    or PGPASSFILE authentication support.
    """
    
    def __init__(self, cpu_count: int = None, memory_gb: int = None, storage_type: StorageType = None, 
                 desired_rto_in_minutes: int = None, deployment_type: DeploymentType = None):
        """
        Initialize PostgreSQL connection by checking configurations
        and establishing the connection.

        Args:
            cpu_count (int, optional): Number of CPUs to use. Defaults to system CPU count.
            memory_gb (int, optional): Memory in GB. Defaults to system available memory.
            storage_type (StorageType, optional): Storage backend type. Defaults to SSD.
            desired_rto_in_minutes (int, optional): Desired Recovery Time Objective in minutes.
            deployment_type (DeploymentType, optional): Type of deployment (ONPREM or RDS).
        """
        # Set system properties
        self.cpu_count = cpu_count if cpu_count is not None else psutil.cpu_count()
        self.memory_gb = memory_gb if memory_gb is not None else round(psutil.virtual_memory().total / (1024**3))
        self.storage_type = storage_type if storage_type is not None else StorageType.SSD
        self.desired_rto_in_minutes = desired_rto_in_minutes
        self.deployment_type = deployment_type if deployment_type is not None else DeploymentType.ONPREM

        # Validate properties
        self._validate_properties()

        # Initialize connection
        self.config = self._check_postgres_env_variables()
        self.connection = self._establish_connection()

    def _validate_properties(self):
        """
        Validates the system properties provided to the class.
        
        Raises:
            ValueError: If properties are invalid
        """
        if not isinstance(self.cpu_count, int) or self.cpu_count <= 0:
            raise ValueError(f"CPU count must be a positive integer, got {self.cpu_count}")
        
        if not isinstance(self.memory_gb, int) or self.memory_gb <= 0:
            raise ValueError(f"Memory must be a positive integer in GB, got {self.memory_gb}")
        
        if not isinstance(self.storage_type, StorageType):
            raise ValueError(f"Storage type must be a StorageType enum, got {self.storage_type}")
            
        if self.desired_rto_in_minutes is not None:
            if not isinstance(self.desired_rto_in_minutes, int) or self.desired_rto_in_minutes <= 0:
                raise ValueError(f"RTO must be a positive integer in minutes, got {self.desired_rto_in_minutes}")

    def get_system_info(self) -> dict:
        """
        Returns the system properties of the PostgreSQL instance.
        
        Returns:
            dict: Dictionary containing system properties
        """
        return {
            "cpu_count": self.cpu_count,
            "memory_gb": self.memory_gb,
            "storage_type": self.storage_type.value,
            "desired_rto_in_minutes": self.desired_rto_in_minutes,
            "deployment_type": self.deployment_type.value
        }

    def _check_postgres_env_variables(self):
        """
        Ensures that all required PostgreSQL environment variables are set and not empty.
        
        Returns:
            dict: Dictionary containing all PostgreSQL environment variables
            
        Raises:
            SystemExit: If required environment variables are missing or empty
        """
        pgpass_file = os.environ.get('PGPASSFILE')
        
        if pgpass_file:
            required_vars = [
                'POSTGRES_HOST',
                'POSTGRES_PORT',
                'POSTGRES_DB'
            ]
        else:
            required_vars = [
                'POSTGRES_HOST',
                'POSTGRES_PORT',
                'POSTGRES_DB',
                'POSTGRES_USER',
                'POSTGRES_PASSWORD'
            ]
        
        postgres_config = {}
        missing_vars = []
        
        for var in required_vars:
            value = os.environ.get(var)
            if not value:
                missing_vars.append(var)
            else:
                postgres_config[var] = value
        
        if pgpass_file:
            postgres_config['PGPASSFILE'] = pgpass_file
            if not Path(pgpass_file).is_file():
                print(f"Error: PGPASSFILE '{pgpass_file}' does not exist or is not a file.")
                sys.exit(1)
            if os.name == 'posix':
                permissions = oct(Path(pgpass_file).stat().st_mode)[-3:]
                if permissions != '600':
                    print(f"Warning: pgpass file permissions are {permissions}, should be 600")
        
        if missing_vars:
            print(f"Error: The following required PostgreSQL environment variables are missing or empty:")
            for var in missing_vars:
                print(f"  - {var}")
            print("\nPlease set these environment variables before running this script.")
            sys.exit(1)
        
        return postgres_config

    def _establish_connection(self):
        """
        Establishes a connection to PostgreSQL using the verified configuration.
        
        Returns:
            connection: psycopg2 connection object
            
        Raises:
            psycopg2.Error: If connection fails
        """
        try:
            if 'PGPASSFILE' in self.config:
                os.environ['PGPASSFILE'] = self.config['PGPASSFILE']
                connection = psycopg2.connect(
                    host=self.config['POSTGRES_HOST'],
                    port=self.config['POSTGRES_PORT'],
                    database=self.config['POSTGRES_DB']
                )
            else:
                connection = psycopg2.connect(
                    host=self.config['POSTGRES_HOST'],
                    port=self.config['POSTGRES_PORT'],
                    database=self.config['POSTGRES_DB'],
                    user=self.config['POSTGRES_USER'],
                    password=self.config['POSTGRES_PASSWORD']
                )
            return connection
        except psycopg2.Error as e:
            print(f"Error: Could not connect to PostgreSQL database:")
            print(f"  {str(e)}")
            sys.exit(1)

    def get_connection(self):
        """
        Returns the established database connection.
        
        Returns:
            connection: psycopg2 connection object
        """
        return self.connection

    def close_connection(self):
        """
        Closes the database connection if it exists.
        """
        if hasattr(self, 'connection') and self.connection is not None:
            self.connection.close()

    def check_page_cost_parameters(self):
        """
        Checks the random_page_cost and seq_page_cost parameters from pg_settings
        and provides assessment in a tabular format.
        
        Returns:
            list: List of dictionaries containing parameter assessments
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT name, setting::float
                    FROM pg_settings 
                    WHERE name IN ('random_page_cost', 'seq_page_cost');
                """)
                
                settings = {row[0]: row[1] for row in cursor.fetchall()}
                random_page_cost = settings['random_page_cost']
                seq_page_cost = settings['seq_page_cost']
                cost_difference = random_page_cost - seq_page_cost
                
                is_failed = (self.storage_type == StorageType.SSD and cost_difference > 0.3)
                
                return [{
                    "parameter": "random_page_cost/seq_page_cost",
                    "check_result": "FAILED" if is_failed else "PASSED",
                    "priority": "MEDIUM" if is_failed else "LOW",
                    "notes": ("For SSD: reduce random_page_cost to within 0.1-0.3 of seq_page_cost" 
                            if is_failed else "Optimal for current storage type")
                }]
                
        except psycopg2.Error as e:
            return [{
                "parameter": "random_page_cost/seq_page_cost",
                "check_result": "ERROR",
                "priority": "HIGH",
                "notes": f"Error: {e}"
            }]

    def check_shared_buffers(self):
        """
        Checks if shared_buffers parameter is properly configured
        based on available system memory.
        
        Returns:
            list: List containing shared_buffers assessment
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT setting, unit 
                    FROM pg_settings 
                    WHERE name = 'shared_buffers';
                """)
                
                setting, unit = cursor.fetchone()
                shared_buffers_value = int(setting)
                
                # Convert shared_buffers to GB based on unit
                if unit == 'kB':
                    shared_buffers_gb = shared_buffers_value / (1024 * 1024)
                elif unit == 'MB':
                    shared_buffers_gb = shared_buffers_value / 1024
                elif unit == '8kB':
                    shared_buffers_gb = (shared_buffers_value * 8) / (1024 * 1024)
                elif unit == 'GB':
                    shared_buffers_gb = shared_buffers_value
                else:
                    shared_buffers_gb = 0
                
                memory_threshold = self.memory_gb * 0.4
                is_failed = shared_buffers_gb > memory_threshold
                
                return [{
                    "parameter": "shared_buffers",
                    "check_result": "FAILED" if is_failed else "PASSED",
                    "priority": "HIGH",
                    "notes": (f"Exceeds 40% of memory ({shared_buffers_gb:.1f}GB/{memory_threshold:.1f}GB). Reduce to prevent OS pressure."
                            if is_failed else
                            "Within acceptable range")
                }]
                
        except psycopg2.Error as e:
            return [{
                "parameter": "shared_buffers",
                "check_result": "ERROR",
                "priority": "HIGH",
                "notes": f"Error fetching shared_buffers parameter: {e}"
            }]


    def check_max_connections_memory(self):
        """
        Checks if max_connections combined with work_mem and shared_buffers
        could potentially exceed available system memory.
        
        Returns:
            list: List containing max_connections memory assessment
        """
        try:
            with self.connection.cursor() as cursor:
                # Get max_connections
                cursor.execute("""
                    SELECT setting::int
                    FROM pg_settings 
                    WHERE name = 'max_connections';
                """)
                max_connections = cursor.fetchone()[0]

                # Get work_mem and its unit
                cursor.execute("""
                    SELECT setting, unit
                    FROM pg_settings 
                    WHERE name = 'work_mem';
                """)
                work_mem_value, work_mem_unit = cursor.fetchone()
                work_mem_value = int(work_mem_value)

                # Convert work_mem to MB
                if work_mem_unit == 'kB':
                    work_mem_mb = work_mem_value / 1024
                elif work_mem_unit == '8kB':
                    work_mem_mb = (work_mem_value * 8) / 1024
                elif work_mem_unit == 'GB':
                    work_mem_mb = work_mem_value * 1024
                else:  # MB
                    work_mem_mb = work_mem_value

                # Get shared_buffers and its unit
                cursor.execute("""
                    SELECT setting, unit
                    FROM pg_settings 
                    WHERE name = 'shared_buffers';
                """)
                shared_buffers_value, shared_buffers_unit = cursor.fetchone()
                shared_buffers_value = int(shared_buffers_value)

                # Convert shared_buffers to GB
                if shared_buffers_unit == 'kB':
                    shared_buffers_gb = shared_buffers_value / (1024 * 1024)
                elif shared_buffers_unit == 'MB':
                    shared_buffers_gb = shared_buffers_value / 1024
                elif shared_buffers_unit == '8kB':
                    shared_buffers_gb = (shared_buffers_value * 8) / (1024 * 1024)
                else:  # GB
                    shared_buffers_gb = shared_buffers_value

                # Calculate total potential memory usage in GB
                total_work_mem_gb = (work_mem_mb * max_connections) / 1024
                total_memory_needed_gb = total_work_mem_gb + shared_buffers_gb
                
                is_failed = total_memory_needed_gb >= self.memory_gb
                
                return [{
                    "parameter": "max_connections",
                    "check_result": "FAILED" if is_failed else "PASSED",
                    "priority": "HIGH",
                    "notes": (f"Memory usage ({total_memory_needed_gb:.1f}GB) may exceed available ({self.memory_gb}GB). "
                            f"Reduce connections ({max_connections}) or work_mem ({work_mem_mb:.0f}MB)."
                            if is_failed else
                            "Memory configuration within safe limits")
                }]
                
        except psycopg2.Error as e:
            return [{
                "parameter": "max_connections",
                "check_result": "ERROR",
                "priority": "HIGH",
                "notes": f"Error checking memory configuration: {e}"
            }]

    def check_maintenance_work_mem(self):
        """
        Checks if maintenance_work_mem is set to a value greater than 1GB.
        
        Returns:
            list: List containing maintenance_work_mem assessment
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT setting, unit
                    FROM pg_settings 
                    WHERE name = 'maintenance_work_mem';
                """)
                
                setting, unit = cursor.fetchone()
                mem_value = int(setting)
                
                # Convert to MB for comparison
                if unit == 'kB':
                    mem_mb = mem_value / 1024
                elif unit == '8kB':
                    mem_mb = (mem_value * 8) / 1024
                elif unit == 'GB':
                    mem_mb = mem_value * 1024
                else:  # MB
                    mem_mb = mem_value
                
                # Check if greater than 1GB (1024MB)
                is_too_large = mem_mb > 1024
                
                return [{
                    "parameter": "maintenance_work_mem",
                    "check_result": "FAILED" if is_too_large else "PASSED",
                    "priority": "MEDIUM",
                    "notes": (f"Exceeds 1GB ({mem_mb:.0f}MB). Reduce to prevent excessive memory usage."
                            if is_too_large else
                            "Within recommended limits")
                }]
                
        except psycopg2.Error as e:
            return [{
                "parameter": "maintenance_work_mem",
                "check_result": "ERROR",
                "priority": "HIGH",
                "notes": f"Error checking maintenance_work_mem parameter: {e}"
            }]



    def check_work_mem(self):
        """
        Checks if work_mem is properly configured based on available memory and max_connections.
        Evaluates if potential memory usage (work_mem * max_connections) exceeds 25% of available memory
        after accounting for shared_buffers.
        
        Returns:
            list: List containing work_mem assessment
        """
        try:
            with self.connection.cursor() as cursor:
                # Get work_mem and its unit
                cursor.execute("""
                    SELECT setting, unit
                    FROM pg_settings 
                    WHERE name = 'work_mem';
                """)
                work_mem_value, work_mem_unit = cursor.fetchone()
                work_mem_value = int(work_mem_value)

                # Convert work_mem to MB
                if work_mem_unit == 'kB':
                    work_mem_mb = work_mem_value / 1024
                elif work_mem_unit == '8kB':
                    work_mem_mb = (work_mem_value * 8) / 1024
                elif work_mem_unit == 'GB':
                    work_mem_mb = work_mem_value * 1024
                else:  # MB
                    work_mem_mb = work_mem_value

                # Get max_connections
                cursor.execute("""
                    SELECT setting::int
                    FROM pg_settings 
                    WHERE name = 'max_connections';
                """)
                max_connections = cursor.fetchone()[0]

                # Get shared_buffers and its unit
                cursor.execute("""
                    SELECT setting, unit
                    FROM pg_settings 
                    WHERE name = 'shared_buffers';
                """)
                shared_buffers_value, shared_buffers_unit = cursor.fetchone()
                shared_buffers_value = int(shared_buffers_value)

                # Convert shared_buffers to MB
                if shared_buffers_unit == 'kB':
                    shared_buffers_mb = shared_buffers_value / 1024
                elif shared_buffers_unit == 'MB':
                    shared_buffers_mb = shared_buffers_value
                elif shared_buffers_unit == '8kB':
                    shared_buffers_mb = (shared_buffers_value * 8) / 1024
                elif shared_buffers_unit == 'GB':
                    shared_buffers_mb = shared_buffers_value * 1024
                else:
                    shared_buffers_mb = 0

                # Convert system memory to MB
                system_memory_mb = self.memory_gb * 1024
                
                # Calculate possible available memory (25% of what's left after shared_buffers)
                possible_avail_mb = (system_memory_mb - shared_buffers_mb) * 0.25
                
                # Calculate potential memory usage
                potential_usage_mb = work_mem_mb * max_connections
                
                is_failed = potential_usage_mb > possible_avail_mb
                
                return [{
                    "parameter": "work_mem",
                    "check_result": "FAILED" if is_failed else "PASSED",
                    "priority": "HIGH",
                    "notes": (f"Potential usage ({potential_usage_mb:.0f}MB) exceeds 25% limit ({possible_avail_mb:.0f}MB). "
                            f"Reduce work_mem or connections."
                            if is_failed else
                            "Within reasonable limits")
                }]
                
        except psycopg2.Error as e:
            return [{
                "parameter": "work_mem",
                "check_result": "ERROR",
                "priority": "HIGH",
                "notes": f"Error checking work_mem parameter: {e}"
            }]

    def format_results(self, results, 
                      sort_by_priority=True, 
                      show_passed=True, 
                      show_skipped=True,
                      priorities=None,
                      parameters=None,
                      output_format='grid',
                      csv_file=None):
        """
        Formats the assessment results based on provided parameters.
        
        Args:
            results (list): List of assessment results
            sort_by_priority (bool): Whether to sort results by priority
            show_passed (bool): Whether to show passed checks
            show_skipped (bool): Whether to show skipped checks
            priorities (list): List of priorities to include (e.g., ['HIGH', 'MEDIUM'])
            parameters (list): List of specific parameters to include
            output_format (str): Output format ('grid', 'simple', 'pipe', etc.)
            csv_file (str): Optional path to save results as CSV
        
        Returns:
            str: Formatted assessment results
        """
        try:
            # Convert results to DataFrame
            df = pd.DataFrame(results)
            
            # Filter based on check_result if needed
            if not show_passed:
                df = df[df['check_result'] != 'PASSED']
            if not show_skipped:
                df = df[df['check_result'] != 'SKIPPED']
            
            # Filter by priorities if specified
            if priorities:
                df = df[df['priority'].isin(priorities)]
            
            # Filter by parameters if specified
            if parameters:
                df = df[df['parameter'].isin(parameters)]
            
            # Sort by priority if requested
            if sort_by_priority:
                priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
                df['priority_sort'] = df['priority'].map(priority_order)
                df = df.sort_values('priority_sort').drop('priority_sort', axis=1)
            
            # Save to CSV if filename provided
            if csv_file:
                try:
                    df.to_csv(csv_file, index=False)
                    print(f"Results saved to {csv_file}")
                except Exception as e:
                    print(f"Error saving to CSV: {str(e)}")
            
            # Return empty string if no results match filters
            if df.empty:
                return "No results match the specified criteria."
            
            # Format the results
            return tabulate(df, headers='keys', tablefmt=output_format, showindex=False)
            
        except Exception as e:
            return f"Error formatting results: {str(e)}"

    def check_all_parameters(self, **format_params):
        """
        Runs all parameter checks and combines the results.
        Optional formatting parameters can be provided to customize output.
        
        Args:
            **format_params: Keyword arguments for format_results method
        
        Returns:
            str or list: Formatted results string if format_params provided, otherwise raw results list
        """
        results = []
        results.extend(self.check_page_cost_parameters())
        results.extend(self.check_shared_buffers())
        results.extend(self.check_max_connections_memory())
        results.extend(self.check_maintenance_work_mem())
        results.extend(self.check_work_mem())
        
        # Return formatted results if format parameters provided
        if format_params:
            return self.format_results(results, **format_params)
        return results

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='PostgreSQL Connection Manager')
    parser.add_argument('--cpu-count', 
                       type=int,
                       help='Number of CPUs to use')
    parser.add_argument('--memory-gb', 
                       type=int,
                       help='Memory in GB')
    parser.add_argument('--storage-type',
                       type=str,
                       choices=['ssd', 'hdd'],
                       help='Storage backend type (ssd or hdd)')
    parser.add_argument('--desired-rto',
                       type=int,
                       help='Desired Recovery Time Objective in minutes')
    
    parser.add_argument('--deployment-type',
                       type=str,
                       choices=['onprem', 'rds'],
                       help='Deployment type (onprem or rds)')
    parser.add_argument('--csv-output',
                       type=str,
                       help='Path to save results as CSV file')

    args = parser.parse_args()

    try:
        # Convert storage type string to enum if provided
        storage_type = None
        if args.storage_type:
            storage_type = StorageType(args.storage_type.lower())

        # Convert deployment type string to enum if provided
        deployment_type = None
        if args.deployment_type:
            deployment_type = DeploymentType(args.deployment_type.lower())

        # Create PostgreSQL connection instance with provided arguments
        postgresql_instance = PostgresqlConnection(
            cpu_count=args.cpu_count,
            memory_gb=args.memory_gb,
            storage_type=storage_type,
            desired_rto_in_minutes=args.desired_rto,
            deployment_type=deployment_type
        )
        
        checkpoint_assessment = CheckpointAssessment(postgresql_instance.get_connection(), postgresql_instance.desired_rto_in_minutes)
        worker_assessment = WorkerAssessment(postgresql_instance.get_connection(), postgresql_instance.cpu_count)
        observability_assessment = ObservabilityAssessment(postgresql_instance.get_connection())
        timeouts_assessment = TimeoutsAssessment(postgresql_instance.get_connection())
        # Get the connection and test it
        conn = postgresql_instance.get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            
            # Get all parameter check results
            all_results = postgresql_instance.check_all_parameters()
            checkpoint_results = checkpoint_assessment.prepare_checkpoint_stats()
            worker_results = worker_assessment.prepare_worker_stats()
            observability_results = observability_assessment.assess_monitoring_settings()
            all_results.extend(checkpoint_results)
            all_results.extend(worker_results)
            all_results.extend(observability_results)
            all_results.extend(timeouts_assessment.check_idle_timeouts())
            # Format and display results
            print(f"PostgreSQL {version[0]}\n")
            formatted_results = postgresql_instance.format_results(
                all_results,
                show_passed=True,
                sort_by_priority=True,
                output_format='grid',
                csv_file=args.csv_output
            )
            print(formatted_results)
        
    except psycopg2.Error as e:
        print(f"Database error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        # Close the connection through the instance
        if 'postgresql_instance' in locals():
            postgresql_instance.close_connection()
