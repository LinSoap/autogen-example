import re
import numpy as np
import pandas as pd
from pathlib import Path
from fastmcp import FastMCP
from typing import Union, List, Any, Dict, Optional

# Initialize FastMCP
mcp = FastMCP("excel-operate-mcp")

# Supported file formats
SUPPORTED_FORMATS = [".csv", ".xlsx", ".xls"]


def get_excel_path(filename: str) -> Path:
    """
    获取 Excel 或 CSV 文件的绝对路径。

    Args:
        filename (str): 文件的绝对路径。

    Returns:
        Path: 文件的绝对路径 Path 对象。

    Raises:
        ValueError: 当文件名为空、不是字符串或不是绝对路径时抛出。
    """
    if not filename or not isinstance(filename, str):
        raise ValueError("文件名不能为空且必须为字符串")

    # 移除不可见控制字符（如 \t \n \r），以及前后空白字符
    cleaned_filename = re.sub(r"[\x00-\x1F]+", "", filename).strip()

    # 使用 Path 处理路径，跨平台兼容
    file_path = Path(cleaned_filename)

    # 验证是否为绝对路径
    if not file_path.is_absolute():
        raise ValueError(f"期望绝对路径，但收到相对路径: {filename}")

    return file_path


@mcp.tool()
async def get_excel_sheet_name(file_path: str) -> Dict[str, Any]:
    """
    Retrieves the list of sheet names from an Excel file (.xlsx or .xls format).

    Description:
        This function reads an Excel file and returns the names of all worksheets contained within it.
        It supports .xlsx and .xls file formats and performs validation to ensure the file exists and is in a supported format.

    Args:
        file_path（str）: Absolute path to the file (.xlsx or .xls).

    Returns:
        Dict[str, Any]: Dictionary with sheet names or error information.
    """

    full_path = Path(get_excel_path(file_path))
    if not full_path.exists():
        return {"status": "error", "message": f"文件未找到: {full_path}", "error_code": "FILE_NOT_FOUND"}

    try:
        if full_path.suffix.lower() not in [".xlsx", ".xls"]:
            return {
                "status": "error",
                "message": f"不支持的文件格式: {full_path.suffix}",
                "error_code": "INVALID_FORMAT",
            }

        with pd.ExcelFile(full_path, engine="openpyxl") as xls:
            sheet_names = xls.sheet_names
        return {"status": "success", "file_path": str(full_path), "sheet_names": sheet_names}

    except Exception as e:
        return {"status": "error", "message": f"获取工作表名称时发生错误: {str(e)}", "error_code": "SHEET_NAMES_ERROR"}


@mcp.tool()
async def get_column_names(
    file_path: str, sheet_name: str = "Sheet1", max_rows_to_check: int = 10, skip_non_header_rows: bool = True
) -> Dict[str, Any]:
    """
    Retrieves column names from an Excel or CSV file by detecting the header row.

    Description:
        This function identifies the header row in an Excel (.xlsx, .xls) or CSV file by finding the first row where the number of non-empty cells equals the total number of columns.
        It supports automatic header detection and optionally removes rows before the header.

    Args:
        file_path (str): Absolute path to the file (.xlsx, .xls, or .csv).
        sheet_name (str, optional): Name of the Excel worksheet (ignored for CSV). Defaults to "Sheet1".
        max_rows_to_check (int, optional): Maximum rows to scan for header detection. Defaults to 5.
        skip_non_header_rows (bool, optional): If True, skips rows before the header row. Defaults to True.

    Returns:
        Dict[str, Any]: Dictionary containing column names or error information.
    """

    full_path = Path(get_excel_path(file_path))
    if not full_path.exists():
        return {"status": "error", "message": f"文件未找到: {full_path}", "error_code": "FILE_NOT_FOUND"}

    try:
        file_extension = full_path.suffix.lower()
        if file_extension not in SUPPORTED_FORMATS:
            return {
                "status": "error",
                "message": f"不支持的文件格式: {file_extension}，支持的格式为: {', '.join(SUPPORTED_FORMATS)}",
                "error_code": "INVALID_FORMAT",
            }

        # 读取列名（仅加载表头）
        if file_extension == ".csv":
            df = pd.read_csv(full_path, encoding="utf-8", header=None, nrows=max_rows_to_check)
        else:
            df = pd.read_excel(
                full_path, sheet_name=sheet_name, header=None, nrows=max_rows_to_check, engine="openpyxl"
            )

        # 查找标题行：非空单元格数量等于总列数的第一行
        total_columns = df.shape[1]
        header_row_idx = next((idx for idx, row in df.iterrows() if row.dropna().count() == total_columns), None)
        if header_row_idx is None:
            return {
                "status": "error",
                "message": f"未找到有效的标题行（列数为 {total_columns}）。请检查文件格式。",
                "error_code": "NO_HEADER_FOUND",
            }

        # 提取标题行作为列名
        columns = df.iloc[header_row_idx].dropna().astype(str).str.strip().tolist()
        if not columns:
            return {"status": "error", "message": "未找到列名", "error_code": "NO_COLUMNS_FOUND"}

        # 如果需要，跳过非标题行
        if skip_non_header_rows and header_row_idx > 0:
            if file_extension == ".csv":
                df_clean = pd.read_csv(full_path, encoding="utf-8", skiprows=header_row_idx)
            else:
                df_clean = pd.read_excel(full_path, sheet_name=sheet_name, skiprows=header_row_idx, engine="openpyxl")

            # Save cleaned file
            if file_extension == ".csv":
                df_clean.to_csv(full_path, index=False, encoding="utf-8")
            else:
                df_clean.to_excel(full_path, sheet_name=sheet_name, index=False, engine="openpyxl")

        return {
            "status": "success",
            "file_path": str(full_path),
            "sheet_name": sheet_name if file_extension != ".csv" else None,
            "columns_count": len(columns),
            "columns": columns,
        }

    except pd.errors.EmptyDataError:
        return {"status": "error", "message": "文件为空或格式不正确。", "error_code": "EMPTY_DATA"}
    except Exception as e:
        return {"status": "error", "message": f"读取列名时发生错误: {str(e)}", "error_code": "READ_ERROR"}


