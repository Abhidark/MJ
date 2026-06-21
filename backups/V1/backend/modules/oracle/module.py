"""
Oracle Module -- Analytics & Data Analysis
Performs calculations, statistics, and data analysis on provided numbers.
"""

import re
import math
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.base_module import BaseModule


class OracleModule(BaseModule):
    name = "oracle"
    display_name = "Oracle"
    icon = "\U0001f4c8"  # chart increasing
    description = "Analytics -- calculations, statistics, and data analysis"
    version = "1.0"
    category = "utility"
    enabled = True

    KEYWORDS = [
        r"\banalyze\b", r"\banalysis\b", r"\bstatistics?\b", r"\bdata\b",
        r"\btrend\b", r"\bcalculat\w*\b", r"\bmath\b", r"\baverage\b",
        r"\bmean\b", r"\bmedian\b", r"\bmode\b", r"\bstd\s*dev\b",
        r"\bstandard\s+deviation\b", r"\bsum\b", r"\bpercentage\b",
        r"\bpercent\b", r"\bratio\b", r"\bgrowth\b", r"\bvariance\b",
        r"\bmin\b", r"\bmax\b", r"\brange\b", r"\bcorrelation\b",
    ]

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        text_lower = text.lower()
        for pattern in self.KEYWORDS:
            if re.search(pattern, text_lower):
                return 0.8
        # Check if there are numbers to analyze
        numbers = re.findall(r"-?\d+\.?\d*", text)
        if len(numbers) >= 3:
            return 0.6
        if intent in ("calculate", "analyze", "statistics", "math"):
            return 0.9
        return 0.0

    def _extract_numbers(self, text: str) -> list[float]:
        """Extract all numbers from text."""
        matches = re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?", text)
        numbers = []
        for m in matches:
            try:
                numbers.append(float(m.replace(",", "")))
            except ValueError:
                pass
        return numbers

    def _calculate_stats(self, numbers: list[float]) -> dict:
        """Calculate comprehensive statistics for a list of numbers."""
        n = len(numbers)
        if n == 0:
            return {}

        sorted_nums = sorted(numbers)
        total = sum(numbers)
        mean = total / n

        # Median
        if n % 2 == 0:
            median = (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
        else:
            median = sorted_nums[n // 2]

        # Mode
        counter = Counter(numbers)
        max_count = max(counter.values())
        modes = [k for k, v in counter.items() if v == max_count]
        mode = modes[0] if max_count > 1 else None

        # Variance and std dev
        variance = sum((x - mean) ** 2 for x in numbers) / n
        std_dev = math.sqrt(variance)

        # Range
        data_range = sorted_nums[-1] - sorted_nums[0]

        # Quartiles
        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        q1 = sorted_nums[q1_idx] if n >= 4 else sorted_nums[0]
        q3 = sorted_nums[q3_idx] if n >= 4 else sorted_nums[-1]

        return {
            "count": n,
            "sum": total,
            "mean": round(mean, 4),
            "median": round(median, 4),
            "mode": mode,
            "min": sorted_nums[0],
            "max": sorted_nums[-1],
            "range": round(data_range, 4),
            "variance": round(variance, 4),
            "std_dev": round(std_dev, 4),
            "q1": round(q1, 4),
            "q3": round(q3, 4),
        }

    def _detect_operation(self, text: str) -> str:
        """Detect what specific operation is being asked for."""
        text_lower = text.lower()
        if re.search(r"\baverage\b|\bmean\b", text_lower):
            return "mean"
        if re.search(r"\bmedian\b", text_lower):
            return "median"
        if re.search(r"\bmode\b", text_lower):
            return "mode"
        if re.search(r"\bsum\b|\btotal\b|\badd\b", text_lower):
            return "sum"
        if re.search(r"\bstd|standard\s+dev\b|\bdeviation\b", text_lower):
            return "std_dev"
        if re.search(r"\bvariance\b", text_lower):
            return "variance"
        if re.search(r"\bpercentage\b|\bpercent\b", text_lower):
            return "percentage"
        if re.search(r"\bgrowth\b|\bincrease\b|\bchange\b", text_lower):
            return "growth"
        return "full"

    def _eval_math_expression(self, text: str) -> tuple[float | None, str]:
        """Safely evaluate a math expression."""
        # Extract expression
        match = re.search(r"(?:calculate|compute|what\s+is|solve)\s*:?\s*(.+)", text, re.IGNORECASE)
        expr = match.group(1).strip() if match else text

        # Clean expression
        expr = re.sub(r"[^0-9+\-*/().%^ ]", "", expr)
        expr = expr.replace("^", "**")

        if not expr or not re.search(r"\d", expr):
            return None, ""

        try:
            # Safe eval with only math operations
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sqrt": math.sqrt, "pow": pow, "log": math.log,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "pi": math.pi, "e": math.e,
            }
            result = eval(expr, {"__builtins__": {}}, allowed_names)
            return result, expr
        except Exception:
            return None, expr

    def execute(self, text: str, context: dict) -> dict:
        numbers = self._extract_numbers(text)
        operation = self._detect_operation(text)

        # Try math expression first if few numbers
        if len(numbers) <= 2:
            result, expr = self._eval_math_expression(text)
            if result is not None:
                return {
                    "response": f"\U0001f9ee **Calculation Result:**\n\n  `{expr}` = **{result:,.4f}**" if isinstance(result, float) else f"\U0001f9ee **Calculation Result:**\n\n  `{expr}` = **{result}**",
                    "data": {"expression": expr, "result": result},
                    "action": "calculated",
                }

        if not numbers:
            return {
                "response": (
                    "\U0001f4ca I can analyze data for you! Please provide some numbers.\n\n"
                    "**Examples:**\n"
                    "- \"Analyze these: 10, 20, 30, 40, 50\"\n"
                    "- \"Calculate average of 85, 92, 78, 95, 88\"\n"
                    "- \"What is 15% of 2500?\""
                ),
                "data": None,
                "action": "no_data",
            }

        # Percentage calculation
        if operation == "percentage" and len(numbers) >= 2:
            pct = numbers[0]
            of_val = numbers[1]
            result = (pct / 100) * of_val
            return {
                "response": f"\U0001f4ca {pct}% of {of_val} = **{result:,.2f}**",
                "data": {"percentage": pct, "of": of_val, "result": result},
                "action": "percentage",
            }

        # Growth rate
        if operation == "growth" and len(numbers) >= 2:
            old_val, new_val = numbers[0], numbers[1]
            if old_val != 0:
                growth = ((new_val - old_val) / abs(old_val)) * 100
                trend = "\U0001f4c8" if growth >= 0 else "\U0001f4c9"
                return {
                    "response": (
                        f"{trend} **Growth Analysis:**\n\n"
                        f"  From: {old_val:,.2f}\n"
                        f"  To: {new_val:,.2f}\n"
                        f"  Change: {new_val - old_val:,.2f}\n"
                        f"  Growth Rate: **{growth:+.2f}%**"
                    ),
                    "data": {"old": old_val, "new": new_val, "growth": growth},
                    "action": "growth",
                }

        # Full statistics
        stats = self._calculate_stats(numbers)

        if operation == "mean":
            return {
                "response": f"\U0001f4ca **Mean (Average):** {stats['mean']:,.4f}",
                "data": stats,
                "action": "mean",
            }
        elif operation == "median":
            return {
                "response": f"\U0001f4ca **Median:** {stats['median']:,.4f}",
                "data": stats,
                "action": "median",
            }
        elif operation == "sum":
            return {
                "response": f"\U0001f4ca **Sum:** {stats['sum']:,.4f}",
                "data": stats,
                "action": "sum",
            }
        elif operation in ("std_dev", "variance"):
            return {
                "response": (
                    f"\U0001f4ca **Std Dev:** {stats['std_dev']:,.4f}\n"
                    f"  **Variance:** {stats['variance']:,.4f}"
                ),
                "data": stats,
                "action": "std_dev",
            }

        # Full report
        nums_str = ", ".join(f"{n:g}" for n in numbers[:20])
        lines = [
            f"\U0001f4ca **Statistical Analysis** ({stats['count']} values):\n",
            f"  Data: [{nums_str}{'...' if len(numbers) > 20 else ''}]\n",
            f"  Sum: {stats['sum']:,.4f}",
            f"  Mean: {stats['mean']:,.4f}",
            f"  Median: {stats['median']:,.4f}",
            f"  Mode: {stats['mode'] if stats['mode'] else 'No mode'}",
            f"  Min: {stats['min']:,.4f}  |  Max: {stats['max']:,.4f}",
            f"  Range: {stats['range']:,.4f}",
            f"  Std Dev: {stats['std_dev']:,.4f}",
            f"  Variance: {stats['variance']:,.4f}",
        ]
        return {
            "response": "\n".join(lines),
            "data": stats,
            "action": "full_stats",
        }

    def get_system_prompt_addition(self) -> str:
        return (
            "Provide data-driven answers with numbers and analysis. "
            "When the user provides numbers, calculate statistics and show insights."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        numbers = self._extract_numbers(text)
        if numbers:
            stats = self._calculate_stats(numbers)
            return f"[Oracle] Numbers found: {numbers}. Mean: {stats.get('mean')}, Median: {stats.get('median')}"
        return "[Oracle] Analytical query detected."

    def get_settings(self) -> dict:
        return {"enabled": self.enabled}

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
        ]
