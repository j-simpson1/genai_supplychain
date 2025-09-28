import ast
import math
import os
from typing import Any, Dict, List, Union

import pandas as pd
from langchain.agents import tool


def _get_mode_str(s: pd.Series) -> str:
    """Get the most common string value from a series."""
    mode = s.dropna().mode()
    return mode.iloc[0] if not mode.empty else ""


def _get_mode_int(s: pd.Series) -> int:
    """Get the most common integer value from a series."""
    mode = s.dropna().mode()
    return int(mode.iloc[0]) if not mode.empty else 0


def bottom_quartile_avg(s: pd.Series, ndigits: int = 2) -> float:
    """Calculate bottom quartile average using Q1 threshold."""
    s = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
    if s.empty:
        return 0.0
    if len(s) == 1:
        return round(float(s.iloc[0]), ndigits)
    q1 = s.quantile(0.25)
    val = float(s[s <= q1].mean())
    return round(val, ndigits)


@tool
def parts_summary(articles_path: str, parts_path: str) -> List[Dict[str, Any]]:
    """
    Summarizes by productId using bottom-quartile average price (<= Q1),
    counts, most-common country, quantity, line item total, and % of total.
    """
    try:
        # Load & cleanup
        articles = pd.read_csv(articles_path)
        parts = pd.read_csv(parts_path)

        articles["price"] = pd.to_numeric(articles["price"], errors="coerce")
        articles = articles.dropna(subset=["price"])
        parts["quantity"] = pd.to_numeric(parts["quantity"], errors="coerce")

        # Aggregate articles by productId
        art_summary = (
            articles.groupby("productId", dropna=False)
            .agg(
                bottomQuartileAvgPrice=("price", bottom_quartile_avg),
                numArticles=("price", "size"),
                mostCommonCountryOfOrigin=("countryOfOrigin", _get_mode_str),
            )
            .reset_index()
        )

        # One row per productId from parts (mode description & quantity)
        parts_summary_df = (
            parts.groupby("productId", dropna=False)
            .agg(
                partDescription=("partDescription", _get_mode_str),
                quantity=("quantity", _get_mode_int),
            )
            .reset_index()
        )

        # Merge + totals
        out = (
            art_summary.merge(parts_summary_df, on="productId", how="left")
            .fillna({"quantity": 0})
        )
        out["lineItemTotalExclVAT"] = (out["bottomQuartileAvgPrice"] * out["quantity"]).round(2)
        total = float(out["lineItemTotalExclVAT"].sum()) or 1.0
        out["percentageOfTotalCost"] = (out["lineItemTotalExclVAT"] / total * 100).round(2)

        # Columns + return
        out = out[
            [
                "productId",
                "partDescription",
                "bottomQuartileAvgPrice",
                "numArticles",
                "mostCommonCountryOfOrigin",
                "quantity",
                "lineItemTotalExclVAT",
                "percentageOfTotalCost",
            ]
        ]
        return out.to_dict(orient="records")

    except Exception as e:
        print(f"Error in parts_summary: {e}")
        return []


@tool
def top_5_parts_by_price(articles_path: str, parts_path: str) -> List[Dict[str, Any]]:
    """Get top 5 productIds by bottom-quartile average price with quantity and article count."""
    try:
        # Load & clean
        articles = pd.read_csv(articles_path)
        parts = pd.read_csv(parts_path)

        articles["price"] = pd.to_numeric(articles.get("price"), errors="coerce")
        articles = articles.dropna(subset=["price"])
        parts["quantity"] = pd.to_numeric(parts.get("quantity"), errors="coerce")

        # Aggregate articles by productId (prices & counts)
        art_summary = (
            articles.groupby("productId", dropna=False)
            .agg(
                bottomQuartileAvgPrice=("price", bottom_quartile_avg),
                numArticles=("price", "size"),
            )
            .reset_index()
        )

        # One row per productId from parts (mode description & quantity)
        parts_summary_df = (
            parts.groupby("productId", dropna=False)
            .agg(
                partDescription=("partDescription", _get_mode_str),
                quantity=("quantity", _get_mode_int),
            )
            .reset_index()
        )

        # Merge and select top 5 by price
        out = art_summary.merge(parts_summary_df, on="productId", how="left").fillna({"quantity": 0})
        out = out.sort_values("bottomQuartileAvgPrice", ascending=False).head(5)

        # Shape & return
        out = out[["productId", "partDescription", "bottomQuartileAvgPrice", "numArticles", "quantity"]]
        return out.to_dict(orient="records")

    except Exception as e:
        print(f"Error in top_5_parts_by_price: {e}")
        return []


