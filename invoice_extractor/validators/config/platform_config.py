import sys
from pathlib import Path

_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from invoice_extractor.utils.queries import (
    fact_pads_adsp, 
    fact_pads_cm, 
    fact_pads_DV360, 
    fact_pads_sa
)

PLATFORM_CONFIGS = {
    "ADSP": {
        "query_bigq": fact_pads_adsp,
        "query_provider": """
        SELECT *
        FROM `apimonday-377411.fact_pads.adsp_provider`
        WHERE DATE(invoice_date) >= @month;
        """,
        "output_table": "adsp_validation",
    },
    "CM": {
        "query_bigq": fact_pads_cm,
        "query_provider": """
            SELECT * 
            FROM `project.dataset.cm_provider` 
            WHERE month = @month
        """,
        "output_table": "cm_validation",
    },
    "DV": {
        "query_bigq": fact_pads_DV360,
        "query_provider": """
            SELECT * 
            FROM `project.dataset.dv_provider` 
            WHERE month = @month
        """,
        "output_table": "dv_validation",
    },
    "SA": {
        "query_bigq": fact_pads_sa,
        "query_provider": """
            SELECT * 
            FROM `project.dataset.sa_provider` 
            WHERE month = @month
        """,
        "output_table": "sa_validation",
    }
}
