import psycopg2

class TimeoutsAssessment:
    def __init__(self, connection):
        """
        Initialize the Timeouts assessment with a database connection.
        Args:
            connection: A psycopg2 connection object
        """
        self.connection = connection
    
    def check_idle_timeouts(self):
        """
        Checks if idle_in_transaction_session_timeout, idle_session_timeout,
        and statement_timeout are configured with non-zero values.
        
        Returns:
            list: List containing timeout assessments
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT name, setting::int, unit
                    FROM pg_settings 
                    WHERE name IN (
                        'idle_in_transaction_session_timeout', 
                        'idle_session_timeout',
                        'statement_timeout'
                    );
                """)
                
                settings = {row[0]: {"value": row[1], "unit": row[2]} for row in cursor.fetchall()}
                results = []
                
                # Check idle_in_transaction_session_timeout
                trans_timeout = settings.get('idle_in_transaction_session_timeout', {"value": 0})
                is_trans_timeout_disabled = trans_timeout["value"] == 0
                
                results.append({
                    "parameter": "idle_in_transaction_session_timeout",
                    "check_result": "FAILED" if is_trans_timeout_disabled else "PASSED",
                    "priority": "LOW",
                    "notes": ("No timeout set. Add timeout to prevent resource locks."
                            if is_trans_timeout_disabled else
                            f"Timeout set: {trans_timeout['value']} {trans_timeout['unit']}")
                })
                
                # Check idle_session_timeout
                session_timeout = settings.get('idle_session_timeout', {"value": 0})
                is_session_timeout_disabled = session_timeout["value"] == 0
                
                results.append({
                    "parameter": "idle_session_timeout",
                    "check_result": "FAILED" if is_session_timeout_disabled else "PASSED",
                    "priority": "LOW",
                    "notes": ("No timeout set. Add timeout to terminate inactive sessions."
                            if is_session_timeout_disabled else
                            f"Timeout set: {session_timeout['value']} {session_timeout['unit']}")
                })

                # Check statement_timeout
                stmt_timeout = settings.get('statement_timeout', {"value": 0})
                is_stmt_timeout_disabled = stmt_timeout["value"] == 0
                
                results.append({
                    "parameter": "statement_timeout",
                    "check_result": "FAILED" if is_stmt_timeout_disabled else "PASSED",
                    "priority": "LOW",
                    "notes": ("No timeout set. Add timeout to prevent long-running queries."
                            if is_stmt_timeout_disabled else
                            f"Timeout set: {stmt_timeout['value']} {stmt_timeout['unit']}")
                })
                
                return results
                
        except psycopg2.Error as e:
            return [{
                "parameter": "timeouts",
                "check_result": "ERROR",
                "priority": "HIGH",
                "notes": f"Error: {e}"
            }]
