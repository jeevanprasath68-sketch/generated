"""
Universal Calculator & Metric Converter CLI Module

Provides robust engines for:
- Basic Arithmetic
- Equation Solving (Linear)
- Unit & Metric Conversion (Length, Volume, Area, Weight, Temperature)
- Matrix Operations & 2D Convolution
"""

import sys
import math
from typing import List, Union, Tuple

class ArithmeticCalculator:
    @staticmethod
    def add(a: float, b: float) -> float:
        return a + b

    @staticmethod
    def subtract(a: float, b: float) -> float:
        return a - b

    @staticmethod
    def multiply(a: float, b: float) -> float:
        return a * b

    @staticmethod
    def divide(a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Division by zero is not allowed.")
        return a / b

    @staticmethod
    def power(base: float, exp: float) -> float:
        return math.pow(base, exp)

    @staticmethod
    def sqrt(a: float) -> float:
        if a < 0:
            raise ValueError("Cannot compute square root of a negative number.")
        return math.sqrt(a)


class EquationSolver:
    @staticmethod
    def solve_linear(a: float, b: float) -> float:
        """Solves ax + b = 0 for x. Returns x."""
        if a == 0:
            if b == 0:
                raise ValueError("Infinite solutions (identity equation 0 = 0).")
            else:
                raise ValueError("No solution (contradiction a = 0, b != 0).")
        return -b / a


class UnitConverter:
    # Conversion factors relative to base unit (meters, square meters, cubic meters, kilograms, Celsius)
    LENGTH_FACTORS = {
        'mm': 0.001,
        'cm': 0.01,
        'm': 1.0,
        'km': 1000.0,
        'inch': 0.0254,
        'ft': 0.3048,
        'mile': 1609.344
    }

    AREA_FACTORS = {
        'sq_m': 1.0,
        'sq_cm': 0.0001,
        'sq_km': 1000000.0,
        'sq_ft': 0.092903,
        'acre': 4046.86,
        'hectare': 10000.0
    }

    VOLUME_FACTORS = {
        'm3': 1.0,
        'liter': 0.001,
        'ml': 0.000001,
        'gallon': 0.00378541,
        'cup': 0.00024
    }

    WEIGHT_FACTORS = {
        'g': 0.001,
        'kg': 1.0,
        'mg': 0.000001,
        'lb': 0.453592,
        'oz': 0.0283495
    }

    @classmethod
    def convert_length(cls, value: float, from_unit: str, to_unit: str) -> float:
        return cls._convert(value, from_unit, to_unit, cls.LENGTH_FACTORS, "length")

    @classmethod
    def convert_area(cls, value: float, from_unit: str, to_unit: str) -> float:
        return cls._convert(value, from_unit, to_unit, cls.AREA_FACTORS, "area")

    @classmethod
    def convert_volume(cls, value: float, from_unit: str, to_unit: str) -> float:
        return cls._convert(value, from_unit, to_unit, cls.VOLUME_FACTORS, "volume")

    @classmethod
    def convert_weight(cls, value: float, from_unit: str, to_unit: str) -> float:
        return cls._convert(value, from_unit, to_unit, cls.WEIGHT_FACTORS, "weight")

    @classmethod
    def convert_temperature(cls, value: float, from_unit: str, to_unit: str) -> float:
        fu = from_unit.lower()
        tu = to_unit.lower()
        valid = {'c', 'f', 'k'}
        if fu not in valid or tu not in valid:
            raise ValueError(f"Invalid temperature unit. Choose from {valid}")
        
        # Convert to Celsius first
        if fu == 'c':
            c = value
        elif fu == 'f':
            c = (value - 32) * 5.0 / 9.0
        elif fu == 'k':
            c = value - 273.15
        else:
            c = 0.0

        # Convert from Celsius to target
        if tu == 'c':
            return c
        elif tu == 'f':
            return c * 9.0 / 5.0 + 32
        elif tu == 'k':
            return c + 273.15
        return c

    @staticmethod
    def _convert(value: float, from_unit: str, to_unit: str, factors: dict, category: str) -> float:
        fu = from_unit.lower()
        tu = to_unit.lower()
        if fu not in factors or tu not in factors:
            raise ValueError(f"Invalid {category} unit. Valid units: {list(factors.keys())}")
        base_val = value * factors[fu]
        return base_val / factors[tu]


class MatrixCalculator:
    @staticmethod
    def add(mat_a: List[List[float]], mat_b: List[List[float]]) -> List[List[float]]:
        MatrixCalculator._validate_matrix(mat_a)
        MatrixCalculator._validate_matrix(mat_b)
        if len(mat_a) != len(mat_b) or len(mat_a[0]) != len(mat_b[0]):
            raise ValueError("Matrices must have the same dimensions for addition.")
        return [[mat_a[i][j] + mat_b[i][j] for j in range(len(mat_a[0]))] for i in range(len(mat_a))]

    @staticmethod
    def multiply(mat_a: List[List[float]], mat_b: List[List[float]]) -> List[List[float]]:
        MatrixCalculator._validate_matrix(mat_a)
        MatrixCalculator._validate_matrix(mat_b)
        rows_a, cols_a = len(mat_a), len(mat_a[0])
        rows_b, cols_b = len(mat_b), len(mat_b[0])

        if cols_a != rows_b:
            raise ValueError(f"Incompatible dimensions for multiplication: ({rows_a}x{cols_a}) and ({rows_b}x{cols_b}).")

        result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
        for i in range(rows_a):
            for j in range(cols_b):
                for k in range(cols_a):
                    result[i][j] += mat_a[i][k] * mat_b[k][j]
        return result

    @staticmethod
    def convolve2d(image: List[List[float]], kernel: List[List[float]]) -> List[List[float]]:
        """Performs 2D discrete convolution without padding (valid convolution)."""
        MatrixCalculator._validate_matrix(image)
        MatrixCalculator._validate_matrix(kernel)
        
        img_h, img_w = len(image), len(image[0])
        k_h, k_w = len(kernel), len(kernel[0])

        if k_h > img_h or k_w > img_w:
            raise ValueError("Kernel dimensions cannot be larger than image dimensions.")

        out_h = img_h - k_h + 1
        out_w = img_w - k_w + 1
        output = [[0.0 for _ in range(out_w)] for _ in range(out_h)]

        for i in range(out_h):
            for j in range(out_w):
                val = 0.0
                for ki in range(k_h):
                    for kj in range(k_w):
                        val += image[i + ki][j + kj] * kernel[k_h - 1 - ki][k_w - 1 - kj]
                output[i][j] = val
        return output

    @staticmethod
    def _validate_matrix(mat: List[List[float]]):
        if not mat or not mat[0]:
            raise ValueError("Matrix cannot be empty.")
        cols = len(mat[0])
        for row in mat:
            if len(row) != cols:
                raise ValueError("Matrix rows must all have the same length.")


def main():
    print("=== Python Universal Calculator Module ===")
    if len(sys.argv) < 2:
        print("Usage: python app.py [arithmetic|equation|convert|matrix] ...")
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == 'arithmetic':
        if len(sys.argv) < 5:
            print("Usage: python app.py arithmetic [add|sub|mul|div|pow] a b")
            sys.exit(1)
        op, a, b = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
        if op == 'add': res = ArithmeticCalculator.add(a, b)
        elif op == 'sub': res = ArithmeticCalculator.subtract(a, b)
        elif op == 'mul': res = ArithmeticCalculator.multiply(a, b)
        elif op == 'div': res = ArithmeticCalculator.divide(a, b)
        elif op == 'pow': res = ArithmeticCalculator.power(a, b)
        else: raise ValueError(f"Unknown op {op}")
        print(f"Result: {res}")

    elif mode == 'equation':
        if len(sys.argv) < 4:
            print("Usage: python app.py equation a b  (solves ax + b = 0)")
            sys.exit(1)
        a, b = float(sys.argv[2]), float(sys.argv[3])
        res = EquationSolver.solve_linear(a, b)
        print(f"Solution x = {res}")

    else:
        print(f"Mode {mode} not fully wired in quick CLI. Run pytest for comprehensive validation.")


if __name__ == '__main__':
    main()