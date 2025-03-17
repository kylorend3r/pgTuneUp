import pandas as pd
import psycopg2

class ObservabilityAssessment:
    def __init__(self, connection):
        """
        Initialize the Observability assessment with a database connection.

        Args:
            connection: A psycopg2 connection object
        """
        self.connection = connection
    
    def _get_track_io_timing(self):
        """
        Check if track_io_timing is enabled.
        
        Returns:
            dict: A dictionary containing the assessment result with keys:
                - 'result': The current track_io_timing setting
                - 'check_result': 'warning' if track_io_timing is off, 'pass' otherwise
                - 'priority': 'low' indicating this is a low priority setting
                - 'notes': Description of the finding
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT setting FROM pg_settings WHERE name = 'track_io_timing';")
        setting_value = cursor.fetchone()[0]  # Extract the value from the tuple
        
        assessment = {
            'parameter': 'track_io_timing',
            'check_result': 'FAILED' if setting_value == 'off' else 'PASSED',
            'priority': 'LOW',
            'notes': (
                "track_io_timing is disabled. Enabling this setting allows for "
                "measuring I/O timings which is useful for performance diagnostics."
                if setting_value == 'off' else
                "track_io_timing is enabled, which allows for measuring I/O timings."
            )
        }
        
        return assessment
        
    def _get_track_wal_io_timing(self):
        """
        Check if track_wal_io_timing is enabled.
        
        Returns:
            dict: A dictionary containing the assessment result with keys:
                - 'result': The current track_wal_io_timing setting
                - 'check_result': 'warning' if track_wal_io_timing is off, 'pass' otherwise
                - 'priority': 'low' indicating this is a low priority setting
                - 'notes': Description of the finding
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT setting FROM pg_settings WHERE name = 'track_wal_io_timing';")
        setting_value = cursor.fetchone()[0]  # Extract the value from the tuple
        
        assessment = {
            'parameter': 'track_wal_io_timing',
            'check_result': 'FAILED' if setting_value == 'off' else 'PASSED',
            'priority': 'LOW',
            'notes': (
                "track_wal_io_timing is disabled. Enabling this setting allows for "
                "measuring WAL I/O timings which can help diagnose WAL-related performance issues."
                if setting_value == 'off' else
                "track_wal_io_timing is enabled, which allows for measuring WAL I/O timings."
            )
        }
        
        return assessment
        
    def _get_track_commit_timestamp(self):
        """
        Check if track_commit_timestamp is enabled.
        
        Returns:
            dict: A dictionary containing the assessment result with keys:
                - 'result': The current track_commit_timestamp setting
                - 'check_result': 'warning' if track_commit_timestamp is off, 'pass' otherwise
                - 'priority': 'low' indicating this is a low priority setting
                - 'notes': Description of the finding
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT setting FROM pg_settings WHERE name = 'track_commit_timestamp';")
        setting_value = cursor.fetchone()[0]  # Extract the value from the tuple
        
        assessment = {
            'parameter': "track_commit_timestamp",
            'check_result': 'FAILED' if setting_value == 'off' else 'PASSED',
            'priority': 'LOW',
            'notes': (
                "track_commit_timestamp is disabled. Enabling this setting allows tracking "
                "transaction commit timestamps, which is useful for replication and temporal queries."
                if setting_value == 'off' else
                "track_commit_timestamp is enabled, which allows tracking of transaction commit timestamps."
            )
        }
        
        return assessment
        
    def _get_log_lock_waits(self):
        """
        Check if log_lock_waits is enabled.
        
        Returns:
            dict: A dictionary containing the assessment result with keys:"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT setting FROM pg_settings WHERE name = 'log_lock_waits';")
        setting_value = cursor.fetchone()[0]  # Extract the value from the tuple
        
        assessment = {
            'parameter': 'log_lock_waits',
            'check_result': 'FAILED' if setting_value == 'off' else 'PASSED',
            'priority': 'LOW',
            'notes': (
                "log_lock_waits is disabled. Enabling this setting allows logging of lock wait events, which can help diagnose lock contention issues."
                if setting_value == 'off' else
                "log_lock_waits is enabled, which allows logging of lock wait events."
            )
        }   
        return assessment
        
    def _get_log_temp_files(self):
        """
        Check if log_temp_files is properly configured.
        
        Returns:
            dict: A dictionary containing the assessment result with keys:
                - 'result': The current log_temp_files setting
                - 'check_result': 'warning' if log_temp_files is -1, 'pass' otherwise
                - 'priority': 'low' indicating this is a low priority setting
                - 'notes': Description of the finding
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT setting FROM pg_settings WHERE name = 'log_temp_files';")
        setting_value = cursor.fetchone()[0]  # Extract the value from the tuple
        
        assessment = {
            'parameter': "log_temp_files",
            'check_result': 'FAILED' if setting_value == '-1' else 'PASSED',
            'priority': 'LOW',
            'notes': (
                "log_temp_files is disabled (-1). Setting this to a value (in KB) will log the use of "
                "temporary files larger than that threshold, which helps identify queries that might "
                "benefit from more work_mem allocation."
                if setting_value == '-1' else
                f"log_temp_files is set to {setting_value}KB, which logs usage of temporary files "
                f"larger than this threshold to help identify inefficient queries."
            )
        }
        
        return assessment
        
    def assess_monitoring_settings(self):
        """
        Collect all monitoring-related settings assessments.
        
        Returns:
            list: A list of dictionaries containing assessment results for various 
                  monitoring settings, each with the following keys:
                  - 'result': Current value of the setting
                  - 'check_result': 'warning' or 'pass' based on assessment
                  - 'priority': Priority level of the finding
                  - 'notes': Description of the finding
        """
        assessments = []
        
        # Collect all assessments
        assessments.append(self._get_track_io_timing())
        assessments.append(self._get_track_wal_io_timing())
        assessments.append(self._get_track_commit_timestamp())
        assessments.append(self._get_log_lock_waits())
        assessments.append(self._get_log_temp_files())
        
        return assessments