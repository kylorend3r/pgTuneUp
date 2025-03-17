import pandas as pd
from tabulate import tabulate
from pathlib import Path
from enums.storage_type import StorageType
from enums.deployment_type import DeploymentType
import psycopg2

class WorkerAssessment:
    """
    A class to assess PostgreSQL worker configurations.
    """
    def __init__(self, connection, cpu_count):
        """
        Initialize the WorkerAssessment with a database connection.

        Args:
            connection: A psycopg2 connection object
            cpu_count: Number of CPUs
        """
        self.connection = connection
        self.cpu_count = cpu_count
    def _check_autovacuum_max_workers(self):
        """
        Checks if autovacuum_max_workers is properly configured based on CPU count.
        Uses formula: autovacuum_max_workers = min(max(3, n/5), 16) where n is cpu_count.
        
        Returns:
            list: List containing autovacuum_max_workers assessment
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT setting::int
                    FROM pg_settings 
                    WHERE name = 'autovacuum_max_workers';
                """)
                
                current_workers = cursor.fetchone()[0]
                
                # Calculate recommended workers using the formula
                recommended_workers = min(max(3, int(self.cpu_count/5)), 16)
                
                is_suboptimal = current_workers != recommended_workers
                
                return [{
                    "parameter": "autovacuum_max_workers",
                    "check_result": "FAILED" if is_suboptimal else "PASSED",
                    "priority": "MEDIUM",
                    "notes": (f"Current: {current_workers}, Recommended: {recommended_workers} for {self.cpu_count} CPUs"
                            if is_suboptimal else
                            f"Optimal for {self.cpu_count} CPUs")
                }]
                
        except psycopg2.Error as e:
            return [{
                "parameter": "autovacuum_max_workers",
                "check_result": "ERROR",
                "priority": "HIGH",
                "notes": f"Error checking autovacuum_max_workers parameter: {e}"
            }]

    def _check_max_parallel_maintenance_workers(self):
        """
        Checks if max_parallel_maintenance_workers is properly configured based on CPU count.
        Uses formula: max_parallel_maintenance_workers = min(max(2, n/8), 8) where n is cpu_count.
        
        Returns:
            list: List containing max_parallel_maintenance_workers assessment
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT setting::int
                    FROM pg_settings 
                    WHERE name = 'max_parallel_maintenance_workers';
                """)
                
                current_workers = cursor.fetchone()[0]
                
                # Calculate recommended workers using the formula
                recommended_workers = min(max(2, int(self.cpu_count/8)), 8)
                
                is_suboptimal = current_workers != recommended_workers
                
                return [{
                    "parameter": "max_parallel_maintenance_workers",
                    "check_result": "FAILED" if is_suboptimal else "PASSED",
                    "priority": "MEDIUM",
                    "notes": (f"Current: {current_workers}, Recommended: {recommended_workers} for {self.cpu_count} CPUs"
                            if is_suboptimal else
                            f"Optimal for {self.cpu_count} CPUs")
                }]
                
        except psycopg2.Error as e:
            return [{
                "parameter": "max_parallel_maintenance_workers",
                "check_result": "ERROR",
                "priority": "HIGH",
                "notes": f"Error checking max_parallel_maintenance_workers parameter: {e}"
            }]
        
    def prepare_worker_stats(self):
        """
        Prepare worker statistics for display.
        """
        all_results=[]
        all_results.extend(self._check_autovacuum_max_workers())
        all_results.extend(self._check_max_parallel_maintenance_workers())
        return all_results