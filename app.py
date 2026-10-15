import re
from typing import Any, Dict, List, Tuple, Union
import numpy as np
import sympy as sp
import streamlit as st


# =====================================================================
# 1. CORE BUSINESS LOGIC
# =====================================================================

class MathEvaluator:
    """Safe evaluation of basic and scientific mathematical expressions."""

    ALLOWED_NAMES: Dict[str, Any] = {
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "sqrt": sp.sqrt,
        "log": sp.log,
        "ln": sp.log,
        "exp": sp.exp,
        "abs": sp.Abs,
        "pi": sp.pi,
        "e": sp.E,
        "factorial": sp.factorial,
    }

    @classmethod
    def evaluate(cls, expression: str) -> Tuple[float, str]:
        """Parses and evaluates a mathematical string into numerical float and exact form."""
        if not expression or not expression.strip():
            raise ValueError("Expression cannot be empty.")

        clean_expr = expression.replace("^", "**").strip()
        # Safety check: allow only digits, basic operators, symbols, dots, parentheses
        if not re.match(r"^[0-9a-zA-Z_\+\-\*/\^\(\)\.,\s]+$", clean_expr):
            raise ValueError("Invalid characters detected in expression.")

        try:
            parsed = sp.sympify(clean_expr, locals=cls.ALLOWED_NAMES)
            numerical_val = float(parsed.evalf())
            exact_str = str(parsed)
            return numerical_val, exact_str
        except Exception as e:
            raise ValueError(f"Could not evaluate expression: {e}") from e


class EquationSolver:
    """Solves algebraic equations and systems of equations symbolically."""

    @staticmethod
    def solve_single(eq_string: str, var_name: str = "x") -> List[str]:
        """Solves an equation like 'x**2 - 4 = 0' or '2*x + 5 = 15'."""
        if not eq_string or not eq_string.strip():
            raise ValueError("Equation string cannot be empty.")

        clean_eq = eq_string.replace("^", "**").strip()
        var = sp.Symbol(var_name)

        if "=" in clean_eq:
            parts = clean_eq.split("=")
            if len(parts) != 2:
                raise ValueError("Equation must have exactly one '=' sign.")
            lhs = sp.sympify(parts[0])
            rhs = sp.sympify(parts[1])
            target_eq = sp.Eq(lhs, rhs)
        else:
            target_eq = sp.Eq(sp.sympify(clean_eq), 0)

        solutions = sp.solve(target_eq, var)
        return [str(sol) for sol in solutions]

    @staticmethod
    def solve_linear_system(eqs: List[str], vars_list: List[str]) -> Dict[str, str]:
        """Solves a system of equations given a list of equation strings and variables."""
        if not eqs or not vars_list:
            raise ValueError("Equations and variables cannot be empty.")

        symbols = [sp.Symbol(v.strip()) for v in vars_list]
        parsed_eqs = []
        for eq_str in eqs:
            eq_clean = eq_str.replace("^", "**").strip()
            if "=" in eq_clean:
                lhs, rhs = eq_clean.split("=", 1)
                parsed_eqs.append(sp.Eq(sp.sympify(lhs), sp.sympify(rhs)))
            else:
                parsed_eqs.append(sp.Eq(sp.sympify(eq_clean), 0))

        solution = sp.solve(parsed_eqs, symbols, dict=True)
        if not solution:
            return {}
        
        res = {}
        for sym in symbols:
            if sym in solution[0]:
                res[str(sym)] = str(solution[0][sym])
        return res


