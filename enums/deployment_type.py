from enum import Enum

class DeploymentType(Enum):
    """
    Enum representing different types of PostgreSQL deployments.
    """
    ONPREM = "onprem"
    RDS = "rds" 