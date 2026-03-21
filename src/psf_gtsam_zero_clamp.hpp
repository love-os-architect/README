#pragma once
#include <gtsam/nonlinear/NonlinearFactor.h>
#include <gtsam/linear/NoiseModel.h>
#include <Eigen/Dense>
#include "psf_zero_clamp.hpp"

namespace psf {

/** * M-Estimator for GTSAM: /0 Formulation 
 * Applies linear bounding to the scalar loss function after geometric projection.
 */
class ZeroClampMEstimator : public gtsam::noiseModel::mEstimator::Base {
    double tau_;
public:
    using shared_ptr = boost::shared_ptr<ZeroClampMEstimator>;
    explicit ZeroClampMEstimator(double tau) : tau_(tau) {}

    double weight(double error) const override {
        const double a = std::abs(error);
        if (!std::isfinite(a) || a < 1e-12) return 1.0;
        return (a <= tau_) ? 1.0 : (tau_ / a);
    }

    gtsam::Vector weights(const gtsam::Vector& errors) const override {
        gtsam::Vector w(errors.size());
        for (int i = 0; i < errors.size(); ++i) w(i) = weight(errors(i));
        return w;
    }

    double loss(double error) const override {
        const double a = std::abs(error);
        if (a <= tau_) return 0.5 * a * a;
        return tau_ * a - 0.5 * tau_ * tau_;
    }

    static shared_ptr Create(double tau) {
        return boost::make_shared<ZeroClampMEstimator>(tau);
    }
};

/**
 * Convenience wrapper for clamping geodesic residuals (e.g., SO(3) Logmap outputs)
 * before injecting them into the GTSAM factor graph.
 */
inline Eigen::VectorXd zeroClampGeodesic(const Eigen::VectorXd& r, double tau) {
    return zeroClampVector(r, tau);
}

} // namespace psf