class UnitConverter:
    """Handles dimensional analysis and unit conversions across standard metrics."""

    CONVERSIONS: Dict[str, Dict[str, float]] = {
        "Length/Height": {
            "m": 1.0,
            "km": 1000.0,
            "cm": 0.01,
            "mm": 0.001,
            "inch": 0.0254,
            "ft": 0.3048,
            "yard": 0.9144,
            "mile": 1609.344,
        },
        "Area": {
            "sq_m": 1.0,
            "sq_km": 1_000_000.0,
            "sq_cm": 0.0001,
            "sq_ft": 0.09290304,
            "sq_yd": 0.83612736,
            "acre": 4046.8564224,
            "hectare": 10000.0,
        },
        "Volume": {
            "cu_m": 1.0,
            "liter": 0.001,
            "ml": 0.000001,
            "cu_ft": 0.028316846592,
            "gallon_us": 0.003785411784,
            "quart_us": 0.000946352946,
        },
        "Mass": {
            "kg": 1.0,
            "g": 0.001,
            "mg": 0.000001,
            "lb": 0.45359237,
            "oz": 0.028349523125,
            "tonne": 1000.0,
        },
    }

    @classmethod
    def convert(cls, value: float, category: str, from_unit: str, to_unit: str) -> float:
        if category == "Temperature":
            return cls._convert_temperature(value, from_unit, to_unit)

        if category not in cls.CONVERSIONS:
            raise ValueError(f"Unsupported category: {category}")

        cat_units = cls.CONVERSIONS[category]
        if from_unit not in cat_units or to_unit not in cat_units:
            raise ValueError(f"Units must be in {list(cat_units.keys())}")

        # Convert to base unit then to target unit
        base_val = value * cat_units[from_unit]
        return base_val / cat_units[to_unit]

    @staticmethod
    def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
        units = {"Celsius", "Fahrenheit", "Kelvin"}
        if from_unit not in units or to_unit not in units:
            raise ValueError(f"Temperature unit must be one of {units}")

        # Standardize to Celsius
        if from_unit == "Celsius":
            c = value
        elif from_unit == "Fahrenheit":
            c = (value - 32.0) * 5.0 / 9.0
        else:  # Kelvin
            c = value - 273.15

        # Convert to target
        if to_unit == "Celsius":
            return c
        elif to_unit == "Fahrenheit":
            return (c * 9.0 / 5.0) + 32.0
        else:  # Kelvin
            return c + 273.15


