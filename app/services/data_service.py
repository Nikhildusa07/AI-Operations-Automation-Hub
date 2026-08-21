from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd


SUPPORTED_EXTENSIONS = {
    ".csv",
    ".xlsx",
}


# =========================================================
# HELPERS
# =========================================================

def _safe_records(dataframe: pd.DataFrame):
    """
    Convert dataframe rows into JSON-safe dictionaries.
    """

    if dataframe.empty:
        return []

    records = dataframe.head(5).copy()

    records = records.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    records = records.where(
        pd.notna(records),
        None,
    )

    return records.to_dict(
        orient="records"
    )


def _clean_column_name(column: Any) -> str:
    """
    Normalize column names.
    """

    return (
        str(column)
        .strip()
        .replace("\n", " ")
        .replace("\t", " ")
    )


# =========================================================
# LOAD DATASET
# =========================================================

def load_dataset(
    file_bytes: bytes,
    filename: str,
) -> pd.DataFrame:

    if not filename:
        raise ValueError(
            "Filename is required."
        )

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            "Unsupported file type. "
            "Only CSV and XLSX files are supported."
        )

    if not file_bytes:
        raise ValueError(
            "Uploaded file is empty."
        )

    try:

        if extension == ".csv":
            dataframe = pd.read_csv(
                BytesIO(file_bytes)
            )

        else:
            dataframe = pd.read_excel(
                BytesIO(file_bytes)
            )

    except Exception as exc:

        raise ValueError(
            f"Unable to read dataset: {str(exc)}"
        )

    if dataframe.empty:
        raise ValueError(
            "Dataset does not contain any rows."
        )

    # Normalize column names
    dataframe.columns = [
        _clean_column_name(column)
        for column in dataframe.columns
    ]

    # Reject completely unnamed datasets
    if not any(
        str(column).strip()
        for column in dataframe.columns
    ):
        raise ValueError(
            "Dataset does not contain valid column names."
        )

    return dataframe


# =========================================================
# DATASET ANALYSIS
# =========================================================

def analyze_dataset(
    dataframe: pd.DataFrame,
    filename: str,
) -> Dict[str, Any]:

    if dataframe is None or dataframe.empty:
        raise ValueError(
            "Dataset is empty."
        )

    rows = len(dataframe)
    columns = list(dataframe.columns)

    # -----------------------------------------------------
    # Missing values
    # -----------------------------------------------------

    missing_values = {}

    for column in columns:

        missing_count = int(
            dataframe[column].isna().sum()
        )

        if missing_count > 0:
            missing_values[column] = missing_count

    total_missing_values = sum(
        missing_values.values()
    )

    # -----------------------------------------------------
    # Numeric columns
    # -----------------------------------------------------

    numeric_columns = list(
        dataframe.select_dtypes(
            include="number"
        ).columns
    )

    numeric_summary = {}

    for column in numeric_columns:

        series = dataframe[column]

        if series.dropna().empty:
            continue

        numeric_summary[column] = {
            "count": int(series.count()),
            "sum": round(
                float(series.sum()),
                2,
            ),
            "average": round(
                float(series.mean()),
                2,
            ),
            "minimum": round(
                float(series.min()),
                2,
            ),
            "maximum": round(
                float(series.max()),
                2,
            ),
        }

    # -----------------------------------------------------
    # Categorical columns
    # -----------------------------------------------------

    categorical_columns = list(
        dataframe.select_dtypes(
            include=[
                "object",
                "category",
                "bool",
            ]
        ).columns
    )

    categorical_summary = {}

    for column in categorical_columns:

        value_counts = (
            dataframe[column]
            .fillna("Missing")
            .astype(str)
            .value_counts()
            .head(10)
        )

        categorical_summary[column] = {
            str(key): int(value)
            for key, value in value_counts.items()
        }

    # -----------------------------------------------------
    # Duplicate rows
    # -----------------------------------------------------

    duplicate_rows = int(
        dataframe.duplicated().sum()
    )

    # -----------------------------------------------------
    # Completely empty rows
    # -----------------------------------------------------

    empty_rows = int(
        dataframe.isna().all(axis=1).sum()
    )

    # -----------------------------------------------------
    # Invalid records
    #
    # A record is considered invalid when:
    # 1. The complete row is empty.
    # 2. It contains non-finite numeric values.
    # -----------------------------------------------------

    invalid_record_indexes = set(
        dataframe.index[
            dataframe.isna().all(axis=1)
        ].tolist()
    )

    for column in numeric_columns:

        numeric_values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        invalid_mask = (
            dataframe[column].notna()
            & ~np.isfinite(numeric_values)
        )

        invalid_record_indexes.update(
            dataframe.index[invalid_mask].tolist()
        )

    invalid_records = len(
        invalid_record_indexes
    )

    # -----------------------------------------------------
    # Data types
    # -----------------------------------------------------

    data_types = {
        column: str(
            dataframe[column].dtype
        )
        for column in columns
    }

    # -----------------------------------------------------
    # Quality score
    # -----------------------------------------------------

    total_cells = rows * len(columns)

    if total_cells > 0:
        missing_ratio = (
            total_missing_values
            / total_cells
        )
    else:
        missing_ratio = 0

    duplicate_ratio = (
        duplicate_rows / rows
        if rows > 0
        else 0
    )

    invalid_ratio = (
        invalid_records / rows
        if rows > 0
        else 0
    )

    quality_score = max(
        0,
        round(
            100
            - (missing_ratio * 40)
            - (duplicate_ratio * 30)
            - (invalid_ratio * 30),
            2,
        ),
    )

    # -----------------------------------------------------
    # Preview
    # -----------------------------------------------------

    preview = _safe_records(
        dataframe
    )

    return {
        "filename": filename,
        "rows": rows,
        "columns": columns,
        "column_count": len(columns),

        "numeric_columns": numeric_columns,
        "numeric_summary": numeric_summary,

        "categorical_columns": categorical_columns,
        "categorical_summary": categorical_summary,

        "missing_values": missing_values,
        "total_missing_values": total_missing_values,

        "duplicate_rows": duplicate_rows,
        "empty_rows": empty_rows,
        "invalid_records": invalid_records,

        "data_types": data_types,

        "quality_score": quality_score,

        "preview": preview,
    }


