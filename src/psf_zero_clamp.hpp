#pragma once
#include <Eigen/Dense>
#include <algorithm>
#include <cmath>

namespace psf {

/** * Geometric Vector Projection (/0 Gate)
 * Projects a residual vector 'r' onto a sphere of radius 'tau' while preserving its direction.
 * This prevents outlier spikes from corrupting the optimizer's trajectory.
 */
template <class Derived>
inline Eigen::Matrix<typename Derived::Scalar, Derived::RowsAtCompileTime, 1>
zeroClampVector(const Eigen::MatrixBase<Derived>& r, typename Derived::Scalar tau) {
    using T = typename Derived::Scalar;
    const T n = r.norm();
    // If the vector is finite and within the radius, return as is.
    if (!std::isfinite(n) || n <= T(1e-15) || n <= tau) return r.derived();
    // Otherwise, project it onto the manifold boundary (R -> 0 surrender).
    return (tau / n) * r.derived();
}

/** * /0 Robust Scalar Loss (Huber-equivalent interface for Ceres) 
 * Computes the loss, its first, and second derivatives.
 */
template <typename T>
inline void rhoZeroClamp(T s, T tau, T rho[3]) {
    const T t2 = tau * tau;
    if (s <= t2) {
        rho[0] = T(0.5) * s;
        rho[1] = T(0.5);
        rho[2] = T(0.0);
    } else {
        const T r = std::sqrt(s);
        rho[0] = tau * r - T(0.5) * t2;                   // Linear tail
        rho[1] = (r > T(0)) ? (tau / (T(2) * r)) : T(0);  // First derivative
        rho[2] = (r > T(0)) ? (-tau / (T(4) * r * r * r)) : T(0); // Second derivative
    }
}

} // namespace psf