@tool
def top_5_part_distribution_by_country(articles_path: str, parts_path: str = None) -> List[Dict[str, Any]]:
    """Get top 5 countries by number of unique parts (unique articleNo).

    If parts_path is provided, restricts to productIds present in parts CSV.
    """
    try:
        # Load
        articles = pd.read_csv(articles_path, dtype={"articleNo": str})
        articles["productId"] = pd.to_numeric(articles.get("productId"), errors="coerce")
        articles["countryOfOrigin"] = articles.get("countryOfOrigin").fillna("Unknown")

        # Optionally filter to productIds referenced in parts.csv
        if parts_path is not None:
            parts = pd.read_csv(parts_path)
            parts_ids = pd.to_numeric(parts.get("productId"), errors="coerce").dropna().unique()
            articles = articles[articles["productId"].isin(parts_ids)]

        # Count unique parts by country
        distribution = (
            articles.dropna(subset=["articleNo", "countryOfOrigin"])
                    .groupby("countryOfOrigin")["articleNo"]
                    .nunique()
                    .reset_index(name="parts_count")
                    .sort_values("parts_count", ascending=False)
                    .head(5)
        )

        return distribution.to_dict(orient="records")

    except Exception as e:
        print(f"Error in top_5_part_distribution_by_country: {e}")
        return []


@tool
def bottom_quartile_average_price(articles_path: str, parts_path: str) -> List[Dict[str, Any]]:
    """Get bottom quartile average price per productId with part details and line totals.

    Returns data with partDescription, quantity, taxable status, and line item total (excl. VAT).
    """
    try:
        # Load & light cleanup
        articles = pd.read_csv(articles_path, dtype={"articleNo": str})
        parts = pd.read_csv(parts_path)

        # Ensure numeric productId/price; drop rows with missing price
        articles["productId"] = pd.to_numeric(articles.get("productId"), errors="coerce")
        articles["price"] = pd.to_numeric(articles.get("price"), errors="coerce")
        articles = articles.dropna(subset=["productId", "price"])

        parts["productId"] = pd.to_numeric(parts.get("productId"), errors="coerce")
        parts = parts.dropna(subset=["productId"])
        parts = parts.drop_duplicates(subset=["productId"], keep="first")

        # Compute BQ average per productId (using shared helper)
        quartile_prices = (
            articles.groupby("productId")["price"]
                    .apply(bottom_quartile_avg)
                    .reset_index(name="bottomQuartileAvgPrice")
        )

        # Merge with parts for description/quantity/taxable
        merged = quartile_prices.merge(
            parts[["productId", "partDescription", "quantity", "taxable"]],
            on="productId",
            how="left"
        )

        # Types & defaults
        merged["partDescription"] = merged["partDescription"].fillna("")
        merged["quantity"] = pd.to_numeric(merged["quantity"], errors="coerce").fillna(0).astype(int)
        merged["taxable"] = merged["taxable"].fillna(False).astype(bool)

        # Line item total (excl. VAT)
        merged["lineItemTotalExclVAT"] = (merged["bottomQuartileAvgPrice"] * merged["quantity"]).round(2)

        # Order by price (desc)
        merged = merged.sort_values(by="bottomQuartileAvgPrice", ascending=False)

        cols = ["productId", "partDescription", "bottomQuartileAvgPrice", "quantity", "taxable", "lineItemTotalExclVAT"]
        existing_cols = [c for c in cols if c in merged.columns]
        return merged[existing_cols].to_dict(orient="records")

    except Exception as e:
        print(f"Error in top_5_part_distribution_by_country: {e}")
        return []


@tool
def total_component_price(articles_path: str, parts_path: str, vat_rate: float) -> Dict[str, float]:
    """Calculate total component cost using bottom quartile average prices.

    Charges VAT only on taxable parts. Accepts vat_rate as decimal (0.2) or percentage (20).
    """
    try:
        # Normalize VAT rate (accept 0.2 or 20)
        vat_rate = float(vat_rate)
        if vat_rate > 1:
            vat_rate = vat_rate / 100.0

        # Load & light cleanup
        articles = pd.read_csv(articles_path, dtype={"articleNo": str})
        parts = pd.read_csv(parts_path)

        articles["productId"] = pd.to_numeric(articles.get("productId"), errors="coerce")
        articles["price"] = pd.to_numeric(articles.get("price"), errors="coerce")
        articles = articles.dropna(subset=["productId", "price"])

        parts["productId"] = pd.to_numeric(parts.get("productId"), errors="coerce")
        parts["quantity"] = pd.to_numeric(parts.get("quantity"), errors="coerce")
        parts = parts.dropna(subset=["productId"])
        parts = parts.drop_duplicates(subset=["productId"], keep="first")

        # Compute BQ average per productId (using shared helper)
        bq_prices = (
            articles.groupby("productId")["price"]
                    .apply(bottom_quartile_avg)
                    .reset_index(name="avg_price")
        )

        # Merge with quantity & taxable
        merged = bq_prices.merge(
            parts[["productId", "quantity", "taxable"]],
            on="productId",
            how="left"
        )

        merged["quantity"] = merged["quantity"].fillna(0).astype(int)
        merged["taxable"] = merged["taxable"].fillna(False).astype(bool)

        # Calculate totals
        taxable_rows = merged["taxable"]
        taxable_cost = (merged.loc[taxable_rows, "avg_price"] * merged.loc[taxable_rows, "quantity"]).sum()
        nontaxable_cost = (merged.loc[~taxable_rows, "avg_price"] * merged.loc[~taxable_rows, "quantity"]).sum()

        total_excl_vat = float(round(taxable_cost + nontaxable_cost, 2))
        total_incl_vat = float(round(taxable_cost * (1 + vat_rate) + nontaxable_cost, 2))

        return {
            "totalComponentCostExclVAT": total_excl_vat,
            "totalComponentCostInclVAT": total_incl_vat
        }

    except Exception as e:
        print(f"Error in total_component_price: {e}")
        return {"totalComponentCostExclVAT": 0.0, "totalComponentCostInclVAT": 0.0}

