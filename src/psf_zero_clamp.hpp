#pragma once

#include <Eigen/Dense>
#include <cmath>

namespace psf {

/**
 * Love-OS PSF-Zero Geometric Vector Projection (/0 Gate)
 *
 * Projects any vector r onto a sphere of radius tau while preserving direction.
 * This implements the core "Infinity → North Pole" projection,
 * preventing divergent residuals from destabilizing the optimizer.
 *
 * Formula: r_clamped = tau * r / ||r||   (when ||r|| > tau)
 */
template <typename Derived>
inline Eigen::Matrix<typename Derived::Scalar, Derived::RowsAtCompileTime, 1>
zeroClampVector(const Eigen::MatrixBase<Derived>& r, 
                typename Derived::Scalar tau = 1.0) {
    
    using T = typename Derived::Scalar;
    const T n = r.norm();

    // Safe zone: return original vector
    if (!std::isfinite(n) || n <= T(1e-14) || n <= tau) {
        return r.derived();
    }

    // /0 Projective Clamp
    return (tau / n) * r.derived();
}

/**
 * Love-OS PSF-Zero Robust Scalar Loss Function
 *
 * Used primarily with Ceres Solver as a LossFunction.
 * Implements a smooth projective saturation that transitions from quadratic
 * to linear behavior, preventing large residuals from dominating the optimization.
 */
template <typename T>
inline void rhoZeroClamp(T s, T tau, T rho[3]) {
    // s = squared residual (standard Ceres convention)
    const T abs_r = std::sqrt(std::max(s, T(0.0)));

    if (abs_r <= T(1e-14)) {
        rho[0] = rho[1] = rho[2] = T(0.0);
        return;
    }

    if (abs_r <= tau) {
        // Quadratic region (normal least-squares behavior)
        rho[0] = T(0.5) * s;
        rho[1] = T(0.5);
        rho[2] = T(0.0);
    } else {
        // Projective linear tail: rho(r) = tau * |r| - 0.5 * tau^2
        const T clamped_r = tau * abs_r / (tau + abs_r);   // softer version for stability
        const T clamped_s = clamped_r * clamped_r;

        rho[0] = clamped_s;
        rho[1] = T(2.0) * clamped_r * (clamped_r / abs_r);   // d(rho)/ds
        rho[2] = T(0.0);                                     // second derivative (approx)
    }
}

/**
 * Convenience overload for direct vector clamping with custom tau
 */
template <typename Derived>
inline Eigen::Matrix<typename Derived::Scalar, Derived::RowsAtCompileTime, 1>
zeroClampVector(const Eigen::MatrixBase<Derived>& r, double tau) {
    return zeroClampVector(r, static_cast<typename Derived::Scalar>(tau));
}

} // namespace psf
