import streamlit as st
import numpy as np
from scipy import linalg
from scipy.signal import convolve2d
import sympy as sp
from typing import Union, List, Dict, Any, Tuple

# ==========================================
# BUSINESS LOGIC & ENGINES
# ==========================================

class BasicCalculator:
    @staticmethod
    def calculate(expression: str) -> Union[float, int]:
        """Safely evaluates a basic mathematical expression."""
        try:
            # Using sympy for safe evaluation
            cleaned = expression.strip()
            if not cleaned:
                raise ValueError("Expression cannot be empty.")
            result = sp.sympify(cleaned)
            if result.is_number:
                return float(result)
            return float(result.evalf())
        except Exception as e:
            raise ValueError(f"Invalid mathematical expression: {e}")

    @staticmethod
    def solve_equation(eq_str: str, var_str: str = 'x') -> List[Any]:
        """Solves an algebraic equation for a given variable."""
        try:
            parts = eq_str.split('=')
            if len(parts) == 2:
                lhs = sp.sympify(parts[0].strip())
                rhs = sp.sympify(parts[1].strip())
                equation = sp.Eq(lhs, rhs)
            else:
                equation = sp.sympify(eq_str)
            
            var = sp.Symbol(var_str)
            solutions = sp.solve(equation, var)
            return solutions
        except Exception as e:
            raise ValueError(f"Could not solve equation: {e}")


class MetricConverter:
    # Conversion factors relative to base unit (meters for length, liters for volume, square meters for area)
    LENGTH_CONVERSIONS = {
        'meters': 1.0,
        'kilometers': 1000.0,
        'centimeters': 0.01,
        'millimeters': 0.001,
        'miles': 1609.34,
        'yards': 0.9144,
        'feet': 0.3048,
        'inches': 0.0254
    }

    VOLUME_CONVERSIONS = {
        'liters': 1.0,
        'milliliters': 0.001,
        'cubic meters': 1000.0,
        'cubic centimeters': 0.001,
        'gallons (US)': 3.78541,
        'quarts (US)': 0.946353,
        'cups (US)': 0.24
    }

    AREA_CONVERSIONS = {
        'square meters': 1.0,
        'square kilometers': 1e6,
        'square miles': 2.58999e6,
        'acres': 4046.86,
        'hectares': 10000.0,
        'square feet': 0.092903,
        'square inches': 0.00064516
    }

    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str, category: str) -> float:
        if category == 'Length':
            table = cls.LENGTH_CONVERSIONS
        elif category == 'Volume':
            table = cls.VOLUME_CONVERSIONS
        elif category == 'Area':
            table = cls.AREA_CONVERSIONS
        else:
            raise ValueError(f"Unknown category: {category}")

        if from_unit not in table or to_unit not in table:
            raise ValueError("Invalid unit provided.")

        # Convert to base, then to target
        base_value = value * table[from_unit]
        converted_value = base_value / table[to_unit]
        return converted_value


