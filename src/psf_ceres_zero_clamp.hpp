#pragma once
#include <ceres/ceres.h>
#include <Eigen/Dense>
#include <cmath>

namespace psf {

// ===============================================
// 1. ZeroClampLoss (LossFunction) — 
// ===============================================
class ZeroClampLoss final : public ceres::LossFunction {
public:
    explicit ZeroClampLoss(double tau) : tau_(tau) {}

    void Evaluate(double s, double rho[3]) const override {
        // s = squared residual (Ceres標準)
        const double r = std::sqrt(std::max(s, 0.0));
        if (r < 1e-14) {
            rho[0] = 0.0; rho[1] = 0.0; rho[2] = 0.0;
            return;
        }

        // /0 Projective Clamp: r → tau * r / (tau + r)  (soft saturation)
        const double clamped_r = tau_ * r / (tau_ + r);
        const double clamped_s = clamped_r * clamped_r;

        rho[0] = clamped_s;                          // effective loss
        rho[1] = 2.0 * clamped_r * (clamped_r / r); // d(rho)/ds
        rho[2] = 0.0;                                // second derivative (approx)
    }

private:
    const double tau_;
};

// ===============================================
// 2. ZeroClampCostWrapper (Strong Vector Projection)
// ===============================================
class ZeroClampCostWrapper final : public ceres::CostFunction {
public:
    explicit ZeroClampCostWrapper(ceres::CostFunction* inner,
                                  double tau,
                                  bool take_ownership = true)
        : inner_(inner), tau_(tau), own_(take_ownership) {
        set_num_residuals(inner_->num_residuals());
        *mutable_parameter_block_sizes() = inner_->parameter_block_sizes();
    }

    ~ZeroClampCostWrapper() override {
        if (own_) delete inner_;
    }

    bool Evaluate(double const* const* parameters,
                  double* residuals,
                  double** jacobians) const override {

        if (!inner_->Evaluate(parameters, residuals, jacobians)) return false;

        const int n_res = num_residuals();
        Eigen::Map<Eigen::VectorXd> r(residuals, n_res);
        const double n = r.norm();

        if (!std::isfinite(n) || n <= 1e-14 || n <= tau_) {
            return true;  // safe zone → no projection
        }

        // /0 Geometric Projection: r' = tau * r / ||r||
        const double alpha = tau_ / n;
        r *= alpha;   // project residual vector

        // Jacobian correction via chain rule:
        // J_new = alpha * (I - r r^T / ||r||^2) * J_old
        if (jacobians) {
            const Eigen::MatrixXd I = Eigen::MatrixXd::Identity(n_res, n_res);
            const Eigen::MatrixXd P = I - (r * r.transpose()) / (n * n);  // tangent projection

            const auto& block_sizes = parameter_block_sizes();
            for (size_t i = 0; i < block_sizes.size(); ++i) {
                if (jacobians[i]) {
                    Eigen::Map<Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>>
                        J(jacobians[i], n_res, block_sizes[i]);

                    J = alpha * P * J;   // full chain rule
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

} // namespace psf
