#pragma once

#include <ceres/ceres.h>
#include <gtsam/nonlinear/NonlinearFactor.h>
#include <gtsam/linear/NoiseModel.h>
#include <Eigen/Dense>
#include <cmath>

/**
 * Love-OS PSF-Zero /0 Projection for Nonlinear Optimization
 *
 * This module implements the core "Zero Clamp" mechanism that projects
 * potentially divergent residuals or errors onto a finite sphere,
 * embodying the principle: "Infinity is projected to the North Pole,
 * turning ego (divergence) into love (zero-dissipation stability)."
 */

namespace psf {

// ===============================================
// 1. ZeroClampLoss - Recommended LossFunction for Ceres
// ===============================================
/**
 * Ceres LossFunction that applies /0 projective saturation.
 * Softly bounds large residuals while preserving direction.
 */
class ZeroClampLoss final : public ceres::LossFunction {
public:
    explicit ZeroClampLoss(double tau) : tau_(std::max(tau, 1e-8)) {}

    void Evaluate(double s, double rho[3]) const override {
        // s = squared residual
        const double r = std::sqrt(std::max(s, 0.0));
        if (r < 1e-14) {
            rho[0] = rho[1] = rho[2] = 0.0;
            return;
        }

        // Projective clamp: r_clamped = tau * r / (tau + r)
        const double r_clamped = tau_ * r / (tau_ + r);
        const double s_clamped = r_clamped * r_clamped;

        rho[0] = s_clamped;                          // effective loss
        rho[1] = 2.0 * r_clamped * (r_clamped / r);  // first derivative w.r.t. s
        rho[2] = 0.0;                                // second derivative (approximated)
    }

private:
    const double tau_;
};

// ===============================================
// 2. ZeroClampCostWrapper - Strong vector projection for Ceres
// ===============================================
/**
 * CostFunction wrapper that applies full /0 geometric projection
 * to the entire residual vector and correctly updates Jacobians
 * using the chain rule.
 */
class ZeroClampCostWrapper final : public ceres::CostFunction {
public:
    explicit ZeroClampCostWrapper(ceres::CostFunction* inner,
                                  double tau,
                                  bool take_ownership = true)
        : inner_(inner),
          tau_(std::max(tau, 1e-8)),
          own_(take_ownership) {
        set_num_residuals(inner_->num_residuals());
        *mutable_parameter_block_sizes() = inner_->parameter_block_sizes();
    }

    ~ZeroClampCostWrapper() override {
        if (own_) delete inner_;
    }

    bool Evaluate(double const* const* parameters,
                  double* residuals,
                  double** jacobians) const override {

        if (!inner_->Evaluate(parameters, residuals, jacobians)) {
            return false;
        }

        const int n_res = num_residuals();
        Eigen::Map<Eigen::VectorXd> r(residuals, n_res);
        const double n = r.norm();

        if (!std::isfinite(n) || n < 1e-14 || n <= tau_) {
            return true;  // inside safe zone
        }

        // /0 Projective Clamp: r' = tau * r / ||r||
        const double alpha = tau_ / n;
        r *= alpha;

        // Jacobian correction via chain rule
        if (jacobians) {
            Eigen::MatrixXd I = Eigen::MatrixXd::Identity(n_res, n_res);
            Eigen::MatrixXd P = I - (r * r.transpose()) / (n * n);  // tangent projector

            const auto& block_sizes = parameter_block_sizes();
            for (size_t i = 0; i < block_sizes.size(); ++i) {
                if (jacobians[i]) {
                    Eigen::Map<Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>>
                        J(jacobians[i], n_res, block_sizes[i]);

                    J = alpha * P * J;
                }
            }
        }

        return true;
    }

private:
    ceres::CostFunction* inner_;
    const double tau_;
    const bool own_;
};

// ===============================================
// 3. ZeroClampMEstimator - Robust M-Estimator for GTSAM
// ===============================================
/**
 * GTSAM M-Estimator implementing /0 projective weighting.
 * Enables robust optimization under large geodesic or residual errors.
 */
class ZeroClampMEstimator : public gtsam::noiseModel::mEstimator::Base {
public:
    using shared_ptr = boost::shared_ptr<ZeroClampMEstimator>;

    explicit ZeroClampMEstimator(double tau = 1.0)
        : tau_(std::max(tau, 1e-8)) {}

    double weight(double error) const override {
        const double a = std::abs(error);
        if (a < 1e-12) return 1.0;
        return tau_ / (tau_ + a);               // /0 weighting
    }

    gtsam::Vector weights(const gtsam::Vector& errors) const override {
        gtsam::Vector w(errors.size());
        for (int i = 0; i < errors.size(); ++i) {
            w(i) = weight(errors(i));
        }
        return w;
    }

    double loss(double error) const override {
        const double a = std::abs(error);
        if (a < 1e-12) return 0.0;
        const double clamped = tau_ * a / (tau_ + a);
        return 0.5 * clamped * clamped;         // quadratic loss in projected space
    }

    static shared_ptr Create(double tau = 1.0) {
        return boost::make_shared<ZeroClampMEstimator>(tau);
    }

private:
    const double tau_;
};

/**
 * Convenience function for clamping geodesic residuals
 * (e.g., SO(3) Logmap, SE(3) pose errors).
 */
inline Eigen::VectorXd zeroClampGeodesic(const Eigen::VectorXd& residual, double tau = 1.0) {
    const double n = residual.norm();
    if (n < 1e-12) return residual;
    return (tau / n) * residual;   // strict projective clamp
}

} // namespace psf
