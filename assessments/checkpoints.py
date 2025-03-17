import pandas as pd
from tabulate import tabulate
from pathlib import Path
from enums.storage_type import StorageType
from enums.deployment_type import DeploymentType

class CheckpointAssessment:
    """
    A class to assess PostgreSQL checkpoint configurations.
    """
    
    def __init__(self, connection, desired_rto_in_minutes):
        """
        Initialize the CheckpointAssessment with a database connection.

        Args:
            connection: A psycopg2 connection object
        """
        self.connection = connection
        self.desired_rto_in_minutes = desired_rto_in_minutes

    def _get_maxwritten_clean_stats(self):
        """
        Get checkpoint statistics from the database.
        """
        cursor = self.connection.cursor()
        cursor.execute(""" SELECT maxwritten_clean from pg_stat_bgwriter;""")
        max_written_stat = cursor.fetchall()
        cursor.close()
        return max_written_stat[0][0]
    def _get_checkpoint_stats(self):
        """
        Get checkpoint statistics from the database.
        """
        cursor = self.connection.cursor()
        cursor.execute(""" SELECT num_timed, num_requested from pg_stat_checkpointer;""")
        stats = cursor.fetchall() 
        cursor.close()
        return stats
    def _get_checkpoint_timeout(self):
        """
        Checks if checkpoint_timeout is properly configured based on desired RTO.
        Warns if checkpoint_timeout is greater than desired RTO.
        
        Returns:
            list: List containing checkpoint_timeout assessment
        """

        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT setting, unit 
                FROM pg_settings 
                WHERE name = 'checkpoint_timeout';
            """)
            
            setting, unit = cursor.fetchone()
            timeout_seconds = int(setting)
            
            if unit == 's':
                timeout_minutes = timeout_seconds / 60
                return timeout_minutes
            elif unit == 'min':
                timeout_minutes = timeout_seconds
                return timeout_minutes
            else:
                return None

                
    def prepare_checkpoint_stats(self):
        """
        Prepare checkpoint statistics for display.
        """
        all_results=[]
        checkpoint_stats = self._get_checkpoint_stats()
        bgwriter_stats=self._get_maxwritten_clean_stats()
        checkpoint_timeout = self._get_checkpoint_timeout()
        if self.desired_rto_in_minutes is None:
            all_results.append [{
                "parameter": "checkpoint_timeout",
                "check_result": "SKIPPED",
                "priority": "MEDIUM",
                "notes": "No RTO specified"
            }]
        if checkpoint_timeout > self.desired_rto_in_minutes:
            all_results.append({
                "parameter": "checkpoint_timeout",
                "check_result": "FAILED",
                "priority": "MEDIUM",
                "notes": f"Exceeds RTO ({checkpoint_timeout:.1f}min > {self.desired_rto_in_minutes}min). Reduce to meet recovery objectives."
            })
        else:
            all_results.append({
                "parameter": "checkpoint_timeout",
                "check_result": "PASSED",
                "priority": "LOW",
                "notes": "Within acceptable range for RTO"
            })
        if bgwriter_stats > 0:
                all_results.append({
                "parameter": "bgwriter_lru_maxpages",
                "check_result": "FAILED",
                "priority": "MEDIUM",
                "notes": f"Consider increasing bgwriter_lru_maxpages to reduce checkpoint I/O spikes."
            })
        else:
            all_results.append({
                "parameter": "bgwriter_lru_maxpages",
                "check_result": "PASSED",
                "priority": "LOW",
                "notes": "bgwriter_lru_maxpages is properly configured."
            })
        if checkpoint_stats[0][0] < checkpoint_stats[0][1]:
            all_results.append({
                "parameter": "max_wal_size",
                "check_result": "FAILED",
                "priority": "HIGH",
                "notes": "Consider increasing max_wal_size to reduce checkpoint frequency and I/O spikes."
            })
        else:
            all_results.append({
                "parameter": "max_wal_size",
                "check_result": "PASSED",
                "priority": "LOW",
                "notes": "max_wal_size is properly configured."
            })            
        return all_results
