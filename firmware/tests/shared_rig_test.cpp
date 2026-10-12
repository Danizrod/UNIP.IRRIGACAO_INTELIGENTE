#include "shared_rig.hpp"
#include <cassert>
#include <set>
#include <tuple>
using namespace irrigation;
struct JournalMock:Journal {
 std::set<std::string> ids;int64_t floor=0,last=0;
 bool observe_time(int64_t now)override{if(now<floor)return false;floor=now;return true;}
 bool contains(const std::string&id)override{return ids.count(id);}
 bool reserve(const std::string&id,int64_t)override{ids.insert(id);return true;}
 int64_t last_cycle_at()override{return last;}
 bool record_cycle_at(int64_t value)override{last=value;return true;}
};
struct DriverMock:ChannelDriver {
 int active=-1,starts=0;std::vector<size_t> order;
 void off_all()override{active=-1;}
 bool on(size_t channel)override{assert(active==-1);active=static_cast<int>(channel);++starts;order.push_back(channel);return true;}
};
int main(){
 JournalMock journal;DriverMock driver;std::vector<std::pair<size_t,Event>> events;
 std::array<UnitIdentity,3> units={UnitIdentity{"sim-pot-01","T1"},UnitIdentity{"sim-pot-02","T2"},UnitIdentity{"sim-pot-03","T3"}};
 Limits limits{true,50,10,30,60,20,5};int ids=0;
 auto emit=[&](size_t unit,const Event&e){events.push_back({unit,e});return true;};
 SharedRig rig(units,limits,journal,driver,[&](){return "local-"+std::to_string(++ids);},emit,20,2);
 assert(driver.active==-1&&rig.identity(2).treatment=="T3");
 std::array<Sensors,3> sensors;
 auto sample=[&](int64_t time,double removed,bool stable){for(auto&s:sensors){s={true,40,1000,removed,time,stable};}};
 sample(100,0,false);rig.connectivity(true);rig.tick(sensors,100);assert(!rig.synchronize(100));
 assert(!rig.submit(0,{"before-stable",100,110,10,5},sensors[0],100));assert(events.back().second.reason=="shared_mass_not_stable");
 sample(102,0,true);rig.tick(sensors,102);assert(rig.synchronize(102));assert(rig.submit(0,{"unit-0",102,120,10,5},sensors[0],102));assert(driver.active==0);
 assert(!rig.submit(1,{"unit-1-busy",102,120,10,5},sensors[1],102));assert(events.back().first==1&&events.back().second.reason=="shared_executor_busy");
 sample(103,10,false);rig.tick(sensors,103);assert(driver.active==-1&&rig.running());
 assert(!rig.synchronize(103));assert(!rig.submit(2,{"unit-2-settling",103,120,10,5},sensors[2],103));
 sample(105,10,true);rig.tick(sensors,105);assert(!rig.running());assert(events.back().first==0&&events.back().second.status=="completed");
 assert(!rig.submit(1,{"unit-1-interval",105,130,10,5},sensors[1],105));assert(events.back().second.reason=="global_minimum_interval");
 sample(123,10,true);assert(rig.submit(1,{"unit-1",123,140,10,5},sensors[1],123));assert(driver.active==1);rig.watchdog(124);assert(driver.active==-1&&!rig.running());
 assert(events.back().first==1&&events.back().second.status=="failed");
 // Local requests across all units are round-robin and never overlap a remote cycle.
 rig.connectivity(false);
 for(int cycle=0;cycle<3;++cycle){
  int64_t start=150+cycle*30;sample(start,20+cycle*50,true);for(auto&s:sensors)s.soil=20;
  rig.tick(sensors,start);assert(driver.active==cycle);assert(events.back().first==static_cast<size_t>(cycle)&&events.back().second.local);
  sample(start+1,70+cycle*50,false);for(auto&s:sensors)s.soil=20;rig.tick(sensors,start+1);assert(driver.active==-1&&rig.running());
  sample(start+3,70+cycle*50,true);for(auto&s:sensors)s.soil=20;rig.tick(sensors,start+3);assert(!rig.running());assert(events.back().first==static_cast<size_t>(cycle)&&events.back().second.status=="completed");
 }
 assert(driver.order==std::vector<size_t>({0,1,0,1,2}));
 // Unstable post-cycle mass fails without starting another channel.
 sample(250,170,true);rig.connectivity(true);rig.advance(250);assert(rig.synchronize(250));assert(rig.submit(2,{"unstable-end",250,270,10,5},sensors[2],250));
 sample(251,180,false);rig.tick(sensors,251);sample(257,180,false);rig.tick(sensors,257);assert(events.back().second.reason=="mass_stabilization_timeout"&&driver.active==-1);
}
