#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "psf_zero_eit/chaos_utils.hpp"
#include <deque>

using sensor_msgs::msg::PointCloud2;

struct LidarItem { PointCloud2::SharedPtr msg; rclcpp::Time due; rclcpp::Time orig_stamp; };

class ChaosInjectorLidar : public rclcpp::Node {
public:
  ChaosInjectorLidar() : Node("chaos_injector_lidar") {
    declare_parameter<std::string>("in_topic",  "/lidar/points");
    declare_parameter<std::string>("out_topic", "/chaos/lidar/points");
    prm_.delay_min_ms   = declare_parameter<double>("delay_min_ms",   -30.0);
    prm_.delay_max_ms   = declare_parameter<double>("delay_max_ms",   +50.0);
    prm_.jitter_sigma_ms= declare_parameter<double>("jitter_sigma_ms", 5.0);
    prm_.burst_prob     = declare_parameter<double>("burst_prob", 0.02);
    prm_.burst_delay_ms = declare_parameter<double>("burst_delay_ms", 120.0);
    prm_.drop_prob      = declare_parameter<double>("drop_prob", 0.01);
    prm_.dup_prob       = declare_parameter<double>("dup_prob", 0.005);
    prm_.reorder_window_ms = declare_parameter<double>("reorder_window_ms", 20.0);
    prm_.skew_ppm       = declare_parameter<double>("skew_ppm", 50.0);
    prm_.hold_publish   = declare_parameter<bool>("hold_publish", true);
    prm_.stamp_only     = declare_parameter<bool>("stamp_only", false);
    prm_.seed           = static_cast<uint32_t>(declare_parameter<int>("seed", 0));
    
    in_topic_  = get_parameter("in_topic").as_string();
    out_topic_ = get_parameter("out_topic").as_string();
    rng_ = std::make_unique<psf::ChaosRNG>(prm_.seed);

    sub_ = create_subscription<PointCloud2>(in_topic_, rclcpp::SensorDataQoS(),
      std::bind(&ChaosInjectorLidar::cb, this, std::placeholders::_1));
    pub_ = create_publisher<PointCloud2>(out_topic_, 10);

    timer_ = create_wall_timer(std::chrono::milliseconds(10), // 100Hzで十分
              std::bind(&ChaosInjectorLidar::drain, this));

    RCLCPP_WARN(get_logger(), "LiDAR chaos injector: %s -> %s", in_topic_.c_str(), out_topic_.c_str());
  }

private:
  psf::ChaosParams prm_;
  std::unique_ptr<psf::ChaosRNG> rng_;
  std::string in_topic_, out_topic_;
  rclcpp::Subscription<PointCloud2>::SharedPtr sub_;
  rclcpp::Publisher<PointCloud2>::SharedPtr pub_;
  rclcpp::TimerBase::SharedPtr timer_;
  std::deque<LidarItem> buf_;

  void cb(const PointCloud2::SharedPtr msg) {
    if (rng_->bernoulli(prm_.drop_prob)) return; // ドロップ

    double d_ms = rng_->uniform(prm_.delay_min_ms, prm_.delay_max_ms) 
                + rng_->normal(0.0, prm_.jitter_sigma_ms);
    if (rng_->bernoulli(prm_.burst_prob)) d_ms += prm_.burst_delay_ms;

    static double skew_acc = 0.0;
    skew_acc += (prm_.skew_ppm * 1e-6) * d_ms;
    double total_ms = d_ms + skew_acc;

    auto out = std::make_shared<PointCloud2>(*msg);
    rclcpp::Time orig_stamp = msg->header.stamp;
    
    // 
    rclcpp::Time new_stamp = rclcpp::Time((orig_stamp.nanoseconds() + static_cast<int64_t>(total_ms * 1e6)), RCL_ROS_TIME);
    out->header.stamp = new_stamp;

    // TODO

    if (prm_.stamp_only) {
      pub_->publish(*out);
      if (rng_->bernoulli(prm_.dup_prob)) pub_->publish(*out);
      return;
    }

    double hold_ms = std::max(0.0, total_ms);
    rclcpp::Time due = this->get_clock()->now() + rclcpp::Duration::from_nanoseconds(static_cast<int64_t>(hold_ms * 1e6));
    buf_.push_back({out, due, orig_stamp});
  }

  void drain() {
    if (buf_.empty()) return;
    rclcpp::Time now = this->get_clock()->now();

    for (auto it = buf_.begin(); it != buf_.end();) {
      if (it->due <= now) {
        pub_->publish(*(it->msg));
        if (rng_->bernoulli(prm_.dup_prob)) pub_->publish(*(it->msg));
        it = buf_.erase(it);
      } else {
        ++it;
      }
    }

    // 
    if (buf_.size() >= 2) {
      double span_ms = (buf_.back().due - buf_.front().due).seconds() * 1000.0;
      if (span_ms > 0.0 && span_ms <= prm_.reorder_window_ms && rng_->bernoulli(0.3)) {
        size_t i = static_cast<size_t>(std::floor(rng_->uniform(0, (double)buf_.size())));
        size_t j = static_cast<size_t>(std::floor(rng_->uniform(0, (double)buf_.size())));
        std::swap(buf_[i], buf_[j]);
      }
    }
  }
};

int main(int argc, char** argv){
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ChaosInjectorLidar>());
  rclcpp::shutdown();
  return 0;
}
