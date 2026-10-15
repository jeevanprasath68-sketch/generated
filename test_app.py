import pytest
import numpy as np
from app import MathEvaluator, EquationSolver, UnitConverter, MatrixEngine, parse_matrix_input


def test_math_evaluator_valid_and_precedence():
    val, exact = MathEvaluator.evaluate("3 + 5 * 2")
    assert val == 13.0
    assert exact == "13"

    val_trig, _ = MathEvaluator.evaluate("sqrt(16) + cos(0)")
    assert np.isclose(val_trig, 5.0)


def test_math_evaluator_invalid_expression():
    with pytest.raises(ValueError):
        MathEvaluator.evaluate("")
    with pytest.raises(ValueError):
        MathEvaluator.evaluate("import os; os.system('echo')")


def test_equation_solver_linear_and_quadratic():
    # Linear: 2*x + 4 = 10 -> x = 3
    roots = EquationSolver.solve_single("2*x + 4 = 10", "x")
    assert roots == ["3"]

    # Quadratic: x^2 - 4 = 0 -> [-2, 2]
    roots_quad = EquationSolver.solve_single("x^2 - 4 = 0", "x")
    assert set(roots_quad) == {"-2", "2"}


def test_equation_solver_system():
    eqs = ["x + y = 5", "x - y = 1"]
    sol = EquationSolver.solve_linear_system(eqs, ["x", "y"])
    assert sol == {"x": "3", "y": "2"}


def test_unit_converter_length_and_temperature():
    # Length: 1 km to meters
    res_m = UnitConverter.convert(1.0, "Length/Height", "km", "m")
    assert res_m == 1000.0

    # Area: 1 sq km to sq m
    res_area = UnitConverter.convert(1.0, "Area", "sq_km", "sq_m")
    assert res_area == 1_000_000.0

    # Temperature: 100 C to Fahrenheit
    res_f = UnitConverter.convert(100.0, "Temperature", "Celsius", "Fahrenheit")
    assert np.isclose(res_f, 212.0)

    # Invalid unit
    with pytest.raises(ValueError):
        UnitConverter.convert(10.0, "Length/Height", "invalid", "m")


def test_matrix_operations():
    a = np.array([[1.0, 2.0], [3.0, 4.0]])
    b = np.array([[2.0, 0.0], [1.0, 2.0]])

    # Multiplication
    mult = MatrixEngine.multiply(a, b)
    expected_mult = np.array([[4.0, 4.0], [10.0, 8.0]])
    np.testing.assert_allclose(mult, expected_mult)

    # Determinant and Inverse
    det = MatrixEngine.determinant(a)
    assert np.isclose(det, -2.0)
    inv = MatrixEngine.inverse(a)
    np.testing.assert_allclose(np.matmul(a, inv), np.eye(2), atol=1e-7)

    # Singular matrix inverse failure
    singular = np.array([[1.0, 2.0], [2.0, 4.0]])
    with pytest.raises(ValueError, match="singular"):
        MatrixEngine.inverse(singular)


def test_matrix_solve_system():
    # 2*x + y = 8, x + 3*y = 13 => x = 2.2, y = 3.6
    a = np.array([[2.0, 1.0], [1.0, 3.0]])
    b = np.array([8.0, 13.0])
    x = MatrixEngine.solve_linear(a, b)
    np.testing.assert_allclose(x, [2.2, 3.6])


def test_convolution_1d_and_2d():
    # 1D Convolution
    sig = np.array([1.0, 2.0, 3.0])
    ker = np.array([0.0, 1.0, 0.5])
    conv1d = MatrixEngine.convolve_1d(sig, ker, mode="full")
    # Expected: [0, 1, 2.5, 4, 1.5]
    np.testing.assert_allclose(conv1d, [0.0, 1.0, 2.5, 4.0, 1.5])

    # 2D Convolution (Identity impulse kernel)
    img = np.array([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0]
    ])
    identity_ker = np.array([
        [0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0]
    ])
    res_same = MatrixEngine.convolve_2d(img, identity_ker, mode="same")
    np.testing.assert_allclose(res_same, img)

    # 2D valid convolution
    box_ker = np.ones((2, 2))
    res_valid = MatrixEngine.convolve_2d(img, box_ker, mode="valid")
    # Top-left 2x2 sum: 1+2+4+5 = 12
    assert res_valid[0, 0] == 12.0
    assert res_valid.shape == (2, 2)


def test_parse_matrix_input():
    text = "1 2 3\n4 5 6"
    arr = parse_matrix_input(text)
    assert arr.shape == (2, 3)
    assert arr[1, 1] == 5.0

    # Inconsistent columns
    with pytest.raises(ValueError):
        parse_matrix_input("1 2\n3 4 5")