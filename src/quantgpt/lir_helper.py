# src/quantgpt/lir_helper.py
import sqlite3

def get_lir_scores(assessment_id: int, db_path: str) -> str:
    """
    Given an assessment_id, look up lir_id from risk_assessments table,
    then return a string "L I R" from the lir table.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 1: get lir_id from assessments
    cursor.execute("SELECT lir_id FROM risk_assessments WHERE assessment_id = ?", (assessment_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "N/A"
    lir_id = row[0]

    # Step 2: get likelihood, impact, overall_risk from lir
    cursor.execute("SELECT likelihood, impact, overall_risk FROM lir WHERE lir_id = ?", (lir_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return row
    else:
        return "N/A"