@tool
def top_5_suppliers_by_articles(articles_path: str) -> List[Dict[str, Any]]:
    """Get the top 5 suppliers by number of unique articles."""
    try:

        # Load with sensible types
        df = pd.read_csv(articles_path, dtype={"articleNo": str})

        # Basic cleanup
        if "supplierName" not in df.columns:
            return []
        df["supplierName"] = df["supplierName"].fillna("Unknown").astype(str).str.strip()
        df = df.dropna(subset=["articleNo"])
        df["articleNo"] = df["articleNo"].astype(str).str.strip()

        # Prefer grouping by (supplierId, supplierName) if supplierId exists (avoids name collisions)
        group_cols = ["supplierId", "supplierName"] if "supplierId" in df.columns else ["supplierName"]

        supplier_counts = (
            df.groupby(group_cols)["articleNo"]
              .nunique()
              .reset_index(name="article_count")
              .sort_values("article_count", ascending=False)
              .head(5)
        )

        return supplier_counts.to_dict(orient="records")

    except Exception as e:
        print(f"Error in top_5_suppliers_by_articles: {e}")
        return []


# small calculator for the db_analyst node

_ALLOWED_NODES = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd, ast.Tuple, ast.List, ast.Call, ast.Name, ast.Expr,
    ast.Dict
}
_FUNCS = {
    "sum": sum,
    "min": min,
    "max": max,
    "round": round,
    "sqrt": math.sqrt,
    "log": math.log,   # log(x) is natural log
    "log10": math.log10,
    "mean": lambda xs: (sum(xs)/len(xs)) if xs else 0.0,
}
_NAMES = {"pi": math.pi, "e": math.e}

def _check(node: ast.AST) -> None:
    if type(node) not in _ALLOWED_NODES:
        raise ValueError(f"Disallowed expression: {type(node).__name__}")
    for child in ast.iter_child_nodes(node):
        _check(child)

def _eval(node: ast.AST) -> Union[int, float, str, List[Any]]:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        v = _eval(node.operand)
        return +v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.BinOp):
        a, b = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Add): return a + b
        if isinstance(node.op, ast.Sub): return a - b
        if isinstance(node.op, ast.Mult): return a * b
        if isinstance(node.op, ast.Div): return a / b
        if isinstance(node.op, ast.Mod): return a % b
        if isinstance(node.op, ast.FloorDiv): return a // b
        if isinstance(node.op, ast.Pow): return a ** b
        raise ValueError("Unsupported operator")
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e) for e in node.elts]
    if isinstance(node, ast.Name):
        if node.id in _NAMES: return _NAMES[node.id]
        raise ValueError(f"Unknown name: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name): raise ValueError("Only simple calls allowed")
        fname = node.func.id
        if fname not in _FUNCS: raise ValueError(f"Unknown function: {fname}")
        args = [_eval(a) for a in node.args]
        return _FUNCS[fname](*args)
    raise ValueError("Unsupported expression type")

@tool
def calculator(expression: str) -> str:
    """Safely evaluate arithmetic expressions with limited operations.

    Allowed operations: + - * / ** % //, parentheses, lists/tuples
    Allowed functions: sum/min/max/round/sqrt/log/log10/mean
    Allowed constants: pi, e
    """
    try:
        tree = ast.parse(expression, mode="eval")
        _check(tree)
        value = _eval(tree)
        return str(value)
    except Exception as e:
        return f"Error in calculator: {e}"


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Build full paths
    articles_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
    parts_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

    # Call one of the tools
    result = (total_component_price.invoke({
        "articles_path": articles_path,
        "parts_path": parts_path,
        "vat_rate": 0.2
    }))
    print(result)