# =========================================================
# AUTOMATED DATA CLEANING
# =========================================================

def clean_dataset(
    dataframe: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:

    if dataframe is None or dataframe.empty:
        raise ValueError(
            "Dataset is empty."
        )

    cleaned = dataframe.copy()

    original_rows = len(cleaned)
    original_columns = len(cleaned.columns)

    cleaning_actions = []

    # -----------------------------------------------------
    # Normalize column names
    # -----------------------------------------------------

    original_columns_list = list(
        cleaned.columns
    )

    cleaned.columns = [
        _clean_column_name(column)
        for column in cleaned.columns
    ]

    if original_columns_list != list(
        cleaned.columns
    ):
        cleaning_actions.append(
            "Normalized column names."
        )

    # -----------------------------------------------------
    # Remove completely empty rows
    # -----------------------------------------------------

    empty_rows = int(
        cleaned.isna().all(axis=1).sum()
    )

    if empty_rows > 0:

        cleaned = cleaned.dropna(
            how="all"
        )

        cleaning_actions.append(
            f"Removed {empty_rows} completely empty rows."
        )

    # -----------------------------------------------------
    # Remove completely empty columns
    # -----------------------------------------------------

    empty_columns = [
        column
        for column in cleaned.columns
        if cleaned[column].isna().all()
    ]

    if empty_columns:

        cleaned = cleaned.drop(
            columns=empty_columns
        )

        cleaning_actions.append(
            f"Removed {len(empty_columns)} completely empty columns."
        )

    # -----------------------------------------------------
    # Remove duplicate rows
    # -----------------------------------------------------

    duplicate_rows = int(
        cleaned.duplicated().sum()
    )

    if duplicate_rows > 0:

        cleaned = cleaned.drop_duplicates()

        cleaning_actions.append(
            f"Removed {duplicate_rows} duplicate rows."
        )

    # -----------------------------------------------------
    # Clean string values
    # -----------------------------------------------------

    string_columns = list(
        cleaned.select_dtypes(
            include=["object", "string"]
        ).columns
    )

    string_cleaned = False

    for column in string_columns:

        cleaned[column] = (
            cleaned[column]
            .apply(
                lambda value:
                value.strip()
                if isinstance(value, str)
                else value
            )
        )

        string_cleaned = True

    if string_cleaned:
        cleaning_actions.append(
            "Trimmed unnecessary whitespace from text values."
        )

    # -----------------------------------------------------
    # Replace invalid numeric values
    # -----------------------------------------------------

    numeric_columns = list(
        cleaned.select_dtypes(
            include="number"
        ).columns
    )

    invalid_numeric_values = 0

    for column in numeric_columns:

        series = cleaned[column]

        invalid_mask = (
            series.notna()
            & ~np.isfinite(series)
        )

        count = int(
            invalid_mask.sum()
        )

        if count > 0:

            invalid_numeric_values += count

            cleaned.loc[
                invalid_mask,
                column,
            ] = np.nan

    if invalid_numeric_values > 0:

        cleaning_actions.append(
            f"Converted {invalid_numeric_values} invalid numeric values to missing values."
        )

    # -----------------------------------------------------
    # Fill missing numeric values with median
    # -----------------------------------------------------

    numeric_filled = 0

    for column in numeric_columns:

        missing_count = int(
            cleaned[column].isna().sum()
        )

        if missing_count == 0:
            continue

        median_value = cleaned[column].median()

        if pd.notna(median_value):

            cleaned[column] = (
                cleaned[column].fillna(
                    median_value
                )
            )

            numeric_filled += missing_count

    if numeric_filled > 0:

        cleaning_actions.append(
            f"Filled {numeric_filled} missing numeric values using column medians."
        )

    # -----------------------------------------------------
    # Fill missing categorical/text values
    # -----------------------------------------------------

    categorical_columns = list(
        cleaned.select_dtypes(
            include=[
                "object",
                "string",
                "category",
            ]
        ).columns
    )

    categorical_filled = 0

    for column in categorical_columns:

        missing_count = int(
            cleaned[column].isna().sum()
        )

        if missing_count == 0:
            continue

        cleaned[column] = (
            cleaned[column].fillna(
                "Unknown"
            )
        )

        categorical_filled += missing_count

    if categorical_filled > 0:

        cleaning_actions.append(
            f"Filled {categorical_filled} missing text/categorical values with 'Unknown'."
        )

    # -----------------------------------------------------
    # Final report
    # -----------------------------------------------------

    remaining_missing = int(
        cleaned.isna().sum().sum()
    )

    final_rows = len(cleaned)
    final_columns = len(cleaned.columns)

    return cleaned, {
        "original_rows": original_rows,
        "cleaned_rows": final_rows,
        "rows_removed": (
            original_rows - final_rows
        ),

        "original_columns": original_columns,
        "cleaned_columns": final_columns,
        "columns_removed": (
            original_columns - final_columns
        ),

        "remaining_missing_values": (
            remaining_missing
        ),

        "cleaning_actions": cleaning_actions,

        "status": "CLEANED",
    }


# =========================================================
# BUSINESS INSIGHTS
# =========================================================

def generate_business_insights(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:

    insights = []
    warnings = []
    recommendations = []

    # -----------------------------------------------------
    # Dataset size
    # -----------------------------------------------------

    insights.append(
        f"Dataset contains {analysis['rows']} rows "
        f"and {analysis['column_count']} columns."
    )

    # -----------------------------------------------------
    # Quality score
    # -----------------------------------------------------

    insights.append(
        f"Overall data quality score is "
        f"{analysis['quality_score']}%."
    )

    # -----------------------------------------------------
    # Missing data
    # -----------------------------------------------------

    if analysis["missing_values"]:

        warnings.append(
            "Some columns contain missing values."
        )

        recommendations.append(
            "Review missing values and clean incomplete records."
        )

    # -----------------------------------------------------
    # Duplicate data
    # -----------------------------------------------------

    if analysis["duplicate_rows"] > 0:

        warnings.append(
            f"{analysis['duplicate_rows']} duplicate "
            "rows were detected."
        )

        recommendations.append(
            "Remove duplicate records before business analysis."
        )

    # -----------------------------------------------------
    # Invalid records
    # -----------------------------------------------------

    if analysis["invalid_records"] > 0:

        warnings.append(
            f"{analysis['invalid_records']} invalid records "
            "were detected."
        )

        recommendations.append(
            "Review invalid records before processing the dataset."
        )

    # -----------------------------------------------------
    # Empty rows
    # -----------------------------------------------------

    if analysis["empty_rows"] > 0:

        warnings.append(
            f"{analysis['empty_rows']} completely empty "
            "rows were detected."
        )

    # -----------------------------------------------------
    # Numeric insights
    # -----------------------------------------------------

    for column, values in analysis[
        "numeric_summary"
    ].items():

        insights.append(
            f"{column}: total={values['sum']}, "
            f"average={values['average']}, "
            f"minimum={values['minimum']}, "
            f"maximum={values['maximum']}."
        )

    # -----------------------------------------------------
    # Categorical insights
    # -----------------------------------------------------

    for column, values in analysis[
        "categorical_summary"
    ].items():

        if values:

            top_value = next(
                iter(values.items())
            )

            insights.append(
                f"{column}: most common value "
                f"'{top_value[0]}' appears "
                f"{top_value[1]} times."
            )

    # -----------------------------------------------------
    # Overall recommendation
    # -----------------------------------------------------

    if not warnings:

        recommendations.append(
            "Dataset passed the available data quality checks."
        )

    else:

        recommendations.append(
            "Run the automated data-cleaning workflow "
            "before using the dataset for important decisions."
        )

    return {
        "insights": insights,
        "warnings": warnings,
        "recommendations": recommendations,
    }