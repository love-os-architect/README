#pragma once
#include <ceres/ceres.h>
#include <Eigen/Dense>
#include "psf_zero_clamp.hpp"

namespace psf {

class ZeroClampLoss final : public ceres::LossFunction {
public:
    explicit ZeroClampLoss(double tau) : tau_(tau) {}
    void Evaluate(double s, double rho[3]) const override {
        psf::rhoZeroClamp(s, tau_, rho); 
    }
private:
    double tau_;
};

/**
 * Wraps an existing Ceres CostFunction. 
 * Intercepts the computed residuals and Jacobians, applying the /0 geometric 
 * projection vector clamp and rigorously updating the Jacobians via the chain rule.
 */
class ZeroClampCostWrapper : public ceres::CostFunction {
public:
    explicit ZeroClampCostWrapper(ceres::CostFunction* inner, double tau, bool take_ownership=true)
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
        
        // 1. Evaluate the underlying cost function
        if (!inner_->Evaluate(parameters, residuals, jacobians)) return false;

        const int num_res = num_residuals();
        Eigen::Map<Eigen::VectorXd> r(residuals, num_res);
        double n = r.norm();

        // 2. If the residual is within the safe zone, do nothing.
        if (!std::isfinite(n) || n <= 1e-15 || n <= tau_) {
            return true;
        }

        // 3. /0 Geometric Projection Activation (R -> 0 Surrender)
        double alpha = tau_ / n;

        // 4. Rigorous Jacobian Projection Update (Chain Rule)
        // J_new = alpha * (I - (r * r^T) / ||r||^2) * J_old
        if (jacobians) {
            Eigen::MatrixXd I_minus_rr = Eigen::MatrixXd::Identity(num_res, num_res) 
                                       - (r * r.transpose()) / (n * n);
            
            const auto& block_sizes = parameter_block_sizes();
            for (size_t i = 0; i < block_sizes.size(); ++i) {
                if (jacobians[i]) {
                    Eigen::Map<Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>> 
                        J(jacobians[i], num_res, block_sizes[i]);
                    
                    // Apply the projection derivative to the Jacobian
                    J = alpha * I_minus_rr * J; 
                }
            }
        }

        // 5. Finally, project the residual vector itself
        r = alpha * r;

        return true;
    }

private:
    ceres::CostFunction* inner_;
    double tau_;
    bool own_;
};

} // namespace psf