class MatrixEngine:
    """Linear algebra engine including matrix solving and 1D/2D convolution."""

    @staticmethod
    def add(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.add(a, b)

    @staticmethod
    def subtract(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.subtract(a, b)

    @staticmethod
    def multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.matmul(a, b)

    @staticmethod
    def transpose(a: np.ndarray) -> np.ndarray:
        return np.transpose(a)

    @staticmethod
    def determinant(a: np.ndarray) -> float:
        if a.shape[0] != a.shape[1]:
            raise ValueError("Determinant requires a square matrix.")
        return float(np.linalg.det(a))

    @staticmethod
    def inverse(a: np.ndarray) -> np.ndarray:
        if a.shape[0] != a.shape[1]:
            raise ValueError("Inverse requires a square matrix.")
        det = np.linalg.det(a)
        if np.isclose(det, 0.0):
            raise ValueError("Matrix is singular and non-invertible.")
        return np.linalg.inv(a)

    @staticmethod
    def solve_linear(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Solves Ax = b."""
        if a.shape[0] != a.shape[1]:
            raise ValueError("Matrix A must be square to solve Ax = b.")
        if np.isclose(np.linalg.det(a), 0.0):
            raise ValueError("Matrix A is singular; no unique solution.")
        return np.linalg.solve(a, b)

    @staticmethod
    def convolve_1d(signal: np.ndarray, kernel: np.ndarray, mode: str = "full") -> np.ndarray:
        """Computes 1D discrete convolution."""
        if signal.ndim != 1 or kernel.ndim != 1:
            raise ValueError("Signal and kernel must both be 1-dimensional.")
        if len(signal) == 0 or len(kernel) == 0:
            raise ValueError("Arrays cannot be empty.")
        return np.convolve(signal, kernel, mode=mode)

    @staticmethod
    def convolve_2d(matrix: np.ndarray, kernel: np.ndarray, mode: str = "same") -> np.ndarray:
        """Pure NumPy 2D convolution supporting 'full', 'valid', and 'same' modes."""
        if matrix.ndim != 2 or kernel.ndim != 2:
            raise ValueError("Matrix and kernel must both be 2-dimensional.")

        m_h, m_w = matrix.shape
        k_h, k_w = kernel.shape
        if m_h == 0 or m_w == 0 or k_h == 0 or k_w == 0:
            raise ValueError("Matrix dimensions must be non-zero.")

        # Rotate kernel 180 degrees for true convolution
        k_flipped = np.flipud(np.fliplr(kernel))

        if mode == "full":
            pad_h, pad_w = k_h - 1, k_w - 1
            padded = np.pad(matrix, ((pad_h, pad_h), (pad_w, pad_w)), mode="constant")
            out_h = m_h + k_h - 1
            out_w = m_w + k_w - 1
            out = np.zeros((out_h, out_w), dtype=float)
            for i in range(out_h):
                for j in range(out_w):
                    out[i, j] = np.sum(padded[i : i + k_h, j : j + k_w] * k_flipped)
            return out

        elif mode == "valid":
            if m_h < k_h or m_w < k_w:
                raise ValueError("Matrix dimensions must be >= kernel dimensions for 'valid' mode.")
            out_h = m_h - k_h + 1
            out_w = m_w - k_w + 1
            out = np.zeros((out_h, out_w), dtype=float)
            for i in range(out_h):
                for j in range(out_w):
                    out[i, j] = np.sum(matrix[i : i + k_h, j : j + k_w] * k_flipped)
            return out

        elif mode == "same":
            pad_top = k_h // 2
            pad_bottom = k_h - 1 - pad_top
            pad_left = k_w // 2
            pad_right = k_w - 1 - pad_left
            padded = np.pad(matrix, ((pad_top, pad_bottom), (pad_left, pad_right)), mode="constant")
            out = np.zeros((m_h, m_w), dtype=float)
            for i in range(m_h):
                for j in range(m_w):
                    out[i, j] = np.sum(padded[i : i + k_h, j : j + k_w] * k_flipped)
            return out

        else:
            raise ValueError("Mode must be 'full', 'valid', or 'same'.")


# =====================================================================
# 2. STREAMLIT USER INTERFACE
# =====================================================================

def parse_matrix_input(text: str) -> np.ndarray:
    """Converts multiline string of numbers into a 2D numpy array."""
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    if not lines:
        raise ValueError("Matrix input cannot be empty.")
    data = [[float(val.strip()) for val in re.split(r"[,\s]+", line)] for line in lines]
    # Check equal length rows
    row_lens = {len(r) for r in data}
    if len(row_lens) > 1:
        raise ValueError("All rows in the matrix must have the same number of columns.")
    return np.array(data, dtype=float)


def render_ui():
    st.set_page_config(page_title="OmniCalc Pro & Matrix Engine", page_icon="🧮", layout="wide")
    st.title("🧮 OmniCalc Pro & Matrix Engine")
    st.caption("Basic & Scientific Math, Symbolic Equations, Metric Converter, Linear Algebra & Convolution")

    tabs = st.tabs([
        "🔢 Math Calculator",
        "📐 Equation Solver",
        "🔄 Metric Converter",
        "🔳 Matrix & Convolution"
    ])

    # TAB 1: MATH CALCULATOR
    with tabs[0]:
        st.header("Basic & Scientific Math")
        col1, col2 = st.columns([2, 1])
        with col1:
            expr = st.text_input("Enter expression:", value="sqrt(16) + 3^2 * cos(pi/3)")
            if st.button("Calculate Expression", key="btn_eval"):
                try:
                    val, exact = MathEvaluator.evaluate(expr)
                    st.success(f"Result: **{val}**")
                    st.info(f"Exact symbolic representation: `{exact}`")
                except Exception as ex:
                    st.error(str(ex))
        with col2:
            st.markdown("**Supported Operations:**")
            st.code("+, -, *, /, ^, sqrt(), log(), sin(), cos(), tan(), abs(), pi, e, factorial()")

    # TAB 2: EQUATION SOLVER
    with tabs[1]:
        st.header("Symbolic Equation Solver")
        eq_mode = st.radio("Solver Mode", ["Single Variable", "System of Linear Equations"], horizontal=True)

        if eq_mode == "Single Variable":
            eq_input = st.text_input("Equation (e.g. 2*x^2 - 8 = 0 or 3*x + 5 = 20):", value="x^2 - 5*x + 6 = 0")
            var_sym = st.text_input("Variable to solve for:", value="x")
            if st.button("Solve Equation", key="btn_eq_single"):
                try:
                    roots = EquationSolver.solve_single(eq_input, var_sym)
                    st.write(f"Found **{len(roots)}** solution(s):" if roots else "No solutions found.")
                    for idx, root in enumerate(roots, 1):
                        st.latex(f"{var_sym}_{{{idx}}} = {root}")
                except Exception as ex:
                    st.error(str(ex))
        else:
            st.markdown("Enter linear equations separated by newlines:")
            eq_sys = st.text_area("Equations:", value="2*x + y = 10\nx - y = 2", height=100)
            sys_vars = st.text_input("Variables (comma-separated):", value="x, y")
            if st.button("Solve System", key="btn_eq_sys"):
                try:
                    v_list = [v.strip() for v in sys_vars.split(",")]
                    eqs_list = [l.strip() for l in eq_sys.split("\n") if l.strip()]
                    results = EquationSolver.solve_linear_system(eqs_list, v_list)
                    if results:
                        st.success("Solution found:")
                        for k, v in results.items():
                            st.latex(f"{k} = {v}")
                    else:
                        st.warning("No unique solution found or system is inconsistent.")
                except Exception as ex:
                    st.error(str(ex))

    # TAB 3: METRIC CONVERTER
    with tabs[2]:
        st.header("Metric & Imperial Converter")
        cat = st.selectbox("Category", list(UnitConverter.CONVERSIONS.keys()) + ["Temperature"])

        if cat == "Temperature":
            avail_units = ["Celsius", "Fahrenheit", "Kelvin"]
        else:
            avail_units = list(UnitConverter.CONVERSIONS[cat].keys())

        c1, c2, c3 = st.columns(3)
        with c1:
            val = st.number_input("Value to Convert", value=100.0, format="%f")
        with c2:
            from_u = st.selectbox("From Unit", avail_units, index=0)
        with c3:
            to_u = st.selectbox("To Unit", avail_units, index=1 if len(avail_units) > 1 else 0)

        if st.button("Convert Units", key="btn_conv"):
            try:
                converted = UnitConverter.convert(val, cat, from_u, to_u)
                st.metric(label=f"{from_u} -> {to_u}", value=f"{converted:.6g}")
            except Exception as ex:
                st.error(str(ex))

    # TAB 4: MATRIX & CONVOLUTION
    with tabs[3]:
        st.header("Matrix Calculator & Convolution Engine")
        m_feature = st.selectbox(
            "Choose Operation",
            ["Basic Linear Algebra", "Solve Ax = b", "1D Convolution", "2D Convolution"]
        )

        if m_feature == "Basic Linear Algebra":
            st.subheader("Matrix Operations")
            c_a, c_b = st.columns(2)
            with c_a:
                raw_a = st.text_area("Matrix A (rows separated by newlines, cols by spaces/commas):", value="1 2\n3 4")
            with c_b:
                raw_b = st.text_area("Matrix B (Optional for unary ops):", value="5 6\n7 8")

            op = st.selectbox("Operation", ["A + B", "A - B", "A * B", "Transpose(A)", "Determinant(A)", "Inverse(A)"])
            if st.button("Compute", key="btn_mat_basic"):
                try:
                    mat_a = parse_matrix_input(raw_a)
                    if op == "Transpose(A)":
                        res = MatrixEngine.transpose(mat_a)
                        st.write("**Result:**"); st.dataframe(res)
                    elif op == "Determinant(A)":
                        det = MatrixEngine.determinant(mat_a)
                        st.metric("Determinant of A", f"{det:.6g}")
                    elif op == "Inverse(A)":
                        res = MatrixEngine.inverse(mat_a)
                        st.write("**Inverse Matrix:**"); st.dataframe(res)
                    else:
                        mat_b = parse_matrix_input(raw_b)
                        if op == "A + B":
                            res = MatrixEngine.add(mat_a, mat_b)
                        elif op == "A - B":
                            res = MatrixEngine.subtract(mat_a, mat_b)
                        else:
                            res = MatrixEngine.multiply(mat_a, mat_b)
                        st.write("**Result:**"); st.dataframe(res)
                except Exception as ex:
                    st.error(str(ex))

        elif m_feature == "Solve Ax = b":
            st.subheader("Solve Linear System Ax = b")
            c_a, c_b = st.columns([2, 1])
            with c_a:
                raw_a = st.text_area("Square Matrix A:", value="2 1\n1 3")
            with c_b:
                raw_b = st.text_area("Vector b (1D or single column):", value="8\n13")

            if st.button("Solve System", key="btn_mat_solve"):
                try:
                    mat_a = parse_matrix_input(raw_a)
                    vec_b = parse_matrix_input(raw_b).flatten()
                    sol = MatrixEngine.solve_linear(mat_a, vec_b)
                    st.success("Solution Vector x:")
                    st.dataframe(sol.reshape(-1, 1))
                except Exception as ex:
                    st.error(str(ex))

        elif m_feature == "1D Convolution":
            st.subheader("1D Discrete Convolution")
            sig_txt = st.text_input("Signal vector (space-separated):", value="1 2 3 4 5")
            ker_txt = st.text_input("Kernel vector (space-separated):", value="1 0 -1")
            mode_1d = st.selectbox("Mode", ["full", "same", "valid"])

            if st.button("Run 1D Convolution", key="btn_conv1d"):
                try:
                    sig = np.array([float(x) for x in re.split(r"[,\s]+", sig_txt.strip())])
                    ker = np.array([float(x) for x in re.split(r"[,\s]+", ker_txt.strip())])
                    result = MatrixEngine.convolve_1d(sig, ker, mode=mode_1d)
                    st.write("**Convolved Signal:**")
                    st.line_chart(result)
                    st.dataframe(result.reshape(1, -1))
                except Exception as ex:
                    st.error(str(ex))

        elif m_feature == "2D Convolution":
            st.subheader("2D Matrix Convolution / Image Filtering")
            c1, c2 = st.columns(2)
            with c1:
                mat_2d_txt = st.text_area("Input Matrix / Image:", value="1 2 3 4\n5 6 7 8\n9 10 11 12\n13 14 15 16")
            with c2:
                preset = st.selectbox("Preset Kernels", ["Custom", "Sobel Horizontal", "Sobel Vertical", "Box Blur", "Sharpen"])
                if preset == "Sobel Horizontal":
                    def_k = "-1 -2 -1\n0 0 0\n1 2 1"
                elif preset == "Sobel Vertical":
                    def_k = "-1 0 1\n-2 0 2\n-1 0 1"
                elif preset == "Box Blur":
                    def_k = "0.111 0.111 0.111\n0.111 0.111 0.111\n0.111 0.111 0.111"
                elif preset == "Sharpen":
                    def_k = "0 -1 0\n-1 5 -1\n0 -1 0"
                else:
                    def_k = "0 1 0\n1 -4 1\n0 1 0"
                ker_2d_txt = st.text_area("Kernel:", value=def_k)

            mode_2d = st.selectbox("Convolution Mode", ["same", "valid", "full"])
            if st.button("Run 2D Convolution", key="btn_conv2d"):
                try:
                    matrix_in = parse_matrix_input(mat_2d_txt)
                    kernel_in = parse_matrix_input(ker_2d_txt)
                    res_2d = MatrixEngine.convolve_2d(matrix_in, kernel_in, mode=mode_2d)
                    st.write(f"**Result ({res_2d.shape[0]}x{res_2d.shape[1]}):**")
                    st.dataframe(res_2d)
                except Exception as ex:
                    st.error(str(ex))


if __name__ == "__main__":
    render_ui()