import pytest
import numpy as np
from app import BasicCalculator, MetricConverter, MatrixCalculator

def test_basic_calculator_arithmetic():
    assert BasicCalculator.calculate("2 + 3 * 4") == 14.0
    assert BasicCalculator.calculate("(10 - 2) / 4") == 2.0
    with pytest.raises(ValueError):
        BasicCalculator.calculate("")
    with pytest.raises(ValueError):
        BasicCalculator.calculate("2 + *")

def test_equation_solver():
    solutions = BasicCalculator.solve_equation("x**2 - 9 = 0", "x")
    assert sorted([float(s) for s in solutions]) == [-3.0, 3.0]
    
    linear_sol = BasicCalculator.solve_equation("3 * x = 12", "x")
    assert float(linear_sol[0]) == 4.0

def test_metric_converter():
    # Length conversion
    meters_to_km = MetricConverter.convert(1000, "meters", "kilometers", "Length")
    assert meters_to_km == 1.0

    # Volume conversion
    liters_to_ml = MetricConverter.convert(1.5, "liters", "milliliters", "Volume")
    assert liters_to_ml == 1500.0

    # Area conversion
    sqm_to_sqkm = MetricConverter.convert(1e6, "square meters", "square kilometers", "Area")
    assert sqm_to_sqkm == 1.0

    with pytest.raises(ValueError):
        MetricConverter.convert(10, "meters", "liters", "Length")
    with pytest.raises(ValueError):
        MetricConverter.convert(10, "meters", "kilometers", "InvalidCategory")

def test_matrix_parsing_and_operations():
    mat_str = "1, 2\n3, 4"
    parsed = MatrixCalculator.parse_matrix(mat_str)
    assert parsed.shape == (2, 2)
    assert np.allclose(parsed, np.array([[1.0, 2.0], [3.0, 4.0]]))

    mat_a = np.array([[1.0, 2.0], [3.0, 4.0]])
    mat_b = np.array([[2.0, 0.0], [1, 2]])

    # Addition
    added = MatrixCalculator.add(mat_a, mat_b)
    assert np.allclose(added, np.array([[3.0, 2.0], [4.0, 6.0]]))

    # Subtraction
    subbed = MatrixCalculator.subtract(mat_a, mat_b)
    assert np.allclose(subbed, np.array([[-1.0, 2.0], [2.0, 2.0]]))

    # Multiplication
    mult = MatrixCalculator.multiply(mat_a, mat_b)
    assert np.allclose(mult, np.array([[4.0, 4.0], [10.0, 8.0]]))

    # Determinant
    det = MatrixCalculator.determinant(mat_a)
    assert pytest.approx(det, 0.01) == -2.0

    # Inverse
    inv = MatrixCalculator.inverse(mat_a)
    expected_inv = np.array([[-2.0, 1.0], [1.5, -0.5]])
    assert np.allclose(inv, expected_inv)

    # Dimension error checks
    with pytest.raises(ValueError):
        MatrixCalculator.add(mat_a, np.array([[1.0]]))
    
    # Singular matrix inverse error check
    singular_mat = np.array([[1.0, 2.0], [2.0, 4.0]])
    with pytest.raises(ValueError):
        MatrixCalculator.inverse(singular_mat)

def test_convolution_solver():
    matrix = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    kernel = np.array([[1.0, 0.0], [0.0, -1.0]])
    
    conv_res = MatrixCalculator.convolve(matrix, kernel, mode='same')
    assert conv_res.shape == (3, 3)
    assert isinstance(conv_res, np.ndarray)