class MatrixCalculator:
    @staticmethod
    def parse_matrix(matrix_str: str) -> np.ndarray:
        """Parses a comma/newline separated string into a numpy array."""
        try:
            lines = matrix_str.strip().split('\n')
            matrix_data = [[float(num.strip()) for num in line.split(',') if num.strip() != ''] for line in lines if line.strip() != '']
            if not matrix_data:
                raise ValueError("Empty matrix.")
            return np.array(matrix_data)
        except Exception as e:
            raise ValueError(f"Invalid matrix format. Use comma-separated values per row and newlines for rows: {e}")

    @staticmethod
    def add(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        if a.shape != b.shape:
            raise ValueError("Matrices must have the same dimensions for addition.")
        return a + b

    @staticmethod
    def subtract(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        if a.shape != b.shape:
            raise ValueError("Matrices must have the same dimensions for subtraction.")
        return a - b

    @staticmethod
    def multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.dot(a, b)

    @staticmethod
    def determinant(a: np.ndarray) -> float:
        if a.shape[0] != a.shape[1]:
            raise ValueError("Matrix must be square to calculate determinant.")
        return float(linalg.det(a))

    @staticmethod
    def inverse(a: np.ndarray) -> np.ndarray:
        if a.shape[0] != a.shape[1]:
            raise ValueError("Matrix must be square to calculate inverse.")
        try:
            return linalg.inv(a)
        except np.linalg.LinAlgError:
            raise ValueError("Matrix is singular and cannot be inverted.")

    @staticmethod
    def convolve(matrix: np.ndarray, kernel: np.ndarray, mode: str = 'same') -> np.ndarray:
        """Performs 2D convolution between a matrix and a kernel."""
        return convolve2d(matrix, kernel, mode=mode, boundary='fill', fillvalue=0)


# ==========================================
# STREAMLIT UI INTERFACE
# ==========================================

def main():
    st.set_page_config(page_title="Multi-Tool Advanced Calculator", page_icon="🧮", layout="wide")
    
    st.title("🧮 Multi-Tool Advanced Calculator Suite")
    st.markdown("A comprehensive computational tool for basic math, algebra, metric conversions, and matrix/convolution operations.")

    tabs = st.tabs(["Basic Math & Equations", "Metric Converter", "Matrix Operations", "2D Convolution"])

    # Tab 1: Basic Math & Equations
    with tabs[0]:
        st.header("Basic Arithmetic & Algebraic Solver")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Arithmetic Calculator")
            expr = st.text_input("Enter expression (e.g., (15 + 5) * 3 / 2):", "(15 + 5) * 3 / 2")
            if st.button("Calculate Expression"):
                try:
                    res = BasicCalculator.calculate(expr)
                    st.success(f"Result: **{res}**")
                except Exception as e:
                    st.error(str(e))

        with col2:
            st.subheader("Equation Solver")
            eq = st.text_input("Enter equation (e.g., 2*x + 5 = 15 or x**2 - 4 = 0):", "2*x + 5 = 15")
            var = st.text_input("Variable to solve for:", "x")
            if st.button("Solve Equation"):
                try:
                    sols = BasicCalculator.solve_equation(eq, var)
                    st.success(f"Solutions for {var}: **{sols}**")
                except Exception as e:
                    st.error(str(e))

    # Tab 2: Metric Converter
    with tabs[1]:
        st.header("Metric & Unit Converter")
        category = st.selectbox("Select Category", ["Length", "Volume", "Area"])
        
        if category == "Length":
            units = list(MetricConverter.LENGTH_CONVERSIONS.keys())
        elif category == "Volume":
            units = list(MetricConverter.VOLUME_CONVERSIONS.keys())
        else:
            units = list(MetricConverter.AREA_CONVERSIONS.keys())

        c1, c2, c3 = st.columns(3)
        with c1:
            val = st.number_input("Value to convert", value=1.0)
        with c2:
            from_u = st.selectbox("From Unit", units, index=0)
        with c3:
            to_u = st.selectbox("To Unit", units, index=min(1, len(units)-1))

        if st.button("Convert Units"):
            try:
                converted = MetricConverter.convert(val, from_u, to_u, category)
                st.metric(label=f"Converted to {to_u}", value=f"{converted:,.6f}")
            except Exception as e:
                st.error(str(e))

    # Tab 3: Matrix Operations
    with tabs[2]:
        st.header("Matrix Calculator")
        op = st.selectbox("Operation", ["Addition", "Subtraction", "Multiplication", "Determinant", "Inverse"])
        
        st.markdown("Enter matrix values separated by commas per row, and newlines for each row.")
        m_input_1 = st.text_area("Matrix A:", "1, 2\n3, 4")
        
        m_input_2 = ""
        if op in ["Addition", "Subtraction", "Multiplication"]:
            m_input_2 = st.text_area("Matrix B:", "5, 6\n7, 8")

        if st.button("Compute Matrix"):
            try:
                mat_a = MatrixCalculator.parse_matrix(m_input_1)
                if op in ["Addition", "Subtraction", "Multiplication"]:
                    mat_b = MatrixCalculator.parse_matrix(m_input_2)
                    if op == "Addition":
                        res_mat = MatrixCalculator.add(mat_a, mat_b)
                    elif op == "Subtraction":
                        res_mat = MatrixCalculator.subtract(mat_a, mat_b)
                    else:
                        res_mat = MatrixCalculator.multiply(mat_a, mat_b)
                    st.write("Resultant Matrix:")
                    st.code(str(res_mat))
                elif op == "Determinant":
                    det = MatrixCalculator.determinant(mat_a)
                    st.success(f"Determinant: **{det}**")
                elif op == "Inverse":
                    inv = MatrixCalculator.inverse(mat_a)
                    st.write("Inverse Matrix:")
                    st.code(str(inv))
            except Exception as e:
                st.error(str(e))

    # Tab 4: 2D Convolution
    with tabs[3]:
        st.header("2D Convolution Solver")
        st.markdown("Perform 2D convolution between an input matrix (e.g. image patch) and a convolution kernel/filter.")
        
        col_a, col_b = st.columns(2)
        with col_a:
            input_mat_str = st.text_area("Input Matrix", "1, 2, 3\n4, 5, 6\n7, 8, 9")
        with col_b:
            kernel_str = st.text_area("Kernel / Filter", "1, 0\n0, -1")

        conv_mode = st.selectbox("Convolution Mode", ["same", "valid", "full"])

        if st.button("Run Convolution"):
            try:
                matrix = MatrixCalculator.parse_matrix(input_mat_str)
                kernel = MatrixCalculator.parse_matrix(kernel_str)
                conv_result = MatrixCalculator.convolve(matrix, kernel, mode=conv_mode)
                st.write(f"Convolution Result ({conv_mode} mode):")
                st.code(str(conv_result))
            except Exception as e:
                st.error(str(e))


if __name__ == '__main__':
    main()