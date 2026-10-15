"""
Comprehensive Pytest Test Suite for Universal Calculator & Metric Converter
"""

import pytest
from app import ArithmeticCalculator, EquationSolver, UnitConverter, MatrixCalculator

# --- Arithmetic Tests ---
def test_arithmetic_basic():
    assert ArithmeticCalculator.add(2, 3) == 5
    assert ArithmeticCalculator.subtract(5, 2) == 3
    assert ArithmeticCalculator.multiply(4, 3) == 12
    assert ArithmeticCalculator.divide(10, 2) == 5
    assert ArithmeticCalculator.power(2, 3) == 8
    assert ArithmeticCalculator.sqrt(9) == 3

def test_arithmetic_edge_cases():
    with pytest.raises(ValueError, match="Division by zero"):
        ArithmeticCalculator.divide(5, 0)

    with pytest.raises(ValueError, match="square root of a negative"):
        ArithmeticCalculator.sqrt(-4)


# --- Equation Solver Tests ---
def test_equation_solver_linear():
    # 2x + 4 = 0 -> x = -2
    assert EquationSolver.solve_linear(2, 4) == -2.0
    # -3x + 9 = 0 -> x = 3
    assert EquationSolver.solve_linear(-3, 9) == 3.0

def test_equation_solver_edge_cases():
    with pytest.raises(ValueError, match="Infinite solutions"):
        EquationSolver.solve_linear(0, 0)

    with pytest.raises(ValueError, match="No solution"):
        EquationSolver.solve_linear(0, 5)


# --- Unit Converter Tests ---
def test_unit_converter_length():
    assert UnitConverter.convert_length(1, 'm', 'cm') == 100.0
    assert UnitConverter.convert_length(1000, 'm', 'km') == 1.0

def test_unit_converter_temperature():
    assert UnitConverter.convert_temperature(0, 'c', 'f') == 32.0
    assert UnitConverter.convert_temperature(100, 'c', 'k') == 373.15
    assert UnitConverter.convert_temperature(32, 'f', 'c') == 0.0

def test_unit_converter_invalid():
    with pytest.raises(ValueError, match="Invalid length unit"):
        UnitConverter.convert_length(10, 'parsec', 'm')

    with pytest.raises(ValueError, match="Invalid temperature unit"):
        UnitConverter.convert_temperature(25, 'rankine', 'c')


# --- Matrix Calculator & Convolution Tests ---
def test_matrix_operations():
    mat_a = [[1, 2], [3, 4]]
    mat_b = [[5, 6], [7, 8]]
    
    added = MatrixCalculator.add(mat_a, mat_b)
    assert added == [[6, 8], [10, 12]]

    mult = MatrixCalculator.multiply(mat_a, mat_b)
    assert mult == [[19, 22], [43, 50]]

def test_matrix_convolution():
    image = [
        [1, 2, 3,
         4],
        [5, 6, 7,
         8],
        [9, 10, 11,
         12]
    ] # 3x4
    kernel = [
        [1, 0],
        [0, -1]
    ] # 2x2
    
    # Convolution should produce (3-2+1) x (4-2+1) = 2 x 3 matrix
    result = MatrixCalculator.convolve2d(image, kernel)
    assert len(result) == 2
    assert len(result[0]) == 3

def test_matrix_edge_cases():
    with pytest.raises(ValueError, match="same dimensions"):
        MatrixCalculator.add([[1, 2]], [[1, 2, 3]])

    with pytest.raises(ValueError, match="Incompatible dimensions"):
        MatrixCalculator.multiply([[1, 2]], [[1], [2], [3]])

    with pytest.raises(ValueError, match="Kernel dimensions cannot be larger"):
        MatrixCalculator.convolve2d([[1]], [[1, 2], [3, 4]])