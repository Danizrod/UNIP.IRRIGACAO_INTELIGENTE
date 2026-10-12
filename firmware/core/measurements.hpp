#pragma once
#include <cmath>
#include <optional>
#include <string>

namespace irrigation {
struct RelativeSoilCalibration {
 std::string id;
 double dry_raw,wet_raw;
 std::optional<double> index(double raw)const{
  if(id.empty()||!std::isfinite(raw)||!std::isfinite(dry_raw)||!std::isfinite(wet_raw)||dry_raw==wet_raw)return {};
  double value=100*(raw-dry_raw)/(wet_raw-dry_raw);
  if(value<0||value>100)return {}; // Out-of-calibration range is not silently clipped.
  return value;
 }
};
struct SensorAdapter {virtual ~SensorAdapter()=default;virtual bool sample()=0;};
// Stabilized masses only; computes reservoir withdrawal, not guaranteed plant delivery.
inline std::optional<double> withdrawn_ml(double before_g,double after_g,double density_g_ml,bool stable){
 if(!stable||!std::isfinite(before_g)||!std::isfinite(after_g)||!std::isfinite(density_g_ml)||density_g_ml<=0||before_g<after_g||after_g<0)return {};
 return (before_g-after_g)/density_g_ml;
}
// Trapezoidal integration for the pump branch. A missing/invalid sample invalidates the cycle.
class PumpEnergy {
 double previous_w=0,previous_s=0,wh=0,max_gap;bool first=true,valid=true;
public:
 explicit PumpEnergy(double max_gap_s):max_gap(max_gap_s){if(!std::isfinite(max_gap)||max_gap<=0)valid=false;}
 bool add(double seconds,double voltage,double current){
  if(!valid||!std::isfinite(seconds)||!std::isfinite(voltage)||!std::isfinite(current)||voltage<0||current<0||(!first&&(seconds<=previous_s||seconds-previous_s>max_gap))){valid=false;return false;}
  double watts=voltage*current;if(!std::isfinite(watts)){valid=false;return false;}
  if(!first)wh+=(previous_w+watts)*0.5*(seconds-previous_s)/3600;
  first=false;previous_s=seconds;previous_w=watts;return true;
 }
 std::optional<double> result()const{return valid&&!first?std::optional<double>(wh):std::nullopt;}
};
}