@mcp.tool()
async def read_sheet_data(file_path: str, sheet_name: str = "Sheet1") -> Dict[str, Any]:
    """
    Reads the first 5 rows of an Excel or CSV file to provide a preview of its structure and content.

    Description:
        This function retrieves the first 5 rows of data from a specified Excel worksheet (.xlsx or .xls) or CSV file, including column names and their respective data types.
        It is primarily used to allow the model to understand the file's structure, content, and purpose by providing a concise data sample.

    Args:
        file_path (str): Absolute path to the file (.xlsx, .xls, or .csv).
        sheet_name (str, optional): Name of the Excel worksheet (ignored for CSV). Defaults to "Sheet1".

    Returns:
        Dict[str, Any]: Dictionary containing file data or error information.
    """

    full_path = Path(get_excel_path(file_path))
    if not full_path.exists():
        return {"status": "error", "message": f"文件未找到: {full_path}", "error_code": "FILE_NOT_FOUND"}

    try:
        # Determine file type and read accordingly
        file_extension = full_path.suffix.lower()
        if file_extension not in SUPPORTED_FORMATS:
            return {
                "status": "error",
                "message": f"不支持的文件格式: {file_extension}. 支持格式: {', '.join(SUPPORTED_FORMATS)}",
                "error_code": "INVALID_FORMAT",
            }

        if file_extension == ".csv":
            result = pd.read_csv(full_path, encoding="utf-8")
        else:
            result = pd.read_excel(full_path, sheet_name=sheet_name, engine="openpyxl")

        if result.empty:
            return {
                "status": "warning",
                "message": "文件中未找到数据",
                "data": [],
                "rows": 0,
                "columns": [],
                "file_path": str(full_path),
                "sheet_name": sheet_name if file_extension != ".csv" else None,
            }

        return {
            "status": "success",
            "file_path": str(full_path),
            "sheet_name": sheet_name if file_extension != ".csv" else None,
            "rows": result.shape[0],
            "columns": result.columns.tolist(),
            "data": result[:5].to_dict(orient="records"),
            "data_types": result.dtypes.astype(str).to_dict(),
        }

    except pd.errors.EmptyDataError:
        return {"status": "error", "message": "文件为空或格式不正确。", "error_code": "EMPTY_DATA"}
    except Exception as e:
        return {"status": "error", "message": f"读取文件时发生错误: {str(e)}", "error_code": "READ_ERROR"}


@mcp.tool()
async def read_range_sheet_data(
    file_path: str,
    sheet_name: str = "Sheet1",
    columns: Optional[Union[str, List[str]]] = None,
    condition: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieves specific data from an Excel or CSV file with optional column selection and filtering conditions.

    Description:
        This function extracts data from an Excel (.xlsx, .xls) or CSV file, allowing users to specify a subset of columns to include and apply filtering conditions to select rows based on column values.
        It is designed for flexible data extraction, enabling targeted data retrieval for further processing or analysis.

    Args:
        file_path (str): Absolute path to the file (.xlsx, .xls, or .csv).
        sheet_name (str, optional): Name of the Excel worksheet (ignored for CSV). Defaults to "Sheet1".
        columns (Optional[Union[str, List[str]]], optional): List of column names to read (all columns if None).
        condition (Optional[Dict[str, Any]], optional): Filter conditions, e.g., {"Column_Name": "Value"}.

    Returns:
        Dict[str, Any]: Dictionary containing filtered data or error information.
    """

    # 文件路径验证
    full_path = Path(get_excel_path(file_path))
    if not full_path.exists():
        return {"status": "error", "message": f"文件未找到: {full_path}", "error_code": "FILE_NOT_FOUND"}

    try:
        # 文件格式验证
        file_extension = full_path.suffix.lower()
        if file_extension not in SUPPORTED_FORMATS:
            return {
                "status": "error",
                "message": f"不支持的文件格式: {file_extension}，支持的格式为: {', '.join(SUPPORTED_FORMATS)}",
                "error_code": "INVALID_FORMAT",
            }

        # 读取数据
        if file_extension == ".csv":
            df = pd.read_csv(full_path, encoding="utf-8", usecols=columns)
        else:  # xlsx 或 xls
            df = pd.read_excel(full_path, sheet_name=sheet_name, usecols=columns, engine="openpyxl")

        if df.empty:
            return {
                "status": "warning",
                "message": "文件中未找到数据",
                "data": [],
                "row_count": 0,
                "columns": [],
                "file_path": str(full_path),
                "sheet_name": sheet_name if file_extension != ".csv" else None,
            }

        # 应用筛选条件
        if condition:
            for column, value in condition.items():
                if column not in df.columns:
                    return {"status": "error", "message": f"筛选列 '{column}' 不存在", "error_code": "INVALID_COLUMN"}
                df = df[df[column] == value]

        return {
            "status": "success",
            "file_path": str(full_path),
            "sheet_name": sheet_name if file_extension != ".csv" else None,
            "row_count": len(df),
            "columns": df.columns.tolist(),
            "data": df.to_dict(orient="records"),
        }

    except ValueError as ve:
        return {"status": "error", "message": f"工作表 {sheet_name} 不存在: {str(ve)}", "error_code": "SHEET_NOT_FOUND"}
    except Exception as e:
        return {"status": "error", "message": f"读取数据时发生错误: {str(e)}", "error_code": "DATA_READ_ERROR"}


@mcp.tool()
async def merge_multiple_data(
    file_configs: List[Dict[str, Any]],
    output_filepath: str,
    output_type: str = "file",
    output_sheet_name: str = "MergedSheet",
    merge_type: str = "append",
    merge_key: Optional[Union[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Merges multiple Excel or CSV files into a single output file or appends to an existing Excel file.

    Description:
        This function combines data from multiple Excel (.xlsx, .xls) or CSV files based on the specified merge type (append, merge, union, or intersection).
        It supports creating a new file or appends to an existing Excel file as a new sheet.
        The function validates input files, handles different merge strategies, and removes duplicate columns when necessary.

    Args:
        file_configs (List[Dict[str, Any]]): A list of dictionaries specifying input files and their sheets. Each dictionary must contain:
            - file_path (str): The absolute path to the file (.xlsx, .xls, or .csv).
            - sheet_name (str or List[str], optional): The name(s) of the Excel worksheet(s) to read (ignored for CSV). If None, all sheets are used for Excel files.
        output_filepath (str): The absolute path for the output file or target Excel file to append to.
        output_type (str, optional): The output type:
            - "file": Creates a new file (CSV or Excel).
            - "sheet": Appends to an existing Excel file as a new sheet.
            Defaults to "file".
        output_sheet_name (str, optional): The name of the output sheet for Excel files or when appending. Defaults to "MergedSheet".
        merge_type (str, optional): The merge strategy:
            - "append": Concatenates files vertically (row-wise, assuming same columns).
            - "merge": Merges files horizontally based on specified key column(s).
            - "union": Concatenates files and removes duplicate rows based on all columns.
            - "intersection": Keeps only rows present in all files (based on all columns).
            Defaults to "append".
        merge_key (Optional[Union[str, List[str]]], optional): Column(s) to use as keys for "merge" merge_type.

    Returns:
        Dict[str, Any]: Dictionary with merge result or error information.
    """
    if not file_configs:
        return {"status": "error", "message": "必须提供至少一个输入文件", "error_code": "INSUFFICIENT_FILES"}

    try:
        # Validate file paths and configurations
        output_path = Path(get_excel_path(output_filepath))
        output_ext = output_path.suffix.lower()
        if output_ext not in SUPPORTED_FORMATS:
            return {
                "status": "error",
                "message": f"不支持的输出文件格式: {output_ext}. 支持格式: {', '.join(SUPPORTED_FORMATS)}",
                "error_code": "INVALID_FORMAT",
            }

        if output_type not in ["file", "sheet"]:
            return {
                "status": "error",
                "message": f"不支持的输出类型: {output_type}. 支持类型: file, sheet",
                "error_code": "INVALID_OUTPUT_TYPE",
            }

        # Read all dataframes
        dfs = []
        input_configs = []
        for config in file_configs:
            file_path = config.get("file_path")
            sheet_name = config.get("sheet_name")
            if not file_path:
                return {"status": "error", "message": "文件配置中缺少 file_path", "error_code": "MISSING_FILEPATH"}

            path = Path(get_excel_path(file_path))
            if not path.exists():
                return {"status": "error", "message": f"文件 {path} 不存在", "error_code": "FILE_NOT_FOUND"}

            ext = path.suffix.lower()
            if ext == ".csv":
                df = pd.read_csv(path, encoding="utf-8")
                dfs.append(df)
                input_configs.append({"file_path": str(path), "sheet_name": None})
            else:
                if not sheet_name:
                    return {
                        "status": "error",
                        "message": f"Excel 文件 {path} 必须指定 sheet_name",
                        "error_code": "MISSING_SHEET_NAME",
                    }

                try:
                    df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
                    dfs.append(df)
                    input_configs.append({"file_path": str(path), "sheet_name": sheet_name})

                except ValueError as ve:
                    return {
                        "status": "error",
                        "message": f"工作表 {sheet_name} 在文件 {path} 中不存在: {str(ve)}",
                        "error_code": "SHEET_NOT_FOUND",
                    }

        if not dfs:
            return {"status": "error", "message": "未读取到有效的数据表", "error_code": "NO_VALID_DATA"}

        # Perform merge based on merge_type
        removed_columns = []
        if merge_type == "append":
            try:
                merged_df = pd.concat(dfs, ignore_index=True)
            except ValueError as e:
                return {
                    "status": "error",
                    "message": f"列名不一致，无法执行 append 合并: {str(e)}",
                    "error_code": "COLUMN_MISMATCH",
                }

        elif merge_type == "merge":
            if not merge_key:
                return {
                    "status": "error",
                    "message": "merge_type 为 'merge' 时必须提供 merge_key",
                    "error_code": "MISSING_MERGE_KEY",
                }
            merge_keys = [merge_key] if isinstance(merge_key, str) else merge_key
            for df in dfs:
                invalid_keys = [k for k in merge_keys if k not in df.columns]
                if invalid_keys:
                    return {
                        "status": "error",
                        "message": f"合并键 {invalid_keys} 在某些文件中不存在",
                        "error_code": "INVALID_MERGE_KEY",
                    }
            merged_df = dfs[0]
            for df in dfs[1:]:
                merged_df = pd.merge(merged_df, df, on=merge_keys, how="outer")

            # Detect and remove duplicate columns
            columns = merged_df.columns.tolist()
            for i, col1 in enumerate(columns):
                for col2 in columns[i + 1 :]:
                    if col1 not in merge_keys and col2 not in merge_keys:  # Skip merge keys
                        if col1 not in removed_columns and col2 not in removed_columns:
                            if merged_df[col1].equals(merged_df[col2]):
                                removed_columns.append(col2)
            if removed_columns:
                merged_df = merged_df.drop(columns=removed_columns)

        elif merge_type == "union":
            merged_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

        elif merge_type == "intersection":
            merged_df = dfs[0]
            for df in dfs[1:]:
                merged_df = pd.merge(merged_df, df, how="inner")
        else:
            return {
                "status": "error",
                "message": f"不支持的合并类型: {merge_type}. 支持类型: append, merge, union, intersection",
                "error_code": "INVALID_MERGE_TYPE",
            }

        # Save merged file based on output_type
        if output_type == "file":
            if output_ext == ".csv":
                merged_df.to_csv(output_path, index=False, encoding="utf-8")
            else:
                merged_df.to_excel(output_path, sheet_name=output_sheet_name, index=False, engine="openpyxl")
        elif output_type == "sheet":
            if output_ext == ".csv":
                return {
                    "status": "error",
                    "message": "CSV 文件不支持追加到特定 sheet",
                    "error_code": "INVALID_OUTPUT_TYPE_FOR_CSV",
                }
            # Append to existing Excel file
            if output_path.exists():
                with pd.ExcelFile(output_path, engine="openpyxl") as xls:
                    if output_sheet_name in xls.sheet_names:
                        return {
                            "status": "error",
                            "message": f"工作表 {output_sheet_name} 已存在于 {output_path}",
                            "error_code": "SHEET_ALREADY_EXISTS",
                        }
                with pd.ExcelWriter(output_path, engine="openpyxl", mode="a") as writer:
                    merged_df.to_excel(writer, sheet_name=output_sheet_name, index=False)
            else:
                # Create new Excel file if it doesn't exist
                merged_df.to_excel(output_path, sheet_name=output_sheet_name, index=False, engine="openpyxl")

        return {
            "status": "success",
            "message": f"成功合并 {len(dfs)} 个数据集到 {output_path} ({output_type}: {output_sheet_name if output_ext != '.csv' else 'CSV'})",
            "file_path": str(output_path),
            "sheet_name": output_sheet_name if output_ext != ".csv" else None,
            "rows": len(merged_df),
            "columns": merged_df.columns.tolist(),
            "merge_type": merge_type,
            "input_configs": input_configs,
        }

    except pd.errors.EmptyDataError:
        return {"status": "error", "message": "一个或多个文件为空或格式不正确", "error_code": "EMPTY_DATA"}
    except PermissionError:
        return {"status": "error", "message": f"无权限写入文件: {output_path}", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        return {"status": "error", "message": f"合并文件时发生错误: {str(e)}", "error_code": "MERGE_ERROR"}


@mcp.tool()
async def insert_row_to_excel(
    file_path: str, sheet_name: str = "Sheet1", data: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Appends one or more rows of data to an existing Excel or CSV file.

    Description:
        This function adds new rows to an existing Excel (.xlsx, .xls) or CSV file. The new data must match the column structure of the existing file.

    Args:
        file_path (str): Absolute path to the file (.xlsx, .xls, or .csv).
        sheet_name (str, optional): Name of the Excel worksheet (ignored for CSV). Defaults to "Sheet1".
        data (List[Dict[str, Any]]): Data to append as a list of dictionaries (single or multiple rows).

    Returns:
        Dict[str, Any]: Dictionary containing operation result or error information.
    """
    if not data:
        return {"status": "error", "message": "输入数据为空", "error_code": "NO_DATA"}

    try:
        full_path = Path(get_excel_path(file_path))
        file_extension = full_path.suffix.lower()

        # Check if file exists and is valid
        if not full_path.exists():
            return {"status": "error", "message": f"文件 {full_path} 不存在", "error_code": "FILE_NOT_FOUND"}
        if file_extension not in SUPPORTED_FORMATS:
            return {
                "status": "error",
                "message": f"不支持的文件格式: {file_extension}. 支持格式: {', '.join(SUPPORTED_FORMATS)}",
                "error_code": "INVALID_FORMAT",
            }

        # Read existing file
        if file_extension == ".csv":
            existing_df = pd.read_csv(full_path, encoding="utf-8")
        else:
            existing_df = pd.read_excel(full_path, sheet_name=sheet_name, engine="openpyxl")

        # Convert new data to DataFrame
        new_row = pd.DataFrame(data)
        if set(new_row.columns) != set(existing_df.columns):
            return {
                "status": "error",
                "message": "新数据的列名与现有文件不匹配",
                "error_code": "COLUMN_MISMATCH",
                "expected_columns": list(existing_df.columns),
                "provided_columns": list(new_row.columns),
            }

        # Append new row
        updated_df = pd.concat([existing_df, new_row], ignore_index=True)
        if file_extension == ".csv":
            updated_df.to_csv(full_path, index=False, encoding="utf-8")
            return {
                "status": "success",
                "message": "成功向 CSV 文件追加数据",
                "file_path": str(full_path),
                "rows_added": len(new_row),
                "total_rows": len(updated_df),
            }
        else:
            updated_df.to_excel(full_path, sheet_name=sheet_name, index=False, engine="openpyxl")
            return {
                "status": "success",
                "message": f"成功向工作表 {sheet_name} 追加数据",
                "file_path": str(full_path),
                "sheet_name": sheet_name,
                "rows_added": len(new_row),
                "total_rows": len(updated_df),
            }

    except pd.errors.EmptyDataError:
        return {"status": "error", "message": f"文件或工作表 {sheet_name} 为空或无法读取", "error_code": "EMPTY_DATA"}
    except PermissionError:
        return {"status": "error", "message": f"无权限写入文件: {full_path}", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        return {"status": "error", "message": f"追加数据时发生错误: {str(e)}", "error_code": "APPEND_ERROR"}


@mcp.tool()
async def append_column_to_excel(
    file_path: str,
    sheet_name: str = "Sheet1",
    column_name: Optional[Union[str, List[str]]] = None,
    column_data: Optional[Union[Any, List[Any]]] = None,
) -> Dict[str, Any]:
    """
    Adds one or more new columns to an existing Excel or CSV file.

    Description:
        This function appends new column(s) to an existing Excel (.xlsx, .xls) or CSV file.
        The new column(s) can be filled with a single value, a list of values matching the row count, or NaN if no data is provided.

    Args:
        file_path (str): Absolute path to the file (.xlsx, .xls, or .csv).
        sheet_name (str, optional): Name of the Excel worksheet (ignored for CSV). Defaults to "Sheet1".
        column_name (Optional[Union[str, List[str]]], optional): Name of the new column.
        column_data (Optional[Union[Any, List[Any]]], optional): Data for the new column(s).
            - None: Fills the column with NaN.
            - Single value: Applies the same value to all rows.
            - List: Must match the number of rows in the file.

    Returns:
        Dict[str, Any]: Dictionary containing operation result or error information.
    """
    if not column_name:
        return {"status": "error", "message": "必须提供新列的名称", "error_code": "NO_COLUMN_NAME"}

    try:
        full_path = Path(get_excel_path(file_path))
        file_extension = full_path.suffix.lower()

        # Check if file exists and is valid
        if not full_path.exists():
            return {"status": "error", "message": f"文件 {full_path} 不存在", "error_code": "FILE_NOT_FOUND"}
        if file_extension not in SUPPORTED_FORMATS:
            return {
                "status": "error",
                "message": f"不支持的文件格式: {file_extension}. 支持格式: {', '.join(SUPPORTED_FORMATS)}",
                "error_code": "INVALID_FORMAT",
            }

        # Read existing file
        if file_extension == ".csv":
            df = pd.read_csv(full_path, encoding="utf-8")
        else:
            df = pd.read_excel(full_path, sheet_name=sheet_name, engine="openpyxl")

        # Handle single or multiple column names
        column_names = [column_name] if isinstance(column_name, str) else column_name
        for col in column_names:
            if col in df.columns:
                if df[col].isna().all():
                    pass
                else:
                    return {
                        "status": "error",
                        "message": f"列名 {col} 已存在且包含非空数据，无法覆盖",
                        "error_code": "COLUMN_EXISTS_NON_EMPTY",
                    }

        row_count = len(df)
        if isinstance(column_data, list) and len(column_data) != row_count:
            return {
                "status": "error",
                "message": f"列数据长度 {len(column_data)} 与文件行数 {row_count} 不匹配",
                "error_code": "DATA_LENGTH_MISMATCH",
                "expected_length": row_count,
                "provided_length": len(column_data),
            }

        # Add columns
        for col in column_names:
            if column_data is None:
                df[col] = np.nan
            elif isinstance(column_data, list):
                df[col] = column_data
            else:
                df[col] = column_data

        # Save updated file
        if file_extension == ".csv":
            df.to_csv(full_path, index=False, encoding="utf-8")
            return {
                "status": "success",
                "message": f"成功向 CSV 文件添加列 {', '.join(column_names)}",
                "file_path": str(full_path),
                "new_column_names": column_names,
            }
        else:
            df.to_excel(full_path, sheet_name=sheet_name, index=False, engine="openpyxl")
            return {
                "status": "success",
                "message": f"成功向工作表 {sheet_name} 添加列 {', '.join(column_names)}",
                "file_path": str(full_path),
                "sheet_name": sheet_name,
                "new_column_names": column_names,
            }

    except pd.errors.EmptyDataError:
        return {"status": "error", "message": f"文件或工作表 {sheet_name} 为空或无法读取", "error_code": "EMPTY_DATA"}
    except PermissionError:
        return {"status": "error", "message": f"无权限写入文件: {full_path}", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        return {"status": "error", "message": f"添加列时发生错误: {str(e)}", "error_code": "ADD_COLUMN_ERROR"}


@mcp.tool()
async def delete_excel_row_or_column(
    file_path: str,
    sheet_name: str = "Sheet1",
    row: Optional[Union[int, List[int]]] = None,
    column: Optional[Union[str, List[str]]] = None,
    condition: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deletes specific rows, columns, or rows matching a condition from an Excel or CSV file.

    Description:
        This function removes specified rows (by index), columns (by name), or rows matching a given condition from an Excel (.xlsx, .xls) or CSV file.

    Args:
        file_path (str): Absolute path to the file (.xlsx, .xls, or .csv).
        sheet_name (str, optional): Name of the Excel worksheet (ignored for CSV). Defaults to "Sheet1".
        row (Optional[Union[int, List[int]]], optional): Row index(es) to delete (0-based). Defaults to None.
        column (Optional[Union[str, List[str]]], optional): Column name(s) to delete. Defaults to None.
        condition (Optional[Dict[str, Any]], optional): Filter condition, e.g., {"Column_Name": "Value"}.

    Returns:
        Dict[str, Any]: Dictionary containing operation result or error information.
    """
    # 验证输入参数
    if row is None and column is None and condition is None:
        return {
            "status": "error",
            "message": "必须指定要删除的行索引、列名或筛选条件",
            "error_code": "NO_DELETE_CRITERIA",
        }

    try:
        full_path = Path(get_excel_path(file_path))
        file_extension = full_path.suffix.lower()

        # 检查文件是否存在和格式是否有效
        if not full_path.exists():
            return {"status": "error", "message": f"文件 {full_path} 不存在", "error_code": "FILE_NOT_FOUND"}
        if file_extension not in SUPPORTED_FORMATS:
            return {
                "status": "error",
                "message": f"不支持的文件格式: {file_extension}，支持格式: {', '.join(SUPPORTED_FORMATS)}",
                "error_code": "INVALID_FORMAT",
            }

        # 读取文件
        if file_extension == ".csv":
            df = pd.read_csv(full_path, encoding="utf-8")
        else:
            df = pd.read_excel(full_path, sheet_name=sheet_name, engine="openpyxl")

        # 处理行删除（支持负索引）
        operation = []
        row_count = len(df)
        if row is not None:
            rows_to_delete = [row] if isinstance(row, int) else row
            # 将负索引转换为正索引
            normalized_rows = []
            for r in rows_to_delete:
                if r >= 0:
                    normalized_rows.append(r)
                else:
                    normalized_row = row_count + r
                    if normalized_row < 0:
                        return {
                            "status": "error",
                            "message": f"行索引 {r} 超出范围（有效范围: -{row_count} 到 {row_count-1}）",
                            "error_code": "INVALID_ROW_INDEX",
                        }
                    normalized_rows.append(normalized_row)

            # 验证正索引是否有效
            invalid_rows = [r for r in normalized_rows if not (0 <= r < row_count)]
            if invalid_rows:
                return {
                    "status": "error",
                    "message": f"行索引 {invalid_rows} 超出范围（有效范围: 0 到 {row_count-1}）",
                    "error_code": "INVALID_ROW_INDEX",
                }
            # 使用转换后的正索引进行删除
            df = df.drop(index=normalized_rows).reset_index(drop=True)
            operation.append(f"行 {rows_to_delete}")

        # 处理列删除
        if column is not None:
            columns_to_delete = [column] if isinstance(column, str) else column
            invalid_columns = [c for c in columns_to_delete if c not in df.columns]
            if invalid_columns:
                return {
                    "status": "error",
                    "message": f"列名 {invalid_columns} 不存在于文件",
                    "error_code": "COLUMN_NOT_FOUND",
                }
            df = df.drop(columns=columns_to_delete)
            operation.append(f"列 {columns_to_delete}")

        # 根据条件删除行
        if condition is not None:
            for col, val in condition.items():
                if col not in df.columns:
                    return {"status": "error", "message": f"列名 {col} 不存在于文件", "error_code": "COLUMN_NOT_FOUND"}
                initial_rows = len(df)
                df = df[df[col] != val].reset_index(drop=True)
                deleted_rows = initial_rows - len(df)
                if deleted_rows == 0:
                    return {
                        "status": "warning",
                        "message": f"未找到列 {col} 中值为 {val} 的行",
                        "error_code": "NO_MATCHING_ROWS",
                    }
                operation.append(f"{deleted_rows} 行（列 {col} 中值为 {val}）")

        if not operation:
            return {"status": "error", "message": "无效的操作组合", "error_code": "INVALID_OPERATION"}

        # 将更新后的 DataFrame 写回文件
        if file_extension == ".csv":
            df.to_csv(full_path, index=False, encoding="utf-8")
            return {
                "status": "success",
                "message": f"成功从 CSV 文件删除 {', '.join(operation)}",
                "file_path": str(full_path),
                "operations": operation,
                "remaining_rows": len(df),
            }
        else:
            df.to_excel(full_path, sheet_name=sheet_name, index=False, engine="openpyxl")
            return {
                "status": "success",
                "message": f"成功从工作表 {sheet_name} 删除 {', '.join(operation)}",
                "file_path": str(full_path),
                "sheet_name": sheet_name,
                "operations": operation,
                "remaining_rows": len(df),
            }

    except pd.errors.EmptyDataError:
        return {"status": "error", "message": f"文件或工作表 {sheet_name} 为空或无法读取", "error_code": "EMPTY_DATA"}
    except PermissionError:
        return {"status": "error", "message": f"无权限写入文件: {full_path}", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        return {"status": "error", "message": f"删除数据时发生错误: {str(e)}", "error_code": "DELETE_ERROR"}


@mcp.tool()
async def sort_excel_data(
    file_path: str,
    sheet_name: str = "Sheet1",
    sort_columns: Union[str, List[str]] = None,
    ascending: Union[bool, List[bool]] = True,
    top_n: Optional[int] = 10,
) -> Dict[str, Any]:
    """
    Sorts data in an Excel or CSV file by specified columns and returns the sorted data, optionally limited to the top N rows.

    Description:
        This function sorts the data in an Excel (.xlsx, .xls) or CSV file based on one or more specified columns and sort orders (ascending or descending).
        It can return all sorted rows or a specified number of top rows.

    Args:
        file_path (str): The absolute path to the input file (.xlsx, .xls, or .csv).
        sheet_name (str, optional): The name of the Excel worksheet to sort (ignored for CSV files). Defaults to "Sheet1".
        sort_columns (Union[str, List[str]], optional): The column(s) to sort by. If None, returns the original data unsorted.
        ascending (Union[bool, List[bool]], optional): The sort order for each column (True for ascending, False for descending). If a single bool, applies to all columns. Defaults to True.
        top_n (Optional[int], optional): The number of top rows to return. If None, returns all sorted rows. Defaults to 10.

    Returns:
        Dict[str, Any]: Dictionary containing sorted data or error information.
    """
    try:
        # Validate input file
        full_path = Path(get_excel_path(file_path))
        if not full_path.exists():
            return {"status": "error", "message": f"文件 {full_path} 不存在", "error_code": "FILE_NOT_FOUND"}

        file_extension = full_path.suffix.lower()
        if file_extension not in SUPPORTED_FORMATS:
            return {
                "status": "error",
                "message": f"不支持的文件格式: {file_extension}. 支持格式: {', '.join(SUPPORTED_FORMATS)}",
                "error_code": "INVALID_FORMAT",
            }

        # Read data
        if file_extension == ".csv":
            df = pd.read_csv(full_path, encoding="utf-8")
        else:
            df = pd.read_excel(full_path, sheet_name=sheet_name, engine="openpyxl")

        if df.empty:
            return {
                "status": "warning",
                "message": "文件中未找到数据",
                "file_path": str(full_path),
                "sheet_name": sheet_name if file_extension != ".csv" else None,
                "sort_columns": [],
                "ascending": [],
                "row_count": 0,
                "columns": [],
                "data": [],
            }

        # Validate sort columns
        if not sort_columns:
            return {
                "status": "warning",
                "message": "未指定排序列，返回原始数据",
                "file_path": str(full_path),
                "sheet_name": sheet_name if file_extension != ".csv" else None,
                "sort_columns": [],
                "ascending": [],
                "row_count": len(df),
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
            }

        sort_cols = [sort_columns] if isinstance(sort_columns, str) else sort_columns
        invalid_cols = [col for col in sort_cols if col not in df.columns]
        if invalid_cols:
            return {
                "status": "error",
                "message": f"排序列 {invalid_cols} 不存在于文件中",
                "error_code": "INVALID_SORT_COLUMN",
            }

        # Validate ascending parameter
        asc = ascending if isinstance(ascending, list) else [ascending] * len(sort_cols)
        if len(asc) != len(sort_cols):
            return {
                "status": "error",
                "message": f"排序顺序参数数量 {len(asc)} 与排序列数量 {len(sort_cols)} 不匹配",
                "error_code": "ASCENDING_MISMATCH",
            }

        # Perform sorting
        sorted_df = df.sort_values(by=sort_cols, ascending=asc)

        # Select top N rows if specified
        if top_n is not None:
            if top_n <= 0:
                return {"status": "error", "message": "top_n 必须为正整数", "error_code": "INVALID_TOP_N"}
            sorted_df = sorted_df.head(top_n)

        return {
            "status": "success",
            "message": f"成功对列 {sort_cols} 进行排序",
            "file_path": str(full_path),
            "sheet_name": sheet_name if file_extension != ".csv" else None,
            "sort_columns": sort_cols,
            "ascending": asc,
            "row_count": len(sorted_df),
            "columns": sorted_df.columns.tolist(),
            "data": sorted_df.to_dict(orient="records"),
        }

    except pd.errors.EmptyDataError:
        return {"status": "error", "message": "文件为空或格式不正确", "error_code": "EMPTY_DATA"}
    except Exception as e:
        return {"status": "error", "message": f"排序数据时发生错误: {str(e)}", "error_code": "SORT_ERROR"}


def main():
    # mcp.run(transport="stdio")
    mcp.run(transport="sse", host="127.0.0.1", port=8000, log_level="info")  # 绑定到本机  # 可修改端口  # 或 "debug"
    return mcp


if __name__ == "__main__":
    main()
